import pytest
import os
import sys
import uuid
import json
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.failure_model import FailureInfo, FailureCode
from scripts.retry_policy import RetryPolicyEngine, IdempotencyClass, RetryDecision
from scripts.runtime_logger import RuntimeLogger, RunContext

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

def test_retryable_but_not_idempotent():
    # Retryable failure + NOT_RETRYABLE operation -> zero retries
    failure = FailureInfo(
        code=FailureCode.RENDER_TIMEOUT,
        message="Timeout happened",
        cause_type="TimeoutError"
    )
    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.NOT_RETRYABLE, 1)
    
    assert decision.should_retry is False
    assert decision.reason == "Operation is NOT_RETRYABLE"

def test_non_retryable_validation():
    # Non-retryable validation -> zero retries
    failure = FailureInfo(
        code=FailureCode.PLAN_GATE_REJECTED,
        message="Plan invalid",
    )
    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.SAFE_TO_RETRY, 1)
    
    assert decision.should_retry is False
    assert "not retryable" in decision.reason

def test_retry_exhausted_clean_failure():
    # Timeout -> retry -> exhausted -> clean failure
    failure = FailureInfo(
        code=FailureCode.RENDER_TIMEOUT,
        message="Timeout happened"
    )
    # Attempt 1
    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 1)
    assert decision.should_retry is True
    
    # Attempt 2
    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 2)
    assert decision.should_retry is True
    
    # Attempt 3 (Max is 3)
    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 3)
    assert decision.should_retry is False
    assert "Max attempts exhausted" in decision.reason

def test_backoff_mocking(monkeypatch):
    called = []
    def mock_sleep(seconds):
        called.append(seconds)
        
    import time
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    decision = RetryDecision(
        should_retry=True,
        reason="retry",
        next_attempt=2,
        delay_seconds=3,
        max_attempts=3
    )
    
    RetryPolicyEngine.delay_for(decision)
    assert called == [3]

def test_pipeline_retry_loop_integration(clean_logs, monkeypatch):
    """
    Test the pipeline's run_script retry loop itself.
    We will mock safe_subprocess to fail twice with RENDER_TIMEOUT and succeed on third.
    Wait, pipeline.py does not run RENDER_TIMEOUT currently natively in run_script, 
    but run_script defaults to GATE_EXECUTION_FAILED which is retryable (max 3).
    So if we fail twice and succeed on third, it should log attempts.
    """
    from scripts.pipeline import run_script
    
    test_run_id = str(uuid.uuid4())
    ctx = RunContext(run_id=test_run_id, project_id="prj_mock", span_id="test-root-span")
    logger = RuntimeLogger(ctx)
    
    call_count = 0
    
    import scripts.pipeline
    class DummyResult:
        def __init__(self, ret):
            self.returncode = ret
            self.stdout = "dummy out"
            self.stderr = "dummy err"
            
    def mock_safe_subprocess(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return DummyResult(1) # fail
        return DummyResult(0) # success
        
    monkeypatch.setattr(scripts.pipeline, "safe_subprocess", mock_safe_subprocess)
    monkeypatch.setattr("scripts.pipeline.Path.exists", lambda self: True)
    
    # Skip sleeping
    monkeypatch.setattr(RetryPolicyEngine, "delay_for", lambda d: None)
    
    res = run_script(logger, "test", "test", "test.py", IdempotencyClass.SAFE_TO_RETRY)
    assert res is True
    assert call_count == 3
    
    logs = [json.loads(l) for l in clean_logs.read_text(encoding="utf-8").strip().split("\n") if l]
    run_logs = [l for l in logs if l.get("run_id") == test_run_id]
    
    # Check attempts
    scheduled_events = [l for l in run_logs if l.get("event") == "retry.scheduled"]
    assert len(scheduled_events) == 2
    assert scheduled_events[0]["attempt"] == 1
    assert scheduled_events[1]["attempt"] == 2
    
    success_events = [l for l in run_logs if l.get("event") == "retry.success"]
    assert len(success_events) == 1
    assert success_events[0]["attempt"] == 3
    
    # Ensure span IDs are different for each attempt
    gate_starts = [l for l in run_logs if l.get("event") == "gate.execution" and l.get("status") == "started"]
    assert len(gate_starts) == 3
    span_ids = [l["span_id"] for l in gate_starts]
    assert len(set(span_ids)) == 3, "Each attempt must have a unique span_id"
