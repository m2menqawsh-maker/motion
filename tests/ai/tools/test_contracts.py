"""
tests/ai/tools/test_contracts.py
================================
Unit tests for AI Tool contracts, definitions, and types (S27.9).
"""

import pytest
from pydantic import ValidationError

from ai.contracts.base import AIContractModel
from ai.tools.contracts import (
    AssetSummaryItem,
    CancelRunInput,
    CancelRunOutput,
    GetProjectStatusInput,
    GetProjectStatusOutput,
    GetQcReportInput,
    GetQcReportOutput,
    ListAssetsInput,
    ListAssetsOutput,
    PatchBlueprintInput,
    PatchBlueprintOutput,
    ReadBlueprintInput,
    ReadBlueprintOutput,
    StartRunInput,
    StartRunOutput,
    ToolDefinition,
)
from ai.tools.types import (
    AuthorizationDecision,
    IdempotencyPolicy,
    SideEffectClass,
    ToolAuditPolicy,
    TrustedToolExecutionContext,
)


def test_tool_definition_valid():
    """Verify ToolDefinition can be constructed with valid parameters."""
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool for validation",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=20.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    )
    assert tool_def.name == "test_tool"
    assert tool_def.enabled is True
    schema = tool_def.get_input_schema()
    assert "properties" in schema
    assert "project_id" in schema["properties"]


def test_tool_definition_invalid_name():
    r"""Tool name must follow pattern ^[a-zA-Z0-9_\-]+$."""
    with pytest.raises(ValidationError):
        ToolDefinition(
            name="invalid name with spaces!",
            description="desc",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="project:read",
        )


def test_tool_definition_timeout_bounds():
    """Timeout must be strictly bounded between 0 and 300 seconds."""
    with pytest.raises(ValidationError):
        ToolDefinition(
            name="test_tool",
            description="desc",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="project:read",
            timeout_seconds=0.0,
        )

    with pytest.raises(ValidationError):
        ToolDefinition(
            name="test_tool",
            description="desc",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="project:read",
            timeout_seconds=500.0,
        )


def test_input_contract_extra_forbidden():
    """Tool inputs must strictly forbid unknown or forged fields."""
    # Valid input
    valid_inp = GetProjectStatusInput(project_id="prj_123")
    assert valid_inp.project_id == "prj_123"

    # Forged identity or unknown fields must fail validation
    with pytest.raises(ValidationError):
        GetProjectStatusInput.model_validate({"project_id": "prj_123", "workspace_id": "ws_attack"})

    with pytest.raises(ValidationError):
        GetProjectStatusInput.model_validate({"project_id": "prj_123", "role": "admin"})

    with pytest.raises(ValidationError):
        GetProjectStatusInput.model_validate({"project_id": "prj_123", "actor_id": "root"})


def test_input_contract_malformed_id():
    """IDs must conform to safe regex patterns."""
    with pytest.raises(ValidationError):
        GetProjectStatusInput(project_id="../traversal/path")


def test_trusted_tool_execution_context():
    """Verify TrustedToolExecutionContext enforces caller authority and helpers."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_alpha",
        actor_id="usr_momen",
        roles=["editor"],
        permissions=["project:read", "blueprint:edit"],
        is_admin=False,
        accessible_projects=["prj_alpha"],
    )
    assert ctx.can_access_project("prj_alpha") is True
    assert ctx.can_access_project("prj_beta") is False
    assert ctx.has_permission("project:read") is True
    assert ctx.has_permission("admin:access") is False


def test_trusted_tool_execution_context_admin():
    """Admin context bypasses project scope restrictions."""
    ctx = TrustedToolExecutionContext(
        workspace_id="ws_alpha",
        actor_id="usr_admin",
        roles=["admin"],
        is_admin=True,
    )
    assert ctx.can_access_project("prj_any") is True
    assert ctx.has_permission("any:action") is True


def test_all_canonical_contracts_are_ai_contract_models():
    """Ensure all tool inputs and outputs inherit from AIContractModel."""
    contracts = [
        GetProjectStatusInput,
        GetProjectStatusOutput,
        ListAssetsInput,
        AssetSummaryItem,
        ListAssetsOutput,
        ReadBlueprintInput,
        ReadBlueprintOutput,
        PatchBlueprintInput,
        PatchBlueprintOutput,
        StartRunInput,
        StartRunOutput,
        CancelRunInput,
        CancelRunOutput,
        GetQcReportInput,
        GetQcReportOutput,
    ]
    for c in contracts:
        assert issubclass(c, AIContractModel), f"{c.__name__} must inherit from AIContractModel"
        assert c.model_config.get("extra") == "forbid"
        assert c.model_config.get("strict") is True
        assert c.model_config.get("frozen") is True


def test_tool_definition_permission_enum_validation():
    """ToolDefinition.required_permission must be typed to Action enum, rejecting typos and free-form strings."""
    from scripts.core.security.permissions import Action

    # Valid with Action enum
    td_enum = ToolDefinition(
        name="test_tool",
        description="desc",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission=Action.PROJECT_READ,
    )
    assert td_enum.required_permission == Action.PROJECT_READ

    # Valid with valid string corresponding to Action
    td_str = ToolDefinition(
        name="test_tool",
        description="desc",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
    )
    assert td_str.required_permission == Action.PROJECT_READ

    # Typo or invalid permission must fail validation
    with pytest.raises(ValidationError):
        ToolDefinition(
            name="test_tool",
            description="desc",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="project:red",  # Typo!
        )

    with pytest.raises(ValidationError):
        ToolDefinition(
            name="test_tool",
            description="desc",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="random:freeform:permission",
        )


def test_patch_blueprint_input_validation():
    """Verify PatchBlueprintInput validates canonical BlueprintV2 and rejects invalid structures and identity mismatches."""
    from scripts.core.blueprint_model import BlueprintV2

    valid_bp = BlueprintV2(
        project_id="prj_valid",
        fps=30,
        aspect_ratio="16:9",
        scenes=[],
    )

    # Valid payload accepted
    inp = PatchBlueprintInput(
        project_id="prj_valid",
        expected_revision=2,
        blueprint=valid_bp,
    )
    assert inp.project_id == "prj_valid"
    assert inp.expected_revision == 2
    assert inp.blueprint.project_id == "prj_valid"

    # Identity smuggling attack: blueprint project_id != target project_id
    with pytest.raises(ValidationError) as exc_info:
        PatchBlueprintInput(
            project_id="prj_target",
            blueprint=valid_bp,  # valid_bp has project_id="prj_valid"
        )
    assert "does not match target project_id" in str(exc_info.value)

    # Invalid blueprint structure: missing required fields
    with pytest.raises(ValidationError):
        PatchBlueprintInput.model_validate({
            "project_id": "prj_test",
            "blueprint": {"project_id": "prj_test"}  # missing fps, aspect_ratio, scenes
        })

    # Invalid scene structure in blueprint
    with pytest.raises(ValidationError):
        PatchBlueprintInput.model_validate({
            "project_id": "prj_test",
            "blueprint": {
                "project_id": "prj_test",
                "fps": 30,
                "aspect_ratio": "16:9",
                "scenes": [
                    {"scene_id": "sc_01", "template": "title", "startFrame": 0, "durationFrames": 0}  # durationFrames must be >= 1
                ]
            }
        })
