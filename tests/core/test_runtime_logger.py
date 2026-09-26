from scripts.core.runtime_logger import RuntimeLogger, RunContext
from scripts.core.failure_model import FailureInfo, FailureCode
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def test_jsonl_is_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mocking workspace_root internally by changing CWD temporarily
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            run_id = str(uuid.uuid4())
            context = RunContext(project_id="test_proj", run_id=run_id)
            logger = RuntimeLogger(context)
            
            logger.event("pipeline.execution", component="pipeline", status="started")
            logger.event("gate.execution", component="gate", status="running")
            
            log_file = Path(tmpdir) / "logs" / "runtime.jsonl"
            assert log_file.exists()
            
            # Verify valid JSONL
            lines = log_file.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 2
            
            event1 = json.loads(lines[0])
            assert event1["component"] == "pipeline"
            assert event1["status"] == "started"
            assert event1["run_id"] == run_id
            
            event2 = json.loads(lines[1])
            assert event2["span_id"] == context.span_id
        finally:
            os.chdir(old_cwd)

def test_logger_failure_does_not_kill_pipeline():
    # If the file path is invalid or unwritable, it should not throw exception
    # It prints to stderr, but we can just ensure no exception bubbles up
    run_id = str(uuid.uuid4())
    context = RunContext(project_id="test_proj", run_id=run_id)
    logger = RuntimeLogger(context)
    
    # Intentionally corrupt the path
    logger.global_log_file = Path("/invalid/path/that/does/not/exist/runtime.jsonl")
    
    # This should not raise an exception
    logger.event("test.event", component="test", status="started")

def test_failure_event_contains_error_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            run_id = str(uuid.uuid4())
            context = RunContext(project_id="test_proj", run_id=run_id)
            logger = RuntimeLogger(context)
            
            failure = FailureInfo(
                code=FailureCode.RENDER_TIMEOUT,
                message="Render took too long",
                cause_type="TimeoutError",
                stage="RENDER"
            )
            
            logger.event("gate.execution", component="render_project.py", status="failed", failure_info=failure)
            
            global_log_file = Path("logs/runtime.jsonl")
            with open(global_log_file, "r", encoding="utf-8") as f:
                data = json.loads(f.readlines()[0])
            assert "error_code" in data
            assert data["error_code"] == "RENDER_TIMEOUT"
            assert data["status"] == "failed"
        finally:
            os.chdir(old_cwd)
