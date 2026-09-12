import subprocess, json, shutil, pytest
from pathlib import Path

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def test_scaffold_creates_project():
    code, stdout, stderr = run(["python", "scripts/scaffold_project.py", "--name", "Test", "--aspect", "9:16", "--fps", "30", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    assert (Path("projects") / project_id / "project.json").exists()

def test_blueprint_passes_schema():
    code, _, _ = run(["python", "scripts/validate_schemas.py", "projects/demo_brand"])
    assert code == 0

def test_stage_gate_allows_transitions():
    code, stdout, stderr = run(["python", "scripts/scaffold_project.py", "--name", "Gate Test", "--aspect", "9:16", "--fps", "30", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    project_dir = Path("projects") / project_id
    
    shutil.copytree("projects/demo_brand/assets/ready", project_dir / "assets/ready", dirs_exist_ok=True)
    shutil.copy("projects/demo_brand/blueprint.json", project_dir / "blueprint.json")
    shutil.copy("projects/demo_brand/manifest.json", project_dir / "manifest.json")
    shutil.copy("projects/demo_brand/04_timings.json", project_dir / "04_timings.json")
    
    commands = [
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "0"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "0"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "1", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "1"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "1"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "2", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "2"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "2"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "3", "test"],
        ["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "3"]
    ]
    for cmd in commands:
        code, stdout, stderr = run(cmd)
        assert code == 0, f"Command failed: {' '.join(cmd)}\n{stderr}"

def test_render_produces_mp4():
    import sys
    project_dir = Path("projects/demo_brand")
    out_path = Path("out/demo_brand_test.mp4")
    if out_path.exists():
        out_path.unlink()
        
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    code, stdout, stderr = run([npx_cmd, "tsx", "scripts/dev_render_blueprint.ts", str(project_dir), str(out_path)])
    assert code == 0, f"Render failed: {stderr}"
    assert out_path.exists()
    assert out_path.stat().st_size > 0

def test_master_plan_generated():
    project_dir = Path("projects/demo_brand")
    code, stdout, stderr = run(["python", "scripts/gates/plan_report.py", str(project_dir)])
    assert code == 0, f"Plan generation failed: {stderr}"
    assert (project_dir / "master_plan.md").exists()
