"""
api/routers/capabilities.py — API Router for Capability Execution and Discovery (S28-M03 / REALITY-015).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, status

from api.core.auth import Action, require_tenant_context
from api.schemas.capability import (
    CapabilityDescriptorResponse,
    ExecuteCapabilityRequest,
    ExecuteCapabilityResponse,
)
from api.services.capability_service import CapabilityService
from scripts.core.tenant_model import TenantContext

router = APIRouter()


@router.get(
    "/{project_id}/capabilities",
    response_model=List[CapabilityDescriptorResponse],
    summary="List available capabilities with allowlist status",
)
async def list_capabilities(
    project_id: str,
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
) -> List[CapabilityDescriptorResponse]:
    """
    Returns the canonical catalog of capabilities with metadata and client allowlist eligibility.
    """
    return CapabilityService.list_capabilities(project_id=project_id, tenant_context=tenant_ctx)


@router.post(
    "/{project_id}/capabilities/execute",
    response_model=ExecuteCapabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute an authorized capability via CapabilityRouter and ToolGateway",
)
async def execute_capability(
    project_id: str,
    payload: ExecuteCapabilityRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
) -> ExecuteCapabilityResponse:
    """
    Policy-enforced execution entrypoint reaching CapabilityRouter and ToolGateway.
    Enforces tenant boundaries, role permissions, execution timeouts, and input/output contracts.
    """
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key

    return await CapabilityService.execute_capability(
        project_id=project_id,
        tenant_context=tenant_ctx,
        req=payload,
    )
