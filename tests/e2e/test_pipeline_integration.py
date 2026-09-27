import sys
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
    code, stdout, stderr = run([sys.executable, "scripts/scaffold_project.py", "--name", "Test", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    project_dir = Path("projects") / project_id
    
    # Create required files for passing gates
    (project_dir / "assets/ready").mkdir(parents=True, exist_ok=True)
    
    bp = {
        "project_id": project_id,
        "version": "1.0",
        "fps": 30,
        "aspect_ratio": "16:9",
        "meta": {"motion_personality": "Cinematic"},
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
    code, _, _ = run([sys.executable, "scripts/validators/validate_schemas.py", str(project_dir)])
    assert code == 0

def test_stage_gate_allows_transitions(project_setup):
    project_id, project_dir = project_setup
    from scripts.core.lifecycle_service import LifecycleService, LifecyclePreconditionFailedError
    from scripts.core.state_model import LifecycleState, ValidationLevel
    from scripts.core.state_store import StateStore
    
    async def run_transitions():
        # Prepare target project directory for service
        target_dir = PipelineService._get_project_dir(project_id)
        if target_dir != project_dir:
            for f in ["05_blueprint.json", "04_timings.json"]:
                if (project_dir / f).exists():
                    (target_dir / f).write_text((project_dir / f).read_text(encoding="utf-8"), encoding="utf-8")
            StateStore.create(target_dir, project_id)

        # 1. Direct unverified finish_stage MUST be rejected (LED-077 fix)
        with pytest.raises(LifecyclePreconditionFailedError):
            await PipelineService.finish_stage(project_id, "asset_gate")
        
        # 2. Legitimate transitions require evidence through LifecycleService

        (target_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
        LifecycleService.transition(
            target_dir,
            LifecycleState.ASSETS_READY,
            artifacts=[("02_asset_manifest.json", ValidationLevel.EXISTS)]
        )
        
        (target_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
        LifecycleService.transition(
            target_dir,
            LifecycleState.PLAN_READY,
            artifacts=[("master_plan.md", ValidationLevel.SHA256)]
        )
        
        LifecycleService.transition(
            target_dir,
            LifecycleState.BLUEPRINT_READY,
            artifacts=[("05_blueprint.json", ValidationLevel.SHA256)]
        )
        
        status = await PipelineService.get_status(project_id)
        assert status["current_stage"] == "qc_gate"
        assert status["status"] == "started"
        
    asyncio.run(run_transitions())
