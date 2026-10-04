"""
ai/routing/capability_router.py
===============================
Authoritative CapabilityRouter for S28-M03.

The official, single-entry-point routing engine for product capabilities.
Decouples AI callers from underlying execution topology, providers, and legacy tool details.

Architecture:
Caller
  ↓
CapabilityRequest
  ↓
CapabilityRouter
  ├── MODEL ──────────→ ModelRouter Seam (S28-M04 STT boundary preserved)
  ├── TOOL ───────────→ ToolGateway → authorized adapter (MCP / Native / Remote)
  └── DOMAIN_SERVICE ─→ ToolGateway → DomainServiceAdapter → Canonical Domain Owners
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Optional

from ai.capabilities.catalog import CapabilityCatalog, get_capability_catalog
from ai.contracts import (
    AIError,
    AIErrorCode,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
    ProvenanceRecord,
    UsageRecord,
)
from ai.contracts.media_ops import SpeechToTextInput
from ai.routing.router import ModelRouter
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext

logger = logging.getLogger("clean_video.ai.routing.capability_router")


class ModelRouterSeam:
    """
    Integration seam connecting CapabilityRouter to the Model Subsystem.
    In S28-M04: Delegates directly to authoritative ModelRouter.execute_model_capability.
    """

    def __init__(self, model_router: Optional[ModelRouter] = None) -> None:
        self.model_router = model_router or ModelRouter()

    async def execute_model_capability(
        self,
        request: CapabilityRequest,
        cap_def: CapabilityDefinition,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> CapabilityResult:
        res = await self.model_router.execute_model_capability(request, cap_def, context)
        if res.execution_metadata is not None:
            res.execution_metadata["seam"] = "ModelRouterSeam"
        return res


class CapabilityRouter:
    """
    Authoritative Router and entry point for all Capability invocations.
    Translates abstract, provider-neutral CapabilityRequests into concrete executions
    via ModelRouter (for MODEL category) or ToolGateway (for TOOL and DOMAIN_SERVICE categories).
    """

    def __init__(
        self,
        catalog: Optional[CapabilityCatalog] = None,
        tool_gateway: Optional[ToolGateway] = None,
        model_seam: Optional[ModelRouterSeam] = None,
        model_router: Optional[ModelRouter] = None,
    ) -> None:
        self.catalog = catalog or get_capability_catalog()
        self.tool_gateway = tool_gateway or ToolGateway(catalog=self.catalog)
        self.model_router = model_router or ModelRouter()
        self.model_seam = model_seam or ModelRouterSeam(self.model_router)

    async def route_and_execute(
        self,
        request: CapabilityRequest,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> CapabilityResult:
        """
        Routes the capability request to the appropriate subsystem branch based on its canonical category.
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)

        # 1. Resolve CapabilityDefinition from authoritative catalog
        cap_def = self.catalog.get(request.capability_id)
        if not cap_def:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"error_code": "CAPABILITY_NOT_FOUND"},
                implementation_id="unresolved",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.CAPABILITY_UNAVAILABLE,
                    message=f"Unknown capability '{cap_val}'. Must be one of the 32 canonical capabilities.",
                    retryable=False,
                    details={"requested_capability": cap_val},
                ),
            )

        cat_val = cap_def.category.value if hasattr(cap_def.category, "value") else str(cap_def.category)

        # 2. Route by CapabilityCategory
        if cat_val == CapabilityCategory.MODEL.value:
            # Route to MODEL subsystem via ModelRouter
            res = await self.model_router.execute_model_capability(request, cap_def, context)
            if res.execution_metadata is not None:
                res.execution_metadata["router_branch"] = "MODEL"
                res.execution_metadata["seam"] = "ModelRouterSeam"
            return res
        elif cat_val in (CapabilityCategory.TOOL.value, CapabilityCategory.DOMAIN_SERVICE.value):
            # Route to ToolGateway
            res = await self.tool_gateway.execute(request, context)
            if res.execution_metadata is not None:
                res.execution_metadata["router_branch"] = cat_val
            return res
        else:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"category": cat_val},
                implementation_id="unsupported_category",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.CAPABILITY_UNAVAILABLE,
                    message=f"Category '{cat_val}' has no registered router handler.",
                    retryable=False,
                ),
            )


_default_capability_router: Optional[CapabilityRouter] = None


def get_capability_router() -> CapabilityRouter:
    """Returns the singleton canonical CapabilityRouter."""
    global _default_capability_router
    if _default_capability_router is None:
        _default_capability_router = CapabilityRouter()
    return _default_capability_router
