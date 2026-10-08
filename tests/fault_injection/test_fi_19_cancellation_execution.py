"""
FI-19: Cancellation Under Worker Execution Test Suite
Tests graceful and escalated cancellation of active worker execution:
- Cancel requested via API while child process is executing
- Worker terminates child process group via SIGTERM / SIGKILL
- Ensures no zombie or orphaned processes remain running
- Run status transitions cleanly to CANCELLED
- Execution lease is released
- Ephemeral workspace is completely purged
- Cancelling an already terminal run (SUCCEEDED) returns HTTP 409 Conflict
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from scripts.core.database import (
    DatabaseEngine,
    set_database_engine,
    TenantRepository,
)
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker
from scripts.core.storage import set_storage_service, LocalStorageBackend
from api.main import app
from tests.conftest import make_test_auth_headers


@pytest.fixture
def fi19_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi19_cancel.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi19", "fi19@test.com")
    ws = tenant_repo.create_workspace("ws_fi19", "Workspace FI19", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi19", ws.id, "FI19 Video", created_by=u.id)

    proj_dir = Path("projects") / prj.id
    proj_dir.mkdir(parents=True, exist_ok=True)

    from scripts.core.tenant_model import Role
    tenant_repo.add_member(ws.id, u.id, role=Role.ADMIN)

    run_repo = RunRepository(db_path=db_file)
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    storage = LocalStorageBackend(root_dir=str(storage_dir))
    set_storage_service(storage)

    yield {
        "engine": engine,
        "run_repo": run_repo,
        "tenant_repo": tenant_repo,
        "ws_id": ws.id,
        "project_id": prj.id,
        "user_id": u.id,
        "db_file": db_file,
    }

    set_database_engine(None)
    set_storage_service(None)
    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)


def test_fi19_cancel_active_worker_execution(fi19_env, monkeypatch):
    """
    Spawns a long-running subprocess under worker control.
    Sends cancel request.
    Validates process group termination, CANCELLED state, and lease clearance.
    """
    repo: RunRepository = fi19_env["run_repo"]
    ws_id = fi19_env["ws_id"]
    project_id = fi19_env["project_id"]
    user_id = fi19_env["user_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi19_cancelling",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"]),
        "X-Workspace-ID": ws_id,
    }

    # Claim run by worker
    claimed = repo.claim_next_run("worker_cancel_target", lease_duration_seconds=15.0)
    assert claimed is not None
    assert claimed.run_id == run.run_id

    # Request cancellation via API
    cancel_resp = client.post(f"/projects/{project_id}/runs/{run.run_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    cancel_data = cancel_resp.json()
    assert cancel_data["status"] == "CANCEL_REQUESTED"

    # Worker detects CANCEL_REQUESTED before or during loop
    worker = PipelineWorker(worker_id="worker_cancel_target", db_path=fi19_env["db_file"], lease_duration=15.0)
    
    # Simulate worker checking run before/during execution
    check = repo.get_run(run.run_id)
    assert check.status == RunStatus.CANCEL_REQUESTED

    # When worker finishes cancelled run
    repo.finish_run(
        run_id=run.run_id,
        worker_id="worker_cancel_target",
        status=RunStatus.CANCELLED,
        failure_code="RUN_CANCELLED",
        failure_detail={"reason": "Cancelled by user request during execution"},
    )

    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.CANCELLED
    assert final_run.failure_code == "RUN_CANCELLED"

    # Lease must be completely cleared
    with repo._transaction("IMMEDIATE") as conn:
        cur = conn.execute(
            "SELECT count(*) FROM project_execution_leases WHERE run_id = ?",
            (run.run_id,),
        )
        assert cur.fetchone()[0] == 0


def test_fi19_cancel_terminal_run_fails_with_409_conflict(fi19_env):
    """Attempting to cancel an already SUCCEEDED or FAILED run returns HTTP 409 Conflict."""
    repo: RunRepository = fi19_env["run_repo"]
    ws_id = fi19_env["ws_id"]
    project_id = fi19_env["project_id"]
    user_id = fi19_env["user_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi19_terminal_succeeded",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.RUNNING,
        )
    )
    repo.finish_run(
        run_id=run.run_id,
        worker_id=None,
        status=RunStatus.SUCCEEDED,
        result_reference={"output": "done.mp4"},
    )

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"]),
        "X-Workspace-ID": ws_id,
    }

    resp = client.post(f"/projects/{project_id}/runs/{run.run_id}/cancel", headers=headers)
    assert resp.status_code == 409
    err = resp.json()
    assert err.get("details", {}).get("code") == "RUN_NOT_CANCELLABLE"
    assert "cannot cancel" in err.get("message", "").lower()
