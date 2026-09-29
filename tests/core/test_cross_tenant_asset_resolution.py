"""
tests/core/test_cross_tenant_asset_resolution.py — Cross-Tenant Asset Attack & Storage Isolation (S24.5).
"""

from pathlib import Path
import pytest
import json

from api.services.asset_service import AssetService
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.storage import get_storage_service, LocalStorageBackend, set_storage_service
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.manifest_loader import load_manifest, save_manifest
from scripts.core.manifest_model import ManifestV2, AssetV2, AssetKind, Provenance, AssetStatus
from scripts.core.manifest_errors import ManifestValidationError


@pytest.fixture
def multi_tenant_fixture(tmp_path: Path):
    db_file = tmp_path / "tenant_assets.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)

    # Workspace A & Project A
    repo.create_user("usr_alice", "alice@example.com")
    repo.create_workspace("ws_a", "Workspace A", created_by="usr_alice")
    repo.create_project("prj_a", "ws_a", "Project A", created_by="usr_alice")

    # Workspace B & Project B
    repo.create_user("usr_bob", "bob@example.com")
    repo.create_workspace("ws_b", "Workspace B", created_by="usr_bob")
    repo.create_project("prj_b", "ws_b", "Project B", created_by="usr_bob")

    # Create directories
    p_a = tmp_path / "projects" / "prj_a"
    p_b = tmp_path / "projects" / "prj_b"
    p_a.mkdir(parents=True)
    p_b.mkdir(parents=True)

    yield engine, repo, p_a, p_b

    set_database_engine(None)
    set_storage_service(None)


def test_asset_upload_stores_in_storage_service_and_manifest(multi_tenant_fixture, monkeypatch):
    engine, repo, p_a, _ = multi_tenant_fixture
    monkeypatch.setattr(AssetService, "_get_project_dir", classmethod(lambda cls, pid: p_a))

    uploaded = AssetService.upload_asset(
        project_id="prj_a",
        content=b"\x89PNG\r\n\x1a\nfakeimagecontent",
        filename="alice_logo.png",
        asset_id="ast_alice_1",
    )

    assert uploaded["asset_id"] == "ast_alice_1"
    meta = uploaded["metadata"]
    assert meta["workspace_id"] == "ws_a"
    assert meta["storage_key"] == "workspaces/ws_a/projects/prj_a/assets/ast_alice_1/ast_alice_1.png"

    # Verify bytes stored in StorageService
    storage = get_storage_service()
    assert storage.exists(meta["storage_key"]) is True
    assert storage.get(meta["storage_key"]) == b"\x89PNG\r\n\x1a\nfakeimagecontent"


def test_cross_reference_attack_rejected_fail_closed(multi_tenant_fixture, monkeypatch):
    """
    Project A attempts to reference Bob's asset from Project B in its blueprint:
    MUST be rejected fail-closed with validation error.
    """
    engine, repo, p_a, p_b = multi_tenant_fixture

    # 1. Bob uploads asset into Project B
    monkeypatch.setattr(AssetService, "_get_project_dir", classmethod(lambda cls, pid: p_b))
    uploaded_b = AssetService.upload_asset(
        project_id="prj_b",
        content=b"\x89PNG\r\n\x1a\nbobsecret",
        filename="bob_secret.png",
        asset_id="ast_bob_secret",
    )
    assert uploaded_b["asset_id"] == "ast_bob_secret"

    # 2. Project A's manifest has only its own assets
    man_a = ManifestV2(
        project_id="prj_a",
        metadata={"workspace_id": "ws_a"},
        assets=[],
    )

    # 3. Project A's Blueprint deliberately references ast_bob_secret
    blueprint_a = {
        "schema_version": "2.0.0",
        "project_id": "prj_a",
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "aspect_ratio": "16:9",
        "duration_frames": 60,
        "scenes": [
            {
                "scene_id": "scene_0",
                "template": "animatedtext-element",
                "startFrame": 0,
                "durationFrames": 60,
                "media_refs": ["ast_bob_secret"],  # Deliberate Cross-Project / Cross-Tenant reference
                "content": {"text": "Attack Scene"},
            }
        ]
    }

    # 4. Validate Blueprint against Project A manifest -> MUST FAIL CLOSED
    val_result = validate_blueprint_v2(blueprint_a, expected_project_id="prj_a", manifest=man_a)
    assert val_result.ok is False
    assert any("ast_bob_secret" in err and "not found in manifest" in err for err in val_result.errors)


def test_cross_tenant_storage_key_in_manifest_rejected():
    """
    If a manifest contains an asset with a storage_key belonging to another workspace,
    ManifestV2 validation must reject it fail-closed.
    """
    manifest_data = {
        "manifest_version": "2.0.0",
        "project_id": "prj_a",
        "created_at": "2026-09-30T00:00:00Z",
        "metadata": {"workspace_id": "ws_a"},
        "assets": [
            {
                "asset_id": "ast_injected",
                "kind": "image",
                "provenance": "user_upload",
                "status": "ready",
                "source_path": "assets/ready/test.png",
                "processed_path": "assets/ready/test.png",
                "metadata": {
                    "workspace_id": "ws_b",  # Foreign workspace!
                    "storage_key": "workspaces/ws_b/projects/prj_b/assets/secret/stolen.png",
                }
            }
        ]
    }

    from scripts.core.manifest_validator import validate_manifest_semantic
    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest_semantic(manifest_data, expected_project_id="prj_a")

    assert exc_info.value.code == "CROSS_TENANT_ASSET_REFERENCE"
