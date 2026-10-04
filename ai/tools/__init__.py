"""
ai/tools/__init__.py
====================
AI Tool Subsystem (S27.9): Tool Registry, Server-Side Authorization, and Domain Tool Layer.
"""

from __future__ import annotations

from ai.tools.audit import (
    ToolAuditRecord,
    ToolAuditRecorder,
    default_audit_recorder,
)
from ai.tools.authorization import ToolAuthorizationPolicy
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
from ai.tools.gateway import ToolGateway
from ai.tools.dispatcher import ToolDispatcher
from ai.tools.domain import (
    CANONICAL_TOOL_DEFINITIONS,
    register_canonical_tools,
)
from ai.tools.errors import (
    DisabledToolError,
    DuplicateToolError,
    ToolAuthorizationError,
    ToolDomainExecutionError,
    ToolError,
    ToolInputValidationError,
    ToolOutputValidationError,
    ToolPermissionDeniedError,
    ToolTenantAccessDeniedError,
    ToolTimeoutError,
    UnknownToolError,
    to_ai_error,
)
from ai.tools.registry import (
    ToolRegistration,
    ToolRegistry,
    default_tool_registry,
)
from ai.tools.types import (
    AuthorizationDecision,
    AuthorizationDecisionEnum,
    IdempotencyPolicy,
    IdempotencyPolicyEnum,
    SideEffectClass,
    SideEffectClassEnum,
    ToolAuditPolicy,
    ToolAuditPolicyEnum,
    ToolAuthorizationResult,
    TrustedToolExecutionContext,
)


def create_canonical_tool_registry() -> ToolRegistry:
    """Factory creating a new ToolRegistry populated with all canonical domain tools."""
    reg = ToolRegistry()
    register_canonical_tools(reg)
    return reg


__all__ = [
    # Core Orchestration
    "ToolGateway",
    "ToolRegistry",
    "default_tool_registry",
    "create_canonical_tool_registry",
    "ToolDispatcher",
    "ToolAuthorizationPolicy",
    "ToolDefinition",
    "ToolRegistration",
    "register_canonical_tools",
    "CANONICAL_TOOL_DEFINITIONS",
    # Audit
    "ToolAuditRecord",
    "ToolAuditRecorder",
    "default_audit_recorder",
    # Context & Types
    "TrustedToolExecutionContext",
    "ToolAuthorizationResult",
    "SideEffectClass",
    "SideEffectClassEnum",
    "IdempotencyPolicy",
    "IdempotencyPolicyEnum",
    "ToolAuditPolicy",
    "ToolAuditPolicyEnum",
    "AuthorizationDecision",
    "AuthorizationDecisionEnum",
    # Errors
    "ToolError",
    "UnknownToolError",
    "DisabledToolError",
    "DuplicateToolError",
    "ToolInputValidationError",
    "ToolOutputValidationError",
    "ToolAuthorizationError",
    "ToolTenantAccessDeniedError",
    "ToolPermissionDeniedError",
    "ToolTimeoutError",
    "ToolDomainExecutionError",
    "to_ai_error",
    # Contracts
    "GetProjectStatusInput",
    "GetProjectStatusOutput",
    "ListAssetsInput",
    "AssetSummaryItem",
    "ListAssetsOutput",
    "ReadBlueprintInput",
    "ReadBlueprintOutput",
    "PatchBlueprintInput",
    "PatchBlueprintOutput",
    "StartRunInput",
    "StartRunOutput",
    "CancelRunInput",
    "CancelRunOutput",
    "GetQcReportInput",
    "GetQcReportOutput",
]
