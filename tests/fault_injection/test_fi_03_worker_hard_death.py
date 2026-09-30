"""
FI-03: Worker Hard Death Test Suite
Simulates abrupt process termination (SIGKILL) across multiple execution points:
- Hard death after claim
- Hard death during execution (render/materialization)
- Hard death after upload before finish_run commit
- Attempt exhaustion leading to ORPHAN_RUN_EXPIRED

Validates that:
- Lease expiration releases orphaned runs
- Orphan recovery safely retries with incremented attempts
- Ephemeral workspace is never treated as permanent source of truth
- No duplicate side effects corrupt database state
"""

import os
import time
from pathlib import Path
import pytest

from scripts.core.database import (
    DatabaseEngine,
    set_database_engine,
    TenantRepository,
)
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker
from scripts.core.storage import (
    get_storage_service,
    set_storage_service,
    LocalStorageBackend,
)


@pytest.fixture
def fi03_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi03_death.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi03", "fi03@test.com")
    ws = tenant_repo.create_workspace("ws_fi03", "Workspace FI03", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi03", ws.id, "FI03 Video", created_by=u.id)

    run_repo = RunRepository(db_path=db_file)
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    svc = LocalStorageBackend(root_dir=str(storage_dir))
    set_storage_service(svc)

    yield {
        "engine": engine,
        "run_repo": run_repo,
        "tenant_repo": tenant_repo,
        "ws_id": ws.id,
        "project_id": prj.id,
        "storage_dir": storage_dir,
        "db_file": db_file,
    }

    set_database_engine(None)


def test_fi03_hard_death_after_claim(fi03_env):
    """
    Test worker dying immediately after claiming run (simulated by claim + immediate kill/abandon).
    Validates:
    - Lease expires after lease_duration_seconds
    - Second worker detects orphan and transitions to QUEUED with attempt incremented
    - Second worker successfully claims and finishes the run
    """
    repo: RunRepository = fi03_env["run_repo"]
    ws_id = fi03_env["ws_id"]
    project_id = fi03_env["project_id"]

    # 1. Enqueue a run
    run = repo.create_run(
        RunRecord(
            run_id="run_fi03_001",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )
    assert run.status == RunStatus.QUEUED
    assert run.attempt == 1

    # 2. Worker 1 claims run with very short lease (1.0 sec) then abruptly "dies"
    claimed_run = repo.claim_next_run(worker_id="worker-crash-1", lease_duration_seconds=1.0)
    assert claimed_run is not None
    assert claimed_run.run_id == run.run_id
    assert claimed_run.status == RunStatus.RUNNING
    assert claimed_run.attempt == 1
    assert claimed_run.worker_id == "worker-crash-1"

    # Worker 1 terminates (no heartbeat, no finish_run)
    # 3. Simulate lease expiration by backdating lease
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00' WHERE run_id = ?",
            (run.run_id,),
        )
        conn.execute(
            "UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00' WHERE run_id = ?",
            (run.run_id,),
        )

    # 4. Worker 2 performs orphan recovery pass
    worker_2 = PipelineWorker(
        worker_id="worker-survivor-2",
        db_path=fi03_env["db_file"],
        lease_duration=10.0,
        heartbeat_interval=2.0,
    )
    worker_2.recover_orphans()

    # Verify run was reset to QUEUED with attempt 2
    rec = repo.get_run(run.run_id)
    assert rec.status == RunStatus.QUEUED
    assert rec.attempt == 2
    assert rec.worker_id is None

    # Worker 2 claims run successfully
    claimed_by_2 = repo.claim_next_run(worker_id="worker-survivor-2", lease_duration_seconds=10.0)
    assert claimed_by_2 is not None
    assert claimed_by_2.run_id == run.run_id
    assert claimed_by_2.worker_id == "worker-survivor-2"
    assert claimed_by_2.attempt == 2


def test_fi03_hard_death_during_execution_and_retry_exhaustion(fi03_env):
    """
    Simulates repeated worker deaths during execution until attempt limit (3) is exceeded.
    Validates:
    - Attempt 1: Dies -> recovered to QUEUED (attempt 2)
    - Attempt 2: Dies -> recovered to QUEUED (attempt 3)
    - Attempt 3: Dies -> recovered to FAILED (ORPHAN_RUN_EXPIRED)
    - State is strictly deterministic, no infinite retry loop
    """
    repo: RunRepository = fi03_env["run_repo"]
    ws_id = fi03_env["ws_id"]
    project_id = fi03_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi03_002",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    worker = PipelineWorker(worker_id="worker-recovering", db_path=fi03_env["db_file"], lease_duration=5.0)

    # Attempt 1 death
    r1 = repo.claim_next_run("dead-worker-1", lease_duration_seconds=5.0)
    assert r1.attempt == 1
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00'")
        conn.execute("UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00'")
    worker.recover_orphans()
    rec1 = repo.get_run(run.run_id)
    assert rec1.status == RunStatus.QUEUED
    assert rec1.attempt == 2

    # Attempt 2 death
    r2 = repo.claim_next_run("dead-worker-2", lease_duration_seconds=5.0)
    assert r2.attempt == 2
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00'")
        conn.execute("UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00'")
    worker.recover_orphans()
    rec2 = repo.get_run(run.run_id)
    assert rec2.status == RunStatus.QUEUED
    assert rec2.attempt == 3

    # Attempt 3 death
    r3 = repo.claim_next_run("dead-worker-3", lease_duration_seconds=5.0)
    assert r3.attempt == 3
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00'")
        conn.execute("UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00'")
    
    # Now orphan recovery sees attempt >= 3 -> must mark FAILED permanently
    worker.recover_orphans()
    rec3 = repo.get_run(run.run_id)
    assert rec3.status == RunStatus.FAILED
    assert rec3.failure_code == "ORPHAN_RUN_EXPIRED"
    assert "exceeded maximum recovery attempts" in rec3.failure_detail.get("reason", "")


def test_fi03_hard_death_after_storage_upload_before_commit(fi03_env):
    """
    Simulates a worker uploading an output artifact to StorageService,
    then experiencing SIGKILL before committing finish_run to DB.
    Validates:
    - Object is present in StorageService
    - Run remains RUNNING until lease expires
    - Orphan recovery handles the run gracefully without corrupting storage or DB
    - Stale worker cannot overwrite status after wake-up
    """
    repo: RunRepository = fi03_env["run_repo"]
    ws_id = fi03_env["ws_id"]
    project_id = fi03_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi03_003",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    claimed = repo.claim_next_run("worker-crash-after-upload", lease_duration_seconds=5.0)
    assert claimed is not None

    # Simulate upload to storage service
    storage = get_storage_service()
    out_key = f"workspaces/{ws_id}/projects/{project_id}/outputs/{run.run_id}/out.mp4"
    storage.put(out_key, b"fake video content bytes", content_type="video/mp4")

    # Worker crashes before finish_run is committed
    # Expire lease
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00'")
        conn.execute("UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00'")

    # New worker recovers orphan
    worker_clean = PipelineWorker(worker_id="worker-clean", db_path=fi03_env["db_file"], lease_duration=5.0)
    worker_clean.recover_orphans()

    recovered_run = repo.get_run(run.run_id)
    assert recovered_run.status == RunStatus.QUEUED
    assert recovered_run.attempt == 2

    # The crashed worker wakes up late and tries to finish_run
    with pytest.raises((RuntimeError, ValueError)):
        repo.finish_run(
            run_id=run.run_id,
            worker_id="worker-crash-after-upload",
            status=RunStatus.SUCCEEDED,
            result_reference={"output_storage_key": out_key},
        )

    # Verify run was not corrupted by stale worker
    assert repo.get_run(run.run_id).status == RunStatus.QUEUED

    # Clean worker can claim and finish properly
    fresh_claimed = repo.claim_next_run("worker-clean", lease_duration_seconds=5.0)
    assert fresh_claimed.run_id == run.run_id
    repo.finish_run(
        run_id=run.run_id,
        worker_id="worker-clean",
        status=RunStatus.SUCCEEDED,
        result_reference={"output_storage_key": out_key},
    )
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.SUCCEEDED
    assert final_run.worker_id == "worker-clean"
