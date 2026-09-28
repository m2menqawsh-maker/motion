"""
S13 Red Tests / Reproductions
Proving the defects on the current codebase:
- ASSET-003: Materialization leaves partial public media on failure.
- ASSET-010: Re-materialization leaves stale files in active published media.
- ASSET-004: move_asset / move_asset_status ignores from_status / expected_status.
- ASSET-007: Cache identity does not respect processing specification change or version.
- LED-036: materialize_project.py imports api.services and calls un-awaited async get_status().
"""

import json
import shutil
import subprocess
import sys
import importlib.util
from pathlib import Path
import pytest


def test_asset_003_materialization_partial_publish_on_failure(tmp_path):
    """
    ASSET-003: If materialization fails midway, existing published generation must NOT be modified.
    """
    workspace = Path.cwd()
    project_id = "prj_asset_003_red"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video1 = assets_ready / "s13_red_003_vid1.mp4"
    video2 = assets_ready / "s13_red_003_vid2.mp4"
    video1.write_text("new vid1 content", encoding="utf-8")
    video2.write_text("new vid2 content", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id
    gen_old_dir = pub_project / "generations" / "gen_initial_old"
    gen_old_dir.mkdir(parents=True, exist_ok=True)

    old_file = gen_old_dir / "old_generation.mp4"
    old_file.write_text("old generation content", encoding="utf-8")
    old_media_map_content = json.dumps({"old_gen": f"projects/{project_id}/generations/gen_initial_old/old_generation.mp4"})
    (project_dir / "media_map.json").write_text(old_media_map_content, encoding="utf-8")

    try:
        manifest = {
            "manifest_version": "2.0.0",
            "project_id": project_id,
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_valid_1",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video1.absolute())
                },
                {
                    "asset_id": "ast_failing_2",
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
                    "media_refs": ["ast_valid_1", "ast_failing_2"]
                }
            ]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        hook_script = tmp_path / "run_failing_materialize.py"
        hook_script.write_text(f"""
import sys, shutil
from pathlib import Path

orig_copy2 = shutil.copy2
def rigged_copy2(src, dst, **kwargs):
    if "ast_failing_2" in str(dst) or "ast_failing_2" in str(src):
        raise IOError("Injected disk failure copying ast_failing_2")
    return orig_copy2(src, dst, **kwargs)

shutil.copy2 = rigged_copy2

with open({repr(str(workspace / "scripts" / "generators" / "materialize_project.py"))}) as f:
    code = compile(f.read(), "materialize_project.py", "exec")
    sys.argv = ["materialize_project.py", {repr(str(project_dir))}]
    exec(code, {{"__name__": "__main__", "__file__": {repr(str(workspace / "scripts" / "generators" / "materialize_project.py"))}}})
""", encoding="utf-8")

        cmd = [sys.executable, str(hook_script)]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace))
        assert res.returncode != 0, "Materialize should have failed due to injected error"

        # ASSET-003 Check:
        assert old_file.exists() and old_file.read_text(encoding="utf-8") == "old generation content"
        media_map_data = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_valid_1" not in media_map_data, "media_map.json contains partial asset from failed run!"
        assert "old_gen" in media_map_data
    finally:
        if video1.exists():
            video1.unlink()
        if video2.exists():
            video2.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_asset_010_stale_files_remain_after_rematerialization(tmp_path):
    """
    ASSET-010: Re-materializing with a subset of assets must NOT leave stale files in active generation.
    """
    workspace = Path.cwd()
    project_id = "prj_asset_010_red"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video_a = assets_ready / "s13_vid_a.mp4"
    video_b = assets_ready / "s13_vid_b.mp4"
    video_a.write_text("content A", encoding="utf-8")
    video_b.write_text("content B", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id

    try:
        # Step 1: Manifest with A and B
        manifest_1 = {
            "manifest_version": "2.0.0",
            "project_id": project_id,
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_a",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video_a.absolute())
                },
                {
                    "asset_id": "ast_b",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video_b.absolute())
                }
            ]
        }
        (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest_1), encoding="utf-8")
        blueprint_1 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "template": "ShowcaseWrapper",
                    "startFrame": 0,
                    "durationFrames": 30,
                    "media_refs": ["ast_a", "ast_b"]
                }
            ]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint_1), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        cmd = [sys.executable, str(workspace / "scripts" / "generators" / "materialize_project.py"), str(project_dir)]
        res1 = subprocess.run(cmd, capture_output=True, text=True)
        assert res1.returncode == 0, f"Initial materialization failed: {res1.stderr}\n{res1.stdout}"

        map1 = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_a" in map1 and "ast_b" in map1
        assert (workspace / "remotion-app" / "public" / map1["ast_a"]).exists()
        assert (workspace / "remotion-app" / "public" / map1["ast_b"]).exists()

        # Step 2: Update manifest to ONLY contain A
        manifest_2 = {
            "manifest_version": "2.0.0",
            "project_id": project_id,
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_a",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    "processed_path": str(video_a.absolute())
                }
            ]
        }
        (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest_2), encoding="utf-8")
        blueprint_2 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "template": "ShowcaseWrapper",
                    "startFrame": 0,
                    "durationFrames": 30,
                    "media_refs": ["ast_a"]
                }
            ]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint_2), encoding="utf-8")

        res2 = subprocess.run(cmd, capture_output=True, text=True)
        assert res2.returncode == 0, f"Second materialization failed: {res2.stderr}\n{res2.stdout}"

        map2 = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_a" in map2
        assert "ast_b" not in map2

        # Active generation must only contain ast_a
        active_gen_path = map2["ast_a"]
        active_gen_dir = (workspace / "remotion-app" / "public" / active_gen_path).parent
        assert (active_gen_dir / "ast_a.mp4").exists()
        assert not (active_gen_dir / "ast_b.mp4").exists(), f"Defect ASSET-010: stale file ast_b.mp4 still exists in active generation {active_gen_dir}!"
    finally:
        if video_a.exists():
            video_a.unlink()
        if video_b.exists():
            video_b.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_asset_004_status_transition_without_expected_status_enforcement(tmp_path):
    """
    ASSET-004: move_asset_status in file_organizer.py rejects from_status mismatch.
    """
    organizer_path = Path(".agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/utils/file_organizer.py").resolve()
    spec = importlib.util.spec_from_file_location("file_organizer", organizer_path)
    file_organizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(file_organizer)

    mock_base = tmp_path / "mock_workspace"
    file_organizer.workspace_dir = str(mock_base)
    file_organizer.BASE_ASSET_DIR = mock_base / "assets"
    
    ready_img_dir = mock_base / "assets" / "ready" / "image"
    ready_img_dir.mkdir(parents=True, exist_ok=True)
    test_file = ready_img_dir / "photo.png"
    test_file.write_text("img content", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        file_organizer.move_asset_status(
            file_path=str(test_file.relative_to(mock_base)),
            from_status="incoming",
            to_status="processing",
            asset_type="image"
        )

    assert "mismatch" in str(exc_info.value).lower()
    assert test_file.exists()
    target_path = mock_base / "assets" / "processing" / "image" / "photo.png"
    assert not target_path.exists()


def test_asset_007_cache_identity_respects_spec_and_version():
    """
    ASSET-007: Cache identity must incorporate content hash, normalized processing spec hash,
    and processor version.
    """
    from scripts.core.asset_cache import (
        compute_cache_identity,
        compute_processing_spec_hash,
        normalize_processing_spec,
    )

    content_hash = "a" * 64
    spec_a = {"lufs": -16.0, "format": "wav", "channels": 2}
    spec_b = {"channels": 2, "format": "wav", "lufs": -16.0}
    spec_c = {"lufs": -24.0, "format": "wav", "channels": 2}
    
    norm_a = normalize_processing_spec(spec_a)
    norm_b = normalize_processing_spec(spec_b)
    assert norm_a == norm_b
    
    hash_spec_a = compute_processing_spec_hash(spec_a)
    hash_spec_b = compute_processing_spec_hash(spec_b)
    hash_spec_c = compute_processing_spec_hash(spec_c)
    assert hash_spec_a == hash_spec_b
    assert hash_spec_a != hash_spec_c

    key_v1 = compute_cache_identity(content_hash, hash_spec_a, processor_version="1.0.0")
    key_v2 = compute_cache_identity(content_hash, hash_spec_a, processor_version="2.0.0")
    assert key_v1 != key_v2

    diff_content_hash = "b" * 64
    key_diff_content = compute_cache_identity(diff_content_hash, hash_spec_a, processor_version="1.0.0")
    assert key_v1 != key_diff_content


def test_led_036_materializer_imports_pipeline_service():
    """
    LED-036: materialize_project.py must not import from api.services.
    """
    mat_file = Path("scripts/generators/materialize_project.py")
    content = mat_file.read_text(encoding="utf-8")
    assert "from api.services" not in content
    assert "PipelineService.get_status" not in content
