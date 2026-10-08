"""
FI-09: Duplicate Run / Idempotency Test Suite
Tests idempotency semantics and duplicate suppression:
- Same idempotency key + same payload returns existing run (HTTP 202, no duplicate execution)
- Same idempotency key + different payload raises HTTP 409 Conflict (IdempotencyConflictError)
- Requests without idempotency key create separate runs
- Repeated requests for a completed run return the completed state without re-triggering execution
- Event log contains exactly ONE RUN_QUEUED event per run
"""

import os
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from scripts.core.database import (
    DatabaseEngine,
    set_database_engine,
    TenantRepository,
)
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunStatus
from scripts.core.storage import set_storage_service, LocalStorageBackend
from api.main import app
from tests.conftest import make_test_auth_headers


@pytest.fixture
def fi09_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi09_idempotency.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi09", "fi09@test.com")
    ws = tenant_repo.create_workspace("ws_fi09", "Workspace FI09", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi09", ws.id, "FI09 Video", created_by=u.id)

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


def test_fi09_identical_requests_return_same_run_without_duplicate(fi09_env):
    """
    Submitting the exact same run request twice with identical idempotency key:
    - Both calls return HTTP 202 Accepted.
    - Both calls return the exact same run_id.
    - Exactly one Run record exists in DB.
    - Exactly one RUN_QUEUED event is recorded.
    """
    ws_id = fi09_env["ws_id"]
    project_id = fi09_env["project_id"]
    user_id = fi09_env["user_id"]
    repo: RunRepository = fi09_env["run_repo"]

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }
    payload = {"idempotency_key": "idemp-test-duplicate-001", "parameters": {"quality": "1080p"}}

    # Call 1
    resp1 = client.post(f"/projects/{project_id}/runs", headers=headers, json=payload)
    assert resp1.status_code == 202
    data1 = resp1.json()
    run_id1 = data1["run_id"]

    # Call 2 (Exact duplicate)
    resp2 = client.post(f"/projects/{project_id}/runs", headers=headers, json=payload)
    assert resp2.status_code == 202
    data2 = resp2.json()
    run_id2 = data2["run_id"]

    assert run_id1 == run_id2

    # Verify DB has only 1 run
    runs = repo.list_runs(project_id)
    assert len(runs) == 1

    # Verify only 1 RUN_QUEUED event was recorded
    events = repo.get_events(run_id1)
    queued_events = [e for e in events if e.event_type == "RUN_QUEUED"]
    assert len(queued_events) == 1


def test_fi09_idempotency_key_payload_conflict(fi09_env):
    """
    Submitting the same idempotency key with a DIFFERENT payload must fail with HTTP 409 Conflict.
    """
    ws_id = fi09_env["ws_id"]
    project_id = fi09_env["project_id"]
    user_id = fi09_env["user_id"]

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }

    # Initial request
    resp1 = client.post(
        f"/projects/{project_id}/runs",
        headers=headers,
        json={"idempotency_key": "conflict-key-999", "parameters": {"preset": "draft"}},
    )
    assert resp1.status_code == 202

    # Conflicting request (different parameters with same key)
    resp2 = client.post(
        f"/projects/{project_id}/runs",
        headers=headers,
        json={"idempotency_key": "conflict-key-999", "parameters": {"preset": "high_quality_4k"}},
    )
    assert resp2.status_code == 409
    err = resp2.json()
    assert "Idempotency conflict" in err.get("message", "") or "Idempotency conflict" in err.get("detail", "")


def test_fi09_request_without_idempotency_key_creates_distinct_runs(fi09_env):
    """Requests without an idempotency key create separate distinct runs."""
    ws_id = fi09_env["ws_id"]
    project_id = fi09_env["project_id"]
    user_id = fi09_env["user_id"]
    repo: RunRepository = fi09_env["run_repo"]

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }

    resp1 = client.post(f"/projects/{project_id}/runs", headers=headers, json={})
    assert resp1.status_code == 202
    run1 = resp1.json()["run_id"]

    resp2 = client.post(f"/projects/{project_id}/runs", headers=headers, json={})
    assert resp2.status_code == 202
    run2 = resp2.json()["run_id"]

    assert run1 != run2
    runs = repo.list_runs(project_id)
    assert len(runs) >= 2


def test_fi09_duplicate_on_completed_run_returns_terminal_state(fi09_env):
    """
    Submitting duplicate idempotency key on an already completed/succeeded run:
    - Returns HTTP 202 with status SUCCEEDED
    - Does not re-queue or restart the run
    """
    ws_id = fi09_env["ws_id"]
    project_id = fi09_env["project_id"]
    user_id = fi09_env["user_id"]
    repo: RunRepository = fi09_env["run_repo"]

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }
    payload = {"idempotency_key": "completed-key-100", "parameters": {}}

    resp1 = client.post(f"/projects/{project_id}/runs", headers=headers, json=payload)
    assert resp1.status_code == 202
    run_id = resp1.json()["run_id"]

    # Transition run to SUCCEEDED
    claimed = repo.claim_next_run(worker_id="worker_idemp", lease_duration_seconds=10.0)
    repo.finish_run(
        run_id=run_id,
        worker_id="worker_idemp",
        status=RunStatus.SUCCEEDED,
        result_reference={"output_file": "done.mp4"},
    )

    # Re-send exact same request
    resp2 = client.post(f"/projects/{project_id}/runs", headers=headers, json=payload)
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["run_id"] == run_id
    assert data2["status"] == "SUCCEEDED"
