"""S02 Acceptance Contract 004: Non-Reviewer Cannot Approve Stage Reviews.

Vulnerability: AUTH-004 / AUTH-005
Contract:
Approval of review gates (such as Gate 3 / .studio_approved) requires explicit
Reviewer authorization (Role.REVIEWER or Role.ADMIN). An Editor or Viewer
attempting to approve a gate must be rejected with HTTP 403 Forbidden.
"""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from scripts.core.state_store import StateStore
from scripts.core.security import Principal, PrincipalType, Role, Action, AuthorizationPolicy


@pytest.mark.acceptance
def test_editor_cannot_approve_review_gates():
    """An Editor principal must be forbidden from approving review gates."""
    project_id = "test_acc_004_proj"
    project_dir = Path("projects") / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        StateStore.create(project_dir, project_id)

        editor = Principal(
            principal_id="usr_editor_only",
            principal_type=PrincipalType.HUMAN,
            roles=set(),
            project_scopes={project_id: {Role.EDITOR}}
        )

        # 1. Direct authorization policy enforcement check
        assert not AuthorizationPolicy.is_authorized(editor, Action.REVIEW_APPROVE, project_id), (
            "Policy invariant broken: Role.EDITOR must not have REVIEW_APPROVE permission."
        )

        client = TestClient(app)
        from api.core.auth import create_signed_token
        token = create_signed_token(editor)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(f"/gates/{project_id}/approve/gate_3", headers=headers)

        assert response.status_code == 403, (
            f"Expected HTTP 403 Forbidden when editor attempts gate approval, but received {response.status_code}. "
            "Gate approval currently lacks role enforcement."
        )
    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir)
