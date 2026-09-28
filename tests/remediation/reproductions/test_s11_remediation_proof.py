"""
Remediation Proof for S11:
Verifies that all defects identified in reproductions are strictly closed:
1. AssetGate fails closed on missing manifest.
2. Materializer halts before any side effects on duplicate asset IDs.
3. Materializer halts before any side effects on project ID mismatch.
4. API /projects/{id} returns manifest: null (not empty {}) when missing.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


def test_asset_gate_fails_closed_on_missing_manifest(tmp_path):
    """VERIFIED: asset_gate.py returns (False, ...) when manifest does not exist."""
    from scripts.gates.asset_gate import run_gate
    
    non_existent = tmp_path / "projects" / "prj_missing" / "02_asset_manifest.json"
    success, msg = run_gate(str(non_existent))
    
    assert success is False
    assert "Manifest validation error" in msg or "Manifest file not found" in msg


def test_materializer_halts_on_duplicate_asset_id(tmp_path):
    """VERIFIED: materialize_project.py fails before filesystem mutation when duplicate asset_ids exist."""
    workspace = Path.cwd()
    project_id = "test_dup_closed"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video1 = assets_ready / "dup_closed1.mp4"
    video2 = assets_ready / "dup_closed2.mp4"
    video1.write_text("vid1", encoding="utf-8")
    video2.write_text("vid2", encoding="utf-8")

    try:
        manifest = {
            "manifest_version": "2.0.0",
            "project_id": project_id,
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_duplicate",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video1.absolute())
                },
                {
                    "asset_id": "ast_duplicate",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video2.absolute())
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

        assert res.returncode != 0
        assert "DUPLICATE_ASSET_ID" in res.stdout
        # Zero side-effects: media_map.json must NOT exist!
        assert not (project_dir / "media_map.json").exists()
    finally:
        if video1.exists():
            video1.unlink()
        if video2.exists():
            video2.unlink()


def test_materializer_halts_on_project_id_mismatch(tmp_path):
    """VERIFIED: materialize_project.py fails before mutation when manifest.project_id mismatches directory."""
    workspace = Path.cwd()
    dir_project_id = "test_dir_proj2"
    manifest_project_id = "test_different_proj2"
    project_dir = tmp_path / "projects" / dir_project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video = assets_ready / "proj_mismatch2.mp4"
    video.write_text("vid", encoding="utf-8")

    try:
        manifest = {
            "manifest_version": "2.0.0",
            "project_id": manifest_project_id,  # MISMATCH!
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_mismatch_vid",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video.absolute())
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

        assert res.returncode != 0
        assert "Project identity mismatch" in res.stdout
        assert not (project_dir / "media_map.json").exists()
    finally:
        if video.exists():
            video.unlink()


def test_api_returns_none_not_empty_dict_on_missing_manifest(tmp_path):
    """VERIFIED: API /projects/{id} returns manifest=null, never failing open to empty {}."""
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app, headers={"X-Principal-ID": "test_admin", "X-Principal-Roles": "admin"})
    # Create project
    res = client.post("/projects/", json={"name": "ApiManifestCheck", "language": "ar"})
    assert res.status_code == 200
    project_id = res.json()["project_id"]

    # Delete 02_asset_manifest.json to simulate missing manifest
    manifest_path = Path("projects") / project_id / "02_asset_manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()

    try:
        res = client.get(f"/projects/{project_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["manifest"] is None, f"Expected manifest=None, got: {data['manifest']}"
    finally:
        # Cleanup project
        proj_dir = Path("projects") / project_id
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
