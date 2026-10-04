"""
tests/ai/tools/test_security_adversarial.py
===========================================
Adversarial security test suite with Zero-Side-Effect proof (S27.9).

Requirements:
- Section 28: Cross-Tenant Attack Test (BLOCKER)
- Section 29: Zero-Side-Effect Proof (Denial before mutation, counter = 0, state unchanged)
- Section 30: Forged Identity Attacks (workspace_id, role, actor_id, approved_by rejected)
- Section 31: Revoked Access (Execution-time authorization authority)
- Section 32: Disabled Tool Attack
- Section 33: Unknown Tool Attack
- Section 34: Parameter Injection / Path Traversal
- Section 51: Full denial verification matrix
"""

from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

from ai.contracts.errors import AIErrorCode
from ai.contracts.tools import ToolCall, ToolCallStatus
from ai.tools.contracts import (
    GetProjectStatusInput,
    GetProjectStatusOutput,
    PatchBlueprintInput,
    PatchBlueprintOutput,
    StartRunInput,
    StartRunOutput,
    ToolDefinition,
)
from ai.tools.dispatcher import ToolDispatcher
from ai.tools.domain import register_canonical_tools
from ai.tools.registry import ToolRegistry
from ai.tools.types import (
    IdempotencyPolicy,
    SideEffectClass,
    ToolAuditPolicy,
    TrustedToolExecutionContext,
)
from scripts.core.database import get_database_engine, TenantRepository


@pytest.fixture
def clean_tool_registry():
    reg = ToolRegistry()
    register_canonical_tools(reg)
    return reg


def test_cross_tenant_attack_zero_side_effects(tmp_path):
    """
    CRITICAL BLOCKER TEST (Section 28 & 29):
    Actor A in Workspace A attempts to mutate Project B belonging to Workspace B.
    Assertion: DENIED + ZERO SIDE EFFECTS PROOF (Adapter is NEVER called, counter = 0).
    """
    engine = get_database_engine()
    repo = TenantRepository(engine)

    # 1. Setup Tenant B and Project B in DB
    import uuid
    uid = uuid.uuid4().hex[:8]
    user_b = f"usr_b_{uid}"
    ws_b = f"ws_b_{uid}"
    proj_b = f"prj_b_{uid}"

    repo.create_user(user_b, f"{user_b}_{uid}@example.com")
    repo.create_workspace(ws_b, "Workspace B", created_by=user_b)
    repo.create_project(proj_b, ws_b, created_by=user_b, name="Project B")

    # 2. Spy adapter to prove zero side effects
    adapter_invocation_count = 0

    def spy_patch_adapter(inp: PatchBlueprintInput, ctx: TrustedToolExecutionContext):
        nonlocal adapter_invocation_count
        adapter_invocation_count += 1
        return PatchBlueprintOutput(project_id=inp.project_id, revision=99, success=True, message="mutated")

    reg = ToolRegistry()
    tool_def = ToolDefinition(
        name="patch_blueprint",
        description="Mutate blueprint",
        input_contract=PatchBlueprintInput,
        output_contract=PatchBlueprintOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="blueprint:edit",
        timeout_seconds=10.0,
    )
    reg.register(tool_def, spy_patch_adapter)
    dispatcher = ToolDispatcher(registry=reg)

    # 3. Legitimate Actor A authenticated in Workspace A
    actor_a_context = TrustedToolExecutionContext(
        workspace_id=f"ws_a_{tmp_path.name}",
        actor_id=f"usr_a_{tmp_path.name}",
        roles=["editor"],
        permissions=["blueprint:edit"],
        is_admin=False,
    )

    # 4. Actor A sends valid ToolCall targeting Project B
    attack_call = ToolCall(
        call_id="call_attack_cross_tenant",
        tool_name="patch_blueprint",
        parameters={
            "project_id": proj_b,
            "blueprint": {"project_id": proj_b, "fps": 60, "aspect_ratio": "16:9", "scenes": []},
        },
    )

    result = dispatcher.dispatch(attack_call, actor_a_context)

    # 5. Assertions: Denied closed
    assert result.status == ToolCallStatus.ERROR
    assert result.output is None
    assert result.error is not None
    assert result.error.code == AIErrorCode.TENANT_ACCESS_DENIED

    # 6. ZERO SIDE EFFECTS PROOF
    assert adapter_invocation_count == 0, "Security Invariant Violated: Adapter was invoked on cross-tenant request!"


def test_forged_identity_attack_rejected():
    """
    Section 30: Model attempts to forge authoritative identity claims in ToolCall.
    ToolCall validation strictly forbids identity/permission fields.
    """
    # 1. Attempt forged workspace_id
    with pytest.raises(ValueError, match="Security violation.*workspace_id"):
        ToolCall(
            call_id="call_forge_ws",
            tool_name="patch_blueprint",
            parameters={
                "project_id": "prj_target",
                "workspace_id": "ws_victim",
            },
        )

    # 2. Attempt forged role
    with pytest.raises(ValueError, match="Security violation.*role"):
        ToolCall(
            call_id="call_forge_role",
            tool_name="patch_blueprint",
            parameters={
                "project_id": "prj_target",
                "role": "admin",
            },
        )

    # 3. Attempt forged approved_by
    with pytest.raises(ValueError, match="Security violation.*approved_by"):
        ToolCall(
            call_id="call_forge_approved",
            tool_name="patch_blueprint",
            parameters={
                "project_id": "prj_target",
                "approved_by": "root",
            },
        )

    # 4. Attempt forged actor_id
    with pytest.raises(ValueError, match="Security violation.*actor_id"):
        ToolCall(
            call_id="call_forge_actor",
            tool_name="patch_blueprint",
            parameters={
                "project_id": "prj_target",
                "actor_id": "sys_admin",
            },
        )


def test_forged_identity_input_model_extra_forbid():
    """Even if ToolCall didn't catch it, input contracts have extra='forbid'."""
    with pytest.raises(ValidationError):
        PatchBlueprintInput.model_validate({
            "project_id": "prj_1",
            "blueprint": {},
            "is_admin": True,
        })


def test_revoked_access_enforced_at_runtime():
    """
    Section 31: Caller had access at schema time, but access was revoked
    before dispatch. Dispatcher MUST deny execution with ZERO side effects.
    """
    adapter_called = 0

    def spy_adapter(inp, ctx):
        nonlocal adapter_called
        adapter_called += 1
        return StartRunOutput(
            project_id=inp.project_id,
            run_id="run_1",
            status="QUEUED",
            is_created=True,
            input_revision=1,
        )

    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            name="start_run",
            description="Start run",
            input_contract=StartRunInput,
            output_contract=StartRunOutput,
            side_effect_class=SideEffectClass.RUN_CONTROL,
            required_permission="run:execute",
        ),
        spy_adapter,
    )
    dispatcher = ToolDispatcher(registry=reg)

    # Context with revoked permission (empty permissions list)
    revoked_ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_revoked",
        roles=["viewer"],  # Demoted from editor to viewer
        permissions=["project:read"],  # run:execute was removed
        is_admin=False,
    )

    call = ToolCall(
        call_id="call_revoked",
        tool_name="start_run",
        parameters={"project_id": "prj_1"},
    )

    res = dispatcher.dispatch(call, revoked_ctx)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.POLICY_DENIED
    assert adapter_called == 0, "Adapter must not be called after permission revocation!"


def test_disabled_tool_attack_zero_side_effects():
    """
    Section 32: Model sends call to disabled tool.
    Must fail closed with ZERO side effects.
    """
    adapter_called = 0

    def spy_adapter(inp, ctx):
        nonlocal adapter_called
        adapter_called += 1
        return StartRunOutput(project_id="prj_1", run_id="run_x", status="QUEUED", is_created=True, input_revision=1)

    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            name="start_run",
            description="Start run",
            input_contract=StartRunInput,
            output_contract=StartRunOutput,
            side_effect_class=SideEffectClass.RUN_CONTROL,
            required_permission="run:execute",
            enabled=False,  # DISABLED
        ),
        spy_adapter,
    )
    dispatcher = ToolDispatcher(registry=reg)

    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_admin",
        roles=["admin"],
        is_admin=True,
    )
    call = ToolCall(call_id="call_dis", tool_name="start_run", parameters={"project_id": "prj_1"})

    res = dispatcher.dispatch(call, ctx)
    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.CAPABILITY_UNAVAILABLE
    assert adapter_called == 0


def test_unknown_tool_attack_zero_side_effects():
    """
    Section 33: Model attempts unknown tool 'delete_everything'.
    Must fail closed without evaluation or side effects.
    """
    reg = ToolRegistry()
    dispatcher = ToolDispatcher(registry=reg)

    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_1",
        roles=["admin"],
        is_admin=True,
    )
    call = ToolCall(call_id="call_unknown", tool_name="delete_everything", parameters={})

    res = dispatcher.dispatch(call, ctx)
    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.CAPABILITY_UNAVAILABLE


def test_parameter_injection_path_traversal():
    """
    Section 34: Model passes traversal strings in project_id.
    Strict regex validation rejects the input.
    """
    dispatcher = ToolDispatcher()
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_1",
        actor_id="usr_1",
        roles=["admin"],
        is_admin=True,
    )

    traversal_payloads = [
        "../../etc/passwd",
        "prj_test/../other",
        "prj; DROP TABLE projects;",
        "prj\x00nullbyte",
    ]

    for payload in traversal_payloads:
        with pytest.raises(ValidationError):
            GetProjectStatusInput(project_id=payload)


def test_no_qc_or_human_approval_bypass_tool_exists(clean_tool_registry):
    """
    Section 41: Verify there are NO tools registered that allow AI to
    approve QC, bypass review, or forge human decisions.
    """
    tools = clean_tool_registry.list_tools(include_disabled=True)
    forbidden_names = {
        "approve_qc",
        "approve_project",
        "mark_human_approved",
        "force_pass_gate",
        "unlock_studio",
        "approve_review",
    }
    registered_names = {t.name for t in tools}
    overlap = forbidden_names.intersection(registered_names)
    assert len(overlap) == 0, f"Forbidden authority bypass tools detected in registry: {overlap}"


def test_mutating_tool_timeout_guarantees_state_unmodified():
    """
    BLOCKER 3 Proof: When a mutating tool adapter times out or is cancelled,
    cooperative checkpoints prevent post-timeout side-effects.
    Empirically proves: state before == state after.
    """
    initial_state = {"revision": 1, "mutated": False}
    current_state = dict(initial_state)

    def slow_mutating_adapter(inp: PatchBlueprintInput, ctx: TrustedToolExecutionContext):
        # Adapter simulates slow operation
        import time
        time.sleep(0.15)
        # Pre-commit checkpoint
        ctx.assert_not_timed_out()
        # Side effect
        current_state["revision"] = 2
        current_state["mutated"] = True
        return PatchBlueprintOutput(project_id=inp.project_id, revision=2, success=True, message="mutated")

    reg = ToolRegistry()
    tool_def = ToolDefinition(
        name="patch_blueprint",
        description="Mutate blueprint",
        input_contract=PatchBlueprintInput,
        output_contract=PatchBlueprintOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="blueprint:edit",
        timeout_seconds=0.05,  # 50ms timeout < 150ms sleep
    )
    reg.register(tool_def, slow_mutating_adapter)
    dispatcher = ToolDispatcher(registry=reg)

    ctx = TrustedToolExecutionContext(
        workspace_id="ws_timeout_test",
        actor_id="usr_tester",
        roles=["editor"],
        permissions=["blueprint:edit"],
        is_admin=False,
    )

    call = ToolCall(
        call_id="call_slow_mutate",
        tool_name="patch_blueprint",
        parameters={
            "project_id": "prj_safe",
            "blueprint": {"project_id": "prj_safe", "fps": 30, "aspect_ratio": "16:9", "scenes": []},
        },
    )

    result = dispatcher.dispatch(call, ctx)

    # Dispatcher must return TIMEOUT error
    assert result.status == ToolCallStatus.ERROR
    assert result.error is not None
    assert result.error.code == AIErrorCode.TIMEOUT

    # Wait for background thread to reach pre-commit checkpoint
    import time
    time.sleep(0.15)

    # Invariant: state before == state after
    assert current_state == initial_state, f"State was corrupted after timeout: {current_state} != {initial_state}"
    assert current_state["mutated"] is False
    assert current_state["revision"] == 1


def test_trusted_identity_construction_from_canonical_types():
    """
    BLOCKER 4 Proof: TrustedToolExecutionContext constructed from canonical Principal & TenantContext
    properly binds identity and cannot be forged.
    """
    from scripts.core.security.principal import Principal, PrincipalType, Role
    from scripts.core.tenant_model import TenantContext

    # 1. From Principal
    p = Principal(
        principal_id="usr_canonical_principal",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
        project_scopes={"prj_scoped": {Role.EDITOR}},
    )
    ctx_p = TrustedToolExecutionContext.from_principal(p, workspace_id="ws_canonical")
    assert ctx_p.actor_id == "usr_canonical_principal"
    assert ctx_p.workspace_id == "ws_canonical"
    assert ctx_p.is_admin is False
    assert "editor" in ctx_p.roles
    assert ctx_p.can_access_project("prj_scoped") is True
    assert ctx_p.can_access_project("prj_other") is False
    assert ctx_p.has_permission("blueprint:edit") is True

    # 2. From TenantContext
    tc = TenantContext(
        workspace_id="ws_tenant_ctx",
        user_id="usr_canonical_tenant",
        role=Role.VIEWER,
        principal=Principal(
            principal_id="usr_canonical_tenant",
            principal_type=PrincipalType.HUMAN,
            roles={Role.VIEWER},
        ),
    )
    ctx_tc = TrustedToolExecutionContext.from_tenant_context(tc)
    assert ctx_tc.actor_id == "usr_canonical_tenant"
    assert ctx_tc.workspace_id == "ws_tenant_ctx"
    assert ctx_tc.is_admin is False
    assert "viewer" in ctx_tc.roles
    assert ctx_tc.has_permission("project:read") is True
    assert ctx_tc.has_permission("blueprint:edit") is False  # Viewer lacks blueprint:edit!

