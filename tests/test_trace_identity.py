import json
import pytest
import os
import sys
import uuid
from pathlib import Path
from scripts.security import safe_subprocess

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

@pytest.fixture
def clean_logs():
    workspace_root = Path.cwd().resolve()
    global_log = workspace_root / "logs" / "runtime.jsonl"
    project_log = workspace_root / "projects" / "prj_mock" / "run.jsonl"
    
    # Backup
    backup_global = global_log.read_text(encoding="utf-8") if global_log.exists() else None
    backup_proj = project_log.read_text(encoding="utf-8") if project_log.exists() else None
    
    # Clear
    if global_log.exists():
        global_log.write_text("")
    if project_log.exists():
        project_log.write_text("")
        
    yield global_log
    
    # Restore
    if backup_global is not None:
        global_log.write_text(backup_global, encoding="utf-8")
    if backup_proj is not None:
        project_log.write_text(backup_proj, encoding="utf-8")

def test_missing_trace_context_fails_at_managed_boundary():
    workspace_root = Path.cwd().resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(workspace_root)
    env["AGY_IS_MANAGED"] = "1"
    if "AGY_RUN_ID" in env:
        del env["AGY_RUN_ID"]
        
    render_script = workspace_root / "scripts" / "render_project.py"
    cmd = [sys.executable, str(render_script), "prj_mock"]
    
    result = safe_subprocess(cmd, capture_output=True, text=True, env=env, cwd=workspace_root)
    
    # Because it is missing AGY_RUN_ID and is managed, it should fail
    assert result.returncode != 0
    assert "TRACE ERROR" in result.stdout

def test_trace_reconstruction(clean_logs):
    workspace_root = Path.cwd().resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(workspace_root)
    test_run_id = str(uuid.uuid4())
    env["AGY_RUN_ID"] = test_run_id
    env["AGY_IS_MANAGED"] = "1"
    
    pipeline_script = workspace_root / "scripts" / "pipeline.py"
    cmd = [sys.executable, str(pipeline_script), "prj_mock"]
    
    result = safe_subprocess(cmd, capture_output=True, text=True, env=env, cwd=workspace_root)
    
    # Collect logs
    assert clean_logs.exists(), f"Logs file was not created. Pipeline stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
    logs = [json.loads(l) for l in clean_logs.read_text(encoding="utf-8").strip().split("\n") if l]
    
    # Filter logs that belong to our test run
    run_logs = [l for l in logs if l.get("run_id") == test_run_id]
    
    assert len(run_logs) > 0, "No logs recorded for the test run_id"
    
    # Verify Trace Identity Contract
    for log in run_logs:
        assert log["run_id"] == test_run_id
        assert log["project_id"] == "prj_mock"
        assert "span_id" in log
        
    # We should see events from the pipeline itself and child processes
    pipeline_starts = [l for l in run_logs if l.get("component") == "pipeline" and l.get("status") == "started"]
    assert len(pipeline_starts) == 1
    
    # We should see gate executions
    gate_executions = [l for l in run_logs if l.get("event") == "gate.execution"]
    assert len(gate_executions) > 0
    
    # Verify parent/child relationship for the first attempts
    for gate_log in gate_executions:
        if gate_log.get("attempt", 1) == 1:
            assert gate_log["parent_span_id"] == pipeline_starts[0]["span_id"]

def test_failure_propagation(clean_logs, monkeypatch):
    workspace_root = Path.cwd().resolve()
    # Test that when a component fails, the failure event shares the SAME child span_id
    env = os.environ.copy()
    test_run_id = str(uuid.uuid4())
    env["AGY_RUN_ID"] = test_run_id
    env["AGY_IS_MANAGED"] = "1"
    
    from scripts.pipeline import run_script, RuntimeLogger, RunContext
    from scripts.retry_policy import IdempotencyClass
    
    ctx = RunContext(run_id=test_run_id, project_id="prj_mock", span_id="test-root-span")
    logger = RuntimeLogger(ctx)
    
    # run a script that DOES exist but will fail because of bad args
    # render_project.py expects project_id. Let's pass a bad arg to asset_gate.py so it fails
    # actually, just let's run Python with a syntax error inline via safe_subprocess mock?
    # No, run_script takes a script_name. Let's use `pipeline.py` itself with a bad arg, it will fail.
    # Actually, if we just mock safe_subprocess to return a non-zero exit code:
    
    import scripts.pipeline
    class DummyResult:
        returncode = 1
        stdout = "dummy error"
        stderr = "dummy error"
    
    monkeypatch.setattr(scripts.pipeline, "safe_subprocess", lambda *a, **kw: DummyResult())
    
    # Also need to bypass script existence check by mocking Path.exists
    monkeypatch.setattr("scripts.pipeline.Path.exists", lambda self: True)
    
    res = run_script(logger, "test_stage", "test_component", "dummy_script.py", IdempotencyClass.NOT_RETRYABLE)
    assert res is False
    
    assert clean_logs.exists()
    logs = [json.loads(l) for l in clean_logs.read_text(encoding="utf-8").strip().split("\n") if l]
    run_logs = [l for l in logs if l.get("run_id") == test_run_id]
    
    assert len(run_logs) == 3  # 1 started, 1 failure, 1 aborted
    
    started_log = run_logs[0]
    failure_log = run_logs[1]
    aborted_log = run_logs[2]
    
    assert started_log["status"] == "started"
    assert failure_log["status"] == "failure"
    assert aborted_log["event"] == "retry.aborted"
    
    # Crucial part: The failed child span_id is preserved!
    assert started_log["span_id"] == failure_log["span_id"]
    assert started_log["parent_span_id"] == "test-root-span"
    assert failure_log["parent_span_id"] == "test-root-span"
    assert aborted_log["span_id"] == failure_log["span_id"]
