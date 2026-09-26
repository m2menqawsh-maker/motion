import pytest
import json
import subprocess
import sys
import shutil
from pathlib import Path

def test_asset_009_materializer_path_traversal(tmp_path):
    """
    Finding: ASSET-009
    Expected correct behavior: materialize_project.py must reject asset_id containing
    path traversal sequences ('..') and source paths outside the project workspace.
    Actual behavior on current main: canon() allows absolute paths, and aid is concatenated
    directly into pub_media / f"{aid}{src.suffix}", copying files outside intended boundary.
    """
    project_id = "repro-asset-009"
    proj_dir = Path.cwd() / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    outside_dir = tmp_path / "outside_attacker"
    outside_dir.mkdir(parents=True, exist_ok=True)
    secret_file = outside_dir / "secret.txt"
    secret_file.write_text("CONFIDENTIAL_DATA", encoding="utf-8")
    
    pub_projects = Path.cwd() / "remotion-app" / "public" / "projects" / project_id
    escaped_file = pub_projects / "traversal_escape.txt"
    
    try:
        manifest = {
            "project_id": project_id,
            "assets": [
                {
                    "asset_id": "../traversal_escape",
                    "type": "image",
                    "path": str(secret_file.resolve())
                }
            ]
        }
        (proj_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
        (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
        
        script_path = Path.cwd() / "scripts" / "generators" / "materialize_project.py"
        proc = subprocess.run(
            [sys.executable, str(script_path), str(proj_dir)],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        # Assertion proving the defect:
        # Correct behavior: materialize_project MUST reject traversal and NOT write outside pub_media
        # Current behavior on main: escaped_file was written outside media directory!
        assert not escaped_file.exists(), (
            f"DEFECT PROVEN (ASSET-009): materialize_project.py copied external file "
            f"and escaped media directory to: {escaped_file} (Return code: {proc.returncode})"
        )
    finally:
        # Clean up
        if escaped_file.exists():
            escaped_file.unlink()
        if pub_projects.exists():
            shutil.rmtree(pub_projects)
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
