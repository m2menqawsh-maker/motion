"""
ai/tools/domain/__init__.py
==========================
Canonical domain tool registrations for AI subsystem (S27.9).
"""

from __future__ import annotations

from ai.tools.contracts import (
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
    UpdateAssetStatusInput,
    UpdateAssetStatusOutput,
    CheckAssetCacheInput,
    CheckAssetCacheOutput,
    SaveAssetCacheInput,
    SaveAssetCacheOutput,
)
from ai.tools.domain.assets import (
    check_asset_cache_adapter,
    list_assets_adapter,
    save_asset_cache_adapter,
    update_asset_status_adapter,
)
from ai.tools.domain.blueprint import patch_blueprint_adapter, read_blueprint_adapter
from ai.tools.domain.projects import get_project_status_adapter
from ai.tools.domain.qc import get_qc_report_adapter
from ai.tools.domain.runs import cancel_run_adapter, start_run_adapter
from ai.tools.registry import ToolRegistry
from ai.tools.types import IdempotencyPolicy, SideEffectClass, ToolAuditPolicy

CANONICAL_TOOL_DEFINITIONS = [
    ToolDefinition(
        name="get_project_status",
        description="Query the canonical lifecycle status, allowed actions, and blocked reason of a project.",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        timeout_seconds=15.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="list_assets",
        description="List all verified media assets registered to the project in the asset manifest.",
        input_contract=ListAssetsInput,
        output_contract=ListAssetsOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="asset:read",
        timeout_seconds=15.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="read_blueprint",
        description="Retrieve the authoritative structural blueprint specification for the project.",
        input_contract=ReadBlueprintInput,
        output_contract=ReadBlueprintOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="blueprint:read",
        timeout_seconds=15.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="patch_blueprint",
        description="Validate and update the structural blueprint specification for the project.",
        input_contract=PatchBlueprintInput,
        output_contract=PatchBlueprintOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="blueprint:edit",
        timeout_seconds=30.0,
        idempotency_policy=IdempotencyPolicy.NON_IDEMPOTENT,
        audit_policy=ToolAuditPolicy.VERBOSE,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="start_run",
        description="Trigger an asynchronous pipeline execution run for the project.",
        input_contract=StartRunInput,
        output_contract=StartRunOutput,
        side_effect_class=SideEffectClass.RUN_CONTROL,
        required_permission="run:execute",
        timeout_seconds=30.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_BY_KEY,
        audit_policy=ToolAuditPolicy.VERBOSE,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="cancel_run",
        description="Request cancellation of an active pipeline execution run.",
        input_contract=CancelRunInput,
        output_contract=CancelRunOutput,
        side_effect_class=SideEffectClass.RUN_CONTROL,
        required_permission="run:cancel",
        timeout_seconds=30.0,
        idempotency_policy=IdempotencyPolicy.NON_IDEMPOTENT,
        audit_policy=ToolAuditPolicy.VERBOSE,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="get_qc_report",
        description="Inspect the latest Quality Control and probe report findings for the project.",
        input_contract=GetQcReportInput,
        output_contract=GetQcReportOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="qc:view",
        timeout_seconds=15.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    ),
]

MIGRATED_TOOL_DEFINITIONS = [
    ToolDefinition(
        name="update_asset_status",
        description="Update the lifecycle status of an asset within the authoritative asset manifest (S27.10 Domain Migration).",
        input_contract=UpdateAssetStatusInput,
        output_contract=UpdateAssetStatusOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="asset:upload",
        timeout_seconds=20.0,
        idempotency_policy=IdempotencyPolicy.NON_IDEMPOTENT,
        audit_policy=ToolAuditPolicy.VERBOSE,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="check_asset_cache",
        description="Check whether a processed media asset or variant is cached in project storage (S27.10 Domain Migration).",
        input_contract=CheckAssetCacheInput,
        output_contract=CheckAssetCacheOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="asset:read",
        timeout_seconds=15.0,
        idempotency_policy=IdempotencyPolicy.IDEMPOTENT_READ,
        audit_policy=ToolAuditPolicy.SUMMARY,
        enabled=True,
        version="1.0.0",
    ),
    ToolDefinition(
        name="save_asset_cache",
        description="Save a processed media asset variant to project cache storage (S27.10 Domain Migration).",
        input_contract=SaveAssetCacheInput,
        output_contract=SaveAssetCacheOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission="asset:upload",
        timeout_seconds=20.0,
        idempotency_policy=IdempotencyPolicy.NON_IDEMPOTENT,
        audit_policy=ToolAuditPolicy.VERBOSE,
        enabled=True,
        version="1.0.0",
    ),
]


def register_canonical_tools(registry: ToolRegistry) -> None:
    """Registers the core S27.9 domain tools into the provided ToolRegistry."""
    adapters = {
        "get_project_status": get_project_status_adapter,
        "list_assets": list_assets_adapter,
        "read_blueprint": read_blueprint_adapter,
        "patch_blueprint": patch_blueprint_adapter,
        "start_run": start_run_adapter,
        "cancel_run": cancel_run_adapter,
        "get_qc_report": get_qc_report_adapter,
    }

    for tool_def in CANONICAL_TOOL_DEFINITIONS:
        adapter = adapters[tool_def.name]
        registry.register(tool_def, adapter)


def register_migrated_tools(registry: ToolRegistry) -> None:
    """Registers S27.10 migrated tools into the provided ToolRegistry."""
    adapters = {
        "update_asset_status": update_asset_status_adapter,
        "check_asset_cache": check_asset_cache_adapter,
        "save_asset_cache": save_asset_cache_adapter,
    }

    for tool_def in MIGRATED_TOOL_DEFINITIONS:
        adapter = adapters[tool_def.name]
        registry.register(tool_def, adapter)



