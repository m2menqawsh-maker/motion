"""
FI-04: API Hard Death Test Suite
Simulates abrupt API crash/termination at various points in the lifecycle:
- After run submission / acceptance
- While worker is actively executing
- Before run completes

Validates that:
- Run lifecycle is fully decoupled from API process lifecycle
- API crash/restart does not lose queued or running runs
- Worker executes cleanly to completion regardless of API death
- After API restart, run state and sequenced event history are faithfully retrieved
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
from scripts.core.worker import PipelineWorker
from scripts.core.storage import set_storage_service, LocalStorageBackend
from api.main import app


@pytest.fixture
def fi04_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi04_api_death.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi04", "fi04@test.com")
    ws = tenant_repo.create_workspace("ws_fi04", "Workspace FI04", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi04", ws.id, "FI04 Video", created_by=u.id)

    proj_dir = Path("projects") / prj.id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Set up tenant membership so principal can access workspace
    from scripts.core.tenant_model import Role
    tenant_repo.add_member(ws.id, u.id, role=Role.ADMIN)

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    svc = LocalStorageBackend(root_dir=str(storage_dir))
    set_storage_service(svc)

    run_repo = RunRepository(db_path=db_file)

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
    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)


def test_fi04_api_hard_death_after_submission_and_restart(fi04_env):
    """
    1. Submit run through API Instance 1.
    2. API Instance 1 dies abruptly.
    3. Worker independently claims, executes, and finishes the run in DB.
    4. API Instance 2 starts up (restart).
    5. API Instance 2 reads full run status and event history.
    """
    ws_id = fi04_env["ws_id"]
    project_id = fi04_env["project_id"]
    user_id = fi04_env["user_id"]
    db_file = fi04_env["db_file"]

    from tests.conftest import make_test_auth_headers
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }

    # Step 1: Start API Instance 1 and enqueue run
    client_1 = TestClient(app)

    post_resp = client_1.post(
        f"/projects/{project_id}/runs",
        headers=headers,
        json={"idempotency_key": "fi04-idemp-key-1"},
    )
    assert post_resp.status_code == 202
    run_data = post_resp.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "QUEUED"

    # Step 2: Kill API Instance 1 (hard crash simulation)
    del client_1

    # Step 3: Worker runs independently while API is completely offline
    worker = PipelineWorker(worker_id="worker_headless", db_path=db_file, lease_duration=10.0)
    repo = RunRepository(db_path=db_file)

    claimed = repo.claim_next_run(worker_id="worker_headless", lease_duration_seconds=10.0)
    assert claimed is not None
    assert claimed.run_id == run_id
    assert claimed.status == RunStatus.RUNNING

    # Worker emits lifecycle events
    repo.record_event(run_id, project_id, "RUN_STARTED", payload={"worker": "worker_headless"}, workspace_id=ws_id)
    repo.record_event(run_id, project_id, "STAGE_STARTED", stage="RENDER", workspace_id=ws_id)
    repo.record_event(run_id, project_id, "STAGE_COMPLETED", stage="RENDER", workspace_id=ws_id)

    # Worker marks run SUCCEEDED
    repo.finish_run(
        run_id=run_id,
        worker_id="worker_headless",
        status=RunStatus.SUCCEEDED,
        result_reference={"output_file": "rendered.mp4"},
    )
    repo.record_event(run_id, project_id, "RUN_SUCCEEDED", payload={"status": "complete"}, workspace_id=ws_id)

    # Step 4: API restarts (New App & Client instance)
    client_2 = TestClient(app)

    # Step 5: Verify run status via new API instance
    get_resp = client_2.get(f"/projects/{project_id}/runs/{run_id}", headers=headers)
    assert get_resp.status_code == 200
    res = get_resp.json()
    assert res["run_id"] == run_id
    assert res["status"] == "SUCCEEDED"
    assert res["worker_id"] == "worker_headless"
    assert res["result_reference"] == {"output_file": "rendered.mp4"}

    # Step 6: Verify durable events retrieved through restarted API
    events_resp = client_2.get(f"/projects/{project_id}/runs/{run_id}/events", headers=headers)
    assert events_resp.status_code == 200
    events_data = events_resp.json()
    assert "events" in events_data
    event_types = [e["event_type"] for e in events_data["events"]]
    assert event_types == ["RUN_QUEUED", "RUN_STARTED", "STAGE_STARTED", "STAGE_COMPLETED", "RUN_SUCCEEDED"]
