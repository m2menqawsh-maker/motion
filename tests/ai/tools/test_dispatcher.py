"""
tests/ai/tools/test_dispatcher.py
=================================
Unit tests for canonical ToolDispatcher execution flow and safety gates (S27.9).
"""

import asyncio
import time
import pytest

from ai.contracts.errors import AIErrorCode
from ai.contracts.tools import ToolCall, ToolCallStatus
from ai.tools.audit import ToolAuditRecorder
from ai.tools.contracts import (
    GetProjectStatusInput,
    GetProjectStatusOutput,
    ToolDefinition,
)
from ai.tools.dispatcher import ToolDispatcher
from ai.tools.registry import ToolRegistry
from ai.tools.types import (
    IdempotencyPolicy,
    SideEffectClass,
    ToolAuditPolicy,
    TrustedToolExecutionContext,
)


@pytest.fixture
def test_context():
    return TrustedToolExecutionContext(
        workspace_id="ws_dispatcher_test",
        actor_id="usr_tester",
        roles=["editor"],
        permissions=["project:read", "blueprint:edit"],
        is_admin=False,
    )


@pytest.fixture
def mock_registry():
    reg = ToolRegistry()

    # 1. Normal sync tool
    def sync_adapter(inp: GetProjectStatusInput, ctx: TrustedToolExecutionContext):
        return GetProjectStatusOutput(
            project_id=inp.project_id,
            lifecycle_state="DRAFT",
            revision=1,
            allowed_actions=["project:read"],
        )

    tool_sync = ToolDefinition(
        name="test_sync_tool",
        description="Sync test tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=5.0,
    )
    reg.register(tool_sync, sync_adapter)

    # 2. Async tool
    async def async_adapter(inp: GetProjectStatusInput, ctx: TrustedToolExecutionContext):
        await asyncio.sleep(0.01)
        return GetProjectStatusOutput(
            project_id=inp.project_id,
            lifecycle_state="PLAN_READY",
            revision=2,
            allowed_actions=["project:read"],
        )

    tool_async = ToolDefinition(
        name="test_async_tool",
        description="Async test tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=5.0,
    )
    reg.register(tool_async, async_adapter)

    # 3. Slow tool for timeout test
    def slow_adapter(inp: GetProjectStatusInput, ctx: TrustedToolExecutionContext):
        time.sleep(0.5)
        return GetProjectStatusOutput(
            project_id=inp.project_id,
            lifecycle_state="DRAFT",
            revision=1,
            allowed_actions=[],
        )

    tool_slow = ToolDefinition(
        name="test_slow_tool",
        description="Slow test tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=0.1,  # Short timeout
    )
    reg.register(tool_slow, slow_adapter)

    # 4. Malformed output tool
    def bad_output_adapter(inp: GetProjectStatusInput, ctx: TrustedToolExecutionContext):
        return {"corrupt": "data"}  # Missing required fields of GetProjectStatusOutput

    tool_bad_out = ToolDefinition(
        name="test_bad_output_tool",
        description="Bad output test tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=5.0,
    )
    reg.register(tool_bad_out, bad_output_adapter)

    # 5. Disabled tool
    tool_disabled = ToolDefinition(
        name="test_disabled_tool",
        description="Disabled tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=False,
    )
    reg.register(tool_disabled, sync_adapter)

    return reg


def test_dispatcher_success_sync(mock_registry, test_context):
    """Verify successful dispatch of synchronous adapter."""
    audit = ToolAuditRecorder()
    dispatcher = ToolDispatcher(registry=mock_registry, audit_recorder=audit)

    call = ToolCall(
        call_id="call_sync_1",
        tool_name="test_sync_tool",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.call_id == "call_sync_1"
    assert res.status == ToolCallStatus.SUCCESS
    assert res.error is None
    assert res.output is not None
    assert res.output["lifecycle_state"] == "DRAFT"
    assert res.duration_ms >= 0

    # Verify audit
    records = audit.get_records(tool_name="test_sync_tool")
    assert len(records) == 1
    assert records[0].status == ToolCallStatus.SUCCESS
    assert records[0].actor_id == test_context.actor_id


@pytest.mark.asyncio
async def test_dispatcher_success_async(mock_registry, test_context):
    """Verify successful dispatch of asynchronous adapter."""
    audit = ToolAuditRecorder()
    dispatcher = ToolDispatcher(registry=mock_registry, audit_recorder=audit)

    call = ToolCall(
        call_id="call_async_1",
        tool_name="test_async_tool",
        parameters={"project_id": "prj_async"},
    )
    res = await dispatcher.dispatch_async(call, test_context)

    assert res.status == ToolCallStatus.SUCCESS
    assert res.output["lifecycle_state"] == "PLAN_READY"


def test_dispatcher_unknown_tool(mock_registry, test_context):
    """Calling an unknown tool fails closed before execution."""
    audit = ToolAuditRecorder()
    dispatcher = ToolDispatcher(registry=mock_registry, audit_recorder=audit)

    call = ToolCall(
        call_id="call_unknown",
        tool_name="does_not_exist",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.status == ToolCallStatus.ERROR
    assert res.output is None
    assert res.error.code == AIErrorCode.CAPABILITY_UNAVAILABLE

    records = audit.get_records(tool_name="does_not_exist")
    assert len(records) == 1
    assert records[0].status == ToolCallStatus.ERROR


def test_dispatcher_disabled_tool(mock_registry, test_context):
    """Calling a disabled tool fails closed before execution."""
    audit = ToolAuditRecorder()
    dispatcher = ToolDispatcher(registry=mock_registry, audit_recorder=audit)

    call = ToolCall(
        call_id="call_disabled",
        tool_name="test_disabled_tool",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.CAPABILITY_UNAVAILABLE

    records = audit.get_records(tool_name="test_disabled_tool")
    assert len(records) == 1
    assert records[0].error_code == AIErrorCode.CAPABILITY_UNAVAILABLE.value


def test_dispatcher_invalid_input_schema(mock_registry, test_context):
    """Invalid input payload fails closed with SCHEMA_VALIDATION_FAILED."""
    dispatcher = ToolDispatcher(registry=mock_registry)

    # Missing mandatory 'project_id'
    call = ToolCall(
        call_id="call_bad_schema",
        tool_name="test_sync_tool",
        parameters={"unexpected_param": "val"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED


def test_dispatcher_authorization_denied(mock_registry):
    """Caller lacking permission is rejected before adapter execution."""
    unauthorized_ctx = TrustedToolExecutionContext(
        workspace_id="ws_other",
        actor_id="usr_unauth",
        roles=["guest"],
        permissions=[],  # Lacks project:read
        is_admin=False,
    )
    dispatcher = ToolDispatcher(registry=mock_registry)

    call = ToolCall(
        call_id="call_unauth",
        tool_name="test_sync_tool",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, unauthorized_ctx)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.POLICY_DENIED


def test_dispatcher_timeout_bounded(mock_registry, test_context):
    """Tool exceeding execution timeout returns TIMEOUT error."""
    dispatcher = ToolDispatcher(registry=mock_registry)

    call = ToolCall(
        call_id="call_timeout",
        tool_name="test_slow_tool",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.TIMEOUT


def test_dispatcher_output_validation_failure(mock_registry, test_context):
    """Adapter returning invalid schema fails closed with SCHEMA_VALIDATION_FAILED."""
    dispatcher = ToolDispatcher(registry=mock_registry)

    call = ToolCall(
        call_id="call_corrupt_out",
        tool_name="test_bad_output_tool",
        parameters={"project_id": "prj_test"},
    )
    res = dispatcher.dispatch(call, test_context)

    assert res.status == ToolCallStatus.ERROR
    assert res.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED
