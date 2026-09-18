import pytest
import json
import uuid
from pathlib import Path

from scripts.metrics.metrics_model import HealthStatus
from scripts.metrics.metrics_collector import MetricsCollector

@pytest.fixture
def mock_log_file(tmp_path):
    return tmp_path / "runtime.jsonl"

def write_logs(file_path, events):
    with open(file_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

def test_internal_failure_then_success(mock_log_file):
    run_id = str(uuid.uuid4())
    
    events = [
        {"run_id": run_id, "event": "gate.execution", "status": "started", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "gate.execution", "status": "failure", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "retry.scheduled", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "gate.execution", "status": "started", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "gate.execution", "status": "success", "stage": "render", "component": "remotion", "duration_ms": 1000},
        {"run_id": run_id, "event": "pipeline.execution", "status": "success", "duration_ms": 2000},
    ]
    
    write_logs(mock_log_file, events)
    collector = MetricsCollector(mock_log_file)
    snapshot = collector.collect()
    
    # 1 run, which is successful
    assert snapshot.runs_total == 1
    assert snapshot.runs_success == 1
    assert snapshot.runs_failed == 0
    
    # Internal component metrics
    comp = snapshot.components["remotion"]
    assert comp.failure_count == 1
    assert comp.success_count == 1
    assert comp.retry_count == 1
    
    # Retries total
    assert snapshot.retries_total == 1

def test_multiple_failure_events_single_failed_run(mock_log_file):
    run_id = str(uuid.uuid4())
    
    events = [
        {"run_id": run_id, "event": "gate.execution", "status": "failure", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "gate.execution", "status": "failure", "stage": "render", "component": "remotion"},
        {"run_id": run_id, "event": "pipeline.execution", "status": "failure"},
    ]
    
    write_logs(mock_log_file, events)
    collector = MetricsCollector(mock_log_file)
    snapshot = collector.collect()
    
    # Still only 1 failed run!
    assert snapshot.runs_total == 1
    assert snapshot.runs_failed == 1
    assert snapshot.runs_success == 0
    
def test_health_status_healthy(mock_log_file):
    run_id = str(uuid.uuid4())
    events = [
        {"run_id": run_id, "event": "pipeline.execution", "status": "success"},
    ]
    write_logs(mock_log_file, events)
    collector = MetricsCollector(mock_log_file)
    snapshot = collector.collect()
    
    assert snapshot.health_status == HealthStatus.HEALTHY
    
def test_health_status_unhealthy_critical(mock_log_file):
    run_id = str(uuid.uuid4())
    events = [
        {"run_id": run_id, "event": "system.error", "severity": "CRITICAL"},
        {"run_id": run_id, "event": "pipeline.execution", "status": "success"},
    ]
    write_logs(mock_log_file, events)
    collector = MetricsCollector(mock_log_file)
    snapshot = collector.collect()
    
    assert snapshot.health_status == HealthStatus.UNHEALTHY

def test_health_status_degraded_fallback(mock_log_file):
    run_id = str(uuid.uuid4())
    events = [
        {"run_id": run_id, "event": "system.error", "is_fallback": True},
        {"run_id": run_id, "event": "pipeline.execution", "status": "success"},
    ]
    write_logs(mock_log_file, events)
    collector = MetricsCollector(mock_log_file)
    snapshot = collector.collect()
    
    assert snapshot.health_status == HealthStatus.DEGRADED
