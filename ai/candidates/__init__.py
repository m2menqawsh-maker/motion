"""
ai.candidates
=============
DEPRECATED_COMPATIBILITY_IMPORT: This package has migrated to `creative_governance.candidates`.
All symbols are re-exported for backward compatibility.
Do not add new implementations here.
"""

from __future__ import annotations

from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
    CandidatePermissionError,
    CandidateReviewError,
    CandidateReviewStaleError,
    CandidateReviewTamperedError,
    CandidateTenantMismatchError,
    PromotionCollisionError,
    PromotionError,
    PromotionPreconditionError,
    PromotionRollbackError,
    PromotionSecurityError,
    PromotionTamperedError,
)
from creative_governance.candidates.hashing import (
    compute_candidate_content_hash,
    compute_promotion_manifest_hash,
    compute_review_bundle_hash,
)
from creative_governance.candidates.promotion_service import PromotionService
from creative_governance.candidates.repository import (
    InMemoryTemplateCandidateRepository,
    TemplateCandidateRepository,
)
from creative_governance.candidates.gates import (
    AspectGate,
    CandidateQCGate,
    ContractGate,
    DependencyGate,
    ProbeGate,
    RenderSmokeGate,
    RuntimeContractGate,
    RuntimeGate,
    SecurityGate,
    StaticCodeGate,
    StaticGate,
    TemplateSchemaGate,
    TypeScriptGate,
)
from creative_governance.candidates.policies import (
    CANONICAL_ASPECT_RATIOS,
    CANDIDATE_RUNTIME_QC_PROFILE,
    RUNTIME_VALIDATION_POLICY_VERSION,
    VALIDATION_POLICY_VERSION,
    ValidationFailureCode,
)
from creative_governance.candidates.runtime_runner import (
    CandidateRenderResult,
    IsolatedCandidateRunner,
)
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.validation_service import CandidateValidationService
from creative_governance.candidates.review_service import CandidateReviewService


__all__ = [
    "AspectGate",
    "CANONICAL_ASPECT_RATIOS",
    "CANDIDATE_RUNTIME_QC_PROFILE",
    "CandidateAuthorityError",
    "CandidateConflictError",
    "CandidateEligibilityError",
    "CandidateError",
    "CandidateInvalidStatusError",
    "CandidateNotFoundError",
    "CandidatePermissionError",
    "CandidateQCGate",
    "CandidateRenderResult",
    "CandidateReviewError",
    "CandidateReviewService",
    "CandidateReviewStaleError",
    "CandidateReviewTamperedError",
    "CandidateTenantMismatchError",
    "CandidateValidationService",
    "ContractGate",
    "DependencyGate",
    "InMemoryTemplateCandidateRepository",
    "IsolatedCandidateRunner",
    "ProbeGate",
    "PromotionCollisionError",
    "PromotionError",
    "PromotionPreconditionError",
    "PromotionRollbackError",
    "PromotionSecurityError",
    "PromotionService",
    "PromotionTamperedError",
    "RUNTIME_VALIDATION_POLICY_VERSION",
    "RenderSmokeGate",
    "RuntimeContractGate",
    "RuntimeGate",
    "SecurityGate",
    "StaticCodeGate",
    "StaticGate",
    "TemplateCandidateRepository",
    "TemplateCandidateService",
    "TemplateSchemaGate",
    "TypeScriptGate",
    "VALIDATION_POLICY_VERSION",
    "ValidationFailureCode",
    "compute_candidate_content_hash",
    "compute_promotion_manifest_hash",
    "compute_review_bundle_hash",
]
