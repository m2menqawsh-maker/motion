import os
import subprocess
import json
import re
import pytest
from pathlib import Path

@pytest.fixture
def run_scaffold():
    cmd = [
        "python", "scripts/scaffold_project.py",
        "--name", "Test Project",
        "--aspect", "9:16",
        "--fps", "30",
        "--language", "ar"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, f"Scaffold failed: {result.stderr}"
    project_id = result.stdout.strip()
    project_dir = Path(f"projects/{project_id}")
    yield project_id, project_dir
    # Cleanup (optional but good practice)
    # import shutil
    # shutil.rmtree(project_dir)

def test_directories_created(run_scaffold):
    project_id, project_dir = run_scaffold
    assert (project_dir / "assets/incoming").is_dir()
    assert (project_dir / "assets/cache").is_dir()
    assert (project_dir / "assets/ready").is_dir()
    assert (project_dir / "06_build").is_dir()
    assert (project_dir / ".studio_approved").exists()

def test_project_id_matches_pattern(run_scaffold):
    project_id, _ = run_scaffold
    assert re.match(r"^prj_[a-z0-9]{8}$", project_id)

def test_project_json_schema(run_scaffold):
    project_id, project_dir = run_scaffold
    cmd = ["python", "scripts/validate_schemas.py", str(project_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert "✅ project.json         — سليم" in result.stdout

def test_state_json_schema(run_scaffold):
    project_id, project_dir = run_scaffold
    cmd = ["python", "scripts/validate_schemas.py", str(project_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert "✅ state.json           — سليم" in result.stdout

def test_brand_json_schema(run_scaffold):
    project_id, project_dir = run_scaffold
    cmd = ["python", "scripts/validate_schemas.py", str(project_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert "✅ brand.json           — سليم" in result.stdout
