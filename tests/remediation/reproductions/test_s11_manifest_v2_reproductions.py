"""
Reproduction tests for S11 defects on current main.
Proves the existing architectural flaws before implementing the fixes:
1. AssetGate fails open when manifest is missing.
2. Materializer silently accepts duplicate asset IDs (last one wins).
3. Materializer ignores project_id mismatch between manifest and project directory.
4. Manifest contract split: schemas/manifest.schema.json rejects source="user_upload" which asset_gate expects.
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest
from jsonschema import validate, ValidationError


def test_repro_asset_gate_fails_open_on_missing_manifest(tmp_path):
    """
    DEFECT: asset_gate.py returns (True, 'No manifest found, passing.') when manifest does not exist,
    violating Fail-Closed principle.
    """
    from scripts.gates.asset_gate import run_gate
    
    non_existent = tmp_path / "projects" / "prj_missing" / "02_asset_manifest.json"
    success, msg = run_gate(str(non_existent))
    
    # Current behavior on main: True, 'No manifest found, passing.'
    # Target behavior after S11: Must fail closed!
    assert success is True
    assert "No manifest found" in msg


def test_repro_materializer_duplicate_asset_id_last_one_wins(tmp_path):
    """
    DEFECT: materialize_project.py does not validate duplicate asset IDs,
    silently letting the last duplicate overwrite the earlier ones in media_map.
    """
    workspace = Path.cwd()
    project_id = "test_dup_asset"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video1 = assets_ready / "dup_vid1.mp4"
    video2 = assets_ready / "dup_vid2.mp4"
    video1.write_text("vid1", encoding="utf-8")
    video2.write_text("vid2", encoding="utf-8")

    try:
        # Duplicate asset_id "ast_duplicate" with two different paths
        manifest = {
            "project_id": project_id,
            "assets": [
                {
                    "asset_id": "ast_duplicate",
                    "type": "video",
                    "source": "ready",
                    "path": str(video1.absolute())
                },
                {
                    "asset_id": "ast_duplicate",
                    "type": "video",
                    "source": "ready",
                    "path": str(video2.absolute())
                }
            ]
        }
        (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        blueprint = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "template": "ShowcaseWrapper",
                    "startFrame": 0,
                    "durationFrames": 30,
                    "media_refs": ["ast_duplicate"]
                }
            ]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        cmd = [sys.executable, str(workspace / "scripts" / "generators" / "materialize_project.py"), str(project_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)

        # On current main, materialize_project succeeds (exit code 0) and last one overwrote first one
        assert res.returncode == 0, f"Expected repro to succeed on main, got: {res.stderr}"
        media_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_duplicate" in media_map
    finally:
        if video1.exists():
            video1.unlink()
        if video2.exists():
            video2.unlink()
        pub_file = workspace / "remotion-app" / "public" / "projects" / project_id / "media" / "ast_duplicate.mp4"
        if pub_file.exists():
            pub_file.unlink()


def test_repro_materializer_project_id_mismatch_ignored(tmp_path):
    """
    DEFECT: materialize_project.py does not verify that manifest.project_id matches
    the project directory ID, accepting mismatched identities.
    """
    workspace = Path.cwd()
    dir_project_id = "test_dir_proj"
    manifest_project_id = "test_different_proj"
    project_dir = tmp_path / "projects" / dir_project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video = assets_ready / "proj_mismatch.mp4"
    video.write_text("vid", encoding="utf-8")

    try:
        manifest = {
            "project_id": manifest_project_id,  # MISMATCH!
            "assets": [
                {
                    "asset_id": "ast_mismatch_vid",
                    "type": "video",
                    "source": "ready",
                    "path": str(video.absolute())
                }
            ]
        }
        (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        blueprint = {
            "project_id": dir_project_id,
            "version": "1.0",
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "template": "ShowcaseWrapper",
                    "startFrame": 0,
                    "durationFrames": 30,
                    "media_refs": ["ast_mismatch_vid"]
                }
            ]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        cmd = [sys.executable, str(workspace / "scripts" / "generators" / "materialize_project.py"), str(project_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)

        # On current main, this succeeds and ignores the mismatch!
        assert res.returncode == 0, f"Expected repro to succeed on main, got: {res.stderr}"
    finally:
        if video.exists():
            video.unlink()
        pub_file = workspace / "remotion-app" / "public" / "projects" / dir_project_id / "media" / "ast_mismatch_vid.mp4"
        if pub_file.exists():
            pub_file.unlink()


def test_repro_manifest_schema_contract_split():
    """
    DEFECT: schemas/manifest.schema.json specifies source enum as [incoming, cache, ready],
    while asset_gate.py line 46-49 checks for source == 'user_upload' or 'mcp_fetch'.
    A manifest formatted for asset_gate fails schema validation.
    """
    schema_path = Path("schemas/manifest.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Manifest conforming to asset_gate.py expectations
    asset_gate_manifest = {
        "project_id": "prj_demo",
        "generated_at": "2026-09-28T12:00:00Z",
        "assets": [
            {
                "asset_id": "ast_sample",
                "type": "video",
                "path": "assets/ready/sample.mp4",
                "source": "user_upload",  # Expected by asset_gate.py, but rejected by manifest.schema.json!
                "approved": True
            }
        ]
    }

    # Proves schema rejects it!
    with pytest.raises(ValidationError) as exc_info:
        validate(instance=asset_gate_manifest, schema=schema)
    
    assert "'user_upload' is not one of ['incoming', 'cache', 'ready']" in str(exc_info.value)
