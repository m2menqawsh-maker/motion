"""
Artifacts & Reports Router (S22 - LED-064, LED-069).

Canonical endpoints for project artifact discovery, reports, and human review:
- GET  /projects/{project_id}/artifacts -> Inventory of governed artifacts
- GET  /projects/{project_id}/artifacts/{artifact_type} -> Canonical artifact reader
- GET  /projects/{project_id}/review -> Active review bundle and decision status
- POST /projects/{project_id}/review/approve -> Formal server-authoritative approval
- POST /projects/{project_id}/review/reject -> Formal server-authoritative rejection
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, Response, status, Body
from api.core.auth import require_permission, Principal, Action
from api.schemas.artifact import ArtifactItem, ArtifactInventoryResponse, ArtifactContentResponse
from api.services.domain_artifact_service import DomainArtifactService
from scripts.core.review_service import ReviewService
from scripts.core.state_model import ReviewDecisionType

router = APIRouter()


@router.get(
    "/{project_id}/artifacts",
    response_model=ArtifactInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List project artifacts and reports",
)
async def list_artifacts(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    items = DomainArtifactService.get_inventory(project_id)
    dto_list = [ArtifactItem(**item) for item in items]
    return ArtifactInventoryResponse(project_id=project_id, artifacts=dto_list, total=len(dto_list))


@router.get(
    "/{project_id}/artifacts/{artifact_type}",
    response_model=ArtifactContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a canonical project artifact or report",
)
async def get_artifact(
    project_id: str,
    artifact_type: str,
    response: Response,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    content, filename, revision, sha = DomainArtifactService.read_artifact(project_id, artifact_type)
    response.headers["ETag"] = f'"{revision}"'
    if sha:
        response.headers["X-Checksum-SHA256"] = sha

    return ArtifactContentResponse(
        project_id=project_id,
        kind=artifact_type,
        filename=filename,
        content=content,
        revision=revision,
        sha256=sha,
    )


@router.get(
    "/{project_id}/review",
    status_code=status.HTTP_200_OK,
    summary="Get canonical review bundle and decision status",
)
async def get_review(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    review_status_dto = ReviewService.get_review_status(project_id)
    active_bundle = ReviewService.get_active_bundle(project_id)
    return {
        "status": review_status_dto.model_dump(),
        "active_bundle": active_bundle.model_dump() if active_bundle else None,
    }


@router.post(
    "/{project_id}/review/approve",
    status_code=status.HTTP_200_OK,
    summary="Record server-authoritative review approval",
)
async def approve_review(
    project_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    principal: Principal = Depends(require_permission(Action.REVIEW_APPROVE)),
):
    bundle_id = payload.get("bundle_id")
    if not bundle_id:
        active = ReviewService.get_active_bundle(project_id)
        if not active:
            return Response(
                content='{"error": "No active review bundle found to approve"}',
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json",
            )
        bundle_id = active.review_bundle_id

    reason = payload.get("reason", "Approved via GUI")
    decision = ReviewService.approve(
        project_dir=f"projects/{project_id}",
        bundle_id=bundle_id,
        principal=principal,
        reason=reason,
    )
    return {"status": "success", "decision": decision.model_dump()}


@router.post(
    "/{project_id}/review/reject",
    status_code=status.HTTP_200_OK,
    summary="Record server-authoritative review rejection",
)
async def reject_review(
    project_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    principal: Principal = Depends(require_permission(Action.REVIEW_REJECT)),
):
    bundle_id = payload.get("bundle_id")
    if not bundle_id:
        active = ReviewService.get_active_bundle(project_id)
        if not active:
            return Response(
                content='{"error": "No active review bundle found to reject"}',
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json",
            )
        bundle_id = active.review_bundle_id

    reason = payload.get("reason", payload.get("note", "Rejected via GUI"))
    decision = ReviewService.reject(
        project_dir=f"projects/{project_id}",
        bundle_id=bundle_id,
        principal=principal,
        reason=reason,
    )
    return {"status": "success", "decision": decision.model_dump()}
