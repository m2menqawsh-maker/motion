"""S02 Acceptance Contract 003: Project Scope Isolation.

Vulnerability: AUTH-003 / Project Isolation Contract
Contract:
A Principal granted permissions only for Project A must be forbidden from
reading, mutating, or advancing the pipeline of Project B.
Cross-project requests must return HTTP 403 Forbidden.
"""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from scripts.core.state_store import StateStore
from scripts.core.security import Principal, PrincipalType, Role, Action, AuthorizationPolicy


@pytest.mark.acceptance
def test_principal_without_target_project_scope_must_be_forbidden():
    """Principal with scope for 'proj_allowed' cannot mutate 'proj_forbidden'."""
    scoped_user = Principal(
        principal_id="usr_scoped_01",
        principal_type=PrincipalType.HUMAN,
        roles=set(),
        project_scopes={"proj_allowed": {Role.EDITOR}}
    )

    # 1. Direct authorization policy enforcement check
    assert AuthorizationPolicy.is_authorized(scoped_user, Action.PROJECT_EDIT, "proj_allowed")
    assert not AuthorizationPolicy.is_authorized(scoped_user, Action.PROJECT_EDIT, "proj_forbidden")

    # 2. API level enforcement contract:
    # A request carrying scoped_user credentials to proj_forbidden must return 403 Forbidden
    client = TestClient(app)
    # Simulate authenticated request context (via test header / dependency override when S02 is implemented)
    headers = {"X-Principal-ID": scoped_user.principal_id, "X-Principal-Scope": "proj_allowed"}
    
    # In current main, no scope check exists, returning 404 (if not found) or 200 rather than 403
    response = client.get("/projects/proj_forbidden", headers=headers)
    assert response.status_code == 403, (
        f"Expected HTTP 403 Forbidden for cross-project access attempt, but received {response.status_code}. "
        "Project isolation boundary is currently unenforced."
    )
