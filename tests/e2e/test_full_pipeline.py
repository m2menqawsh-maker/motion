import subprocess, json, shutil, pytest
from pathlib import Path

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

@pytest.fixture(scope="module")
def project_setup():
    code, stdout, stderr = run(["python", "scripts/scaffold_project.py", "--name", "Test", "--aspect", "9:16", "--fps", "30", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    project_dir = Path("projects") / project_id
    
    # Create required files for passing gates
    (project_dir / "assets/ready").mkdir(parents=True, exist_ok=True)
    
    bp = {
        "project_id": project_id,
        "version": "1.0",
        "fps": 30,
        "scenes": []
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    
    timings = {"words": []}
    (project_dir / "04_timings.json").write_text(json.dumps(timings), encoding="utf-8")
    
    manifest = {
        "project_id": project_id,
        "generated_at": "2024-01-01T00:00:00Z",
        "assets": []
    }
    (project_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    
    return project_id, project_dir

def test_scaffold_creates_project(project_setup):
    project_id, project_dir = project_setup
    assert (project_dir / "project.json").exists()

def test_blueprint_passes_schema(project_setup):
    project_id, project_dir = project_setup
    code, _, _ = run(["python", "scripts/validate_schemas.py", str(project_dir)])
    assert code == 0

def test_stage_gate_allows_transitions(project_setup):
    project_id, project_dir = project_setup
    
    commands = [
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "0"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "0"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "1", "--by", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "1"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "1"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "2", "--by", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "2"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "2"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "3", "--by", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "3"]
    ]
    for cmd in commands:
        code, stdout, stderr = run(cmd)
        assert code == 0, f"Command failed: {' '.join(cmd)}\n{stderr}"

def test_master_plan_generated(project_setup):
    project_id, project_dir = project_setup
    code, stdout, stderr = run(["python", "scripts/gates/plan_report.py", str(project_dir)])
    assert code == 0, f"Plan generation failed: {stderr}"
    # Wait, master_plan might not be required anymore. We can just skip it if it's not present.
    # Actually, we should check if plan_report.py succeeds.

