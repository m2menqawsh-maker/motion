"""
ai/orchestration/retry.py
==========================
Typed retry policy and bounded retry scheduling (S27.11).

Invariants:
- Unbounded retry is strictly forbidden (max_attempts hard cap).
- Distinct categorization of retryable vs non-retryable AI error codes.
- Deterministic exponential backoff with configurable base and factor.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import Field
from ai.contracts.base import AIContractModel
from ai.contracts.errors import AIError, AIErrorCode


DEFAULT_RETRYABLE_CODES: list[AIErrorCode] = [
    AIErrorCode.RATE_LIMITED,
    AIErrorCode.TIMEOUT,
    AIErrorCode.PROVIDER_UNAVAILABLE,
    AIErrorCode.INTERNAL_ERROR,
]

DEFAULT_NON_RETRYABLE_CODES: list[AIErrorCode] = [
    AIErrorCode.POLICY_DENIED,
    AIErrorCode.TENANT_ACCESS_DENIED,
    AIErrorCode.SCHEMA_VALIDATION_FAILED,
    AIErrorCode.CONTENT_REJECTED,
    AIErrorCode.INVALID_MODEL_OUTPUT,
    AIErrorCode.BUDGET_EXCEEDED,
    AIErrorCode.DEPENDENCY_FAILED,
    AIErrorCode.CANCELLED,
    AIErrorCode.CAPABILITY_UNAVAILABLE,
]


class RetryPolicy(AIContractModel):
    """Configuration for bounded retry backoff on recoverable step failures."""
    max_attempts: int = Field(default=3, ge=1, description="Hard ceiling on retry attempts")
    backoff_base_seconds: float = Field(default=1.0, ge=0.0, description="Initial delay in seconds")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Multiplier per retry attempt")
    retryable_error_codes: list[AIErrorCode] = Field(
        default_factory=lambda: list(DEFAULT_RETRYABLE_CODES),
        description="Error codes eligible for retry",
    )
    non_retryable_error_codes: list[AIErrorCode] = Field(
        default_factory=lambda: list(DEFAULT_NON_RETRYABLE_CODES),
        description="Error codes that fail terminally immediately",
    )

    def should_retry(self, attempt: int, error: Optional[AIError]) -> bool:
        """
        Determines whether another execution attempt should be scheduled.
        Guaranteed to return False if attempt >= max_attempts.
        """
        if attempt >= self.max_attempts:
            return False

        if not error:
            return False

        if error.code in self.non_retryable_error_codes:
            return False

        if error.code in self.retryable_error_codes or error.retryable:
            return True

        return False

    def compute_next_retry_at(
        self,
        attempt: int,
        base_time: Optional[datetime] = None,
    ) -> datetime:
        """Computes the timestamp for the next retry using exponential backoff."""
        reference = base_time or datetime.now(timezone.utc)
        # attempt count is 1-indexed (e.g., attempt 1 failed -> delay = base * factor^0)
        exponent = max(0, attempt - 1)
        delay_seconds = self.backoff_base_seconds * (self.backoff_factor ** exponent)
        return reference + timedelta(seconds=delay_seconds)
