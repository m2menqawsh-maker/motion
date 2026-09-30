"""
tests/security/test_tenant_authorization.py — Unit & Integration Tests for Tenant Authorization & Isolation (S24.5).
"""

from pathlib import Path
import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient

from api.core.auth import require_permission, require_tenant_context, create_signed_token
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.security.permissions import Action, AccessDeniedError
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.tenant_model import TenantContext


@pytest.fixture
def auth_test_env(tmp_path: Path):
    db_file = tmp_path / "tenant_auth.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    repo = TenantRepository(engine)

    # 1. Setup Tenant A
    repo.create_user("usr_alice", "alice@example.com")
    repo.create_workspace("ws_alpha", "Alpha Workspace", created_by="usr_alice")
    repo.create_project("prj_alpha", "ws_alpha", "Alpha Project", created_by="usr_alice")

    # 2. Setup Tenant B
    repo.create_user("usr_bob", "bob@example.com")
    repo.create_workspace("ws_beta", "Beta Workspace", created_by="usr_bob")
    repo.create_project("prj_beta", "ws_beta", "Beta Project", created_by="usr_bob")

    yield engine, repo
    set_database_engine(None)


def test_cross_tenant_access_denied_direct_enforcement(auth_test_env):
    _, repo = auth_test_env

    # Bob's principal (only member of ws_beta)
    bob_principal = Principal(
        principal_id="usr_bob",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )

    # Alice's principal (member of ws_alpha)
    alice_principal = Principal(
        principal_id="usr_alice",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )

    from scripts.core.security.permissions import AuthorizationPolicy

    # Alice can read/edit her project prj_alpha
    assert AuthorizationPolicy.is_authorized(alice_principal, Action.PROJECT_READ, "prj_alpha") is True
    assert AuthorizationPolicy.is_authorized(alice_principal, Action.PROJECT_EDIT, "prj_alpha") is True

    # Bob CANNOT read or edit Alice's project prj_alpha (even though prj_alpha is a perfectly valid ID!)
    assert AuthorizationPolicy.is_authorized(bob_principal, Action.PROJECT_READ, "prj_alpha") is False
    assert AuthorizationPolicy.is_authorized(bob_principal, Action.PROJECT_EDIT, "prj_alpha") is False

    # Enforce raises AccessDeniedError
    with pytest.raises(AccessDeniedError):
        AuthorizationPolicy.enforce(bob_principal, Action.PROJECT_READ, "prj_alpha")


def test_tenant_api_boundary_via_http(auth_test_env):
    engine, repo = auth_test_env

    # Build a test FastAPI app using our dependencies
    app = FastAPI()

    from api.core.errors import access_denied_handler, authentication_required_handler, AccessDeniedError, AuthenticationRequiredError
    app.add_exception_handler(AccessDeniedError, access_denied_handler)
    app.add_exception_handler(AuthenticationRequiredError, authentication_required_handler)

    @app.get("/projects/{project_id}/state")
    def get_state(project_id: str, tenant: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ))):
        return {"project_id": project_id, "workspace_id": tenant.workspace_id, "user_id": tenant.user_id}

    client = TestClient(app)

    # Bob creates authentic signed bearer token
    bob_principal = Principal(
        principal_id="usr_bob",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    bob_token = create_signed_token(bob_principal)

    # Bob accesses his own project prj_beta -> 200 OK
    resp_bob_own = client.get("/projects/prj_beta/state", headers={"Authorization": f"Bearer {bob_token}"})
    assert resp_bob_own.status_code == 200
    data = resp_bob_own.json()
    assert data["workspace_id"] == "ws_beta"
    assert data["user_id"] == "usr_bob"

    # Bob attempts to access Alice's project prj_alpha -> 403 Forbidden!
    resp_bob_cross = client.get("/projects/prj_alpha/state", headers={"Authorization": f"Bearer {bob_token}"})
    assert resp_bob_cross.status_code == 403

    # Attempting to forge identity via query param or headers -> 403 Forbidden
    resp_forged = client.get(
        "/projects/prj_alpha/state?by=usr_alice&workspace_id=ws_alpha",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_forged.status_code == 403
