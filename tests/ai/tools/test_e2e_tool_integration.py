"""
tests/ai/tools/test_e2e_tool_integration.py
===========================================
End-to-End Integration Tests for AI Tool Subsystem (S27.9).

Proves the complete pipeline:
ToolCall
  ↓
ToolRegistry
  ↓
ToolDispatcher
  ↓
ToolAuthorizationPolicy
  ↓
Domain Tool Adapter
  ↓
Domain Service
  ↓
Typed ToolResult (SUCCESS / ERROR)
"""

import uuid
from unittest.mock import patch
import pytest

from ai.contracts.errors import AIErrorCode
from ai.contracts.tools import ToolCall, ToolCallStatus
from ai.tools import (
    ToolDispatcher,
    TrustedToolExecutionContext,
    create_canonical_tool_registry,
)
from scripts.core.database import get_database_engine, TenantRepository
from scripts.core.run_model import RunRecord, RunStatus


def test_full_pipeline_valid_authorized_start_run():
    """
    End-to-end test: Valid authorized ToolCall to start_run traverses
    Registry -> Dispatcher -> Authorization -> Adapter -> RunService -> ToolResult.
    """
    registry = create_canonical_tool_registry()
    dispatcher = ToolDispatcher(registry=registry)

    ctx = TrustedToolExecutionContext(
        workspace_id="ws_e2e_test",
        actor_id="usr_operator",
        roles=["operator"],
        permissions=["run:execute"],
        is_admin=False,
    )

    call = ToolCall(
        call_id="call_e2e_start_run",
        tool_name="start_run",
        parameters={
            "project_id": "prj_e2e_target",
            "idempotency_key": "idemp_e2e_1",
        },
    )

    mock_record = RunRecord(
        run_id="run_e2e_12345",
        workspace_id="ws_e2e_test",
        project_id="prj_e2e_target",
        status=RunStatus.QUEUED,
        input_revision=4,
        idempotency_key="idemp_e2e_1",
    )

    with patch("api.services.run_service.RunService.create_run", return_value=(mock_record, True)) as mock_create_run:
        result = dispatcher.dispatch(call, ctx)

        assert result.call_id == "call_e2e_start_run"
        assert result.status == ToolCallStatus.SUCCESS
        assert result.error is None
        assert result.output is not None
        assert result.output["project_id"] == "prj_e2e_target"
        assert result.output["run_id"] == "run_e2e_12345"
        assert result.output["status"] == "QUEUED"
        assert result.output["is_created"] is True
        assert result.output["input_revision"] == 4

        mock_create_run.assert_called_once_with(
            project_id="prj_e2e_target",
            idempotency_key="idemp_e2e_1",
            workspace_id="ws_e2e_test",
        )


def test_full_pipeline_cross_tenant_denial_blocks_before_domain_service():
    """
    End-to-end test: Cross-tenant ToolCall traverses Dispatcher and Authorization,
    is rejected with TENANT_ACCESS_DENIED, and NEVER invokes domain service or adapter.
    """
    engine = get_database_engine()
    repo = TenantRepository(engine)

    uid = uuid.uuid4().hex[:8]
    ws_b = f"ws_victim_{uid}"
    user_b = f"usr_victim_{uid}"
    proj_b = f"prj_victim_{uid}"

    repo.create_user(user_b, f"{user_b}@example.com")
    repo.create_workspace(ws_b, "Victim Workspace", created_by=user_b)
    repo.create_project(proj_b, ws_b, created_by=user_b, name="Victim Project")

    registry = create_canonical_tool_registry()
    dispatcher = ToolDispatcher(registry=registry)

    # Attacker in Workspace A
    attacker_ctx = TrustedToolExecutionContext(
        workspace_id=f"ws_attacker_{uid}",
        actor_id=f"usr_attacker_{uid}",
        roles=["editor"],
        permissions=["run:execute"],
        is_admin=False,
    )

    attack_call = ToolCall(
        call_id="call_e2e_attack",
        tool_name="start_run",
        parameters={"project_id": proj_b},
    )

    with patch("api.services.run_service.RunService.create_run") as mock_create_run:
        result = dispatcher.dispatch(attack_call, attacker_ctx)

        assert result.status == ToolCallStatus.ERROR
        assert result.output is None
        assert result.error is not None
        assert result.error.code == AIErrorCode.TENANT_ACCESS_DENIED

        # ZERO SIDE EFFECTS PROOF
        assert mock_create_run.call_count == 0, "RunService must NOT be invoked on cross-tenant call!"


def test_full_pipeline_permission_denial_blocks_before_domain_service():
    """
    End-to-end test: Caller with viewer role attempts mutation tool (patch_blueprint).
    Dispatcher rejects with POLICY_DENIED before PipelineService is touched.
    """
    registry = create_canonical_tool_registry()
    dispatcher = ToolDispatcher(registry=registry)

    viewer_ctx = TrustedToolExecutionContext(
        workspace_id="ws_viewer_test",
        actor_id="usr_viewer_only",
        roles=["viewer"],
        permissions=["project:read"],  # Lacks blueprint:edit
        is_admin=False,
    )

    call = ToolCall(
        call_id="call_viewer_mutation",
        tool_name="patch_blueprint",
        parameters={
            "project_id": "prj_viewer_target",
            "blueprint": {
                "project_id": "prj_viewer_target",
                "fps": 30,
                "aspect_ratio": "16:9",
                "scenes": [],
            },
        },
    )

    with patch("api.services.pipeline_service.PipelineService.mutate_blueprint") as mock_mutate:
        result = dispatcher.dispatch(call, viewer_ctx)

        assert result.status == ToolCallStatus.ERROR
        assert result.error.code == AIErrorCode.POLICY_DENIED
        assert mock_mutate.call_count == 0, "PipelineService.mutate_blueprint must NOT be called!"
