"""
ai/mcp/compatibility/facade.py
===============================
Authoritative Compatibility MCP Facade mediating external MCP client invocations
to canonical ToolGateway and Domain Services (S28-M09).

Invariants:
- NO duplicate business logic: 100% of domain rules live in canonical services.
- Strict TenantContext and authorization enforcement: fail-closed on cross-tenant or unpermitted calls.
- Insecure legacy tools (e.g. concatenate_videos) are fail-closed with structured errors.
- Never masks canonical failures (preserves structured AIError codes and machine-readable details).
- Zero host filesystem leakages; operates through canonical storage abstractions.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ai.routing.capability_router import CapabilityRouter
    from ai.tools.gateway import ToolGateway

from ai.contracts import (
    AIError,
    AIErrorCode,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
)
from ai.mcp.audit import MCPAuditRecord, default_mcp_audit_recorder
from ai.mcp.compatibility.contracts import (
    CompatibilityRequest,
    CompatibilityResponse,
    MCPCompatibilityStatus,
)
from ai.mcp.compatibility.registry import (
    CompatibilityRegistry,
    default_compatibility_registry,
)
from ai.tools.types import TrustedToolExecutionContext


class MCPCompatibilityFacade:
    """
    Authoritative façade mediating external MCP client calls to the ToolGateway pipeline.
    """

    def __init__(
        self,
        registry: Optional[CompatibilityRegistry] = None,
        tool_gateway: Optional[Any] = None,
        capability_router: Optional[Any] = None,
    ) -> None:
        self.registry = registry or default_compatibility_registry
        self._tool_gateway = tool_gateway
        self._capability_router = capability_router

    @property
    def tool_gateway(self) -> Any:
        if self._tool_gateway is None:
            from ai.tools.gateway import get_tool_gateway
            self._tool_gateway = get_tool_gateway()
        return self._tool_gateway

    @property
    def capability_router(self) -> Any:
        if self._capability_router is None:
            from ai.routing.capability_router import get_capability_router
            self._capability_router = get_capability_router()
        return self._capability_router

    async def execute(self, request: CompatibilityRequest) -> CompatibilityResponse:
        """
        Executes an inbound external MCP tool request through the canonical gateway.
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()
        tool_entry = self.registry.get_entry(request.server_id, request.tool_name)

        # 1. Tool Lookup in Compatibility Registry
        if not tool_entry:
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            err = AIError.create(
                code=AIErrorCode.CAPABILITY_UNAVAILABLE,
                message=f"Legacy MCP tool '{request.tool_name}' on server '{request.server_id}' is not recognized.",
                retryable=False,
                details={"server_id": request.server_id, "tool_name": request.tool_name},
            )
            return CompatibilityResponse(
                success=False,
                data=None,
                capability_id="UNKNOWN",
                canonical_owner="NONE",
                duration_ms=duration_ms,
                error=err,
            )

        descriptor = tool_entry.descriptor

        # 2. Blocked Insecure Tool Policy Check
        if descriptor.is_security_blocked or descriptor.status == MCPCompatibilityStatus.BLOCKED:
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            err = AIError.create(
                code=AIErrorCode.POLICY_DENIED,
                message=f"Legacy MCP tool '{descriptor.legacy_tool_name}' is permanently blocked for security: {descriptor.block_reason}",
                retryable=False,
                details={
                    "legacy_tool": descriptor.legacy_tool_name,
                    "server_id": descriptor.legacy_server_id,
                    "block_reason": descriptor.block_reason,
                },
            )
            return CompatibilityResponse(
                success=False,
                data=None,
                capability_id=descriptor.capability_id.value if hasattr(descriptor.capability_id, "value") else str(descriptor.capability_id),
                canonical_owner=descriptor.canonical_owner,
                duration_ms=duration_ms,
                error=err,
            )

        # 3. Construct Trusted Tool Execution Context
        context = TrustedToolExecutionContext(
            actor_id=request.actor_id,
            workspace_id=request.workspace_id,
            correlation_id=f"mcp_compat_{uuid.uuid4().hex[:12]}",
            roles=list(request.roles),
            permissions=list(request.permissions),
        )

        # 4. Bidirectional Argument Translation
        try:
            mapped_input = tool_entry.request_mapper(request.arguments, request.project_id)
        except Exception as e:
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            err = AIError.create(
                code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
                message=f"Failed to map legacy arguments for tool '{request.tool_name}': {e}",
                retryable=False,
                details={"arguments": request.arguments, "error": str(e)},
            )
            return CompatibilityResponse(
                success=False,
                data=None,
                capability_id=descriptor.capability_id.value if hasattr(descriptor.capability_id, "value") else str(descriptor.capability_id),
                canonical_owner=descriptor.canonical_owner,
                duration_ms=duration_ms,
                error=err,
            )

        # 5. Build Canonical CapabilityRequest
        cap_req = CapabilityRequest(
            capability_id=descriptor.capability_id,
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            actor_id=request.actor_id,
            input=mapped_input,
            idempotency_key=request.idempotency_key,
        )

        # 6. Dispatch through Canonical Gateway or Model Seam
        cap_def = self.tool_gateway.catalog.get(descriptor.capability_id)
        is_model = cap_def and cap_def.category == CapabilityCategory.MODEL

        try:
            if is_model:
                cap_res = await self.capability_router.dispatch(cap_req, context)
            else:
                cap_res = await self.tool_gateway.execute(cap_req, context)
        except Exception as e:
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            err = AIError.create(
                code=AIErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error executing capability '{descriptor.capability_id}': {e}",
                retryable=True,
                details={"exception": str(e)},
            )
            return CompatibilityResponse(
                success=False,
                data=None,
                capability_id=descriptor.capability_id.value if hasattr(descriptor.capability_id, "value") else str(descriptor.capability_id),
                canonical_owner=descriptor.canonical_owner,
                duration_ms=duration_ms,
                error=err,
            )

        duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))

        # 7. Evaluate Execution Outcome
        if cap_res.status == CapabilityStatus.FAILED:
            # Audit recording
            default_mcp_audit_recorder.record(
                MCPAuditRecord(
                    server_id=descriptor.legacy_server_id,
                    operation_name=descriptor.legacy_tool_name,
                    actor_id=request.actor_id,
                    workspace_id=request.workspace_id,
                    target_resource=request.project_id,
                    status="ERROR",
                    duration_ms=duration_ms,
                    timestamp=start_time,
                    error_code=cap_res.error.code.value if (cap_res.error and hasattr(cap_res.error.code, "value")) else "UNKNOWN",
                )
            )
            return CompatibilityResponse(
                success=False,
                data=None,
                capability_id=descriptor.capability_id.value if hasattr(descriptor.capability_id, "value") else str(descriptor.capability_id),
                canonical_owner=descriptor.canonical_owner,
                duration_ms=duration_ms,
                error=cap_res.error,
                canonical_output=cap_res.output,
            )

        # 8. Map Successful Canonical Output to Legacy Response
        try:
            legacy_data = tool_entry.response_mapper(cap_res)
        except Exception as e:
            legacy_data = cap_res.output

        default_mcp_audit_recorder.record(
            MCPAuditRecord(
                server_id=descriptor.legacy_server_id,
                operation_name=descriptor.legacy_tool_name,
                actor_id=request.actor_id,
                workspace_id=request.workspace_id,
                target_resource=request.project_id,
                status="SUCCESS",
                duration_ms=duration_ms,
                timestamp=start_time,
                error_code=None,
            )
        )

        return CompatibilityResponse(
            success=True,
            data=legacy_data,
            capability_id=descriptor.capability_id.value if hasattr(descriptor.capability_id, "value") else str(descriptor.capability_id),
            canonical_owner=descriptor.canonical_owner,
            duration_ms=duration_ms,
            error=None,
            canonical_output=cap_res.output,
        )


_default_facade: Optional[MCPCompatibilityFacade] = None

def get_mcp_compatibility_facade() -> MCPCompatibilityFacade:
    global _default_facade
    if _default_facade is None:
        _default_facade = MCPCompatibilityFacade()
    return _default_facade
