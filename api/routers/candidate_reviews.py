"""
api/routers/candidate_reviews.py
================================
Transport-Only API Router for TemplateCandidate Human Review & Approval (S28-07D).

Architectural Invariants:
1. Transport Only: Router never assigns candidate lifecycle status or writes decision records directly.
2. Server-Authoritative Identity: Reviewer identity is derived strictly from server-verified TenantContext,
   NEVER from client request body, query params, or headers. Client claims are not trusted claims.
3. Authority Confinement: Review operations delegate strictly to CandidateReviewService.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ai.contracts.creative.template_candidate import (
    CandidateReviewBundle,
    CandidateReviewDecision,
)
from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
    CandidatePermissionError,
    CandidateReviewError,
    CandidateReviewStaleError,
    CandidateReviewTamperedError,
    CandidateTenantMismatchError,
)
from creative_governance.candidates.review_service import CandidateReviewService
from api.core.auth import require_tenant_context, Action, Principal
from scripts.core.tenant_model import TenantContext

router = APIRouter()


def get_candidate_review_service() -> CandidateReviewService:
    """Dependency provider for CandidateReviewService."""
    from scripts.core.database import get_database_engine
    from scripts.core.template_candidate_repository import SqlTemplateCandidateRepository
    from scripts.core.storage import get_storage_service
    repo = SqlTemplateCandidateRepository(get_database_engine())
    storage = get_storage_service()
    return CandidateReviewService(repository=repo, storage_service=storage)


# Request schemas
class OpenReviewRequest(BaseModel):
    expected_revision: int = Field(ge=1, description="Expected candidate revision for CAS check")


class ApproveReviewRequest(BaseModel):
    expected_revision: int = Field(ge=1, description="Expected candidate revision for CAS check")
    reason: Optional[str] = Field(default=None, description="Optional reviewer explanation")
    # Untrusted client claims: if provided, they are ignored in favor of server-verified identity
    reviewer_id: Optional[str] = Field(default=None, description="UNTRUSTED: Ignored by server authority")
    approved_by: Optional[str] = Field(default=None, description="UNTRUSTED: Ignored by server authority")


class RejectReviewRequest(BaseModel):
    expected_revision: int = Field(ge=1, description="Expected candidate revision for CAS check")
    reason: str = Field(min_length=1, description="Mandatory audit explanation for rejection")
    # Untrusted client claims: if provided, they are ignored in favor of server-verified identity
    reviewer_id: Optional[str] = Field(default=None, description="UNTRUSTED: Ignored by server authority")


@router.post(
    "/{candidate_id}/reviews/open",
    response_model=CandidateReviewBundle,
    status_code=status.HTTP_201_CREATED,
    summary="Freeze candidate validation evidence into a ReviewBundle and transition to AWAITING_APPROVAL",
)
async def open_review(
    candidate_id: str,
    payload: OpenReviewRequest,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.REVIEW_APPROVE)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewBundle:
    try:
        return review_service.open_review(
            tenant_context=tenant_context,
            candidate_id=candidate_id,
            expected_revision=payload.expected_revision,
        )
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CandidatePermissionError, CandidateAuthorityError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (CandidateConflictError, CandidateReviewStaleError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (CandidateInvalidStatusError, CandidateEligibilityError, CandidateReviewTamperedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{candidate_id}/reviews/bundle/active",
    response_model=CandidateReviewBundle,
    status_code=status.HTTP_200_OK,
    summary="Get active ReviewBundle for a candidate",
)
async def get_active_review_bundle(
    candidate_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewBundle:
    bundle = review_service.get_active_review_bundle_for_candidate(tenant_context, candidate_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active review bundle found for candidate '{candidate_id}'",
        )
    return bundle


@router.get(
    "/{candidate_id}/reviews/{review_bundle_id}",
    response_model=CandidateReviewBundle,
    status_code=status.HTTP_200_OK,
    summary="Get a specific ReviewBundle by ID",
)
async def get_review_bundle(
    candidate_id: str,
    review_bundle_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewBundle:
    try:
        return review_service.get_review_bundle(tenant_context, review_bundle_id)
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CandidateReviewTamperedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post(
    "/{candidate_id}/reviews/{review_bundle_id}/approve",
    response_model=CandidateReviewDecision,
    status_code=status.HTTP_200_OK,
    summary="Record human reviewer APPROVAL for a candidate ReviewBundle",
)
async def approve_candidate(
    candidate_id: str,
    review_bundle_id: str,
    payload: ApproveReviewRequest,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.REVIEW_APPROVE)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewDecision:
    try:
        # Note: reviewer identity is derived strictly from tenant_context.principal,
        # completely ignoring any client-provided reviewer_id or approved_by in payload.
        return review_service.approve(
            tenant_context=tenant_context,
            candidate_id=candidate_id,
            review_bundle_id=review_bundle_id,
            expected_revision=payload.expected_revision,
            reason=payload.reason,
        )
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CandidatePermissionError, CandidateAuthorityError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (CandidateConflictError, CandidateReviewStaleError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (CandidateInvalidStatusError, CandidateEligibilityError, CandidateReviewTamperedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{candidate_id}/reviews/{review_bundle_id}/reject",
    response_model=CandidateReviewDecision,
    status_code=status.HTTP_200_OK,
    summary="Record human reviewer REJECTION for a candidate ReviewBundle",
)
async def reject_candidate(
    candidate_id: str,
    review_bundle_id: str,
    payload: RejectReviewRequest,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.REVIEW_REJECT)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewDecision:
    try:
        return review_service.reject(
            tenant_context=tenant_context,
            candidate_id=candidate_id,
            review_bundle_id=review_bundle_id,
            expected_revision=payload.expected_revision,
            reason=payload.reason,
        )
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CandidatePermissionError, CandidateAuthorityError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (CandidateConflictError, CandidateReviewStaleError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (CandidateInvalidStatusError, CandidateEligibilityError, CandidateReviewTamperedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{candidate_id}/decisions",
    response_model=List[CandidateReviewDecision],
    status_code=status.HTTP_200_OK,
    summary="List all review decisions recorded for a candidate",
)
async def list_decisions(
    candidate_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> List[CandidateReviewDecision]:
    return review_service.list_decisions(tenant_context, candidate_id)


@router.get(
    "/{candidate_id}/decisions/{decision_id}",
    response_model=CandidateReviewDecision,
    status_code=status.HTTP_200_OK,
    summary="Get a specific review decision by ID",
)
async def get_decision(
    candidate_id: str,
    decision_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    review_service: CandidateReviewService = Depends(get_candidate_review_service),
) -> CandidateReviewDecision:
    try:
        return review_service.get_decision(tenant_context, decision_id)
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
