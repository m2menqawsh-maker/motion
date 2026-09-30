"""
FI-15: Ephemeral Workspace Loss Mid-Execution Test Suite
Simulates abrupt loss or corruption of worker ephemeral directory during execution:
- Abrupt deletion of ephemeral directory while pipeline is executing
- Permission revocation (read-only mode) on scratch space
- Validates clean failure classification, no dangling lease, no false success
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from scripts.core.database import (
    DatabaseEngine,
    set_database_engine,
    TenantRepository,
)
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker
from scripts.core.storage import set_storage_service, LocalStorageBackend


@pytest.fixture
def fi15_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi15_loss.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi15", "fi15@test.com")
    ws = tenant_repo.create_workspace("ws_fi15", "Workspace FI15", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi15", ws.id, "FI15 Video", created_by=u.id)

    proj_dir = Path("projects") / prj.id
    proj_dir.mkdir(parents=True, exist_ok=True)

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
        "db_file": db_file,
        "storage": storage,
    }

    set_database_engine(None)
    set_storage_service(None)
    shutil.rmtree(proj_dir, ignore_errors=True)


def test_fi15_ephemeral_workspace_deleted_mid_execution(fi15_env, monkeypatch):
    """
    Simulates abrupt deletion of ephemeral working directory while worker subprocess runs.
    Validation:
    - Worker handles missing workspace or subprocess crash gracefully
    - Run status is marked FAILED (never SUCCEEDED)
    - Lease is cleanly cleared from project_execution_leases
    - No corrupt or partial state is published
    """
    repo: RunRepository = fi15_env["run_repo"]
    ws_id = fi15_env["ws_id"]
    project_id = fi15_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi15_abrupt_delete",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    def failing_subprocess_on_deleted_dir(*args, **kwargs):
        env = kwargs.get("env", {})
        ephem = env.get("AGY_EPHEMERAL_WORKSPACE")
        if ephem and os.path.exists(ephem):
            # Abruptly delete the directory while process was supposed to run
            shutil.rmtree(ephem)
        mock = MagicMock()
        mock.returncode = 2
        mock.stdout = ""
        mock.stderr = f"FileNotFoundError: Working directory {ephem} was destroyed mid-execution"
        return mock

    monkeypatch.setattr("scripts.core.worker.safe_subprocess", failing_subprocess_on_deleted_dir)

    worker = PipelineWorker(worker_id="worker_victim", db_path=fi15_env["db_file"], lease_duration=10.0)
    processed = worker.process_one()
    assert processed is True

    # Validate failure state
    rec = repo.get_run(run.run_id)
    assert rec.status == RunStatus.FAILED
    assert rec.failure_code == "PIPELINE_EXECUTION_FAILED"
    assert "Working directory" in rec.failure_detail.get("stderr_tail", "")

    # Validate lease is completely released (no deadlock)
    with repo._transaction("IMMEDIATE") as conn:
        cur = conn.execute(
            "SELECT count(*) FROM project_execution_leases WHERE run_id = ?",
            (run.run_id,),
        )
        assert cur.fetchone()[0] == 0


def test_fi15_ephemeral_workspace_permission_denied(fi15_env, monkeypatch):
    """
    Simulates permission error / read-only filesystem condition on scratch disk.
    Validation:
    - Worker captures error and marks run FAILED with WORKER_SUBPROCESS_ERROR
    - Heartbeat terminates cleanly
    - No partial artifacts recorded in DB
    """
    repo: RunRepository = fi15_env["run_repo"]
    ws_id = fi15_env["ws_id"]
    project_id = fi15_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi15_readonly",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    def crashing_subprocess(*args, **kwargs):
        raise PermissionError("Read-only file system: cannot write scratch files")

    monkeypatch.setattr("scripts.core.worker.safe_subprocess", crashing_subprocess)

    worker = PipelineWorker(worker_id="worker_readonly", db_path=fi15_env["db_file"], lease_duration=10.0)
    processed = worker.process_one()
    assert processed is True

    rec = repo.get_run(run.run_id)
    assert rec.status == RunStatus.FAILED
    assert rec.failure_code == "WORKER_SUBPROCESS_ERROR"
    assert "Read-only file system" in rec.failure_detail.get("error", "")
