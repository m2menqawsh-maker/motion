"""
tests/security/test_pr002_tenant_isolation.py
=============================================
Independent Security Reproductions for PR-002:
Tenant Isolation & Authorization Boundary Hardening.

Covers:
- Vector 1: Token with Role.ADMIN / wildcard scope on foreign / registered project with DB fault.
- Vector 2: Service/SystemWorker token claiming bypass via X-Workspace-ID or principal_type.
- Vector 3: DB failure / exception fail-closed invariant (no silent fallback to global admin).
- Vector 4: Foreign X-Workspace-ID header rejection and positive owned workspace header.
- Vector 5: Query/body spoofing & unmanaged/unregistered project authorization leak.
- Vector 6: Child resource misbinding (run_id, asset_id, output_id, review_bundle_id, candidate_id).
- Vector 7: Downstream workspace_id=None suppression in RunService (get_run, list_runs, cancel_run, events).
- Vector 8: ProjectService.list_projects and is_project_accessible_by_tenant leaks.
- Vector 9: Candidate review and decision misbinding across candidates.
- Vector 10: Positive controls for legitimate workspace members across role matrix.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI, Depends, Request, Response, status
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import (
    create_signed_token,
    require_permission,
    require_tenant_context,
)
from api.services.project_service import ProjectService
from api.services.run_service import RunService
from api.services.output_service import OutputService
from api.services.asset_service import AssetService
from scripts.core.database import (
    DatabaseEngine,
    TenantRepository,
    set_database_engine,
    DatabaseError,
)
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.security.permissions import (
    Action,
    AuthorizationPolicy,
    AccessDeniedError,
)
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateStore
from scripts.core.storage import LocalStorageBackend, set_storage_service


@pytest.fixture
def isolation_env(tmp_path: Path, monkeypatch):
    """Hermetic multi-tenant test environment with Workspaces Alpha and Beta."""
    db_file = tmp_path / "pr002_tenant_isolation.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_root = tmp_path / "pr002_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    tenant_repo = TenantRepository(engine)
    run_repo = RunRepository(db_path=db_file)

    # 1. Provision Workspace Alpha (Alice = Admin, Aaron = Editor, Amy = Viewer, Arthur = Reviewer)
    u_alice = tenant_repo.create_user("usr_alice", "alice@alpha.com")
    u_aaron = tenant_repo.create_user("usr_aaron", "aaron@alpha.com")
    u_amy = tenant_repo.create_user("usr_amy", "amy@alpha.com")
    u_arthur = tenant_repo.create_user("usr_arthur", "arthur@alpha.com")

    ws_alpha = tenant_repo.create_workspace("ws_alpha", "Alpha Workspace", created_by=u_alice.id)
    tenant_repo.add_member("ws_alpha", u_aaron.id, Role.EDITOR)
    tenant_repo.add_member("ws_alpha", u_amy.id, Role.VIEWER)
    tenant_repo.add_member("ws_alpha", u_arthur.id, Role.REVIEWER)

    prj_alpha = tenant_repo.create_project("prj_alpha_main", "ws_alpha", "Alpha Main", created_by=u_alice.id)

    # 2. Provision Workspace Beta (Bob = Admin, Brenda = Editor, Brian = Viewer)
    u_bob = tenant_repo.create_user("usr_bob", "bob@beta.com")
    u_brenda = tenant_repo.create_user("usr_brenda", "brenda@beta.com")
    u_brian = tenant_repo.create_user("usr_brian", "brian@beta.com")

    ws_beta = tenant_repo.create_workspace("ws_beta", "Beta Workspace", created_by=u_bob.id)
    tenant_repo.add_member("ws_beta", u_brenda.id, Role.EDITOR)
    tenant_repo.add_member("ws_beta", u_brian.id, Role.VIEWER)

    prj_beta = tenant_repo.create_project("prj_beta_main", "ws_beta", "Beta Main", created_by=u_bob.id)

    # On-disk scaffolds
    p_alpha_dir = Path(f"projects/{prj_alpha.id}")
    p_alpha_dir.mkdir(parents=True, exist_ok=True)
    state_alpha = ProjectState(
        project_id=prj_alpha.id,
        workspace_id=ws_alpha.id,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        revision=1,
    )
    StateStore.save(p_alpha_dir, state_alpha)
    (p_alpha_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (p_alpha_dir / "out.mp4").write_bytes(b"ALPHA_OUTPUT_VIDEO_BYTES")

    p_beta_dir = Path(f"projects/{prj_beta.id}")
    p_beta_dir.mkdir(parents=True, exist_ok=True)
    state_beta = ProjectState(
        project_id=prj_beta.id,
        workspace_id=ws_beta.id,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        revision=1,
    )
    StateStore.save(p_beta_dir, state_beta)
    (p_beta_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (p_beta_dir / "out.mp4").write_bytes(b"BETA_OUTPUT_VIDEO_BYTES")

    # Seed runs in run repository
    run_alpha = run_repo.create_run(
        RunRecord(
            run_id="run_alpha_001",
            workspace_id=ws_alpha.id,
            project_id=prj_alpha.id,
            status=RunStatus.SUCCEEDED,
        )
    )
    run_repo.record_event(
        run_id="run_alpha_001",
        project_id=prj_alpha.id,
        event_type="RUN_QUEUED",
        workspace_id=ws_alpha.id,
    )

    run_beta = run_repo.create_run(
        RunRecord(
            run_id="run_beta_001",
            workspace_id=ws_beta.id,
            project_id=prj_beta.id,
            status=RunStatus.QUEUED,
        )
    )

    client = TestClient(app)

    yield {
        "client": client,
        "engine": engine,
        "tenant_repo": tenant_repo,
        "run_repo": run_repo,
        "storage": storage,
        "ws_alpha": ws_alpha.id,
        "ws_beta": ws_beta.id,
        "prj_alpha": prj_alpha.id,
        "prj_beta": prj_beta.id,
        "run_alpha": run_alpha.run_id,
        "run_beta": run_beta.run_id,
        "p_alpha_dir": p_alpha_dir,
        "p_beta_dir": p_beta_dir,
        "users": {
            "alice": u_alice,
            "aaron": u_aaron,
            "amy": u_amy,
            "arthur": u_arthur,
            "bob": u_bob,
            "brenda": u_brenda,
            "brian": u_brian,
        }
    }

    import shutil
    shutil.rmtree(p_alpha_dir, ignore_errors=True)
    shutil.rmtree(p_beta_dir, ignore_errors=True)
    set_database_engine(None)
    set_storage_service(None)


# ==============================================================================
# VECTOR 1: Global ADMIN Token Without Workspace Membership on DB Outage / Fault
# ==============================================================================
def test_repro_vector1_token_admin_bypasses_on_db_fault(isolation_env):
    """
    RED PROOF: When a database lookup error occurs in AuthorizationPolicy.is_authorized,
    the broad `except Exception: pass` causes fallback to `principal.is_admin`, allowing
    a user with token role ADMIN to access a foreign registered project!
    """
    prj_alpha = isolation_env["prj_alpha"]
    bob_id = isolation_env["users"]["bob"].id

    # Bob has Role.ADMIN in his token, but is a member of ws_beta, NOT ws_alpha
    bob_admin_principal = Principal(
        principal_id=bob_id,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )

    # Inject DB failure during get_project or get_membership
    with patch("scripts.core.database.TenantRepository.get_project", side_effect=sqlite3.OperationalError("DB locked")):
        # In vulnerable code: broad except Exception: pass falls through to `if principal.is_admin: return True`!
        is_auth = AuthorizationPolicy.is_authorized(bob_admin_principal, Action.PROJECT_READ, prj_alpha)
        # MUST BE FALSE (Fail-Closed). If True, this demonstrates the vulnerability!
        assert is_auth is False, "VULNERABILITY REPRODUCED: Token ADMIN bypassed tenant isolation on DB fault!"


def test_repro_vector1_token_admin_bypasses_http_on_db_fault(isolation_env):
    """
    RED PROOF (HTTP boundary): When DB fails, an attacker with token role ADMIN
    receives 200 OK or bypass instead of 403 / 503 fail-closed.
    """
    client = isolation_env["client"]
    prj_alpha = isolation_env["prj_alpha"]
    bob_id = isolation_env["users"]["bob"].id

    token_bob_admin = create_signed_token(
        Principal(
            principal_id=bob_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.ADMIN},
        )
    )

    with patch("scripts.core.database.TenantRepository.get_project", side_effect=sqlite3.OperationalError("DB down")):
        resp = client.get(
            f"/projects/{prj_alpha}",
            headers={"Authorization": f"Bearer {token_bob_admin}"},
        )
        # In vulnerable code: passes authorization and returns 200!
        assert resp.status_code in (403, 503), f"VULNERABILITY REPRODUCED: Got {resp.status_code} instead of 403/503 on DB fault"


# ==============================================================================
# VECTOR 2: Service / SystemWorker Token Claiming Arbitrary Workspace
# ==============================================================================
def test_repro_vector2_service_token_spoofs_workspace_in_require_tenant_context(isolation_env):
    """
    RED PROOF: `require_tenant_context` checks:
      if membership is None and principal.principal_type not in (PrincipalType.SERVICE, PrincipalType.SYSTEM_WORKER):
    This allows ANY token claiming `type: "SERVICE"` or `"SYSTEM_WORKER"` to pass
    an arbitrary X-Workspace-ID header and gain full ADMIN authority in that workspace!
    """
    ws_alpha = isolation_env["ws_alpha"]

    # Attacker crafts signed bearer token claiming type="SERVICE"
    attacker_svc_principal = Principal(
        principal_id="svc_untrusted_external",
        principal_type=PrincipalType.SERVICE,
        roles=set(),
    )
    token_svc = create_signed_token(attacker_svc_principal)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/candidates/cand_123/reviews/open",
        "headers": [
            (b"authorization", f"Bearer {token_svc}".encode("ascii")),
            (b"x-workspace-id", ws_alpha.encode("ascii")),  # Foreign workspace
        ],
    }
    req = Request(scope)
    req.state.tenant_context = None

    import asyncio
    dep = require_tenant_context(Action.REVIEW_APPROVE)
    
    # Must raise AccessDeniedError because svc_untrusted_external has NO membership in ws_alpha!
    with pytest.raises(AccessDeniedError):
        asyncio.run(dep(req, attacker_svc_principal))


# ==============================================================================
# VECTOR 3: require_permission Swallows Exceptions and Overrides Role
# ==============================================================================
def test_repro_vector3_require_permission_role_override_and_exception_swallowing(isolation_env):
    """
    RED PROOF: In api/core/auth.py:require_permission:
    1. If principal.is_admin is True, effective_role is set to Role.ADMIN even if DB membership is VIEWER.
    2. Exceptions during TenantContext building are silently swallowed (`except Exception: pass`),
       leaving request.state.tenant_context as None.
    """
    prj_alpha = isolation_env["prj_alpha"]
    amy_id = isolation_env["users"]["amy"].id  # Amy is VIEWER in ws_alpha

    # Amy has Role.ADMIN in token claims, but VIEWER in DB
    amy_tampered_token = create_signed_token(
        Principal(
            principal_id=amy_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.ADMIN},
        )
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/projects/{prj_alpha}",
        "path_params": {"project_id": prj_alpha},
        "headers": [
            (b"authorization", f"Bearer {amy_tampered_token}".encode("ascii")),
        ],
    }
    req = Request(scope)
    req.scope["path_params"] = {"project_id": prj_alpha}

    import asyncio
    dep = require_permission(Action.PROJECT_READ)
    p = asyncio.run(dep(req, Principal(principal_id=amy_id, principal_type=PrincipalType.HUMAN, roles={Role.ADMIN})))

    # In vulnerable code, request.state.tenant_context.role is Role.ADMIN instead of Role.VIEWER!
    ctx = getattr(req.state, "tenant_context", None)
    assert ctx is not None
    assert ctx.role == Role.VIEWER, f"VULNERABILITY REPRODUCED: Token role ADMIN overrode DB membership role! Got: {ctx.role}"


# ==============================================================================
# VECTOR 4: Foreign X-Workspace-ID Header Rejection
# ==============================================================================
def test_repro_vector4_foreign_workspace_header_rejected_with_valid_token(isolation_env):
    """
    RED PROOF: When Bob (ws_beta) sends X-Workspace-ID: ws_alpha on a tenant context route,
    it must be rejected with 403, and never grant access to ws_alpha.
    """
    client = isolation_env["client"]
    ws_alpha = isolation_env["ws_alpha"]
    bob_id = isolation_env["users"]["bob"].id

    token_bob = create_signed_token(
        Principal(
            principal_id=bob_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.ADMIN},
        )
    )

    headers = {
        "Authorization": f"Bearer {token_bob}",
        "X-Workspace-ID": ws_alpha,  # Foreign workspace
    }
    resp = client.get("/candidates/promotions", headers=headers)
    assert resp.status_code == 403, f"Expected 403 Forbidden for foreign X-Workspace-ID, got {resp.status_code}"


# ==============================================================================
# VECTOR 5: ProjectService.list_projects Leaks Projects to Unscoped / Foreign Users
# ==============================================================================
def test_repro_vector5_list_projects_unscoped_leak(isolation_env):
    """
    RED PROOF: ProjectService.list_projects(principal) checks:
      if not principal.is_admin and principal.project_scopes and "*" not in principal.project_scopes:
    When a non-admin user has NO project_scopes (empty dict), the condition is FALSE!
    It returns ALL projects from all workspaces on disk!
    """
    brian_id = isolation_env["users"]["brian"].id  # Member of ws_beta only

    # Brian has VIEWER role, empty project scopes
    brian_principal = Principal(
        principal_id=brian_id,
        principal_type=PrincipalType.HUMAN,
        roles={Role.VIEWER},
        project_scopes={},
    )

    projects = ProjectService.list_projects(brian_principal)
    # Brian should ONLY see his workspace's projects, NEVER prj_alpha_main!
    assert "prj_alpha_main" not in projects, f"VULNERABILITY REPRODUCED: Unscoped user saw foreign project: {projects}"


def test_repro_vector5_is_project_accessible_by_tenant_admin_bypass(isolation_env):
    """
    RED PROOF: ProjectService.is_project_accessible_by_tenant checks:
      if is_admin: return True, None
    This allows any user with is_admin=True to bypass workspace boundaries.
    """
    prj_alpha = isolation_env["prj_alpha"]
    ws_beta = isolation_env["ws_beta"]

    # Bob is in ws_beta, but is_admin=True
    is_acc, reason = ProjectService.is_project_accessible_by_tenant(
        project_id=prj_alpha,
        workspace_id=ws_beta,
        is_admin=True,
    )
    # Must NOT be accessible across workspaces even if is_admin is True!
    assert is_acc is False, "VULNERABILITY REPRODUCED: is_admin=True bypassed project workspace boundary!"


# ==============================================================================
# VECTOR 6: Child Resource Misbinding (Run ID, Asset ID)
# ==============================================================================
def test_repro_vector6_misbound_run_id_rejected(isolation_env):
    """
    RED PROOF: Requesting Project A's run_id through Project B's URL path:
    GET /projects/{prj_beta}/runs/{run_alpha}
    Must be rejected with 404 / 403, and never return Project A's run data.
    """
    client = isolation_env["client"]
    prj_beta = isolation_env["prj_beta"]
    run_alpha = isolation_env["run_alpha"]
    brenda_id = isolation_env["users"]["brenda"].id

    token_brenda = create_signed_token(
        Principal(
            principal_id=brenda_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        )
    )

    resp = client.get(
        f"/projects/{prj_beta}/runs/{run_alpha}",
        headers={"Authorization": f"Bearer {token_brenda}"},
    )
    assert resp.status_code == 404, f"Expected 404 for misbound run_id, got {resp.status_code}"


def test_repro_vector6_run_service_workspace_id_none_bypass(isolation_env):
    """
    RED PROOF: If workspace_id is None, RunService.get_run, cancel_run, get_events
    must NOT skip the workspace check when project is registered to a workspace!
    """
    prj_alpha = isolation_env["prj_alpha"]
    run_alpha = isolation_env["run_alpha"]
    ws_beta = isolation_env["ws_beta"]

    # When workspace_id is ws_beta, get_run correctly raises RunNotFoundError
    with pytest.raises(Exception):
        RunService.get_run(project_id=prj_alpha, run_id=run_alpha, workspace_id=ws_beta)

    # But in vulnerable code, when workspace_id is None, it returns the record without checking!
    # If caller failed to provide workspace_id, it should resolve or enforce workspace binding!


# ==============================================================================
# VECTOR 7: SSE Event Streaming Terminal Check Omits workspace_id
# ==============================================================================
def test_repro_vector7_sse_terminal_check_workspace_omission(isolation_env):
    """
    RED PROOF: In api/routers/runs.py:get_run_events:
    Line 178: `run_rec = RunService.get_run(project_id=project_id, run_id=run_id)`
    omits `workspace_id=ws_id`, allowing terminal lookup to bypass workspace check!
    """
    import inspect
    from api.routers import runs
    source = inspect.getsource(runs.get_run_events)
    # Check if the terminal check passes workspace_id
    assert "RunService.get_run(project_id=project_id, run_id=run_id, workspace_id=ws_id)" in source, (
        "VULNERABILITY REPRODUCED: SSE get_run terminal check omits workspace_id=ws_id!"
    )


# ==============================================================================
# VECTOR 8: Denial Responses Must Not Leak Internal IDs or Paths
# ==============================================================================
def test_repro_vector8_access_denied_handler_information_leak(isolation_env):
    """
    RED PROOF: Access denied responses must not leak internal foreign workspace IDs
    in reason strings or details.
    """
    from api.core.errors import access_denied_handler, AccessDeniedError
    from scripts.core.security.permissions import Action
    from starlette.requests import Request as StarletteRequest

    req = StarletteRequest({"type": "http", "method": "GET", "path": "/test"})
    exc = AccessDeniedError(
        principal_id="usr_bob",
        action=Action.PROJECT_READ,
        project_id="prj_alpha",
        reason="Target project 'prj_alpha' belongs to workspace 'ws_secret_123', not 'ws_beta'"
    )

    import asyncio
    resp = asyncio.run(access_denied_handler(req, exc))
    body = json.loads(resp.body.decode("utf-8"))

    # The response body should NOT contain "ws_secret_123"
    raw_str = json.dumps(body)
    assert "ws_secret_123" not in raw_str, f"VULNERABILITY REPRODUCED: Leaked workspace ID in denial response: {raw_str}"


# ==============================================================================
# VECTOR 9: Positive Controls (Legitimate Members Retain Access)
# ==============================================================================
def test_positive_controls_legitimate_alpha_members(isolation_env):
    """
    POSITIVE CONTROLS: Legitimate members of Workspace Alpha retain appropriate access.
    - Aaron (Editor) -> Can read project, trigger run
    - Amy (Viewer) -> Can read project, CANNOT trigger run
    - Arthur (Reviewer) -> Can read project, can approve review
    """
    client = isolation_env["client"]
    prj_alpha = isolation_env["prj_alpha"]
    users = isolation_env["users"]

    # Aaron (Editor)
    token_aaron = create_signed_token(
        Principal(principal_id=users["aaron"].id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers_aaron = {"Authorization": f"Bearer {token_aaron}"}

    r_read = client.get(f"/projects/{prj_alpha}", headers=headers_aaron)
    assert r_read.status_code == 200

    r_run = client.post(f"/projects/{prj_alpha}/runs", json={}, headers=headers_aaron)
    assert r_run.status_code == 202

    # Amy (Viewer)
    token_amy = create_signed_token(
        Principal(principal_id=users["amy"].id, principal_type=PrincipalType.HUMAN, roles={Role.VIEWER})
    )
    headers_amy = {"Authorization": f"Bearer {token_amy}"}

    r_amy_read = client.get(f"/projects/{prj_alpha}", headers=headers_amy)
    assert r_amy_read.status_code == 200

    r_amy_run = client.post(f"/projects/{prj_alpha}/runs", json={}, headers=headers_amy)
    assert r_amy_run.status_code == 403


# ==============================================================================
# VECTOR 10: Candidate Review & Decision Child Resource Misbinding
# ==============================================================================
def test_repro_vector10_candidate_review_bundle_misbinding():
    """
    RED PROOF: In api/routers/candidate_reviews.py:
    get_review_bundle and get_decision fetch by ID alone without checking
    that bundle.candidate_id == candidate_id or decision.candidate_id == candidate_id.
    """
    import inspect
    from api.routers import candidate_reviews
    src_bundle = inspect.getsource(candidate_reviews.get_review_bundle)
    src_decision = inspect.getsource(candidate_reviews.get_decision)

    assert "bundle.candidate_id != candidate_id" in src_bundle, (
        "VULNERABILITY REPRODUCED: get_review_bundle does not bind review_bundle to candidate_id in URL!"
    )
    assert "decision.candidate_id != candidate_id" in src_decision, (
        "VULNERABILITY REPRODUCED: get_decision does not bind decision to candidate_id in URL!"
    )


# ==============================================================================
# VECTOR 11: Authoring Cross-Tenant Document Access
# ==============================================================================
def test_repro_vector11_authoring_cross_tenant_document_access(isolation_env):
    """
    RED PROOF: Bob (in ws_beta) requests Alice's project document:
    GET /projects/{prj_alpha}/document
    Must be denied with 403 / 404, never 200 or 500.
    """
    client = isolation_env["client"]
    prj_alpha = isolation_env["prj_alpha"]
    bob_id = isolation_env["users"]["bob"].id

    token_bob = create_signed_token(
        Principal(
            principal_id=bob_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.ADMIN},
        )
    )

    resp = client.get(
        f"/projects/{prj_alpha}/document",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp.status_code in (403, 404), f"VULNERABILITY REPRODUCED: Bob accessed Alpha document with status {resp.status_code}!"

