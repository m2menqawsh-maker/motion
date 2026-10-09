"""
tests/api/test_tenant_endpoints.py — S24.5 Tenant-Scoped Endpoints & Strict Authorization.

Verifies:
1. Multi-tenant Runs API Isolation (User B cannot trigger, read, list, cancel, or stream runs from Project A).
2. Multi-tenant Review / Approval Isolation (User B cannot approve or reject Project A, actor_id is server-derived).
3. Multi-tenant Output Delivery Isolation (User B cannot download output of Project A; StorageService streaming).
4. Invariant: Valid object ID != authorized access (403 Forbidden).
"""

import json
import pytest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.database import DatabaseEngine, set_database_engine, TenantRepository
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.security.principal import Role
from scripts.core.state_model import LifecycleState, ProjectState, ReviewBundle
from scripts.core.state_store import StateStore
from tests.conftest import make_test_auth_headers


@pytest.fixture
def saas_env(tmp_path):
    # Setup hermetic DB
    db_file = tmp_path / "saas_endpoints.db"
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    # Setup storage
    storage_root = tmp_path / "saas_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    tenant_repo = TenantRepository(db_engine)

    # 1. Tenant Alpha
    user_a = tenant_repo.create_user("usr_alpha_editor", "editor@alpha.com")
    user_a_rev = tenant_repo.create_user("usr_alpha_reviewer", "reviewer@alpha.com")
    ws_a = tenant_repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_a.id)
    tenant_repo.add_member("ws_alpha", user_a_rev.id, Role.REVIEWER)
    prj_a = tenant_repo.create_project("prj_alpha_1", "ws_alpha", "Alpha Video 1", created_by=user_a.id)

    # 2. Tenant Beta
    user_b = tenant_repo.create_user("usr_beta_editor", "editor@beta.com")
    user_b_rev = tenant_repo.create_user("usr_beta_reviewer", "reviewer@beta.com")
    ws_b = tenant_repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_b.id)
    tenant_repo.add_member("ws_beta", user_b_rev.id, Role.REVIEWER)
    prj_b = tenant_repo.create_project("prj_beta_1", "ws_beta", "Beta Video 1", created_by=user_b.id)

    # Setup local project directory for Alpha
    proj_dir_a = Path(f"projects/{prj_a.id}")
    proj_dir_a.mkdir(parents=True, exist_ok=True)
    state_a = ProjectState(
        project_id=prj_a.id,
        workspace_id=ws_a.id,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        revision=1,
    )
    StateStore.save(proj_dir_a, state_a)
    (proj_dir_a / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "probe_qc_report.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "out.mp4").write_bytes(b"ALPHA_OUTPUT_VIDEO_BYTES_STREAM")

    client = TestClient(app)

    yield {
        "client": client,
        "tenant_repo": tenant_repo,
        "user_a": user_a,
        "user_a_rev": user_a_rev,
        "user_b": user_b,
        "user_b_rev": user_b_rev,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "prj_a": prj_a,
        "prj_b": prj_b,
        "proj_dir_a": proj_dir_a,
        "storage": storage_svc,
    }

    import shutil
    shutil.rmtree(proj_dir_a, ignore_errors=True)


def test_runs_api_cross_tenant_isolation(saas_env):
    """Verifies that User B cannot trigger, list, get, or cancel runs on Project A."""
    client = saas_env["client"]
    prj_a_id = saas_env["prj_a"].id

    headers_user_a = make_test_auth_headers(principal_id=saas_env["user_a"].id, roles=["editor"])
    headers_user_b = make_test_auth_headers(principal_id=saas_env["user_b"].id, roles=["editor"])

    # 1. User A triggers run on Project A -> 202 Accepted
    resp_create = client.post(f"/projects/{prj_a_id}/runs", json={}, headers=headers_user_a)
    assert resp_create.status_code == 202
    run_id = resp_create.json()["run_id"]

    # 2. User B attempts to trigger run on Project A -> 403 Forbidden
    resp_b_create = client.post(f"/projects/{prj_a_id}/runs", json={}, headers=headers_user_b)
    assert resp_b_create.status_code == 403

    # 3. User B attempts to get run status on Project A -> 403 Forbidden
    resp_b_get = client.get(f"/projects/{prj_a_id}/runs/{run_id}", headers=headers_user_b)
    assert resp_b_get.status_code == 403

    # 4. User B attempts to list runs on Project A -> 403 Forbidden
    resp_b_list = client.get(f"/projects/{prj_a_id}/runs", headers=headers_user_b)
    assert resp_b_list.status_code == 403

    # 5. User B attempts to cancel run on Project A -> 403 Forbidden
    resp_b_cancel = client.post(f"/projects/{prj_a_id}/runs/{run_id}/cancel", headers=headers_user_b)
    assert resp_b_cancel.status_code == 403

    # 6. User B attempts to get events for run on Project A -> 403 Forbidden
    resp_b_events = client.get(f"/projects/{prj_a_id}/runs/{run_id}/events", headers=headers_user_b)
    assert resp_b_events.status_code == 403


def test_review_approval_cross_tenant_isolation(saas_env):
    """Verifies that User B cannot approve or reject Project A review, and actor identity is authentic."""
    client = saas_env["client"]
    prj_a_id = saas_env["prj_a"].id
    proj_dir_a = saas_env["proj_dir_a"]

    # Create active review bundle on Project A
    from scripts.core.review_service import ReviewService
    from scripts.core.security.principal import Principal, Role, PrincipalType

    principal_admin = Principal(
        principal_id="sys_admin",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )
    bundle = ReviewService.create_review_bundle(
        project_dir=proj_dir_a,
        actor=principal_admin,
    )
    bundle_id = bundle.review_bundle_id

    headers_user_a_rev = make_test_auth_headers(principal_id=saas_env["user_a_rev"].id, roles=["reviewer"])
    headers_user_b_rev = make_test_auth_headers(principal_id=saas_env["user_b_rev"].id, roles=["reviewer"])

    # 1. User B (reviewer in Workspace B) tries to approve Project A -> 403 Forbidden
    resp_b_approve = client.post(
        f"/projects/{prj_a_id}/review/approve",
        json={"bundle_id": bundle_id, "approved_by": "fake_override"},
        headers=headers_user_b_rev,
    )
    assert resp_b_approve.status_code == 403

    # 2. User B tries to reject Project A -> 403 Forbidden
    resp_b_reject = client.post(
        f"/projects/{prj_a_id}/review/reject",
        json={"bundle_id": bundle_id, "reason": "malicious reject"},
        headers=headers_user_b_rev,
    )
    assert resp_b_reject.status_code == 403

    # 3. User A (reviewer in Workspace A) approves Project A -> 200 OK
    resp_a_approve = client.post(
        f"/projects/{prj_a_id}/review/approve",
        json={"bundle_id": bundle_id, "reason": "Approved by Alpha Reviewer"},
        headers=headers_user_a_rev,
    )
    assert resp_a_approve.status_code == 200
    data = resp_a_approve.json()
    assert data["status"] == "success"
    # Ensure server-derived actor_id, NOT client override
    assert data["decision"]["actor_id"] == saas_env["user_a_rev"].id


def test_output_streaming_cross_tenant_isolation(saas_env):
    """Verifies that User B cannot stream or download Project A video output."""
    client = saas_env["client"]
    prj_a_id = saas_env["prj_a"].id

    headers_user_a = make_test_auth_headers(principal_id=saas_env["user_a"].id, roles=["editor"])
    headers_user_b = make_test_auth_headers(principal_id=saas_env["user_b"].id, roles=["editor"])

    # 1. User A downloads output -> 200 OK
    resp_a = client.get(f"/projects/{prj_a_id}/outputs/out.mp4", headers=headers_user_a)
    assert resp_a.status_code == 200
    assert resp_a.content == b"ALPHA_OUTPUT_VIDEO_BYTES_STREAM"

    # 2. User B tries to download Project A output -> 403 Forbidden (Valid ID != Access)
    resp_b = client.get(f"/projects/{prj_a_id}/outputs/out.mp4", headers=headers_user_b)
    assert resp_b.status_code == 403
