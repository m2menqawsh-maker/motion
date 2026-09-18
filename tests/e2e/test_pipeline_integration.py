import subprocess, json, shutil, pytest, asyncio
from pathlib import Path
from api.services.pipeline_service import PipelineService

"""
Classification: PARTIAL_INTEGRATION
This test verifies the gate state transitions through PipelineService.
It does NOT execute actual rendering, FFmpeg, or the Engine. True E2E coverage is deferred to Phase 9.13.
"""

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

@pytest.fixture(scope="module")
def project_setup():
    code, stdout, stderr = run(["python", "scripts/scaffold_project.py", "--name", "Test", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    project_dir = Path("projects") / project_id
    
    # Create required files for passing gates
    (project_dir / "assets/ready").mkdir(parents=True, exist_ok=True)
    
    bp = {
        "project_id": project_id,
        "version": "1.0",
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
    assert (project_dir / ".pipeline_state.json").exists()

def test_blueprint_passes_schema(project_setup):
    project_id, project_dir = project_setup
    code, _, _ = run(["python", "scripts/validate_schemas.py", str(project_dir)])
    assert code == 0

def test_stage_gate_allows_transitions(project_setup):
    project_id, project_dir = project_setup
    
    async def run_transitions():
        await PipelineService.start_stage(project_id, "asset_gate")
        await PipelineService.finish_stage(project_id, "asset_gate")
        await PipelineService.approve_gate(project_id, "asset_gate", approved_by="test_user")
        
        await PipelineService.start_stage(project_id, "plan_gate")
        await PipelineService.finish_stage(project_id, "plan_gate")
        await PipelineService.approve_gate(project_id, "plan_gate", approved_by="test_user")
        
        await PipelineService.start_stage(project_id, "taste_gate")
        await PipelineService.finish_stage(project_id, "taste_gate")
        await PipelineService.approve_gate(project_id, "taste_gate", approved_by="test_user")
        
        status = await PipelineService.get_status(project_id)
        assert status["status"] == "locked"
        assert status["current_stage"] == "taste_gate"
        
    asyncio.run(run_transitions())
