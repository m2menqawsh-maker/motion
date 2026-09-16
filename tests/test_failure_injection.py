import pytest
import os
from scripts.security import safe_subprocess
import shutil
import json
from pathlib import Path

# Note: These tests require the pipeline scripts to be in place.
# We will use a dedicated test project.

PROJECT_ID = "test_failure_proj"

@pytest.fixture(scope="function")
def setup_test_project():
    proj_dir = Path("projects") / PROJECT_ID
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    proj_dir.mkdir(parents=True)
    
    # Create required files for passing phases where needed
    yield proj_dir
    
    # Cleanup
    if proj_dir.exists():
        shutil.rmtree(proj_dir)

def run_pipeline(env_vars: dict = None):
    cmd = ["python", "scripts/pipeline.py", PROJECT_ID]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    if env_vars:
        env.update(env_vars)
        
    result = safe_subprocess(cmd, env=env, capture_output=True, text=True)
    return result

def test_pipeline_normal_behavior_when_disabled(setup_test_project):
    # Injection disabled by default.
    # The pipeline will fail quickly at phase 1 because asset_gate.py requires valid data,
    # but we just want to ensure it doesn't crash or trigger injection logic.
    res = run_pipeline()
    assert "SECURITY_ERROR" not in res.stdout
    assert "Injected" not in res.stdout
    # Fails normally at asset gate or plan gate depending on state
    assert res.returncode == 1 or res.returncode == 0

def test_production_safeguard(setup_test_project):
    env = {
        "AGY_FAILURE_INJECTION_ENABLED": "1",
        "AGY_INJECT_FAILURE": "render_timeout",
        "AGY_ENV": "production"
    }
    res = run_pipeline(env)
    assert "SECURITY_ERROR" in res.stdout
    assert res.returncode == 1

def test_render_timeout_retry(setup_test_project):
    # Simulate we are at BLUEPRINT_READY so we can test render injection
    proj_dir = setup_test_project
    # Create fake files to pass earlier gates
    (proj_dir / "master_plan.md").write_text("plan")
    (proj_dir / "05_blueprint.json").write_text("{}")
    
    # Write a checkpoint so pipeline resumes at Render
    from scripts.checkpoint_model import CheckpointRecord, CheckpointStage, ValidationLevel
    from scripts.checkpoint_store import CheckpointStore
    
    refs = [
        CheckpointStore.create_artifact_record(proj_dir, "master_plan.md", ValidationLevel.SHA256),
        CheckpointStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256)
    ]
    record = CheckpointRecord(
        project_id=PROJECT_ID,
        run_id="test_run",
        checkpoint=CheckpointStage.BLUEPRINT_READY,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(proj_dir, record)
    
    env = {
        "AGY_FAILURE_INJECTION_ENABLED": "1",
        "AGY_INJECT_FAILURE": "render_timeout:first_attempt",
        "AGY_ENV": "test"
    }
    
    res = run_pipeline(env)
    
    assert "Injecting render_timeout at attempt 1" in res.stdout
    assert "إعادة محاولة render_project.py" in res.stdout
    
def test_pipeline_crash_before_plan_recovery(setup_test_project):
    proj_dir = setup_test_project
    # Ensure starting clean
    if (proj_dir / ".pipeline_checkpoint.json").exists():
        os.remove(proj_dir / ".pipeline_checkpoint.json")
        
    # We will simulate being at ASSETS_READY
    from scripts.checkpoint_model import CheckpointRecord, CheckpointStage
    from scripts.checkpoint_store import CheckpointStore
    record = CheckpointRecord(
        project_id=PROJECT_ID,
        run_id="test_run",
        checkpoint=CheckpointStage.ASSETS_READY,
        timestamp=0.0,
    )
    CheckpointStore.save(proj_dir, record)
    
    env = {
        "AGY_FAILURE_INJECTION_ENABLED": "1",
        "AGY_INJECT_FAILURE": "pipeline_crash_before_plan",
        "AGY_ENV": "test"
    }
    
    res = run_pipeline(env)
    
    assert "soft pipeline_crash_before_plan!" in res.stdout
    assert res.returncode == 1
    
    # Now run again without injection. It should recover!
    res2 = run_pipeline()
    assert "استئناف من نقطة الحفظ" in res2.stdout
    assert "ASSETS_READY" in res2.stdout

def test_checkpoint_missing_artifact_rejected(setup_test_project):
    proj_dir = setup_test_project
    
    # Write a checkpoint at RENDERED but do not create out.mp4
    from scripts.checkpoint_model import CheckpointRecord, CheckpointStage, ValidationLevel
    from scripts.checkpoint_store import CheckpointStore
    
    out_mp4 = proj_dir / "out.mp4"
    out_mp4.write_text("dummy video content")
    
    refs = [
        CheckpointStore.create_artifact_record(proj_dir, "out.mp4", ValidationLevel.SIZE)
    ]
    record = CheckpointRecord(
        project_id=PROJECT_ID,
        run_id="test_run",
        checkpoint=CheckpointStage.RENDERED,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(proj_dir, record)
    
    # Now delete out.mp4 to simulate missing artifact!
    out_mp4.unlink()
    
    res = run_pipeline()
    assert "الاستئناف مرفوض: Artifact missing: out.mp4" in res.stdout

def test_silent_failure_postcondition(setup_test_project):
    proj_dir = setup_test_project
    
    # We will simulate being at BLUEPRINT_READY
    from scripts.checkpoint_model import CheckpointRecord, CheckpointStage, ValidationLevel
    from scripts.checkpoint_store import CheckpointStore
    record = CheckpointRecord(
        project_id=PROJECT_ID,
        run_id="test_run",
        checkpoint=CheckpointStage.BLUEPRINT_READY,
        timestamp=0.0,
    )
    CheckpointStore.save(proj_dir, record)
    
    # Create a dummy script for render_project.py that returns 0 but does not create out.mp4
    original_script = Path("scripts/render_project.py").read_text() if Path("scripts/render_project.py").exists() else ""
    Path("scripts/render_project.py").write_text("print('Dummy script exit 0')")
    
    try:
        env = {
            "AGY_ENV": "test"
        }
        res = run_pipeline(env)
        
        # Process should fail because out.mp4 is missing despite exit code 0
        assert "Silent failure detected:" in res.stdout
        assert "was not created despite exit code 0" in res.stdout
    finally:
        # Restore original script
        Path("scripts/render_project.py").write_text(original_script)
