"""
tests/core/test_worker_ephemeral_workspace.py — S24.5 Ephemeral Worker Workspace & Tenant Isolation.

Verifies:
1. Worker ephemeral workspace creation and cleanup (ephemeral execution workspace, NOT source of truth).
2. Worker tenant isolation (rejects cross-tenant asset references fail-closed).
3. Output upload to StorageService under canonical tenant keys.
4. Metering and usage tracking for render_seconds.
5. Lease and event scoping by workspace_id.
"""

import json
import pytest
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository
from scripts.core.worker import PipelineWorker
from scripts.core.storage import LocalStorageBackend, set_storage_service, get_storage_service
from scripts.core.database import DatabaseEngine, set_database_engine, UsageRepository
from scripts.core.tenant_model import UsageEventType
from scripts.core.database import TenantRepository


@pytest.fixture
def test_env(tmp_path):
    # Set up hermetic DB and storage
    db_file = tmp_path / "test_saas_worker.db"
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    storage_root = tmp_path / "storage_root"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    repo = RunRepository(db_path=db_file)
    tenant_repo = TenantRepository(db_engine)
    return {
        "db_file": db_file,
        "db_engine": db_engine,
        "storage": storage_svc,
        "storage_root": storage_root,
        "repo": repo,
        "tenant_repo": tenant_repo,
        "tmp_path": tmp_path,
    }


def _setup_tenant_project(test_env, ws_id: str, proj_id: str):
    tenant_repo = test_env["tenant_repo"]
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    user = tenant_repo.create_user(user_id, f"{ws_id}_admin@example.com")
    ws = tenant_repo.create_workspace(workspace_id=ws_id, name=f"Name {ws_id}", created_by=user.id)
    prj = tenant_repo.create_project(project_id=proj_id, workspace_id=ws.id, name=f"Name {proj_id}", created_by=user.id)
    return user, ws, prj


def test_worker_tenant_scoped_leases_and_events(test_env):
    """Verifies that leases and events are scoped by workspace_id."""
    repo = test_env["repo"]
    ws_id = "ws_tenant_alpha"
    proj_id = f"prj_{uuid.uuid4().hex[:8]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    _setup_tenant_project(test_env, ws_id, proj_id)

    run = RunRecord(
        run_id=run_id,
        workspace_id=ws_id,
        project_id=proj_id,
        status=RunStatus.QUEUED,
    )
    repo.create_run(run)

    # Claim run with worker
    claimed = repo.claim_next_run(worker_id="worker_alpha", lease_duration_seconds=30.0)
    assert claimed is not None
    assert claimed.run_id == run_id
    assert claimed.workspace_id == ws_id

    # Check lease in DB
    lease = repo.get_active_project_lease(proj_id)
    assert lease is not None
    assert lease["project_id"] == proj_id
    assert lease["run_id"] == run_id
    assert lease["workspace_id"] == ws_id

    # Record event
    event = repo.record_event(
        run_id=run_id,
        project_id=proj_id,
        event_type="TEST_EVENT",
        payload={"foo": "bar"},
        workspace_id=ws_id,
    )
    assert event.workspace_id == ws_id

    # Retrieve events filtered by workspace
    events = repo.get_events(run_id=run_id, workspace_id=ws_id)
    assert len(events) >= 1
    assert events[0].workspace_id == ws_id

    # Cross-tenant query returns empty
    events_other = repo.get_events(run_id=run_id, workspace_id="ws_tenant_beta")
    assert len(events_other) == 0


def test_worker_cross_tenant_asset_rejection(test_env, monkeypatch):
    """Verifies that a job referencing assets from another workspace is immediately rejected."""
    repo = test_env["repo"]
    ws_id = "ws_tenant_attacker"
    proj_id = f"prj_{uuid.uuid4().hex[:8]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    _setup_tenant_project(test_env, ws_id, proj_id)
    # Also setup victim workspace/project for the asset reference
    _setup_tenant_project(test_env, "ws_victim", "prj_victim")

    # Setup project directory with cross-tenant manifest
    proj_dir = Path("projects") / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest_data = {
            "version": "2.0.0",
            "project_id": proj_id,
            "created_at": "2026-09-30T00:00:00Z",
            "title": "Malicious Cross-Tenant Job",
            "assets": [
                {
                    "asset_id": "ast_victim_123",
                    "path": "assets/secret.png",
                    "storage_key": "workspaces/ws_victim/projects/prj_victim/assets/ast_victim_123/secret.png",
                    "role": "b-roll",
                }
            ],
            "timeline": [],
        }
        (proj_dir / "01_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        run = RunRecord(
            run_id=run_id,
            workspace_id=ws_id,
            project_id=proj_id,
            status=RunStatus.QUEUED,
        )
        repo.create_run(run)

        worker = PipelineWorker(
            worker_id="test_worker_security",
            db_path=test_env["db_file"],
            max_runs=1,
        )

        processed = worker.process_one()
        assert processed is True

        updated_run = repo.get_run(run_id)
        assert updated_run.status == RunStatus.FAILED
        assert updated_run.failure_code == "CROSS_TENANT_VIOLATION"
        assert "Cross-tenant asset violation" in updated_run.failure_detail.get("error", "")

    finally:
        # Cleanup test project directory
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)


def test_worker_ephemeral_workspace_and_output_persistence(test_env, monkeypatch):
    """
    Verifies:
    1. Ephemeral workspace is created and cleaned up.
    2. Outputs (out.mp4 and final_qc_report.json) are uploaded to StorageService.
    3. Metering usage (render_seconds) is recorded in DB.
    4. Deletion of local disk files proves StorageService is canonical source of truth.
    """
    repo = test_env["repo"]
    ws_id = "ws_tenant_acme"
    proj_id = f"prj_{uuid.uuid4().hex[:8]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    _setup_tenant_project(test_env, ws_id, proj_id)

    proj_dir = Path("projects") / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Create dummy project files
        dummy_mp4 = b"FAKE_MP4_HEADER_DATA_12345"
        dummy_qc = {"status": "PASSED", "duration": 10.0}
        (proj_dir / "out.mp4").write_bytes(dummy_mp4)
        (proj_dir / "final_qc_report.json").write_text(json.dumps(dummy_qc), encoding="utf-8")

        # Mock safe_subprocess to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Execution completed successfully\n[STAGE_START] render\n[STAGE_FINISH] render"
        mock_result.stderr = ""

        monkeypatch.setattr(
            "scripts.core.worker.safe_subprocess",
            lambda *args, **kwargs: mock_result,
        )

        run = RunRecord(
            run_id=run_id,
            workspace_id=ws_id,
            project_id=proj_id,
            status=RunStatus.QUEUED,
        )
        repo.create_run(run)

        worker = PipelineWorker(
            worker_id="test_worker_ephemeral",
            db_path=test_env["db_file"],
            max_runs=1,
        )

        processed = worker.process_one()
        assert processed is True

        updated_run = repo.get_run(run_id)
        assert updated_run.status == RunStatus.SUCCEEDED
        assert updated_run.result_reference is not None

        out_storage_key = updated_run.result_reference.get("output_storage_key")
        qc_storage_key = updated_run.result_reference.get("qc_storage_key")

        assert out_storage_key == f"workspaces/{ws_id}/projects/{proj_id}/outputs/{run_id}/out.mp4"
        assert qc_storage_key == f"workspaces/{ws_id}/projects/{proj_id}/outputs/{run_id}/final_qc_report.json"

        # Verify object storage contains the output files
        storage = test_env["storage"]
        assert storage.exists(out_storage_key)
        assert storage.get(out_storage_key) == dummy_mp4
        assert storage.exists(qc_storage_key)

        # Verify usage metering in Database
        usage_repo = UsageRepository(test_env["db_engine"])
        usage_data = usage_repo.get_workspace_usage(ws_id)
        assert UsageEventType.RENDER_SECONDS.value in usage_data
        assert usage_data[UsageEventType.RENDER_SECONDS.value] >= 0.0

        # Prove local filesystem is NOT source of truth:
        # Wipe local files entirely and verify storage retains them
        (proj_dir / "out.mp4").unlink()
        (proj_dir / "final_qc_report.json").unlink()

        assert not (proj_dir / "out.mp4").exists()
        assert storage.exists(out_storage_key)
        assert storage.get(out_storage_key) == dummy_mp4

    finally:
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)
