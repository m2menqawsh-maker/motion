"""
FI-17: Readiness & Liveness Truthfulness Test Suite
Systematically probes /health/live and /health/ready endpoints under various failure conditions:
- DB outage -> ready fails (503) with machine-readable code, live succeeds (200)
- Storage outage -> ready fails (503) with code STORAGE_UNAVAILABLE, live succeeds (200)
- Missing tooling (FFmpeg) -> ready fails (503), live succeeds (200)
- Healthy state -> ready returns 200 with all components marked 'pass'
"""

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from starlette.testclient import TestClient

from scripts.core.database import (
    DatabaseEngine,
    set_database_engine,
    TenantRepository,
)
from scripts.core.storage import (
    set_storage_service,
    LocalStorageBackend,
    StorageService,
    StorageError,
)
from api.main import app
from api.services.health_service import HealthService


class BrokenStorage(StorageService):
    def put(self, key, data, content_type="application/octet-stream"):
        raise StorageError("Storage disk unreachable")
    def get(self, key): raise StorageError("offline")
    def open(self, key): raise StorageError("offline")
    def exists(self, key): raise StorageError("offline")
    def delete(self, key): raise StorageError("offline")
    def copy(self, src, dst): raise StorageError("offline")
    def metadata(self, key): raise StorageError("offline")
    def signed_url(self, key, expires_in_seconds=3600): raise StorageError("offline")


@pytest.fixture
def fi17_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi17_health.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi17", "fi17@test.com")
    tenant_repo.create_workspace("ws_fi17", "Workspace FI17", created_by=u.id)

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    healthy_storage = LocalStorageBackend(root_dir=str(storage_dir))
    set_storage_service(healthy_storage)

    yield {
        "engine": engine,
        "db_file": db_file,
        "healthy_storage": healthy_storage,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_fi17_healthy_readiness_and_liveness(fi17_env):
    """When all subsystems are operational, live=200 and ready=200 with all checks passing."""
    client = TestClient(app)

    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    data = ready.json()
    assert data["status"] == "ready"
    assert data["checks"]["runs_db"]["status"] == "pass"
    assert data["checks"]["database"]["status"] == "pass"
    assert data["checks"]["storage_backend"]["status"] == "pass"


def test_fi17_database_outage_fails_ready_keeps_live_200(fi17_env, monkeypatch):
    """When DatabaseEngine is down, /health/ready returns 503 with DATABASE_UNAVAILABLE while /health/live returns 200."""
    client = TestClient(app)

    # Simulate database connection outage
    def broken_connect():
        raise ConnectionRefusedError("Database server at postgres:5432 unreachable")

    monkeypatch.setattr(fi17_env["engine"], "get_connection", broken_connect)

    ready = client.get("/health/ready")
    assert ready.status_code == 503
    data = ready.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["database"]["status"] == "fail"
    assert data["checks"]["database"]["code"] == "DATABASE_UNAVAILABLE"
    assert "unreachable" in data["checks"]["database"]["reason"]

    # Liveness MUST remain 200 (process is still alive)
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"


def test_fi17_storage_outage_fails_ready_keeps_live_200(fi17_env):
    """When StorageService is down, /health/ready returns 503 with STORAGE_UNAVAILABLE while /health/live returns 200."""
    client = TestClient(app)

    set_storage_service(BrokenStorage())

    ready = client.get("/health/ready")
    assert ready.status_code == 503
    data = ready.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["storage_backend"]["status"] == "fail"
    assert data["checks"]["storage_backend"]["code"] == "STORAGE_UNAVAILABLE"

    # Liveness probe remains 200
    live = client.get("/health/live")
    assert live.status_code == 200

    # Restore healthy storage
    set_storage_service(fi17_env["healthy_storage"])


def test_fi17_missing_tooling_fails_ready(fi17_env, monkeypatch):
    """When critical tooling (FFmpeg) fails or is missing, readiness probe fails with 503."""
    client = TestClient(app)

    # Mock FFmpeg check to return failure
    def mock_probe_ffmpeg(timeout):
        return False, {
            "status": "fail",
            "reason": "ffmpeg executable not found in PATH or returned error",
            "code": "FFMPEG_UNAVAILABLE",
        }

    monkeypatch.setattr(HealthService, "_probe_ffmpeg", mock_probe_ffmpeg)

    ready = client.get("/health/ready")
    assert ready.status_code == 503
    data = ready.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["ffmpeg"]["status"] == "fail"
    assert data["checks"]["ffmpeg"]["code"] == "FFMPEG_UNAVAILABLE"

    # Liveness probe still 200
    live = client.get("/health/live")
    assert live.status_code == 200
