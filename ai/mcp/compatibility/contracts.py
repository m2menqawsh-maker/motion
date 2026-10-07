"""
ai/mcp/compatibility/contracts.py
===================================
Authoritative contract definitions for the MCP Compatibility Layer (S28-M09).

Invariants:
- Strongly typed compatibility representations; no raw untyped dict boundaries.
- Explicit lifecycle status (FULL, PARTIAL, DEPRECATED, BLOCKED).
- Explicit tenant and actor binding on every inbound compatibility request.
- Preserves machine-readable error identity on failure.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import Field, field_validator

from ai.contracts.base import AIContractModel
from ai.contracts.common import CapabilityType, CapabilityTypeEnum
from ai.contracts.errors import AIError


class MCPCompatibilityStatus(str, Enum):
    """Authoritative compatibility disposition of a legacy MCP tool."""
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    DEPRECATED = "DEPRECATED"
    BLOCKED = "BLOCKED"


class CompatibilityRequest(AIContractModel):
    """
    Inbound execution request from an external MCP client or legacy wrapper.
    Carries required tenant context to ensure fail-closed authorization.
    """
    server_id: str = Field(min_length=1, description="Legacy MCP server identifier")
    tool_name: str = Field(min_length=1, description="Legacy tool function name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Untyped legacy caller arguments")
    workspace_id: str = Field(default="ws_default", min_length=1, description="Tenant boundary isolation key")
    project_id: str = Field(default="prj_default", min_length=1, description="Project context identifier")
    actor_id: str = Field(default="usr_external_mcp", min_length=1, description="Calling actor identifier")
    roles: List[str] = Field(default_factory=lambda: ["EDITOR"], description="RBAC roles for caller")
    permissions: List[str] = Field(default_factory=lambda: ["editor", "viewer", "asset:read", "asset:upload"], description="Granted permissions")
    idempotency_key: Optional[str] = Field(default=None, description="Client idempotency key if provided")


class CompatibilityResponse(AIContractModel):
    """
    Outbound response returned to external MCP client.
    Matches legacy return format while retaining machine-readable canonical metadata.
    """
    success: bool = Field(description="Whether the capability execution succeeded")
    data: Any = Field(default=None, description="Legacy-compatible payload returned to MCP caller")
    capability_id: str = Field(description="Canonical Capability ID executed")
    canonical_owner: str = Field(description="Canonical subsystem that owns the business logic")
    duration_ms: int = Field(ge=0, description="Execution duration in milliseconds")
    error: Optional[AIError] = Field(default=None, description="Structured error when success=False")
    canonical_output: Optional[Dict[str, Any]] = Field(default=None, description="Raw canonical output dictionary")


class LegacyToolDescriptor(AIContractModel):
    """
    Metadata specification for a legacy MCP tool mapped to a canonical capability.
    """
    legacy_server_id: str = Field(min_length=1)
    legacy_tool_name: str = Field(min_length=1)
    capability_id: CapabilityTypeEnum = Field(description="Target canonical capability")
    canonical_owner: str = Field(min_length=1, description="Subsystem owning business logic")
    status: MCPCompatibilityStatus = Field(description="Compatibility level")
    is_security_blocked: bool = Field(default=False)
    block_reason: str = Field(default="")
    description: str = Field(default="")
    requires_project_context: bool = Field(default=True)
    notes: str = Field(default="")
