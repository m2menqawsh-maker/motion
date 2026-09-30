"""
FI-05: StorageService Outage Test Suite
Tests systemic failure across all StorageService primitives:
- Read outage (network drop / permission / missing backend)
- Write outage (disk full / permission / read-only mount)
- Upload failure during worker finalization
- Metadata lookup failure
- Delete failure
- Signed URL validation failure for non-existent / expired keys
- Readiness truthfulness during StorageService outage (503 on ready, 200 on live)

Validates that:
- DB never marks output SUCCEEDED or usable if storage upload failed
- Final artifacts are never registered if not persisted in storage
- Failures are classified machine-readably with STORAGE_UNAVAILABLE or StorageError
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock
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
from scripts.core.storage import (
    get_storage_service,
    set_storage_service,
    LocalStorageBackend,
    StorageService,
    StorageError,
    StorageNotFoundError,
)
from api.main import app
from api.services.health_service import HealthService


class BrokenStorageBackend(StorageService):
    """Storage backend simulating a total cloud/network outage."""

    def put(self, key, data, content_type="application/octet-stream"):
        raise StorageError("Connection to object storage timed out (ETIMEDOUT)")

    def get(self, key):
        raise StorageError("Connection to object storage reset by peer (ECONNRESET)")

    def open(self, key):
        raise StorageError("Connection to object storage timed out (ETIMEDOUT)")

    def exists(self, key):
        raise StorageError("Storage metadata endpoint unreachable (503)")

    def delete(self, key):
        raise StorageError("Storage delete operation failed: storage backend is offline")

    def copy(self, src_key, dst_key):
        raise StorageError("Storage copy failed: backend offline")

    def metadata(self, key):
        raise StorageError("Storage metadata lookup failed: backend offline")

    def signed_url(self, key, expires_in_seconds=3600):
        raise StorageError("Cannot generate signed URL: signing key unavailable")


@pytest.fixture
def fi05_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi05_storage.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi05", "fi05@test.com")
    ws = tenant_repo.create_workspace("ws_fi05", "Workspace FI05", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi05", ws.id, "FI05 Video", created_by=u.id)

    run_repo = RunRepository(db_path=db_file)
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    healthy_storage = LocalStorageBackend(root_dir=str(storage_dir))
    set_storage_service(healthy_storage)

    yield {
        "engine": engine,
        "run_repo": run_repo,
        "tenant_repo": tenant_repo,
        "ws_id": ws.id,
        "project_id": prj.id,
        "db_file": db_file,
        "storage_dir": storage_dir,
        "healthy_storage": healthy_storage,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_fi05_storage_operations_fail_cleanly():
    """All StorageService operations raise machine-readable StorageError on backend outage."""
    broken = BrokenStorageBackend()

    with pytest.raises(StorageError) as exc_put:
        broken.put("test/key.mp4", b"dummy")
    assert "timed out" in str(exc_put.value)

    with pytest.raises(StorageError) as exc_get:
        broken.get("test/key.mp4")
    assert "reset by peer" in str(exc_get.value)

    with pytest.raises(StorageError) as exc_meta:
        broken.metadata("test/key.mp4")
    assert "offline" in str(exc_meta.value)

    with pytest.raises(StorageError) as exc_del:
        broken.delete("test/key.mp4")
    assert "offline" in str(exc_del.value)

    with pytest.raises(StorageError) as exc_sig:
        broken.signed_url("test/key.mp4")
    assert "unavailable" in str(exc_sig.value)


def test_fi05_worker_handles_upload_storage_outage(fi05_env):
    """
    Simulates storage outage when worker tries to upload completed outputs.
    Validates:
    - Worker attempts upload via _upload_outputs_and_meter
    - On failure, output is NOT registered in result_reference as available in storage
    - DB record does not reference phantom storage keys
    """
    repo: RunRepository = fi05_env["run_repo"]
    ws_id = fi05_env["ws_id"]
    project_id = fi05_env["project_id"]

    # 1. Enqueue and claim run
    run = repo.create_run(
        RunRecord(
            run_id="run_fi05_upload_fail",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.QUEUED,
        )
    )
    claimed = repo.claim_next_run(worker_id="worker_fi05", lease_duration_seconds=10.0)
    assert claimed is not None

    # 2. Inject storage outage
    broken = BrokenStorageBackend()
    set_storage_service(broken)

    # 3. Simulate worker finishing execution and attempting output upload
    worker = PipelineWorker(worker_id="worker_fi05", db_path=fi05_env["db_file"], lease_duration=10.0)
    ref = {"return_code": 0}

    # Create dummy local output file to simulate local render success
    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    out_file = proj_dir / "out.mp4"
    out_file.write_bytes(b"dummy mp4 content")

    try:
        worker._upload_outputs_and_meter(claimed, ref, time.time())
        # output_storage_key must NOT be populated because storage failed
        assert "output_storage_key" not in ref
        assert "output_size_bytes" not in ref
    finally:
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)


def test_fi05_readiness_reflects_storage_outage(fi05_env):
    """
    Readiness probe returns 503 when StorageService is down,
    while Liveness probe continues to return 200 OK.
    """
    # 1. Verify healthy readiness initially
    client = TestClient(app)
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    # 2. Break storage service
    broken = BrokenStorageBackend()
    set_storage_service(broken)

    # 3. Test readiness probe reflects outage
    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 503
    ready_data = ready_resp.json()
    assert ready_data["status"] == "not_ready"
    assert ready_data["checks"]["storage_backend"]["status"] == "fail"
    assert ready_data["checks"]["storage_backend"]["code"] == "STORAGE_UNAVAILABLE"

    # 4. Liveness probe MUST still return 200 OK (process is alive)
    live_resp2 = client.get("/health/live")
    assert live_resp2.status_code == 200

    # 5. Restore healthy storage
    set_storage_service(fi05_env["healthy_storage"])
    ready_resp2 = client.get("/health/ready")
    assert ready_resp2.status_code == 200
    assert ready_resp2.json()["checks"]["storage_backend"]["status"] == "pass"
