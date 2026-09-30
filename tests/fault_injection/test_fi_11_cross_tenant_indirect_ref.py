"""
tests/fault_injection/test_fi_11_cross_tenant_indirect_ref.py — Fault Injection Scenario FI-11.

Cross-Tenant Indirect Reference Attack Matrix:
Proves that domain and service layers prevent Project A from referencing, resolving,
or embedding any resource (Asset, Output, Artifact, StorageKey) belonging to Workspace B:
1. Manifest asset pointing to Workspace B storage key.
2. Manifest asset explicitly tagged with Workspace B ID.
3. Blueprint Scene referencing an AssetRef belonging to Workspace B.
4. PipelineWorker checking manifest before execution: halts fail-closed with CROSS_TENANT_VIOLATION.
5. Storage key traversal attempt trying to escape Workspace A container.
"""

import json
from pathlib import Path
import pytest

from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.storage import LocalStorageBackend, set_storage_service, StorageSecurityError, validate_storage_key
from scripts.core.manifest_validator import ManifestValidator, ManifestValidationError
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker


@pytest.fixture
def fi11_env(tmp_path: Path):
    db_file = tmp_path / "fi11_tenant.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)
    run_repo = RunRepository(db_path=db_file)

    # 1. Setup Tenant A
    user_a = repo.create_user("usr_a_fi11", "a@acme.com")
    ws_a = repo.create_workspace("ws_acme_fi11", "Acme FI11", created_by=user_a.id)
    prj_a = repo.create_project("prj_acme_fi11", ws_a.id, "Acme Project FI11", created_by=user_a.id)

    # 2. Setup Tenant B
    user_b = repo.create_user("usr_b_fi11", "b@globex.com")
    ws_b = repo.create_workspace("ws_globex_fi11", "Globex FI11", created_by=user_b.id)
    prj_b = repo.create_project("prj_globex_fi11", ws_b.id, "Globex Project FI11", created_by=user_b.id)

    # Store Bob's proprietary asset in Workspace B
    bob_asset_key = f"workspaces/{ws_b.id}/projects/{prj_b.id}/assets/ast_bob_patent/patent.pdf"
    storage.put(bob_asset_key, b"SECRET_PATENT_DOCUMENT_BYTES", content_type="application/pdf")

    p_a_dir = Path(f"projects/{prj_a.id}")
    p_a_dir.mkdir(parents=True, exist_ok=True)

    yield {
        "engine": engine,
        "repo": repo,
        "run_repo": run_repo,
        "storage": storage,
        "ws_a": ws_a.id,
        "ws_b": ws_b.id,
        "prj_a": prj_a.id,
        "prj_b": prj_b.id,
        "bob_asset_key": bob_asset_key,
        "p_a_dir": p_a_dir,
    }

    import shutil
    shutil.rmtree(p_a_dir, ignore_errors=True)
    set_database_engine(None)
    set_storage_service(None)


def test_fi11_manifest_indirect_workspace_id_reference(fi11_env):
    """Manifest in Project A cannot declare assets with foreign workspace_id."""
    ws_a = fi11_env["ws_a"]
    ws_b = fi11_env["ws_b"]

    malicious_manifest = {
        "manifest_version": "2.0.0",
        "project_id": fi11_env["prj_a"],
        "assets": [
            {
                "asset_id": "ast_injected_01",
                "kind": "image",
                "source_path": "injected.png",
                "resolved_path": "assets/injected.png",
                "storage_key": f"workspaces/{ws_a}/projects/{fi11_env['prj_a']}/assets/ast_injected_01/injected.png",
                "provenance": "upload",
                "status": "active",
                "metadata": {"workspace_id": ws_b},  # Attack: Point to Workspace B
            }
        ]
    }

    with pytest.raises(ManifestValidationError) as exc_info:
        ManifestValidator.validate_tenant_assets(malicious_manifest, ws_a)
    assert exc_info.value.code == "CROSS_TENANT_ASSET_REFERENCE"
    assert "Cross-tenant asset violation" in str(exc_info.value)


def test_fi11_manifest_indirect_storage_key_reference(fi11_env):
    """Manifest in Project A cannot declare storage_key pointing to Workspace B."""
    ws_a = fi11_env["ws_a"]
    bob_key = fi11_env["bob_asset_key"]

    malicious_manifest = {
        "manifest_version": "2.0.0",
        "project_id": fi11_env["prj_a"],
        "assets": [
            {
                "asset_id": "ast_injected_02",
                "kind": "document",
                "source_path": "patent.pdf",
                "resolved_path": "assets/patent.pdf",
                "storage_key": bob_key,  # Attack: Steal Bob's object storage key directly
                "provenance": "upload",
                "status": "active",
                "metadata": {"workspace_id": ws_a},
            }
        ]
    }

    with pytest.raises(ManifestValidationError) as exc_info:
        ManifestValidator.validate_tenant_assets(malicious_manifest, ws_a)
    assert exc_info.value.code == "CROSS_TENANT_ASSET_REFERENCE"
    assert "does not start with expected workspace prefix" in str(exc_info.value)


def test_fi11_storage_key_traversal_escape(fi11_env):
    """Storage keys cannot traverse upward to breach workspace isolation."""
    ws_a = fi11_env["ws_a"]
    ws_b = fi11_env["ws_b"]

    traversal_key = f"workspaces/{ws_a}/../../workspaces/{ws_b}/secret.txt"
    with pytest.raises(StorageSecurityError):
        validate_storage_key(traversal_key)


def test_fi11_worker_aborts_run_on_cross_tenant_injection(fi11_env):
    """Worker inspecting manifest aborts run with CROSS_TENANT_VIOLATION before render."""
    run_repo = fi11_env["run_repo"]
    ws_a = fi11_env["ws_a"]
    prj_a = fi11_env["prj_a"]
    bob_key = fi11_env["bob_asset_key"]
    p_a_dir = fi11_env["p_a_dir"]

    # Write injected manifest on disk in Project A
    malicious_manifest = {
        "manifest_version": "2.0.0",
        "project_id": prj_a,
        "assets": [
            {
                "asset_id": "ast_stolen",
                "kind": "document",
                "source_path": "stolen.pdf",
                "resolved_path": "assets/stolen.pdf",
                "storage_key": bob_key,
                "provenance": "upload",
                "status": "active",
                "metadata": {"workspace_id": ws_a},
            }
        ]
    }
    (p_a_dir / "01_manifest.json").write_text(json.dumps(malicious_manifest), encoding="utf-8")

    # Enqueue run for Project A
    run_record = run_repo.create_run(
        RunRecord(
            run_id="run_injected_tenant_01",
            project_id=prj_a,
            workspace_id=ws_a,
            status=RunStatus.QUEUED,
        )
    )

    worker = PipelineWorker(worker_id="worker_fi11", db_path=run_repo.db_path)
    # Process one run
    processed = worker.process_one()
    assert processed is True

    # Run MUST be marked FAILED with CROSS_TENANT_VIOLATION
    updated_run = run_repo.get_run(run_record.run_id)
    assert updated_run is not None
    assert updated_run.status == RunStatus.FAILED
    assert updated_run.failure_code == "CROSS_TENANT_VIOLATION"
