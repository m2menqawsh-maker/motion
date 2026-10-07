"""
api/routers/authoring.py — Production Authoring API Router.
S28-R14: Exposes Unified Authoring Operations (AI + Human + Templates) over HTTP.

Guarantees:
- Derives actor identity and tenant boundary strictly from server-verified TenantContext.
- Validates ETag and If-Match headers for optimistic concurrency control.
- Enforces durable idempotency via Idempotency-Key header or request payload.
- Zero raw filesystem or business logic inside router handlers.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Depends, Header, Request, Response, status

from api.core.auth import require_permission, require_tenant_context, Principal, Action
from api.core.errors import APIError, RevisionConflictError
from api.services.authoring_service import AuthoringService
from scripts.core.tenant_model import TenantContext

router = APIRouter()


@router.get("/{project_id}/document", summary="Get canonical video document")
async def get_canonical_document(
    project_id: str,
    response: Response,
    revision: Optional[int] = None,
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_READ)),
):
    """Retrieves authoritative Canonical VideoDocument (BlueprintV2) with current revision ETag."""
    doc, rev = AuthoringService.get_canonical_document(
        project_id=project_id,
        tenant_context=tenant_ctx,
        revision=revision,
    )
    response.headers["ETag"] = f'"{rev}"'
    return {
        "status": "success",
        "revision": rev,
        "blueprint": doc,
    }


@router.post("/{project_id}/mutate", summary="Apply human or AI canonical mutation")
async def apply_mutation(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Applies a typed canonical mutation with optimistic revision check and durable idempotency."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="execute_request",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result


@router.post("/{project_id}/batch", summary="Apply atomic mutation batch")
async def apply_batch(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Applies an atomic batch of canonical mutations as a single transaction."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="batch",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result


@router.post("/{project_id}/intent", summary="Apply typed AI authoring intent")
async def apply_intent(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Translates high-level declarative AI intent into typed canonical mutations and commits."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="apply_intent",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result


@router.post("/{project_id}/template", summary="Instantiate template into canonical document")
async def instantiate_template(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Instantiates a TemplateSpec into the canonical document."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="instantiate_template",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result


@router.post("/{project_id}/undo", summary="Undo last canonical mutation")
async def undo(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(default_factory=dict),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Undoes the previous mutation via bijective inverse."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="undo",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result


@router.post("/{project_id}/redo", summary="Redo previously undone canonical mutation")
async def redo(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(default_factory=dict),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant_ctx: TenantContext = Depends(require_tenant_context(Action.AUTHORING_EDIT)),
):
    """Redoes the previously undone mutation."""
    if if_match and "base_revision" not in payload:
        clean = if_match.strip().strip('"').strip("'")
        if clean.isdigit():
            payload["base_revision"] = int(clean)

    if idempotency_key and "operation_id" not in payload:
        payload["operation_id"] = idempotency_key

    actor_id = tenant_ctx.user_id
    result = AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="redo",
        payload=payload,
        actor_id=actor_id,
    )
    response.headers["ETag"] = f'"{result.get("result_revision")}"'
    return result
