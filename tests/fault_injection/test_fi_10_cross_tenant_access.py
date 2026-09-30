"""
tests/fault_injection/test_fi_10_cross_tenant_access.py — Fault Injection Scenario FI-10.

Cross-Tenant Direct Access Attack Matrix:
Proves that User B cannot access, read, modify, delete, execute, or download
any resource belonging to Workspace A / Project A across all endpoints and layers:
- Project ID
- Asset ID (read, upload, delete)
- Run ID (list, start, status, cancel)
- Review / Approval ID (get review, approve, reject)
- Artifact ID (list, fetch)
- Output ID (streaming, download)
- Guessed / Sequential identifiers

Fail-closed invariant: HTTP 403 Forbidden or 404 Not Found everywhere.
Zero information leakage.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.storage import LocalStorageBackend, set_storage_service, build_storage_key
from scripts.core.security.principal import Principal, Role, PrincipalType
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.state_model import LifecycleState, ProjectState, ReviewBundle


@pytest.fixture
def fi10_env(tmp_path: Path):
    db_file = tmp_path / "fi10_tenant.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)
    run_repo = RunRepository(db_path=db_file)

    # 1. Provision Workspace A & Project A (Acme Corp)
    user_a = repo.create_user("usr_alice", "alice@acme.com")
    ws_a = repo.create_workspace("ws_acme", "Acme Workspace", created_by=user_a.id)
    prj_a = repo.create_project("prj_acme_001", ws_a.id, "Acme Project", created_by=user_a.id)

    # 2. Provision Workspace B & Project B (Globex Inc)
    user_b = repo.create_user("usr_bob", "bob@globex.com")
    ws_b = repo.create_workspace("ws_globex", "Globex Workspace", created_by=user_b.id)
    prj_b = repo.create_project("prj_globex_001", ws_b.id, "Globex Project", created_by=user_b.id)

    # 3. Create initial artifacts and storage assets in Project A
    p_a_dir = Path(f"projects/{prj_a.id}")
    p_a_dir.mkdir(parents=True, exist_ok=True)
    manifest_a = {
        "manifest_version": "2.0.0",
        "project_id": prj_a.id,
        "assets": [
            {
                "asset_id": "ast_secret_logo",
                "kind": "image",
                "source_path": "logo.png",
                "resolved_path": "assets/ast_secret_logo.png",
                "storage_key": f"workspaces/{ws_a.id}/projects/{prj_a.id}/assets/ast_secret_logo/logo.png",
                "provenance": "upload",
                "status": "active",
                "metadata": {"workspace_id": ws_a.id},
            }
        ]
    }
    (p_a_dir / "01_manifest.json").write_text(json.dumps(manifest_a), encoding="utf-8")
    (p_a_dir / "00_state.json").write_text(json.dumps({"project_id": prj_a.id, "revision": 1, "lifecycle_state": "DRAFT"}), encoding="utf-8")

    # Store payload in StorageService
    key_a = f"workspaces/{ws_a.id}/projects/{prj_a.id}/assets/ast_secret_logo/logo.png"
    storage.put(key_a, b"SECRET_ALICE_LOGO_PNG_DATA", content_type="image/png")

    # Output file
    out_key = f"workspaces/{ws_a.id}/projects/{prj_a.id}/outputs/run_alice_123/out.mp4"
    storage.put(out_key, b"SECRET_ALICE_RENDERED_VIDEO_BYTES", content_type="video/mp4")

    # Seed run in RunRepository
    run_a = run_repo.create_run(
        RunRecord(
            run_id="run_alice_123",
            project_id=prj_a.id,
            workspace_id=ws_a.id,
            status=RunStatus.SUCCEEDED,
            result_reference={"output_storage_key": out_key}
        )
    )

    client = TestClient(app)

    # Auth headers for Bob (member of ws_globex only)
    principal_bob = Principal(
        principal_id=user_b.id,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},  # Admin in ws_globex
        project_scopes={"prj_globex_001": {Role.ADMIN}}
    )
    token_bob = create_signed_token(principal_bob)
    headers_bob = {
        "Authorization": f"Bearer {token_bob}",
        "X-Principal-ID": user_b.id,
        "X-Principal-Roles": "admin",
        "X-Workspace-ID": ws_b.id,
    }

    # Auth headers for Alice (member of ws_acme only)
    principal_alice = Principal(
        principal_id=user_a.id,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
        project_scopes={"prj_acme_001": {Role.ADMIN}}
    )
    token_alice = create_signed_token(principal_alice)
    headers_alice = {
        "Authorization": f"Bearer {token_alice}",
        "X-Principal-ID": user_a.id,
        "X-Principal-Roles": "admin",
        "X-Workspace-ID": ws_a.id,
    }

    yield {
        "client": client,
        "headers_bob": headers_bob,
        "headers_alice": headers_alice,
        "prj_a": prj_a.id,
        "prj_b": prj_b.id,
        "ws_a": ws_a.id,
        "ws_b": ws_b.id,
        "run_a": run_a.run_id,
        "storage": storage,
    }

    # Cleanup
    import shutil
    shutil.rmtree(p_a_dir, ignore_errors=True)
    set_database_engine(None)
    set_storage_service(None)


def test_fi10_project_direct_access(fi10_env):
    """User B attempts direct operations on Project A."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]
    prj_a = fi10_env["prj_a"]

    # 1. Read Project A
    res = client.get(f"/projects/{prj_a}", headers=headers_b)
    assert res.status_code in (403, 404), f"Expected 403/404, got {res.status_code}: {res.text}"

    # 2. Update Project A
    res = client.put(f"/projects/{prj_a}/brand", json={"primaryColor": "#ff0000"}, headers=headers_b)
    assert res.status_code in (403, 404)


def test_fi10_asset_direct_access(fi10_env):
    """User B attempts to list, read, upload, or delete assets in Project A."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]
    prj_a = fi10_env["prj_a"]

    # 1. List assets of Project A
    res = client.get(f"/projects/{prj_a}/assets", headers=headers_b)
    assert res.status_code in (403, 404)

    # 2. Get asset details
    res = client.get(f"/projects/{prj_a}/assets/ast_secret_logo", headers=headers_b)
    assert res.status_code in (403, 404)

    # 3. Upload asset into Project A
    res = client.post(
        f"/projects/{prj_a}/assets",
        files={"file": ("hack.png", b"HACK_DATA", "image/png")},
        headers=headers_b,
    )
    assert res.status_code in (403, 404)

    # 4. Delete asset from Project A
    res = client.delete(f"/projects/{prj_a}/assets/ast_secret_logo", headers=headers_b)
    assert res.status_code in (403, 404)


def test_fi10_runs_direct_access(fi10_env):
    """User B attempts to list runs, start a run, get run details, or cancel run in Project A."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]
    prj_a = fi10_env["prj_a"]
    run_a = fi10_env["run_a"]

    # 1. List runs
    res = client.get(f"/projects/{prj_a}/runs", headers=headers_b)
    assert res.status_code in (403, 404)

    # 2. Start run in Project A
    res = client.post(f"/projects/{prj_a}/runs", headers=headers_b)
    assert res.status_code in (403, 404)

    # 3. Get run status
    res = client.get(f"/projects/{prj_a}/runs/{run_a}", headers=headers_b)
    assert res.status_code in (403, 404)

    # 4. Cancel run in Project A
    res = client.post(f"/projects/{prj_a}/runs/{run_a}/cancel", headers=headers_b)
    assert res.status_code in (403, 404)


def test_fi10_review_and_approvals(fi10_env):
    """User B attempts to read review bundle, approve, or reject Project A."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]
    prj_a = fi10_env["prj_a"]

    # 1. Read review
    res = client.get(f"/projects/{prj_a}/artifacts/review", headers=headers_b)
    assert res.status_code in (403, 404)

    # 2. Approve Project A
    res = client.post(f"/projects/{prj_a}/artifacts/review/decision", json={"decision": "APPROVED", "reason": "malicious approve"}, headers=headers_b)
    assert res.status_code in (403, 404)

    # 3. Reject Project A
    res = client.post(f"/projects/{prj_a}/artifacts/review/decision", json={"decision": "REJECTED", "reason": "malicious reject"}, headers=headers_b)
    assert res.status_code in (403, 404)


def test_fi10_output_and_streaming(fi10_env):
    """User B attempts to stream or download rendered output of Project A."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]
    prj_a = fi10_env["prj_a"]

    # 1. Download/stream out.mp4
    res = client.get(f"/projects/{prj_a}/outputs/out.mp4", headers=headers_b)
    assert res.status_code in (403, 404)

    # 2. Guessed run output
    res = client.get(f"/projects/{prj_a}/outputs/run_alice_123_out.mp4", headers=headers_b)
    assert res.status_code in (403, 404)


def test_fi10_guessed_identifiers(fi10_env):
    """User B probes guessed/sequential project identifiers."""
    client = fi10_env["client"]
    headers_b = fi10_env["headers_bob"]

    for guessed_id in ["prj_acme_002", "prj_00000001", "prj_admin", "prj_default"]:
        res = client.get(f"/projects/{guessed_id}", headers=headers_b)
        assert res.status_code in (403, 404)
        res_assets = client.get(f"/projects/{guessed_id}/assets", headers=headers_b)
        assert res_assets.status_code in (403, 404)
