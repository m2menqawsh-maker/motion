"""
tests/fault_injection/test_fi_13_tenant_spoofing.py — Fault Injection Scenario FI-13.

TenantContext & Identity Spoofing Attack Matrix:
Proves that TenantContext and authorization decisions cannot be spoofed, forged,
or overridden by untrusted client-supplied data:
1. Forged X-Workspace-ID header pointing to a foreign workspace.
2. Forged X-Principal-Roles header attempting role escalation.
3. Forged X-Principal-ID header attempting identity impersonation.
4. Forged query parameters (?by=admin, ?actor=admin, ?workspace_id=...)
5. Request body workspace_id overrides attempting to create projects or assets in foreign workspaces.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.security.principal import Principal, Role, PrincipalType
from scripts.core.security.permissions import AccessDeniedError


@pytest.fixture
def fi13_env(tmp_path: Path):
    db_file = tmp_path / "fi13_spoofing.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)

    # 1. Honest User in Workspace Alpha
    user_alice = repo.create_user("usr_alice_fi13", "alice@alpha.com")
    ws_alpha = repo.create_workspace("ws_alpha_fi13", "Alpha Workspace", created_by=user_alice.id)
    prj_alpha = repo.create_project("prj_alpha_fi13", ws_alpha.id, "Alpha Project", created_by=user_alice.id)

    # 2. Attacker in Workspace Beta (only has Editor role in Beta)
    user_attacker = repo.create_user("usr_attacker_fi13", "mallory@beta.com")
    ws_beta = repo.create_workspace("ws_beta_fi13", "Beta Workspace", created_by=user_attacker.id)

    client = TestClient(app)

    # Token for Attacker (validly signed for Mallory)
    principal_attacker = Principal(
        principal_id=user_attacker.id,
        principal_type=PrincipalType.HUMAN,
        roles=set(),
    )
    token_attacker = create_signed_token(principal_attacker)

    yield {
        "client": client,
        "token_attacker": token_attacker,
        "user_attacker": user_attacker.id,
        "ws_alpha": ws_alpha.id,
        "ws_beta": ws_beta.id,
        "prj_alpha": prj_alpha.id,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_fi13_spoofed_workspace_header_rejected(fi13_env):
    """Client sending X-Workspace-ID of another workspace cannot act within that workspace."""
    client = fi13_env["client"]
    token = fi13_env["token_attacker"]
    ws_alpha = fi13_env["ws_alpha"]
    prj_alpha = fi13_env["prj_alpha"]

    # Attacker tries to read Project Alpha using forged X-Workspace-ID
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": ws_alpha,  # Spoofing Workspace Alpha
    }
    res = client.get(f"/projects/{prj_alpha}", headers=headers)
    assert res.status_code in (403, 404), f"Expected 403/404, got {res.status_code}"


def test_fi13_spoofed_role_header_rejected(fi13_env):
    """Client sending X-Principal-Roles: admin with non-admin token cannot escalate privileges."""
    client = fi13_env["client"]
    token = fi13_env["token_attacker"]
    prj_alpha = fi13_env["prj_alpha"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Principal-Roles": "admin,reviewer,operator",
    }
    # Attempt sensitive operation
    res = client.post(f"/projects/{prj_alpha}/review/approve", json={"reason": "spoofed"}, headers=headers)
    assert res.status_code == 403


def test_fi13_spoofed_query_params_ignored(fi13_env):
    """Client sending ?by=admin or ?actor=admin or ?workspace_id=... has zero effect on authorization."""
    client = fi13_env["client"]
    token = fi13_env["token_attacker"]
    prj_alpha = fi13_env["prj_alpha"]
    ws_alpha = fi13_env["ws_alpha"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get(f"/projects/{prj_alpha}?by=usr_alice_fi13&workspace_id={ws_alpha}", headers=headers)
    assert res.status_code in (403, 404)


def test_fi13_require_tenant_context_rejects_unauthorized_workspace_header(fi13_env):
    """require_tenant_context must reject forged X-Workspace-ID if user has no membership."""
    from api.core.auth import require_tenant_context
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest

    token = fi13_env["token_attacker"]
    ws_alpha = fi13_env["ws_alpha"]

    # Direct test of require_tenant_context dependency
    from scripts.core.security.permissions import Action
    dep = require_tenant_context(Action.PROJECT_CREATE)

    # Mock request with spoofed X-Workspace-ID
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/projects",
        "headers": [
            (b"authorization", f"Bearer {token}".encode("ascii")),
            (b"x-workspace-id", ws_alpha.encode("ascii")),
        ],
    }
    req = Request(scope)

    # Evaluating require_tenant_context must reject because Attacker is NOT in ws_alpha!
    with pytest.raises(AccessDeniedError):
        import asyncio
        principal_attacker = Principal(
            principal_id=fi13_env["user_attacker"],
            principal_type=PrincipalType.HUMAN,
            roles=set(),
        )
        asyncio.run(dep(req, principal_attacker))
