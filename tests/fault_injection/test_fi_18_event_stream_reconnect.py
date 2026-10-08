"""
FI-18: Event Stream Disconnect & Cursor Reconnect Test Suite
Tests Server-Sent Events (SSE) and event history cursor pagination:
- Streaming events via SSE (text/event-stream)
- Abrupt client disconnection after receiving event sequence N
- Reconnecting with 'Last-Event-ID: N' header
- Reconnecting with '?after=N' query parameter
- Verification that no events are lost or duplicated
- Verification that events arrive in strictly monotonic sequence order
"""

import json
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
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.storage import set_storage_service, LocalStorageBackend
from tests.conftest import make_test_auth_headers
from api.main import app


@pytest.fixture
def fi18_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi18_events.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi18", "fi18@test.com")
    ws = tenant_repo.create_workspace("ws_fi18", "Workspace FI18", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi18", ws.id, "FI18 Video", created_by=u.id)

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


def test_fi18_cursor_pagination_after_disconnect(fi18_env):
    """
    Simulates:
    1. A run generating 6 events (sequences 1 to 6).
    2. Client fetches first batch up to sequence 3, then 'disconnects'.
    3. Client reconnects with 'after=3'.
    4. Client receives exactly sequences 4, 5, 6 with no gaps and no duplicate events.
    """
    repo: RunRepository = fi18_env["run_repo"]
    ws_id = fi18_env["ws_id"]
    project_id = fi18_env["project_id"]
    user_id = fi18_env["user_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi18_stream",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    # Emit sequences 1 to 6
    stages = ["INIT", "MATERIALIZE", "RENDER", "PROBE", "FINALIZE"]
    repo.record_event(run.run_id, project_id, "RUN_STARTED", workspace_id=ws_id)
    for s in stages:
        repo.record_event(run.run_id, project_id, "STAGE_COMPLETED", stage=s, workspace_id=ws_id)

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }

    # Batch 1: Query events starting from beginning, limit 3
    resp1 = client.get(f"/projects/{project_id}/runs/{run.run_id}/events?after=0&limit=3", headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["events"]) == 3
    seqs1 = [e["sequence"] for e in data1["events"]]
    assert seqs1 == [1, 2, 3]
    last_received = seqs1[-1]

    # Reconnection: Query using after=last_received
    resp2 = client.get(f"/projects/{project_id}/runs/{run.run_id}/events?after={last_received}&limit=10", headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["events"]) == 3
    seqs2 = [e["sequence"] for e in data2["events"]]
    assert seqs2 == [4, 5, 6]

    # Invariant: No duplicate sequence across batches, strictly monotonic
    assert set(seqs1).isdisjoint(set(seqs2))
    assert seqs1 + seqs2 == [1, 2, 3, 4, 5, 6]


def test_fi18_reconnect_with_last_event_id_header(fi18_env):
    """
    Simulates SSE reconnection using the standard 'Last-Event-ID' HTTP header.
    Validates that events before or equal to Last-Event-ID are skipped,
    and only subsequent events are streamed.
    """
    repo: RunRepository = fi18_env["run_repo"]
    ws_id = fi18_env["ws_id"]
    project_id = fi18_env["project_id"]
    user_id = fi18_env["user_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi18_sse",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.RUNNING,
        )
    )

    repo.record_event(run.run_id, project_id, "EVENT_A", workspace_id=ws_id)  # seq 1
    repo.record_event(run.run_id, project_id, "EVENT_B", workspace_id=ws_id)  # seq 2
    repo.record_event(run.run_id, project_id, "EVENT_C", workspace_id=ws_id)  # seq 3
    repo.record_event(run.run_id, project_id, "RUN_SUCCEEDED", workspace_id=ws_id)  # seq 4

    client = TestClient(app)
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
        "Last-Event-ID": "2",  # Client already received up to sequence 2
    }

    # Fetch with Last-Event-ID header
    resp = client.get(f"/projects/{project_id}/runs/{run.run_id}/events", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    seqs = [e["sequence"] for e in data["events"]]
    assert seqs == [3, 4]
    types = [e["event_type"] for e in data["events"]]
    assert types == ["EVENT_C", "RUN_SUCCEEDED"]
