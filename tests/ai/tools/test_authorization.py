"""
tests/ai/tools/test_authorization.py
====================================
Unit tests for server-side ToolAuthorizationPolicy and isolation (S27.9).
"""

import pytest

from ai.contracts.errors import AIErrorCode
from ai.tools.authorization import ToolAuthorizationPolicy
from ai.tools.contracts import (
    GetProjectStatusInput,
    PatchBlueprintInput,
    StartRunInput,
    ToolDefinition,
)
from ai.tools.types import (
    AuthorizationDecision,
    SideEffectClass,
    TrustedToolExecutionContext,
)
from scripts.core.database import get_database_engine, TenantRepository


@pytest.fixture
def sample_read_tool():
    return ToolDefinition(
        name="test_read_tool",
        description="Read project data",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusInput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=True,
    )


@pytest.fixture
def sample_mutation_tool():
    return ToolDefinition(
        name="test_mutation_tool",
        description="Mutate project blueprint",
        input_contract=PatchBlueprintInput,
        output_contract=PatchBlueprintInput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="blueprint:edit",
        enabled=True,
    )


@pytest.fixture
def sample_admin_tool():
    return ToolDefinition(
        name="test_admin_tool",
        description="System administration tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusInput,
        side_effect_class=SideEffectClass.ADMIN,
        required_permission="system:admin",
        enabled=True,
    )


def test_auth_allow_matching_workspace_and_permission(sample_read_tool):
    """Authenticated caller with correct workspace and permission is allowed."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_1",
        roles=["viewer"],
        permissions=["project:read"],
        is_admin=False,
    )
    inp = GetProjectStatusInput(project_id="prj_1")

    res = ToolAuthorizationPolicy.authorize(sample_read_tool, ctx, inp)
    assert res.allowed is True
    assert res.decision == AuthorizationDecision.ALLOW
    assert res.error_code is None


def test_auth_deny_unauthenticated(sample_read_tool):
    """Unauthenticated actor is denied immediately."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="anonymous",
        roles=[],
        permissions=[],
    )
    inp = GetProjectStatusInput(project_id="prj_1")

    res = ToolAuthorizationPolicy.authorize(sample_read_tool, ctx, inp)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_UNAUTHENTICATED
    assert res.error_code == AIErrorCode.POLICY_DENIED


def test_auth_deny_missing_permission(sample_mutation_tool):
    """Caller without required permission is denied with DENY_PERMISSION."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_viewer",
        roles=["viewer"],
        permissions=["project:read"],  # Lacks blueprint:edit
        is_admin=False,
    )
    inp = PatchBlueprintInput(
        project_id="prj_1",
        blueprint={"project_id": "prj_1", "fps": 30, "aspect_ratio": "16:9", "scenes": []}
    )

    res = ToolAuthorizationPolicy.authorize(sample_mutation_tool, ctx, inp)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_PERMISSION
    assert res.error_code == AIErrorCode.POLICY_DENIED


def test_auth_deny_disabled_tool():
    """Disabled tool is rejected with DENY_TOOL_DISABLED."""
    disabled_tool = ToolDefinition(
        name="disabled_tool",
        description="Disabled tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusInput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=False,
    )
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_1",
        roles=["admin"],
        is_admin=True,
    )
    inp = GetProjectStatusInput(project_id="prj_1")

    res = ToolAuthorizationPolicy.authorize(disabled_tool, ctx, inp)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_TOOL_DISABLED
    assert res.error_code == AIErrorCode.CAPABILITY_UNAVAILABLE


def test_auth_admin_tool_non_admin_denied(sample_admin_tool):
    """Non-admin caller attempting admin-classified tool is denied."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_editor",
        roles=["editor"],
        permissions=["system:admin"],  # Even if permission claim exists, role is not admin
        is_admin=False,
    )
    inp = GetProjectStatusInput(project_id="prj_1")

    res = ToolAuthorizationPolicy.authorize(sample_admin_tool, ctx, inp)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_PERMISSION


def test_auth_admin_tool_admin_allowed(sample_admin_tool):
    """Admin caller is allowed for admin-classified tool."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_admin",
        roles=["admin"],
        is_admin=True,
    )
    inp = GetProjectStatusInput(project_id="prj_1")

    res = ToolAuthorizationPolicy.authorize(sample_admin_tool, ctx, inp)
    assert res.allowed is True
    assert res.decision == AuthorizationDecision.ALLOW


def test_auth_accessible_projects_confinement(sample_read_tool):
    """Explicit accessible_projects list restricts project access."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_scoped",
        roles=["editor"],
        permissions=["project:read"],
        accessible_projects=["prj_allowed"],
        is_admin=False,
    )

    # Allowed project
    inp_ok = GetProjectStatusInput(project_id="prj_allowed")
    assert ToolAuthorizationPolicy.authorize(sample_read_tool, ctx, inp_ok).allowed is True

    # Denied project
    inp_forbidden = GetProjectStatusInput(project_id="prj_other")
    res = ToolAuthorizationPolicy.authorize(sample_read_tool, ctx, inp_forbidden)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_TENANT
    assert res.error_code == AIErrorCode.TENANT_ACCESS_DENIED


def test_auth_cross_tenant_database_rejection(sample_read_tool, tmp_path):
    """Project registered to Workspace B must be rejected if caller is in Workspace A."""
    engine = get_database_engine()
    repo = TenantRepository(engine)

    import uuid
    uid = uuid.uuid4().hex[:8]
    ws_b = f"ws_b_{uid}"
    user_b = f"usr_b_{uid}"
    proj_b = f"prj_b_{uid}"

    repo.create_user(user_b, f"{user_b}_{uid}@example.com")
    repo.create_workspace(ws_b, "Workspace B", created_by=user_b)
    repo.create_project(proj_b, ws_b, created_by=user_b, name="Project B")

    # Caller from Workspace A attempts to access Project B
    caller_ctx = TrustedToolExecutionContext(
        workspace_id=f"ws_a_{tmp_path.name}",
        actor_id=f"usr_a_{tmp_path.name}",
        roles=["editor"],
        permissions=["project:read"],
        is_admin=False,
    )
    inp = GetProjectStatusInput(project_id=proj_b)

    res = ToolAuthorizationPolicy.authorize(sample_read_tool, caller_ctx, inp)
    assert res.allowed is False
    assert res.decision == AuthorizationDecision.DENY_TENANT
    assert res.error_code == AIErrorCode.TENANT_ACCESS_DENIED
    assert "Cross-tenant access violation" in (res.reason or "")
