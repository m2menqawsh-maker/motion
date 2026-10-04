"""
ai/budget/service.py
====================
Authoritative Budget & Cost Service for the AI subsystem (S27.5).

Guarantees:
- Sole financial authority over AI spend allocation, reservation, and settlement.
- Zero provider execution (does not call, import, or manage provider execution adapters).
- Invariant under all concurrency: actual_spend + active_reservations <= budget_limit.
- All monetary operations backed by exact Decimal arithmetic (strict rejection of binary float).
- Multi-scope all-or-nothing atomicity and idempotent deduplication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.usage import UsageRecord
from ai.budget.accounting import AccountingEngine
from ai.budget.policy import BudgetPolicy
from ai.budget.repository import BudgetRepository
from ai.budget.reservation import ReservationEngine
from ai.budget.types import (
    AccountingEventType,
    Budget,
    BudgetExceededError,
    BudgetOverageError,
    BudgetScope,
    CostProfile,
    ExpirationResult,
    ReleaseResult,
    ReservationRecord,
    ReservationRequest,
    ReservationResult,
    ReservationStatus,
    SettlementResult,
)


class BudgetService:
    """
    Authoritative service governing AI budget lifecycles:
    reserve -> execute (orchestrator) -> settle / release.
    """

    def __init__(
        self,
        repository: BudgetRepository,
        policy: Optional[BudgetPolicy] = None,
    ):
        self.repository = repository
        self.policy = policy or BudgetPolicy()
        self.reservation_engine = ReservationEngine(repository=self.repository, policy=self.policy)

    # -------------------------------------------------------------------------
    # Budget Management
    # -------------------------------------------------------------------------

    def create_budget(self, budget: Budget) -> Budget:
        """Registers a new budget account in the repository."""
        with self.repository.atomic_transaction():
            existing = self.repository.get_budget(budget.budget_id)
            if existing is not None:
                raise ValueError(f"Budget with id '{budget.budget_id}' already exists")
            self.repository.save_budget(budget)
            return budget

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Retrieves a budget by its canonical identifier."""
        return self.repository.get_budget(budget_id)

    def get_available_budget(self, scope: BudgetScope | str, scope_reference: str) -> Optional[Decimal]:
        """Queries the current derived available balance for a specific scope."""
        budgets = self.repository.get_budgets_for_scopes([(scope, scope_reference)])
        if not budgets:
            return None
        return budgets[0].available

    def can_afford(
        self,
        scopes: List[Tuple[BudgetScope | str, str]],
        amount: Decimal,
        currency: str = "USD",
    ) -> bool:
        """
        Advisory pre-flight check without creating a reservation.
        Returns True if all matching budgets have sufficient available balance.
        """
        if isinstance(amount, float):
            raise TypeError("Monetary amounts must be Decimal, not float")
        if amount <= Decimal("0"):
            return False

        budgets = self.repository.get_budgets_for_scopes(scopes)
        if not budgets:
            return False

        now = datetime.now(timezone.utc)
        for b in budgets:
            if not b.enabled or b.currency != currency:
                return False
            if b.valid_from > now:
                return False
            if b.valid_until and b.valid_until < now:
                return False
            if b.available < amount:
                return False
        return True

    # -------------------------------------------------------------------------
    # Reservation Phase
    # -------------------------------------------------------------------------

    def reserve(self, request: ReservationRequest) -> ReservationResult:
        """
        Atomically requests and locks budget across all applicable scopes.
        Guarantees all-or-nothing execution and idempotency.
        """
        if isinstance(request.amount, float):
            raise TypeError("Monetary amounts must be Decimal, not float")
        if request.amount <= Decimal("0"):
            raise ValueError(f"Reservation amount must be strictly positive, got {request.amount}")

        return self.reservation_engine.reserve(request)

    # -------------------------------------------------------------------------
    # Settlement Phase
    # -------------------------------------------------------------------------

    def settle(
        self,
        reservation_id: str,
        actual_cost: Decimal,
        usage: Optional[UsageRecord] = None,
        actor_id: Optional[str] = None,
    ) -> SettlementResult:
        """
        Finalizes an active reservation with actual settled spend.
        
        Guarantees:
        - Atomic decrement of reserved balance and increment of actual_spend.
        - Difference (reserved - actual) is immediately and safely released to available balance.
        - Strict overage policy: if actual > reserved, checks available headroom; rejects if limit exceeded.
        - Idempotent: repeated settlement with matching actual_cost returns the settled reservation.
        """
        if isinstance(actual_cost, float):
            raise TypeError("Monetary amounts must be Decimal, not float")
        if actual_cost < Decimal("0"):
            raise ValueError(f"Actual cost cannot be negative, got {actual_cost}")

        now = datetime.now(timezone.utc)

        with self.repository.atomic_transaction():
            reservation = self.repository.get_reservation(reservation_id)
            if reservation is None:
                error = AIError(
                    code=AIErrorCode.INTERNAL_ERROR,
                    message=f"Reservation '{reservation_id}' not found",
                    retryable=False,
                    details={"reservation_id": reservation_id},
                )
                return SettlementResult(success=False, error=error)

            # Idempotency check on already settled reservations
            if reservation.status == ReservationStatus.SETTLED:
                if reservation.settled_amount == actual_cost:
                    return SettlementResult(
                        success=True,
                        reservation=reservation,
                        actual_cost=actual_cost,
                        released_cost=Decimal("0"),
                    )
                else:
                    error = AIError(
                        code=AIErrorCode.POLICY_DENIED,
                        message=(
                            f"Reservation '{reservation_id}' is already settled with conflicting amount "
                            f"{reservation.settled_amount} != {actual_cost}"
                        ),
                        retryable=False,
                        details={
                            "reservation_id": reservation_id,
                            "existing_settled_amount": str(reservation.settled_amount),
                            "requested_settled_amount": str(actual_cost),
                        },
                    )
                    return SettlementResult(success=False, error=error)

            if reservation.status != ReservationStatus.ACTIVE:
                error = AIError(
                    code=AIErrorCode.POLICY_DENIED,
                    message=f"Cannot settle reservation in '{reservation.status.value}' status",
                    retryable=False,
                    details={"reservation_id": reservation_id, "status": reservation.status.value},
                )
                return SettlementResult(success=False, error=error)

            # Retrieve locked budget accounts
            budgets: List[Budget] = []
            for b_id in reservation.budget_ids:
                b = self.repository.get_budget(b_id)
                if b is None:
                    error = AIError(
                        code=AIErrorCode.INTERNAL_ERROR,
                        message=f"Associated budget account '{b_id}' missing during settlement",
                        retryable=False,
                        details={"reservation_id": reservation_id, "budget_id": b_id},
                    )
                    return SettlementResult(success=False, error=error)
                budgets.append(b)

            reserved_amount = reservation.reserved_amount
            is_overage = actual_cost > reserved_amount

            # Overage Handling: Verify policy and available capacity
            if is_overage:
                overage_delta = actual_cost - reserved_amount
                if not self.policy.allow_overage_within_limit:
                    error = AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=(
                            f"Settlement cost ({actual_cost}) exceeds reserved amount ({reserved_amount}) "
                            f"and overage is forbidden by budget policy"
                        ),
                        retryable=False,
                        details={
                            "reservation_id": reservation_id,
                            "reserved_amount": str(reserved_amount),
                            "actual_cost": str(actual_cost),
                            "overage_delta": str(overage_delta),
                        },
                    )
                    raise BudgetOverageError(error)

                # Policy permits bounded absorption if available capacity exists
                for budget in budgets:
                    # After releasing reserved_amount, effective available is (budget.available + reserved_amount)
                    # We must verify that actual_cost <= budget.available + reserved_amount
                    # which is equivalent to: budget.actual_spend + actual_cost <= budget.limit
                    if budget.actual_spend + actual_cost > budget.limit:
                        error = AIError(
                            code=AIErrorCode.BUDGET_EXCEEDED,
                            message=(
                                f"Settlement overage exceeds hard budget limit for scope '{budget.scope}'. "
                                f"Spend limit: {budget.limit}, Proposed total spend: {budget.actual_spend + actual_cost}"
                            ),
                            retryable=False,
                            details={
                                "budget_id": budget.budget_id,
                                "scope": str(budget.scope),
                                "limit": str(budget.limit),
                                "actual_spend": str(budget.actual_spend),
                                "proposed_charge": str(actual_cost),
                            },
                        )
                        raise BudgetExceededError(error, scope=budget.scope)

            # Apply atomic settlement to all linked budgets
            released_cost = Decimal("0")
            if actual_cost < reserved_amount:
                released_cost = reserved_amount - actual_cost

            for budget in budgets:
                new_reserved = budget.reserved - reserved_amount
                new_actual = budget.actual_spend + actual_cost
                updated_budget = budget.model_copy(
                    update={
                        "reserved": new_reserved,
                        "actual_spend": new_actual,
                        "version": budget.version + 1,
                        "updated_at": now,
                    }
                )
                self.repository.save_budget(updated_budget)

                # Record accounting event
                event_type = AccountingEventType.ADJUSTED if is_overage else AccountingEventType.SETTLED
                entry = AccountingEngine.create_record(
                    event_type=event_type,
                    reservation_id=reservation_id,
                    budget=updated_budget,
                    amount=actual_cost,
                    idempotency_key=reservation.idempotency_key,
                    run_id=reservation.run_id,
                    actor_id=actor_id,
                    notes=(
                        f"Settled {actual_cost} {reservation.currency} "
                        f"(reserved was {reserved_amount}, released {released_cost})"
                    ),
                )
                self.repository.append_accounting_entry(entry)

            # Update Reservation Record
            metadata = dict(reservation.metadata)
            if usage:
                metadata["usage"] = usage.model_dump(mode="json")

            updated_reservation = reservation.model_copy(
                update={
                    "status": ReservationStatus.SETTLED,
                    "settled_amount": actual_cost,
                    "settled_at": now,
                    "metadata": metadata,
                }
            )
            self.repository.save_reservation(updated_reservation)

            return SettlementResult(
                success=True,
                reservation=updated_reservation,
                actual_cost=actual_cost,
                released_cost=released_cost,
            )

    # -------------------------------------------------------------------------
    # Release / Cancellation Phase
    # -------------------------------------------------------------------------

    def release(
        self,
        reservation_id: str,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> ReleaseResult:
        """
        Releases an active reservation without charges, returning full reserved balance.
        Idempotent: releasing an already released reservation is a safe no-op.
        """
        now = datetime.now(timezone.utc)

        with self.repository.atomic_transaction():
            reservation = self.repository.get_reservation(reservation_id)
            if reservation is None:
                error = AIError(
                    code=AIErrorCode.INTERNAL_ERROR,
                    message=f"Reservation '{reservation_id}' not found",
                    retryable=False,
                    details={"reservation_id": reservation_id},
                )
                return ReleaseResult(success=False, error=error)

            # Idempotent release check
            if reservation.status == ReservationStatus.RELEASED:
                return ReleaseResult(
                    success=True,
                    reservation=reservation,
                    released_amount=Decimal("0"),
                )

            if reservation.status != ReservationStatus.ACTIVE:
                error = AIError(
                    code=AIErrorCode.POLICY_DENIED,
                    message=f"Cannot release reservation with status '{reservation.status.value}'",
                    retryable=False,
                    details={"reservation_id": reservation_id, "status": reservation.status.value},
                )
                return ReleaseResult(success=False, error=error)

            released_amount = reservation.reserved_amount

            # Return funds across all locked budgets
            for b_id in reservation.budget_ids:
                budget = self.repository.get_budget(b_id)
                if budget:
                    new_reserved = budget.reserved - released_amount
                    updated_budget = budget.model_copy(
                        update={
                            "reserved": new_reserved,
                            "version": budget.version + 1,
                            "updated_at": now,
                        }
                    )
                    self.repository.save_budget(updated_budget)

                    # Append accounting record
                    entry = AccountingEngine.create_record(
                        event_type=AccountingEventType.RELEASED,
                        reservation_id=reservation_id,
                        budget=updated_budget,
                        amount=released_amount,
                        idempotency_key=reservation.idempotency_key,
                        run_id=reservation.run_id,
                        actor_id=actor_id,
                        notes=reason or f"Released unutilized reservation {reservation_id}",
                    )
                    self.repository.append_accounting_entry(entry)

            # Update reservation status
            updated_reservation = reservation.model_copy(
                update={
                    "status": ReservationStatus.RELEASED,
                    "released_at": now,
                }
            )
            self.repository.save_reservation(updated_reservation)

            return ReleaseResult(
                success=True,
                reservation=updated_reservation,
                released_amount=released_amount,
            )

    def cancel(
        self,
        reservation_id: str,
        actual_cost: Optional[Decimal] = None,
        actor_id: Optional[str] = None,
    ) -> SettlementResult | ReleaseResult:
        """
        Handles cancellation of an operation:
        - If no actual cost incurred: fully releases reservation.
        - If partial cost incurred: settles the actual cost and releases the remainder.
        """
        if actual_cost is None or actual_cost == Decimal("0"):
            return self.release(reservation_id=reservation_id, actor_id=actor_id, reason="Operation cancelled with zero spend")
        return self.settle(reservation_id=reservation_id, actual_cost=actual_cost, actor_id=actor_id)

    # -------------------------------------------------------------------------
    # Expiration Phase
    # -------------------------------------------------------------------------

    def expire_stale_reservations(self, as_of: Optional[datetime] = None) -> ExpirationResult:
        """
        Sweeps and expires stale ACTIVE reservations that have passed their TTL.
        Releases reserved amounts back to respective budget accounts exactly once.
        """
        target_time = as_of or datetime.now(timezone.utc)
        expired_ids: List[str] = []
        total_released = Decimal("0")

        with self.repository.atomic_transaction():
            stale_reservations = self.repository.get_active_expired_reservations(target_time)

            for res in stale_reservations:
                amount_to_release = res.reserved_amount

                for b_id in res.budget_ids:
                    budget = self.repository.get_budget(b_id)
                    if budget:
                        new_reserved = budget.reserved - amount_to_release
                        updated_budget = budget.model_copy(
                            update={
                                "reserved": new_reserved,
                                "version": budget.version + 1,
                                "updated_at": target_time,
                            }
                        )
                        self.repository.save_budget(updated_budget)

                        entry = AccountingEngine.create_record(
                            event_type=AccountingEventType.EXPIRED,
                            reservation_id=res.reservation_id,
                            budget=updated_budget,
                            amount=amount_to_release,
                            idempotency_key=res.idempotency_key,
                            run_id=res.run_id,
                            notes=f"Reservation expired at {target_time.isoformat()}",
                        )
                        self.repository.append_accounting_entry(entry)

                updated_res = res.model_copy(
                    update={
                        "status": ReservationStatus.EXPIRED,
                        "released_at": target_time,
                    }
                )
                self.repository.save_reservation(updated_res)
                expired_ids.append(res.reservation_id)
                total_released += amount_to_release

        return ExpirationResult(
            expired_count=len(expired_ids),
            released_amount=total_released,
            expired_reservation_ids=expired_ids,
        )

    # -------------------------------------------------------------------------
    # Invariant Verification
    # -------------------------------------------------------------------------

    def verify_invariants(self, budget_id: str) -> bool:
        """
        Enforces and validates the core architectural invariant:
        reserved >= 0
        actual_spend >= 0
        available >= 0
        actual_spend + reserved <= limit
        """
        budget = self.repository.get_budget(budget_id)
        if budget is None:
            raise ValueError(f"Budget '{budget_id}' not found")

        if budget.reserved < Decimal("0"):
            return False
        if budget.actual_spend < Decimal("0"):
            return False
        if budget.available < Decimal("0"):
            return False
        if (budget.actual_spend + budget.reserved) > budget.limit:
            return False
        return True
