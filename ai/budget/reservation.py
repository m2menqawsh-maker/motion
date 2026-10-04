"""
ai/budget/reservation.py
========================
Atomic multi-scope reservation logic for Budget Engine (S27.5).

Invariants:
- All-or-nothing: if any scope lacks sufficient budget, the entire reservation is denied with BUDGET_EXCEEDED.
- Zero partial reservation: no scope balance is deducted if another scope fails.
- Strictly idempotent: duplicate requests with the same idempotency key return the canonical reservation.
- Thread-safe and atomic under high concurrency.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import uuid4

from ai.contracts.errors import AIError, AIErrorCode
from ai.budget.accounting import AccountingEngine
from ai.budget.policy import BudgetPolicy
from ai.budget.repository import BudgetRepository
from ai.budget.types import (
    AccountingEventType,
    Budget,
    BudgetExceededError,
    BudgetScope,
    ReservationRecord,
    ReservationRequest,
    ReservationResult,
    ReservationStatus,
)


class ReservationEngine:
    """
    Executes atomic reservation across multiple budget scopes.
    """

    def __init__(self, repository: BudgetRepository, policy: Optional[BudgetPolicy] = None):
        self.repository = repository
        self.policy = policy or BudgetPolicy()

    def resolve_applicable_scopes(self, request: ReservationRequest) -> List[Tuple[BudgetScope, str]]:
        """Identifies all hierarchical budget scopes that apply to the incoming request."""
        scopes: List[Tuple[BudgetScope, str]] = [
            (BudgetScope.GLOBAL, "global"),
            (BudgetScope.WORKSPACE, request.workspace_id),
        ]
        if request.project_id:
            scopes.append((BudgetScope.PROJECT, request.project_id))
        if request.run_id:
            scopes.append((BudgetScope.AIRUN, request.run_id))
        if request.capability:
            scopes.append((BudgetScope.CAPABILITY, request.capability))
        return scopes

    def reserve(self, request: ReservationRequest) -> ReservationResult:
        """
        Executes atomic check-and-reserve across all applicable scopes.
        Guarantees all-or-nothing semantics and idempotency deduplication.
        """
        now = datetime.now(timezone.utc)

        with self.repository.atomic_transaction():
            # 1. Idempotency Check
            existing = self.repository.get_reservation_by_idempotency_key(request.idempotency_key)
            if existing is not None:
                # If an active or settled reservation with this key exists, return it idempotently
                return ReservationResult(
                    success=True,
                    reservation=existing,
                )

            # 2. Scope Discovery
            scope_pairs = self.resolve_applicable_scopes(request)
            matching_budgets = self.repository.get_budgets_for_scopes(scope_pairs)

            # Ensure at least one budget covers this request (e.g. Workspace or Global)
            workspace_budgets = [
                b for b in matching_budgets
                if b.scope == BudgetScope.WORKSPACE and b.scope_reference == request.workspace_id
            ]
            global_budgets = [
                b for b in matching_budgets
                if b.scope == BudgetScope.GLOBAL
            ]

            if not workspace_budgets and not global_budgets:
                error = AIError(
                    code=AIErrorCode.BUDGET_EXCEEDED,
                    message=f"No budget account exists for workspace '{request.workspace_id}' or global scope",
                    retryable=False,
                    details={
                        "workspace_id": request.workspace_id,
                        "required_amount": str(request.amount),
                        "currency": request.currency,
                    },
                )
                return ReservationResult(
                    success=False,
                    error=error,
                    required_amount=request.amount,
                    available_amount=Decimal("0"),
                )

            # 3. Verification Phase: Check all budgets before mutating any
            for budget in matching_budgets:
                # 3a. Enabled check
                if not budget.enabled:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=f"Budget for scope '{budget.scope}' ({budget.scope_reference}) is disabled",
                        retryable=False,
                        details={
                            "scope": str(budget.scope),
                            "scope_reference": budget.scope_reference,
                            "budget_id": budget.budget_id,
                        },
                    )
                    return ReservationResult(
                        success=False,
                        error=error,
                        denial_scope=budget.scope,
                        available_amount=Decimal("0"),
                        required_amount=request.amount,
                    )

                # 3b. Validity period check
                if budget.valid_from > now:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=f"Budget for scope '{budget.scope}' is not yet active (valid_from: {budget.valid_from.isoformat()})",
                        retryable=False,
                        details={"scope": str(budget.scope), "valid_from": budget.valid_from.isoformat()},
                    )
                    return ReservationResult(
                        success=False,
                        error=error,
                        denial_scope=budget.scope,
                        available_amount=Decimal("0"),
                        required_amount=request.amount,
                    )

                if budget.valid_until is not None and budget.valid_until < now:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=f"Budget for scope '{budget.scope}' has expired (valid_until: {budget.valid_until.isoformat()})",
                        retryable=False,
                        details={"scope": str(budget.scope), "valid_until": budget.valid_until.isoformat()},
                    )
                    return ReservationResult(
                        success=False,
                        error=error,
                        denial_scope=budget.scope,
                        available_amount=Decimal("0"),
                        required_amount=request.amount,
                    )

                # 3c. Currency match
                if budget.currency != request.currency:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=f"Currency mismatch: request requires '{request.currency}', budget uses '{budget.currency}'",
                        retryable=False,
                        details={"request_currency": request.currency, "budget_currency": budget.currency},
                    )
                    return ReservationResult(
                        success=False,
                        error=error,
                        denial_scope=budget.scope,
                    )

                # 3d. Availability check: available = limit - actual_spend - reserved
                available = budget.available
                if available < request.amount:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=(
                            f"Budget exceeded for scope '{budget.scope}' ({budget.scope_reference}). "
                            f"Required: {request.amount} {request.currency}, Available: {available} {budget.currency}"
                        ),
                        retryable=False,
                        details={
                            "scope": str(budget.scope),
                            "scope_reference": budget.scope_reference,
                            "required_amount": str(request.amount),
                            "available_amount": str(available),
                            "limit": str(budget.limit),
                            "currency": budget.currency,
                        },
                    )
                    return ReservationResult(
                        success=False,
                        error=error,
                        denial_scope=budget.scope,
                        available_amount=available,
                        required_amount=request.amount,
                    )

            # 4. Mutation Phase: All scopes passed verification -> atomically update balances
            reservation_id = f"res_{uuid4().hex[:16]}"
            locked_budget_ids: List[str] = []

            for budget in matching_budgets:
                updated_reserved = budget.reserved + request.amount
                updated_budget = budget.model_copy(
                    update={
                        "reserved": updated_reserved,
                        "version": budget.version + 1,
                        "updated_at": now,
                    }
                )
                self.repository.save_budget(updated_budget)
                locked_budget_ids.append(budget.budget_id)

                # Record immutable accounting entry for this budget
                entry = AccountingEngine.create_record(
                    event_type=AccountingEventType.RESERVED,
                    reservation_id=reservation_id,
                    budget=updated_budget,
                    amount=request.amount,
                    idempotency_key=request.idempotency_key,
                    run_id=request.run_id,
                    actor_id=request.actor_id,
                    notes=f"Reserved {request.amount} {request.currency} for scope {budget.scope}",
                )
                self.repository.append_accounting_entry(entry)

            # 5. Create Durable Reservation Record
            ttl = request.ttl_seconds or self.policy.default_reservation_ttl_seconds
            expires_at = now + timedelta(seconds=ttl)

            reservation = ReservationRecord(
                reservation_id=reservation_id,
                workspace_id=request.workspace_id,
                project_id=request.project_id,
                run_id=request.run_id,
                capability=request.capability,
                budget_ids=locked_budget_ids,
                estimated_amount=request.amount,
                reserved_amount=request.amount,
                currency=request.currency,
                status=ReservationStatus.ACTIVE,
                created_at=now,
                expires_at=expires_at,
                idempotency_key=request.idempotency_key,
                cost_profile=request.cost_profile,
                metadata=request.metadata,
            )
            self.repository.save_reservation(reservation)

            return ReservationResult(
                success=True,
                reservation=reservation,
            )
