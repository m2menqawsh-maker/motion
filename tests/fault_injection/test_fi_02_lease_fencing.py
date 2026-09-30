"""
tests/fault_injection/test_fi_02_lease_fencing.py — Fault Injection Scenario FI-02.

Lease Expiry, Heartbeat Outage & Stale Worker Fencing Matrix:
Tests the complete lifecycle of lease loss and recovery:
1. Worker 1 claims a run with lease duration.
2. Heartbeat failure is simulated (database outage during lease renewal).
3. Lease expires.
4. Worker 2 detects the expired orphan run and reclaims it (attempt 2).
5. Invariant: Worker 1 and Worker 2 CANNOT legally hold the job simultaneously.
6. Fencing verification: Worker 1 (stale worker) wakes up late and attempts to publish
   and finish the run.
   Expected Invariant: Stale Worker 1 MUST BE FENCED and rejected with an error!
   Worker 1 must NOT overwrite Worker 2's lease or finish Worker 2's run.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from scripts.core.database import DatabaseEngine, set_database_engine, TenantRepository
from scripts.core.run_repository import (
    RunRepository,
    RunRepositoryError,
)
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker


@pytest.fixture
def fi02_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi02_lease.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi02", "fi02@test.com")
    ws = tenant_repo.create_workspace("ws_fi02", "Workspace FI02", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi02", ws.id, "FI02 Video", created_by=u.id)

    run_repo = RunRepository(db_path=db_file)

    yield {
        "engine": engine,
        "run_repo": run_repo,
        "ws_id": ws.id,
        "prj_id": prj.id,
        "db_file": db_file,
    }

    set_database_engine(None)


def test_fi02_lease_expiry_and_orphan_recovery(fi02_env):
    """Worker 1 acquires lease; heartbeat drops; lease expires; Worker 2 recovers orphan."""
    run_repo = fi02_env["run_repo"]
    prj_id = fi02_env["prj_id"]
    ws_id = fi02_env["ws_id"]

    # 1. Enqueue run
    run = run_repo.create_run(
        RunRecord(
            run_id="run_fi02_001",
            project_id=prj_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    # 2. Worker 1 claims run with very short lease (1 second)
    claimed_w1 = run_repo.claim_next_run(worker_id="worker_1", lease_duration_seconds=1.0)
    assert claimed_w1 is not None
    assert claimed_w1.worker_id == "worker_1"
    assert claimed_w1.status == RunStatus.RUNNING
    assert claimed_w1.attempt == 1

    # 3. Simulate heartbeat failure by manually backdating lease_expires_at into the past
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with run_repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = ? WHERE run_id = ?", (past_iso, run.run_id))
        conn.execute("UPDATE project_execution_leases SET expires_at = ? WHERE run_id = ?", (past_iso, run.run_id))

    # 4. Worker 2 detects expired orphan
    worker_2 = PipelineWorker(worker_id="worker_2", db_path=run_repo.db_path)
    worker_2.recover_orphans()

    # Verify run was reset to QUEUED with attempt incremented
    rec = run_repo.get_run(run.run_id)
    assert rec.status == RunStatus.QUEUED
    assert rec.attempt == 2

    # 5. Worker 2 claims the run
    claimed_w2 = run_repo.claim_next_run(worker_id="worker_2", lease_duration_seconds=60.0)
    assert claimed_w2 is not None
    assert claimed_w2.worker_id == "worker_2"
    assert claimed_w2.attempt == 2


def test_fi02_stale_worker_fenced_from_finish_and_publish(fi02_env):
    """
    CRITICAL FENCING TEST:
    Worker 1 lost its lease and the run was reclaimed by Worker 2.
    Worker 1 attempts to call finish_run on the reclaimed run.
    Invariant: Worker 1 MUST fail and be fenced from marking the run SUCCEEDED.
    """
    run_repo = fi02_env["run_repo"]
    prj_id = fi02_env["prj_id"]
    ws_id = fi02_env["ws_id"]

    # 1. Enqueue run
    run = run_repo.create_run(
        RunRecord(
            run_id="run_fi02_fencing",
            project_id=prj_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    # 2. Worker 1 claims run
    claimed_w1 = run_repo.claim_next_run(worker_id="worker_1", lease_duration_seconds=1.0)
    assert claimed_w1.worker_id == "worker_1"

    # 3. Simulate lease expiration & Worker 2 takeover
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with run_repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = ? WHERE run_id = ?", (past_iso, run.run_id))
        conn.execute("UPDATE project_execution_leases SET expires_at = ? WHERE run_id = ?", (past_iso, run.run_id))

    worker_2 = PipelineWorker(worker_id="worker_2", db_path=run_repo.db_path)
    worker_2.recover_orphans()
    claimed_w2 = run_repo.claim_next_run(worker_id="worker_2", lease_duration_seconds=60.0)
    assert claimed_w2.worker_id == "worker_2"
    assert claimed_w2.attempt == 2

    # 4. Now Worker 1 wakes up late and tries to finish_run!
    # Expected: Fencing MUST reject Worker 1 because Worker 1 no longer owns the active lease!
    with pytest.raises(RunRepositoryError, match="(?i)stale|fence|lease|owner|not owned"):
        run_repo.finish_run(
            run_id=run.run_id,
            worker_id="worker_1",  # Stale worker!
            status=RunStatus.SUCCEEDED,
            result_reference={"output": "stale_output_from_worker_1"},
        )

    # 5. Verify Worker 2's run ownership was NOT stolen
    active_run = run_repo.get_run(run.run_id)
    assert active_run.worker_id == "worker_2", "Worker 2 ownership must remain intact!"
    assert active_run.status == RunStatus.RUNNING
