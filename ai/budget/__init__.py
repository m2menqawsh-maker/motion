"""
ai/budget/__init__.py
=====================
Budget & Cost Engine (S27.5).

Authoritative subsystem managing financial spend constraints, atomic multi-scope reservations,
deterministic usage settlements, and immutable accounting ledgers.

Architectural Guarantees:
- Sole authority on financial spend (Model Router only estimates eligibility).
- Zero provider execution.
- Multi-scope atomic all-or-nothing check-and-reserve.
- Invariant under any concurrency: actual_spend + active_reservations <= budget_limit.
- All monetary operations backed by exact Decimal arithmetic.
"""

from ai.budget.types import (
    AccountingEventType,
    AccountingEventTypeEnum,
    AccountingRecord,
    Budget,
    BudgetExceededError,
    BudgetOverageError,
    BudgetScope,
    BudgetScopeEnum,
    CostProfile,
    CostProfileEnum,
    ExpirationResult,
    ReleaseResult,
    ReservationRecord,
    ReservationRequest,
    ReservationResult,
    ReservationStatus,
    ReservationStatusEnum,
    SettlementResult,
)
from ai.budget.policy import (
    BudgetPolicy,
    CostProfileConfig,
    get_cost_profile_config,
)
from ai.budget.estimator import BudgetEstimator
from ai.budget.repository import (
    BudgetRepository,
    InMemoryBudgetRepository,
)
from ai.budget.reservation import ReservationEngine
from ai.budget.accounting import AccountingEngine
from ai.budget.service import BudgetService

__all__ = [
    "AccountingEngine",
    "AccountingEventType",
    "AccountingEventTypeEnum",
    "AccountingRecord",
    "Budget",
    "BudgetEstimator",
    "BudgetExceededError",
    "BudgetOverageError",
    "BudgetPolicy",
    "BudgetRepository",
    "BudgetScope",
    "BudgetScopeEnum",
    "BudgetService",
    "CostProfile",
    "CostProfileConfig",
    "CostProfileEnum",
    "ExpirationResult",
    "InMemoryBudgetRepository",
    "ReleaseResult",
    "ReservationEngine",
    "ReservationRecord",
    "ReservationRequest",
    "ReservationResult",
    "ReservationStatus",
    "ReservationStatusEnum",
    "SettlementResult",
    "get_cost_profile_config",
]
