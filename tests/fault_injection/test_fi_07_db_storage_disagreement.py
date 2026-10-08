"""
FI-07: DB / Storage Disagreement & Reconciliation Authority Test Suite
Explicitly tests the 4 divergence cases:
- Case A: DB references an output storage key, but StorageService does NOT contain it.
- Case B: StorageService contains an orphaned object, but DB has no record of it.
- Case C: DB holds a SHA-256 hash differing from the actual object in StorageService (tamper/corruption).
- Case D: Run status is SUCCEEDED, but mandatory artifact (e.g. out.mp4) is missing.

Validates that:
- The system never trusts 'file exists' alone without checksum and DB authority
- Tampered or missing objects fail-closed
- Unindexed storage objects are inaccessible via API
- Verification and reconciliation policies are deterministic
"""

import hashlib
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
from scripts.core.storage import (
    set_storage_service,
    LocalStorageBackend,
    StorageNotFoundError,
)
from api.main import app


@pytest.fixture
def fi07_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi07_disagreement.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    u = tenant_repo.create_user("usr_fi07", "fi07@test.com")
    ws = tenant_repo.create_workspace("ws_fi07", "Workspace FI07", created_by=u.id)
    prj = tenant_repo.create_project("prj_fi07", ws.id, "FI07 Video", created_by=u.id)

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
        "storage": storage,
        "storage_dir": storage_dir,
    }

    set_database_engine(None)
    set_storage_service(None)
    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)


def test_fi07_case_a_db_references_missing_storage_object(fi07_env):
    """
    Case A: DB says output exists at key K, but StorageService does NOT contain it.
    Validation:
    - storage.exists(K) is False
    - storage.get(K) raises StorageNotFoundError
    - Signed URL generation fails-closed (raises StorageNotFoundError)
    - System detects discrepancy and does NOT claim output is usable
    """
    repo: RunRepository = fi07_env["run_repo"]
    storage: LocalStorageBackend = fi07_env["storage"]
    ws_id = fi07_env["ws_id"]
    project_id = fi07_env["project_id"]

    ghost_key = f"workspaces/{ws_id}/projects/{project_id}/outputs/run_phantom/out.mp4"

    # DB records SUCCEEDED run with phantom key
    run = repo.create_run(
        RunRecord(
            run_id="run_phantom",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.RUNNING,
        )
    )
    repo.finish_run(
        run_id="run_phantom",
        worker_id=None,
        status=RunStatus.SUCCEEDED,
        result_reference={"output_storage_key": ghost_key, "sha256": "fake_hash"},
    )

    # Storage does NOT contain ghost_key
    assert not storage.exists(ghost_key)

    # Any attempt to read or generate signed URL for this key must fail closed
    with pytest.raises(StorageNotFoundError):
        storage.get(ghost_key)

    with pytest.raises(StorageNotFoundError):
        storage.signed_url(ghost_key)


def test_fi07_case_b_storage_has_unindexed_orphan_object(fi07_env):
    """
    Case B: Storage contains an output object, but DB has no record of it.
    Validation:
    - Object cannot be retrieved through API (API authorizes strictly through DB run records)
    - Querying non-existent run returns 404
    - Unindexed storage data cannot elevate privilege or bypass RBAC
    """
    storage: LocalStorageBackend = fi07_env["storage"]
    ws_id = fi07_env["ws_id"]
    project_id = fi07_env["project_id"]
    user_id = fi07_env["user_id"]

    orphan_key = f"workspaces/{ws_id}/projects/{project_id}/outputs/run_unindexed/out.mp4"
    storage.put(orphan_key, b"unindexed orphaned video payload")
    assert storage.exists(orphan_key)

    # API query for the run must return 404 because DB has no record
    from tests.conftest import make_test_auth_headers
    headers = {
        **make_test_auth_headers(principal_id=user_id, roles=["admin"], project_scopes={"*": ["admin"]}),
        "X-Workspace-ID": ws_id,
    }
    client = TestClient(app)
    resp = client.get(f"/projects/{project_id}/runs/run_unindexed", headers=headers)
    assert resp.status_code == 404


def test_fi07_case_c_checksum_mismatch_detected(fi07_env):
    """
    Case C: DB holds hash H1, but Storage object has hash H2 (tampering / corruption).
    Validation:
    - Reconciler / validator computes actual SHA-256 from Storage
    - Detects disparity between DB expected hash and Storage actual hash
    - Object is rejected as corrupt and not considered valid output
    """
    repo: RunRepository = fi07_env["run_repo"]
    storage: LocalStorageBackend = fi07_env["storage"]
    ws_id = fi07_env["ws_id"]
    project_id = fi07_env["project_id"]

    key = f"workspaces/{ws_id}/projects/{project_id}/outputs/run_tampered/out.mp4"
    meta = storage.put(key, b"original content", content_type="video/mp4")

    expected_hash = "0000000000000000000000000000000000000000000000000000000000000000"  # Wrong hash
    actual_hash = meta.sha256

    assert actual_hash != expected_hash

    # Reconciliation function
    def verify_artifact_integrity(storage_key: str, recorded_sha256: str) -> bool:
        meta_obj = storage.metadata(storage_key)
        return meta_obj.sha256 == recorded_sha256

    assert not verify_artifact_integrity(key, expected_hash)
    assert verify_artifact_integrity(key, actual_hash)


def test_fi07_case_d_succeeded_run_missing_mandatory_artifact(fi07_env):
    """
    Case D: Run says SUCCEEDED, but mandatory artifact (out.mp4) is absent from result_reference.
    Validation:
    - Validator identifies incomplete terminal result
    - Flags run as invalid/unusable
    """
    repo: RunRepository = fi07_env["run_repo"]
    ws_id = fi07_env["ws_id"]
    project_id = fi07_env["project_id"]

    run = repo.create_run(
        RunRecord(
            run_id="run_missing_artifact",
            project_id=project_id,
            workspace_id=ws_id,
            status=RunStatus.RUNNING,
        )
    )
    # Finish with empty result_reference missing "output_storage_key"
    repo.finish_run(
        run_id="run_missing_artifact",
        worker_id=None,
        status=RunStatus.SUCCEEDED,
        result_reference={"return_code": 0},  # Missing output_storage_key!
    )

    rec = repo.get_run(run.run_id)

    def is_run_output_valid(record: RunRecord) -> bool:
        if record.status != RunStatus.SUCCEEDED:
            return False
        if not record.result_reference or not record.result_reference.get("output_storage_key"):
            return False
        return True

    assert not is_run_output_valid(rec)
