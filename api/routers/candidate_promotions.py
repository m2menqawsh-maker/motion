"""
api/routers/candidate_promotions.py
===================================
Transport-Only API Router for TemplateCandidate Promotion to Canonical Registry (S28-07E).

Architectural Invariants:
1. Transport Only: Router never sets CandidateStatus or directly mutates template files or registries.
2. Server-Authoritative Identity: Promoter identity is derived strictly from server-verified TenantContext,
   NEVER from client request body, query params, or headers. Client claims are not trusted claims.
3. Authority Confinement: Promotion operations delegate strictly to PromotionService.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ai.contracts.creative.template_candidate import CandidatePromotionRecord
from creative_governance.candidates.errors import (
    CandidateConflictError,
    CandidateNotFoundError,
    CandidatePermissionError,
    PromotionCollisionError,
    PromotionError,
    PromotionPreconditionError,
    PromotionRollbackError,
    PromotionSecurityError,
    PromotionTamperedError,
)
from creative_governance.candidates.promotion_service import (
    PromotionService,
    create_promotion_service,
)
from api.core.auth import require_tenant_context, Action, TenantContext

router = APIRouter()


def get_promotion_service() -> PromotionService:
    """Dependency provider for PromotionService."""
    return create_promotion_service()


class PromoteCandidateRequest(BaseModel):
    target_template_id: str = Field(
        min_length=3,
        max_length=64,
        description="Target canonical template ID (kebab-case, e.g. 'kinetic-quote-box')",
    )
    expected_revision: int = Field(ge=1, description="Expected candidate revision for CAS check")
    target_template_version: str = Field(default="1.0.0", description="Target semantic version")
    # Untrusted client claims: if provided, they are ignored in favor of server-verified identity
    promoter_id: Optional[str] = Field(default=None, description="UNTRUSTED: Ignored by server authority")
    role: Optional[str] = Field(default=None, description="UNTRUSTED: Ignored by server authority")


@router.post(
    "/{candidate_id}/promote",
    response_model=CandidatePromotionRecord,
    status_code=status.HTTP_200_OK,
    summary="Promote an APPROVED TemplateCandidate into the canonical template registry (S28-07E)",
)
async def promote_candidate(
    candidate_id: str,
    payload: PromoteCandidateRequest,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.TEMPLATE_PROMOTE)),
    promotion_service: PromotionService = Depends(get_promotion_service),
) -> CandidatePromotionRecord:
    try:
        # Note: promoter identity and permissions are strictly derived from tenant_context.principal
        # Client-provided promoter_id and role are completely ignored.
        return promotion_service.promote_candidate(
            tenant_context=tenant_context,
            candidate_id=candidate_id,
            target_template_id=payload.target_template_id,
            expected_revision=payload.expected_revision,
            target_template_version=payload.target_template_version,
        )
    except CandidateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (CandidatePermissionError, PromotionSecurityError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (CandidateConflictError, PromotionCollisionError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PromotionTamperedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except PromotionPreconditionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PromotionRollbackError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Promotion failed and was rolled back: {e}")
    except PromotionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{candidate_id}/promotion",
    response_model=CandidatePromotionRecord,
    status_code=status.HTTP_200_OK,
    summary="Get the promotion record for a specific candidate",
)
async def get_candidate_promotion(
    candidate_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    promotion_service: PromotionService = Depends(get_promotion_service),
) -> CandidatePromotionRecord:
    record = promotion_service.get_candidate_promotion(tenant_context, candidate_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No promotion record found for candidate '{candidate_id}'",
        )
    return record


@router.get(
    "/promotions/{promotion_id}",
    response_model=CandidatePromotionRecord,
    status_code=status.HTTP_200_OK,
    summary="Get a promotion record by promotion ID",
)
async def get_promotion_by_id(
    promotion_id: str,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    promotion_service: PromotionService = Depends(get_promotion_service),
) -> CandidatePromotionRecord:
    record = promotion_service.get_promotion_record(tenant_context, promotion_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion record '{promotion_id}' not found",
        )
    return record


@router.get(
    "/promotions",
    response_model=List[CandidatePromotionRecord],
    status_code=status.HTTP_200_OK,
    summary="List all promotion records for current workspace",
)
async def list_promotions(
    candidate_id: Optional[str] = None,
    tenant_context: TenantContext = Depends(require_tenant_context(Action.PROJECT_READ)),
    promotion_service: PromotionService = Depends(get_promotion_service),
) -> List[CandidatePromotionRecord]:
    return promotion_service.list_promotions(tenant_context, candidate_id=candidate_id)
