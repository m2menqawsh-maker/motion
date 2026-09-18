import pytest
import json
import shutil
from pathlib import Path
import subprocess
import sys

def test_materialize_asset_resolution(tmp_path):
    project_id = "test_asset_proj"
    workspace = Path.cwd()
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    # 1. Create a dummy asset
    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    dummy_video = assets_ready / "dummy_test_video.mp4"
    dummy_video.write_text("fake video data", encoding="utf-8")

    # 2. Create 02_asset_manifest.json with Logical Asset ID
    manifest = {
        "assets": [
            {
                "asset_id": "logical_video_1",
                "type": "video",
                "source": "generated",
                "path": str(dummy_video.absolute())
            }
        ]
    }
    (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # 3. Create 05_blueprint.json referencing Logical Asset ID
    blueprint = {
        "project_id": project_id,
        "version": "1.0",
                "scenes": [
            {
                "scene_id": "scene_1",
                "template": "ShowcaseWrapper",
                "startFrame": 0,
                "durationFrames": 30,
                "media_refs": ["logical_video_1"]
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

    # 4. Run materialize_project.py
    cmd = [sys.executable, str(workspace / "scripts" / "materialize_project.py"), str(project_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    print(res.stdout)
    assert res.returncode == 0, "materialize_project.py failed"

    # 5. Verify media_map.json determinism
    media_map_path = project_dir / "media_map.json"
    assert media_map_path.exists()
    media_map = json.loads(media_map_path.read_text(encoding="utf-8"))
    
    assert "logical_video_1" in media_map
    expected_path = f"projects/{project_id}/media/logical_video_1.mp4"
    assert media_map["logical_video_1"] == expected_path

    # 6. Verify valid materialized asset is readable by runtime
    pub_media = workspace / "remotion-app" / "public" / "projects" / project_id / "media" / "logical_video_1.mp4"
    assert pub_media.exists()
    assert pub_media.read_text(encoding="utf-8") == "fake video data"
    
    # Cleanup
    if pub_media.exists():
        pub_media.unlink()
    if dummy_video.exists():
        dummy_video.unlink()

def test_unknown_asset_id_fails_closed(tmp_path):
    project_id = "test_asset_proj_fail"
    workspace = Path.cwd()
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    manifest = {"assets": []}
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
                "media_refs": ["unknown_asset_id"] # Unknown asset ID!
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

    cmd = [sys.executable, str(workspace / "scripts" / "materialize_project.py"), str(project_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    assert res.returncode != 0
    assert "عنصر يشير لأصل غير مهيأ: unknown_asset_id" in res.stdout

def test_missing_materialized_asset_fails(tmp_path):
    project_id = "test_asset_proj_missing"
    workspace = Path.cwd()
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    manifest = {
        "assets": [
            {
                "asset_id": "logical_video_1",
                "type": "video",
                "source": "generated",
                "path": str(workspace / "assets" / "ready" / "DOES_NOT_EXIST.mp4")
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
                "media_refs": ["logical_video_1"]
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

    cmd = [sys.executable, str(workspace / "scripts" / "materialize_project.py"), str(project_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    assert res.returncode != 0
    assert "missing" in res.stdout or "غير موجود" in res.stdout

def test_developer_path_fails(tmp_path):
    project_id = "test_asset_proj_path"
    workspace = Path.cwd()
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    manifest = {"assets": []}
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
                "media_refs": ["C:/video/clean-video-workspace/assets/ready/developer_video.mp4"]
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

    cmd = [sys.executable, str(workspace / "scripts" / "materialize_project.py"), str(project_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    assert res.returncode != 0
    assert "عنصر يشير لأصل غير مهيأ" in res.stdout

