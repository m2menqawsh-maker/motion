"""
ai/budget/types.py
==================
Canonical data models, enums, and exceptions for the Budget & Cost Engine (S27.5).

Invariants:
- All monetary fields strictly use `StrictDecimal` (never binary float).
- Budgets enforce `available = limit - actual_spend - reserved` (derived, never stored independently).
- Scopes: GLOBAL, WORKSPACE, PROJECT, AIRUN (AI_RUN), CAPABILITY.
- Cost Profiles: ECONOMY, STANDARD, PREMIUM, MAXIMUM (quality/cost policy profiles, not vendor models).
- Immutable, append-oriented accounting records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import Field, JsonValue, field_validator, model_validator
from typing_extensions import Self

from ai.contracts.base import (
    AIContractModel,
    StrictDecimal,
    TzAwareDatetime,
    strict_enum,
)
from ai.contracts.errors import AIError, AIErrorCode


class BudgetScope(str, Enum):
    """Authoritative scopes for budget allocation and spending enforcement."""
    GLOBAL = "GLOBAL"
    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"
    AIRUN = "AIRUN"
    AI_RUN = "AIRUN"  # Normalized alias for AI_RUN
    CAPABILITY = "CAPABILITY"


class CostProfile(str, Enum):
    """
    Quality/cost policy tier profiles.
    Directs routing and spending constraints; never coupled to concrete vendor models.
    """
    ECONOMY = "ECONOMY"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    MAXIMUM = "MAXIMUM"


class ReservationStatus(str, Enum):
    """Lifecycle state of an active or finalized budget reservation."""
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class AccountingEventType(str, Enum):
    """Types of financial ledger events recorded for auditable tracking."""
    RESERVED = "RESERVED"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    ADJUSTED = "ADJUSTED"


BudgetScopeEnum = strict_enum(BudgetScope)
CostProfileEnum = strict_enum(CostProfile)
ReservationStatusEnum = strict_enum(ReservationStatus)
AccountingEventTypeEnum = strict_enum(AccountingEventType)


class Budget(AIContractModel):
    """
    Authoritative budget account definition for a specific scope.
    Strictly Decimal-backed to prevent floating-point drift.
    """
    budget_id: str = Field(min_length=1, description="Canonical budget account identifier")
    scope: BudgetScopeEnum = Field(description="Enforcement scope tier")
    scope_reference: str = Field(min_length=1, description="Scope target identifier (e.g. workspace_id, 'global')")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    limit: StrictDecimal = Field(ge=Decimal("0"), description="Total spend limit allocated to this budget")
    reserved: StrictDecimal = Field(default=Decimal("0"), ge=Decimal("0"), description="Currently active reservations")
    actual_spend: StrictDecimal = Field(default=Decimal("0"), ge=Decimal("0"), description="Accumulated settled spend")
    enabled: bool = Field(default=True, description="Whether this budget account accepts active operations")
    valid_from: TzAwareDatetime = Field(description="Timezone-aware activation datetime")
    valid_until: Optional[TzAwareDatetime] = Field(default=None, description="Optional timezone-aware expiry datetime")
    version: int = Field(default=1, ge=1, description="Optimistic concurrency and audit version counter")
    created_at: TzAwareDatetime = Field(description="Creation timestamp")
    updated_at: TzAwareDatetime = Field(description="Last update timestamp")

    @property
    def available(self) -> Decimal:
        """
        Derived spendable balance.
        Never persisted independently to prevent state divergence.
        """
        return self.limit - self.actual_spend - self.reserved

    @model_validator(mode="after")
    def validate_budget_invariants(self) -> Self:
        if self.limit < Decimal("0"):
            raise ValueError(f"Budget limit cannot be negative: {self.limit}")
        if self.reserved < Decimal("0"):
            raise ValueError(f"Reserved amount cannot be negative: {self.reserved}")
        if self.actual_spend < Decimal("0"):
            raise ValueError(f"Actual spend cannot be negative: {self.actual_spend}")
        if self.currency != "USD":
            raise ValueError(f"Only 'USD' currency is supported in S27.5, got '{self.currency}'")
        return self


class ReservationRecord(AIContractModel):
    """
    Durable, auditable record of an active or concluded budget reservation.
    """
    reservation_id: str = Field(min_length=1, description="Unique reservation identifier")
    workspace_id: str = Field(min_length=1, description="Tenant workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier")
    run_id: Optional[str] = Field(default=None, description="Associated AI Run identifier")
    capability: Optional[str] = Field(default=None, description="Associated capability name")
    budget_ids: List[str] = Field(min_length=1, description="List of budget account IDs locked by this reservation")
    estimated_amount: StrictDecimal = Field(gt=Decimal("0"), description="Estimated expected cost")
    reserved_amount: StrictDecimal = Field(gt=Decimal("0"), description="Exact amount reserved across budgets")
    settled_amount: Optional[StrictDecimal] = Field(default=None, ge=Decimal("0"), description="Final settled amount")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    status: ReservationStatusEnum = Field(default=ReservationStatus.ACTIVE, description="Current lifecycle status")
    created_at: TzAwareDatetime = Field(description="Creation timestamp")
    expires_at: Optional[TzAwareDatetime] = Field(default=None, description="Timezone-aware expiration timestamp")
    settled_at: Optional[TzAwareDatetime] = Field(default=None, description="Settlement timestamp")
    released_at: Optional[TzAwareDatetime] = Field(default=None, description="Release/cancellation timestamp")
    idempotency_key: str = Field(min_length=1, description="Caller-provided idempotency deduplication key")
    cost_profile: Optional[CostProfileEnum] = Field(default=None, description="Cost policy profile applied")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Operational metadata")


class AccountingRecord(AIContractModel):
    """
    Append-only immutable transaction entry recording any budget balance mutation.
    """
    entry_id: str = Field(min_length=1, description="Unique ledger entry identifier")
    timestamp: TzAwareDatetime = Field(description="Timezone-aware event timestamp")
    event_type: AccountingEventTypeEnum = Field(description="Ledger event type")
    reservation_id: str = Field(min_length=1, description="Associated reservation identifier")
    budget_id: str = Field(min_length=1, description="Target budget account identifier")
    scope: BudgetScopeEnum = Field(description="Scope tier of target budget")
    scope_reference: str = Field(min_length=1, description="Scope reference identifier")
    amount: StrictDecimal = Field(ge=Decimal("0"), description="Delta amount applied in this event")
    resulting_reserved: StrictDecimal = Field(ge=Decimal("0"), description="Budget reserved balance post-event")
    resulting_actual_spend: StrictDecimal = Field(ge=Decimal("0"), description="Budget actual_spend post-event")
    resulting_available: StrictDecimal = Field(description="Budget available balance post-event")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key from initiating request")
    run_id: Optional[str] = Field(default=None, description="Optional associated run identifier")
    actor_id: Optional[str] = Field(default=None, description="Actor initiating the mutation")
    notes: Optional[str] = Field(default=None, description="Diagnostic audit notes")


class ReservationRequest(AIContractModel):
    """
    Input parameters to request an atomic budget reservation across all applicable scopes.
    """
    workspace_id: str = Field(min_length=1, description="Tenant workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Optional project identifier")
    run_id: Optional[str] = Field(default=None, description="Optional AI Run identifier")
    capability: Optional[str] = Field(default=None, description="Optional capability name")
    amount: StrictDecimal = Field(gt=Decimal("0"), description="Monetary amount to reserve")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    idempotency_key: str = Field(min_length=1, description="Mandatory idempotency key")
    cost_profile: CostProfileEnum = Field(default=CostProfile.STANDARD, description="Cost policy profile")
    ttl_seconds: Optional[int] = Field(default=300, gt=0, le=86400, description="Reservation time-to-live in seconds")
    actor_id: Optional[str] = Field(default=None, description="Requesting actor identifier")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Contextual request metadata")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v != "USD":
            raise ValueError(f"Only 'USD' currency is supported in S27.5, got '{v}'")
        return v


class ReservationResult(AIContractModel):
    """
    Structured response from an atomic reservation attempt.
    """
    success: bool = Field(description="Whether the reservation succeeded")
    reservation: Optional[ReservationRecord] = Field(default=None, description="Created or deduplicated reservation")
    error: Optional[AIError] = Field(default=None, description="Canonical error if reservation failed")
    denial_scope: Optional[BudgetScopeEnum] = Field(default=None, description="Scope that rejected the reservation")
    available_amount: Optional[Decimal] = Field(default=None, description="Available balance at denial")
    required_amount: Optional[Decimal] = Field(default=None, description="Required amount at denial")


class SettlementResult(AIContractModel):
    """
    Structured response from settling a reservation with actual cost.
    """
    success: bool = Field(description="Whether settlement succeeded")
    reservation: Optional[ReservationRecord] = Field(default=None, description="Updated reservation record")
    actual_cost: Optional[Decimal] = Field(default=None, description="Final settled cost")
    released_cost: Optional[Decimal] = Field(default=None, description="Unused reserved cost released to budget")
    error: Optional[AIError] = Field(default=None, description="Canonical error if settlement failed")


class ReleaseResult(AIContractModel):
    """
    Structured response from releasing an active reservation.
    """
    success: bool = Field(description="Whether release succeeded")
    reservation: Optional[ReservationRecord] = Field(default=None, description="Updated reservation record")
    released_amount: Optional[Decimal] = Field(default=None, description="Amount released back to available budget")
    error: Optional[AIError] = Field(default=None, description="Canonical error if release failed")


class ExpirationResult(AIContractModel):
    """
    Structured response from sweeping expired stale reservations.
    """
    expired_count: int = Field(ge=0, description="Count of reservations transitioned to EXPIRED")
    released_amount: StrictDecimal = Field(ge=Decimal("0"), description="Total amount released back to budgets")
    expired_reservation_ids: List[str] = Field(default_factory=list, description="IDs of expired reservations")


class BudgetExceededError(Exception):
    """Raised when a budget limit is exceeded by a reservation or unbudgeted charge."""
    def __init__(self, error: AIError, scope: Optional[BudgetScope] = None):
        super().__init__(error.message)
        self.error = error
        self.scope = scope


class BudgetOverageError(Exception):
    """Raised when actual cost exceeds reservation in violation of strict overage policy."""
    def __init__(self, error: AIError):
        super().__init__(error.message)
        self.error = error
