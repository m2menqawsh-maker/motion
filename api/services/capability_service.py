"""
api/services/capability_service.py — Production Capability Routing and Execution Service.
S28 / REALITY-015: Connects genuine API user flows to CapabilityRouter and ToolGateway.

Guarantees:
- Derives authorization and isolation strictly from server-verified TenantContext.
- Enforces capability allowlists to prevent unauthorized or administrative operations.
- Enforces project-scoped permissions: mutating capabilities require edit privileges;
  viewers are denied mutation.
- Translates TenantContext into TrustedToolExecutionContext with deadlines and cancel events.
- Never allows AI capabilities to automatically apply proposals, approve (.studio_approved),
  or trigger render runs (preserves human decision authority).
- Operates deterministically offline in CI without paid provider calls or credentials.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from api.core.errors import APIError, ProjectNotFoundError
from api.schemas.capability import (
    CapabilityDescriptorResponse,
    CapabilityErrorDetail,
    ExecuteCapabilityRequest,
    ExecuteCapabilityResponse,
)
from api.services.project_service import ProjectService
from ai.capabilities.catalog import CapabilityCatalog, get_capability_catalog
from ai.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.routing.capability_router import CapabilityRouter, get_capability_router
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.database import TenantSecurityError
from scripts.core.security.permissions import (
    ROLE_PERMISSIONS_MATRIX,
    AccessDeniedError,
    Action,
    Role,
)
from scripts.core.tenant_model import TenantContext
from scripts.security.path_security import validate_project_id

logger = logging.getLogger("clean_video.api.capability_service")

# Permitted capabilities for interactive API caller execution
ALLOWED_CAPABILITIES = {
    CapabilityType.GENERATE_SPEECH_MANIFEST.value,
    CapabilityType.BUILD_SPEECH_TIMELINE.value,
    CapabilityType.CHECK_MEDIA_CACHE.value,
    CapabilityType.STORE_MEDIA_CACHE.value,
    CapabilityType.MUTATE_ASSET_STATUS.value,
    CapabilityType.GET_JOB_STATUS.value,
    CapabilityType.CANCEL_PROCESSING_JOB.value,
    CapabilityType.TRIM_VIDEO.value,
    CapabilityType.RESIZE_VIDEO.value,
    CapabilityType.EXTEND_VIDEO.value,
    CapabilityType.TRIM_AUDIO.value,
    CapabilityType.NORMALIZE_AUDIO_LOUDNESS.value,
    CapabilityType.RESIZE_IMAGE.value,
    CapabilityType.CROP_IMAGE_TO_RATIO.value,
    CapabilityType.PROBE_IMAGE.value,
    CapabilityType.INSPECT_MEDIA.value,
    CapabilityType.SPLIT_SPEECH_TEXT.value,
    CapabilityType.SPEECH_TO_TEXT.value,
}

# Capabilities that perform state mutation or file writing and require edit permissions
MUTATING_CAPABILITIES = {
    CapabilityType.MUTATE_ASSET_STATUS.value,
    CapabilityType.STORE_MEDIA_CACHE.value,
    CapabilityType.CANCEL_PROCESSING_JOB.value,
    CapabilityType.TRIM_VIDEO.value,
    CapabilityType.RESIZE_VIDEO.value,
    CapabilityType.EXTEND_VIDEO.value,
    CapabilityType.TRIM_AUDIO.value,
    CapabilityType.NORMALIZE_AUDIO_LOUDNESS.value,
    CapabilityType.RESIZE_IMAGE.value,
    CapabilityType.CROP_IMAGE_TO_RATIO.value,
}


class CapabilityService:
    """Production domain service governing capability routing and execution."""

    @classmethod
    def list_capabilities(
        cls,
        project_id: str,
        tenant_context: TenantContext,
    ) -> List[CapabilityDescriptorResponse]:
        """
        Lists available capabilities from the canonical catalog with allowlist metadata.
        """
        validate_project_id(project_id)
        catalog: CapabilityCatalog = get_capability_catalog()
        descriptors: List[CapabilityDescriptorResponse] = []

        for cap_def in catalog.list_all():
            cid = cap_def.capability_id.value if hasattr(cap_def.capability_id, "value") else str(cap_def.capability_id)
            descriptors.append(
                CapabilityDescriptorResponse(
                    capability_id=cid,
                    category=cap_def.category.value if hasattr(cap_def.category, "value") else str(cap_def.category),
                    family=cap_def.family.value if hasattr(cap_def.family, "value") else str(cap_def.family),
                    description=cap_def.description or "",
                    cost_class=cap_def.cost_class.value if hasattr(cap_def.cost_class, "value") else str(cap_def.cost_class),
                    latency_class=cap_def.latency_class.value if hasattr(cap_def.latency_class, "value") else str(cap_def.latency_class),
                    is_allowlisted=(cid in ALLOWED_CAPABILITIES),
                )
            )

        return descriptors

    @classmethod
    async def execute_capability(
        cls,
        project_id: str,
        tenant_context: TenantContext,
        req: ExecuteCapabilityRequest,
    ) -> ExecuteCapabilityResponse:
        """
        Policy-enforced boundary executing a domain or tool capability via CapabilityRouter.
        """
        validate_project_id(project_id)
        ws_id = tenant_context.workspace_id
        cap_id = req.capability_id.strip()

        # 1. Capability Allowlist Enforcement
        if cap_id not in ALLOWED_CAPABILITIES:
            logger.warning(
                "Attempted execution of non-allowlisted capability '%s' on project '%s' by workspace '%s'.",
                cap_id,
                project_id,
                ws_id,
            )
            raise APIError(
                message=f"Capability '{cap_id}' is not permitted for client execution.",
                status_code=403,
            )

        # 2. Strict Tenant & Project Boundary Verification
        is_accessible, reason = ProjectService.is_project_accessible_by_tenant(
            project_id=project_id,
            workspace_id=ws_id,
            is_admin=tenant_context.principal.is_admin if tenant_context.principal else False,
            actor_id=tenant_context.principal.principal_id if tenant_context.principal else None,
        )
        if not is_accessible:
            raise TenantSecurityError(
                reason or f"Project '{project_id}' is not accessible by workspace '{ws_id}'."
            )

        # 3. Project-scoped Role Permissions Gate
        # Mutating capabilities require editor or higher permissions
        if cap_id in MUTATING_CAPABILITIES:
            granted_actions = ROLE_PERMISSIONS_MATRIX.get(tenant_context.role, set())
            has_edit = (Action.AUTHORING_EDIT in granted_actions or Action.PROJECT_EDIT in granted_actions or Action.ASSET_UPLOAD in granted_actions)
            if not has_edit and not (tenant_context.principal and tenant_context.principal.is_admin):
                actor_id = tenant_context.principal.principal_id if tenant_context.principal else "unknown"
                raise AccessDeniedError(
                    principal_id=actor_id,
                    action=Action.AUTHORING_EDIT,
                    project_id=project_id,
                    reason=f"Principal '{actor_id}' with role '{tenant_context.role.value}' lacks required edit permission for capability '{cap_id}'.",
                )

        # 4. Construct TrustedToolExecutionContext
        actor_id = tenant_context.principal.principal_id if tenant_context.principal else "system"
        roles_list = [
            r.value if hasattr(r, "value") else str(r)
            for r in (tenant_context.principal.roles if tenant_context.principal else [])
        ]
        permissions_list = [
            a.value if hasattr(a, "value") else str(a)
            for a in ROLE_PERMISSIONS_MATRIX.get(tenant_context.role, set())
        ]
        timeout = min(max(1.0, req.requested_timeout or 30.0), 300.0)

        trusted_tool_context = TrustedToolExecutionContext(
            workspace_id=ws_id,
            actor_id=actor_id,
            roles=roles_list,
            permissions=permissions_list,
            is_admin=tenant_context.principal.is_admin if tenant_context.principal else False,
            accessible_projects=[project_id],
        ).with_timeout(timeout)

        # 5. Build CapabilityRequest
        input_payload = dict(req.input)
        # Authoritative confinement: project_id in input payload must match verified project_id
        input_payload["project_id"] = project_id

        try:
            cap_type = CapabilityType(cap_id)
        except ValueError:
            raise APIError(message=f"Unknown capability type '{cap_id}'.", status_code=400)

        cap_request = CapabilityRequest(
            capability_id=cap_type,
            workspace_id=ws_id,
            project_id=project_id,
            actor_id=actor_id,
            input=input_payload,
            idempotency_key=req.idempotency_key,
            requested_timeout=timeout,
            metadata=req.metadata,
        )

        # 6. Execute via authoritative CapabilityRouter
        router = get_capability_router()
        result: CapabilityResult = await router.route_and_execute(
            cap_request,
            context=trusted_tool_context,
        )

        # 7. Map to typed response contract
        error_detail = None
        if result.error:
            error_detail = CapabilityErrorDetail(
                code=result.error.code.value if hasattr(result.error.code, "value") else str(result.error.code),
                message=result.error.message,
                retryable=result.error.retryable,
                details=result.error.details or {},
            )

        status_str = result.status.value if hasattr(result.status, "value") else str(result.status)

        return ExecuteCapabilityResponse(
            request_id=result.request_id,
            capability_id=cap_id,
            status=status_str,
            output=result.output,
            duration_ms=result.duration_ms,
            error=error_detail,
            execution_metadata=result.execution_metadata or {},
        )
