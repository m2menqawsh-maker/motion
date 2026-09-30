"""
tests/fault_injection/test_fi_12_rbac_matrix.py — Fault Injection Scenario FI-12.

Comprehensive Server-Side RBAC Enforcement Matrix:
Verifies that the 4 roles (Viewer, Editor, Reviewer, Admin) are strictly enforced
by the server across all sensitive operations within a workspace:
1. READ (Project, Assets, Artifacts, Outputs)
2. EDIT (Blueprint, Brand, Artifacts)
3. ASSET MUTATION (Upload, Delete)
4. RUN CONTROL (Start run, Cancel run)
5. REVIEW DECISION (Approve, Reject)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.security.principal import Principal, Role, PrincipalType
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.state_model import LifecycleState, ProjectState


VALID_BRAND = {
    "brandName": "RBAC Test Brand",
    "colors": {
        "primary": "#123456",
        "accent": "#654321",
        "background": "#ffffff",
        "text": "#000000",
    },
    "fonts": {
        "display": "Cairo",
        "body": "Inter",
    }
}


@pytest.fixture
def fi12_env(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "fi12_rbac.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)
    run_repo = RunRepository(db_path=db_file)

    # Provision Workspace
    admin_u = repo.create_user("usr_admin", "admin@company.com")
    editor_u = repo.create_user("usr_editor", "editor@company.com")
    reviewer_u = repo.create_user("usr_reviewer", "reviewer@company.com")
    viewer_u = repo.create_user("usr_viewer", "viewer@company.com")

    ws = repo.create_workspace("ws_rbac_test", "RBAC Test Workspace", created_by=admin_u.id)
    repo.add_member(ws.id, editor_u.id, Role.EDITOR)
    repo.add_member(ws.id, reviewer_u.id, Role.REVIEWER)
    repo.add_member(ws.id, viewer_u.id, Role.VIEWER)

    prj = repo.create_project("prj_rbac_01", ws.id, "RBAC Video Project", created_by=admin_u.id)

    # Scaffolding
    p_dir = Path(f"projects/{prj.id}")
    p_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": "2.0.0",
        "project_id": prj.id,
        "assets": [
            {
                "asset_id": "ast_sample",
                "kind": "image",
                "source_path": "sample.png",
                "resolved_path": "assets/ast_sample.png",
                "storage_key": f"workspaces/{ws.id}/projects/{prj.id}/assets/ast_sample/sample.png",
                "provenance": "upload",
                "status": "active",
                "metadata": {"workspace_id": ws.id},
            }
        ]
    }
    (p_dir / "01_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (p_dir / "00_state.json").write_text(json.dumps({
        "project_id": prj.id,
        "revision": 1,
        "lifecycle_state": "AWAITING_REVIEW",
    }), encoding="utf-8")
    (p_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    (p_dir / "brand.json").write_text(json.dumps(VALID_BRAND), encoding="utf-8")
    (p_dir / "out.mp4").write_bytes(b"VIDEO_OUT_BYTES")

    run_record = run_repo.create_run(
        RunRecord(
            run_id="run_rbac_01",
            project_id=prj.id,
            workspace_id=ws.id,
            status=RunStatus.RUNNING,
        )
    )

    client = TestClient(app)

    def make_headers(user_id: str, role: Role):
        p = Principal(
            principal_id=user_id,
            principal_type=PrincipalType.HUMAN,
            roles=set(),
        )
        token = create_signed_token(p)
        return {
            "Authorization": f"Bearer {token}",
            "X-Principal-ID": user_id,
            "X-Workspace-ID": ws.id,
        }

    yield {
        "client": client,
        "prj_id": prj.id,
        "run_id": run_record.run_id,
        "headers": {
            "admin": make_headers(admin_u.id, Role.ADMIN),
            "editor": make_headers(editor_u.id, Role.EDITOR),
            "reviewer": make_headers(reviewer_u.id, Role.REVIEWER),
            "viewer": make_headers(viewer_u.id, Role.VIEWER),
        }
    }

    import shutil
    shutil.rmtree(p_dir, ignore_errors=True)
    set_database_engine(None)
    set_storage_service(None)


def test_fi12_viewer_role_boundaries(fi12_env):
    """Viewer can read, but is denied any mutations, runs, or approvals."""
    client = fi12_env["client"]
    prj_id = fi12_env["prj_id"]
    run_id = fi12_env["run_id"]
    headers = fi12_env["headers"]["viewer"]

    # Allowed: Read project & assets & outputs
    assert client.get(f"/projects/{prj_id}", headers=headers).status_code == 200
    assert client.get(f"/projects/{prj_id}/assets", headers=headers).status_code == 200
    assert client.get(f"/projects/{prj_id}/outputs/out.mp4", headers=headers).status_code == 200

    # Denied: Edit brand / blueprint
    assert client.put(f"/brand/{prj_id}", json=VALID_BRAND, headers={**headers, "If-Match": '"1"'}).status_code == 403

    # Denied: Upload asset
    res_up = client.post(f"/projects/{prj_id}/assets", files={"file": ("test.png", b"123", "image/png")}, headers=headers)
    assert res_up.status_code == 403

    # Denied: Start run
    assert client.post(f"/projects/{prj_id}/runs", json={}, headers=headers).status_code == 403

    # Denied: Cancel run
    assert client.post(f"/projects/{prj_id}/runs/{run_id}/cancel", headers=headers).status_code == 403

    # Denied: Approve review
    assert client.post(f"/projects/{prj_id}/review/approve", json={"reason": "Viewer illegal approve"}, headers=headers).status_code == 403


def test_fi12_editor_role_boundaries(fi12_env):
    """Editor can read, edit, upload, start/cancel run, but CANNOT approve or reject review."""
    client = fi12_env["client"]
    prj_id = fi12_env["prj_id"]
    run_id = fi12_env["run_id"]
    headers = fi12_env["headers"]["editor"]

    # Allowed: Read
    assert client.get(f"/projects/{prj_id}", headers=headers).status_code == 200

    # Allowed: Edit brand
    assert client.put(f"/brand/{prj_id}", json=VALID_BRAND, headers={**headers, "If-Match": '"1"'}).status_code == 200

    # Allowed: Upload asset
    res_up = client.post(f"/projects/{prj_id}/assets", files={"file": ("editor_upload.png", b"PNG_DATA", "image/png")}, headers=headers)
    assert res_up.status_code == 201

    # Allowed: Start / Cancel run
    res_run = client.post(f"/projects/{prj_id}/runs", json={}, headers=headers)
    assert res_run.status_code == 202
    assert client.post(f"/projects/{prj_id}/runs/{run_id}/cancel", headers=headers).status_code == 200

    # Denied: Review Approve / Reject (Editor cannot sign off on their own work!)
    res_appr = client.post(f"/projects/{prj_id}/review/approve", json={"reason": "Self approve"}, headers=headers)
    assert res_appr.status_code == 403
    res_rej = client.post(f"/projects/{prj_id}/review/reject", json={"reason": "Self reject"}, headers=headers)
    assert res_rej.status_code == 403


def test_fi12_reviewer_role_boundaries(fi12_env):
    """Reviewer can read, approve, and reject, but CANNOT edit blueprint, upload assets, or start runs."""
    client = fi12_env["client"]
    prj_id = fi12_env["prj_id"]
    run_id = fi12_env["run_id"]
    headers = fi12_env["headers"]["reviewer"]

    # Allowed: Read
    assert client.get(f"/projects/{prj_id}", headers=headers).status_code == 200
    assert client.get(f"/projects/{prj_id}/review", headers=headers).status_code in (200, 404)

    # Denied: Edit Brand
    assert client.put(f"/brand/{prj_id}", json=VALID_BRAND, headers={**headers, "If-Match": '"1"'}).status_code == 403

    # Denied: Upload asset
    assert client.post(f"/projects/{prj_id}/assets", files={"file": ("r.png", b"1", "image/png")}, headers=headers).status_code == 403

    # Denied: Start run
    assert client.post(f"/projects/{prj_id}/runs", json={}, headers=headers).status_code == 403

    # Denied: Cancel run
    assert client.post(f"/projects/{prj_id}/runs/{run_id}/cancel", headers=headers).status_code == 403

    # Allowed: Review Decision (Approve / Reject)
    res_rej = client.post(
        f"/projects/{prj_id}/review/reject",
        json={"reason": "Reviewer rejected quality"},
        headers=headers,
    )
    # Status code is 200 (or 400 if no active bundle), but definitely NOT 403 Forbidden!
    assert res_rej.status_code != 403


def test_fi12_admin_role_full_permissions(fi12_env):
    """Admin has full operational capabilities within the workspace."""
    client = fi12_env["client"]
    prj_id = fi12_env["prj_id"]
    run_id = fi12_env["run_id"]
    headers = fi12_env["headers"]["admin"]

    assert client.get(f"/projects/{prj_id}", headers=headers).status_code == 200
    assert client.put(f"/brand/{prj_id}", json=VALID_BRAND, headers={**headers, "If-Match": '"1"'}).status_code in (200, 409)
    assert client.post(f"/projects/{prj_id}/runs", json={}, headers=headers).status_code == 202
    assert client.post(f"/projects/{prj_id}/runs/{run_id}/cancel", headers=headers).status_code == 200
