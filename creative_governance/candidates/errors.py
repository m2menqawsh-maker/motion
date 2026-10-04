"""
creative_governance/candidates/errors.py
=======================
Error types for the TemplateCandidate domain (S28-07A).

Invariants:
- All domain exceptions derive from CandidateError.
- Clear distinction between eligibility, authority, tenant, conflict, and lifecycle violations.
"""

from __future__ import annotations


class CandidateError(Exception):
    """Base exception for all TemplateCandidate operations."""
    pass


class CandidateEligibilityError(CandidateError):
    """Raised when candidate creation is requested without verified NEEDS_CREATE decision and evidence."""
    pass


class CandidateAuthorityError(CandidateError):
    """Raised when caller attempts unauthorized actions, such as setting status=APPROVED or PROMOTED."""
    pass


class CandidateNotFoundError(CandidateError):
    """Raised when a candidate does not exist within the caller's authorized tenant context."""
    pass


class CandidateConflictError(CandidateError):
    """Raised when an optimistic concurrency / CAS check fails due to concurrent modification."""
    pass


class CandidateInvalidStatusError(CandidateError):
    """Raised when attempting an operation invalid for the candidate's current lifecycle status."""
    pass


class CandidateTenantMismatchError(CandidateError):
    """Raised when candidate or project references a tenant/workspace outside caller's context."""
    pass


class CandidateReviewError(CandidateError):
    """Base exception for candidate review domain errors (S28-07D)."""
    pass


class CandidateReviewStaleError(CandidateReviewError):
    """Raised when an approval is attempted on stale validation evidence or drifted candidate."""
    pass


class CandidateReviewTamperedError(CandidateReviewError):
    """Raised when review bundle hash does not match recomputed server hash."""
    pass


class CandidatePermissionError(CandidateAuthorityError):
    """Raised when a principal lacks required review/approval permissions in the workspace."""
    pass


class PromotionError(CandidateError):
    """Base exception for candidate promotion domain errors (S28-07E)."""
    pass


class PromotionPreconditionError(PromotionError):
    """Raised when candidate does not satisfy strict promotion preconditions."""
    pass


class PromotionTamperedError(PromotionError):
    """Raised when cryptographic hashes or approval digests fail verification during promotion."""
    pass


class PromotionSecurityError(PromotionError):
    """Raised when invalid paths, path traversal, or unauthorized actors attempt promotion."""
    pass


class PromotionCollisionError(PromotionError):
    """Raised when target template ID or alias collides with an existing canonical template."""
    pass


class PromotionRollbackError(PromotionError):
    """Raised when post-publish verification fails and canonical publication is rolled back."""
    pass


