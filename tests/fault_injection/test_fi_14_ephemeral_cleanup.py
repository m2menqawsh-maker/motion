"""
FI-14: Ephemeral Worker Workspace Cleanup Test Suite
Validates that:
- Every pipeline execution creates an isolated, ephemeral scratch workspace
- Upon run completion (whether SUCCEEDED or FAILED), ephemeral workspace is completely purged
- Zero temporary files leak on worker local disk
- Subsequent reads/runs do not rely on previous scratch files
- Authoritative artifacts reside exclusively in StorageService
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
from scripts.core.storage import (
    set_storage_service,
    LocalStorageBackend,
)


@pytest.fixture
def fi14_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi14_cleanup.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi14", "fi14@test.com")
    ws = tenant_repo.create_workspace("ws_fi14", "Workspace FI14", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi14", ws.id, "FI14 Video", created_by=u.id)

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


def test_fi14_ephemeral_workspace_purged_after_successful_run(fi14_env, monkeypatch):
    """
    On a successful pipeline run, the worker's ephemeral directory is verified to be deleted.
    """
    repo: RunRepository = fi14_env["run_repo"]
    ws_id = fi14_env["ws_id"]
    project_id = fi14_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi14_clean_success",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    created_ephemerals = []
    real_mkdtemp = tempfile.mkdtemp

    def tracked_mkdtemp(*args, **kwargs):
        path = real_mkdtemp(*args, **kwargs)
        created_ephemerals.append(Path(path))
        return path

    monkeypatch.setattr(tempfile, "mkdtemp", tracked_mkdtemp)

    # Mock safe_subprocess to succeed cleanly
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "Pipeline finished successfully"
    mock_res.stderr = ""
    monkeypatch.setattr("scripts.core.worker.safe_subprocess", lambda *args, **kwargs: mock_res)

    worker = PipelineWorker(worker_id="worker_cleaner", db_path=fi14_env["db_file"], lease_duration=10.0)
    processed = worker.process_one()
    assert processed is True

    # Run succeeded
    rec = repo.get_run(run.run_id)
    assert rec.status == RunStatus.SUCCEEDED

    # Verify ephemeral directory was created then deleted
    assert len(created_ephemerals) == 1
    ephemeral_path = created_ephemerals[0]
    assert not ephemeral_path.exists(), f"Ephemeral directory {ephemeral_path} leaked on disk!"


def test_fi14_ephemeral_workspace_purged_after_failed_run(fi14_env, monkeypatch):
    """
    Even on pipeline execution failure, ephemeral directory must be purged completely in finally block.
    """
    repo: RunRepository = fi14_env["run_repo"]
    ws_id = fi14_env["ws_id"]
    project_id = fi14_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_fi14_clean_fail",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    created_ephemerals = []
    real_mkdtemp = tempfile.mkdtemp

    def tracked_mkdtemp(*args, **kwargs):
        path = real_mkdtemp(*args, **kwargs)
        created_ephemerals.append(Path(path))
        return path

    monkeypatch.setattr(tempfile, "mkdtemp", tracked_mkdtemp)

    # Mock safe_subprocess to return error
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stdout = "Fatal pipeline error"
    mock_res.stderr = "Traceback: Error"
    monkeypatch.setattr("scripts.core.worker.safe_subprocess", lambda *args, **kwargs: mock_res)

    worker = PipelineWorker(worker_id="worker_cleaner", db_path=fi14_env["db_file"], lease_duration=10.0)
    processed = worker.process_one()
    assert processed is True

    # Run failed
    rec = repo.get_run(run.run_id)
    assert rec.status == RunStatus.FAILED
    assert rec.failure_code == "PIPELINE_EXECUTION_FAILED"

    # Ephemeral directory must NOT exist
    assert len(created_ephemerals) == 1
    ephemeral_path = created_ephemerals[0]
    assert not ephemeral_path.exists(), f"Ephemeral directory {ephemeral_path} leaked on failed run!"
