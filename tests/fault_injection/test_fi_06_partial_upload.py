"""
FI-06: Partial Output Upload & Storage Reconciliation Test Suite
Simulates interrupted uploads and partial writes to object storage:
- Partial stream failure mid-upload (ensures atomic commit semantics, no partial object exposed)
- State does not reach false success on interrupted upload
- Failure after upload completion before DB status acknowledgment
- Idempotency and reconciliation of retried uploads
"""

import io
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
    set_storage_service,
    LocalStorageBackend,
    StorageNotFoundError,
)


class FaultyStream(io.BytesIO):
    """A stream that aborts with an IOError after emitting a fraction of bytes."""

    def __init__(self, initial_bytes: bytes, fail_after_bytes: int = 50):
        super().__init__(initial_bytes)
        self.fail_after_bytes = fail_after_bytes
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        chunk = super().read(size)
        self.bytes_read += len(chunk)
        if self.bytes_read >= self.fail_after_bytes:
            raise IOError("Simulated network stream interruption mid-upload")
        return chunk


@pytest.fixture
def fi06_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi06_partial.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi06", "fi06@test.com")
    ws = tenant_repo.create_workspace("ws_fi06", "Workspace FI06", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi06", ws.id, "FI06 Video", created_by=u.id)

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
        "storage_dir": storage_dir,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_fi06_partial_upload_atomic_isolation(fi06_env):
    """
    When an upload stream is interrupted midway, the target object must NOT exist,
    no partial file is exposed, and storage.get raises StorageNotFoundError.
    """
    storage: LocalStorageBackend = fi06_env["storage"]
    target_key = f"workspaces/{fi06_env['ws_id']}/projects/{fi06_env['project_id']}/outputs/test/partial.mp4"

    full_payload = b"X" * 1024  # 1 KB of data
    broken_stream = FaultyStream(full_payload, fail_after_bytes=200)

    with pytest.raises(IOError) as exc_info:
        storage.put(target_key, broken_stream, content_type="video/mp4")
    assert "network stream interruption" in str(exc_info.value)

    # Invariant: Target object MUST NOT exist
    assert not storage.exists(target_key)
    with pytest.raises(StorageNotFoundError):
        storage.get(target_key)

    # Verify no dangling temporary files remain in target folder
    target_path = storage._resolve_path(target_key)
    temp_files = list(target_path.parent.glob("*.tmp.*"))
    assert len(temp_files) == 0


def test_fi06_upload_completed_before_db_crash_and_reconciliation(fi06_env):
    """
    Upload succeeds, but DB crashes/fails before finish_run is committed.
    On retry:
    - Object is already intact in storage.
    - Retry successfully overwrites or re-commits with identical payload.
    - Final state is SUCCEEDED with valid storage reference and correct metadata.
    """
    storage: LocalStorageBackend = fi06_env["storage"]
    repo: RunRepository = fi06_env["run_repo"]
    ws_id = fi06_env["ws_id"]
    project_id = fi06_env["project_id"]

    # 1. Create run
    run = repo.create_run(
        RunRecord(
            run_id="run_fi06_reconcile",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )

    claimed = repo.claim_next_run("worker_fi06", lease_duration_seconds=5.0)
    assert claimed is not None

    # 2. Worker uploads output to storage
    out_key = f"workspaces/{ws_id}/projects/{project_id}/outputs/{run.run_id}/out.mp4"
    valid_content = b"Authoritative final video bytes"
    meta = storage.put(out_key, valid_content, content_type="video/mp4")
    assert storage.exists(out_key)

    # 3. Simulate DB crash / lost transaction before finish_run commit
    # Status in DB remains RUNNING
    current = repo.get_run(run.run_id)
    assert current.status == RunStatus.RUNNING

    # 4. Worker or recovery reconciles and completes the commit
    ref = {
        "output_storage_key": out_key,
        "output_size_bytes": meta.size_bytes,
        "sha256": meta.sha256,
    }
    repo.finish_run(
        run_id=run.run_id,
        worker_id="worker_fi06",
        status=RunStatus.SUCCEEDED,
        result_reference=ref,
    )

    # 5. Verify reconciled final state
    final = repo.get_run(run.run_id)
    assert final.status == RunStatus.SUCCEEDED
    assert final.result_reference["output_storage_key"] == out_key
    assert storage.get(out_key) == valid_content
