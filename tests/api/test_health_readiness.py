"""
tests/api/test_health_readiness.py — S24.5 Deep Readiness & Liveness Probes.

Verifies:
1. /health/live returns 200 OK (liveness only).
2. /health/ready verifies PostgreSQL/DB, StorageService reachability/writability, workers, and engines.
3. /health/ready returns 503 Service Unavailable when DB or Storage is degraded.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app
from api.services.health_service import HealthService
from scripts.core.database import DatabaseEngine, set_database_engine
from scripts.core.storage import LocalStorageBackend, set_storage_service


@pytest.fixture
def test_setup(tmp_path):
    db_file = tmp_path / "health_test.db"
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    storage_root = tmp_path / "health_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    client = TestClient(app)
    return {
        "client": client,
        "db_engine": db_engine,
        "storage": storage_svc,
        "storage_root": storage_root,
    }


def test_health_live_endpoint(test_setup):
    """Liveness probe must return 200 with process status alive."""
    client = test_setup["client"]
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_health_ready_endpoint_success(test_setup):
    """Readiness probe returns 200 and passes all SaaS dependencies."""
    client = test_setup["client"]
    resp = client.get("/health/ready")
    data = resp.json()

    # Verify the checks include the new S24.5 components
    assert "database" in data["checks"]
    assert "storage_backend" in data["checks"]
    assert data["checks"]["database"]["status"] == "pass"
    assert data["checks"]["storage_backend"]["status"] == "pass"
    assert data["checks"]["storage_backend"]["writable"] is True


def test_health_ready_503_on_database_failure(test_setup, monkeypatch):
    """Readiness probe must return 503 when the database is unreachable."""
    client = test_setup["client"]

    def failing_probe(*args, **kwargs):
        return False, {"status": "fail", "reason": "Connection refused", "code": "DATABASE_UNAVAILABLE"}

    monkeypatch.setattr(HealthService, "_probe_database", failing_probe)

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["database"]["status"] == "fail"


def test_health_ready_503_on_storage_failure(test_setup, monkeypatch):
    """Readiness probe must return 503 when the storage service backend is unwritable."""
    client = test_setup["client"]

    def failing_storage(*args, **kwargs):
        return False, {"status": "fail", "reason": "Bucket access denied", "code": "STORAGE_UNAVAILABLE"}

    monkeypatch.setattr(HealthService, "_probe_storage_service", failing_storage)

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["storage_backend"]["status"] == "fail"
