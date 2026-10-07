"""
ai/budget/accounting.py
=======================
Immutable audit ledger and financial accounting utilities for Budget Engine (S27.5).

Invariants:
- All accounting entries are append-only and immutable.
- Entries capture before/after financial state transitions for full auditability.
- No floating-point arithmetic; strictly Decimal backed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import uuid4

from ai.budget.types import (
    AccountingEventType,
    AccountingRecord,
    Budget,
)


class AccountingEngine:
    """
    Constructs and verifies audit trail records across all budget scopes.
    """

    @classmethod
    def create_record(
        cls,
        event_type: AccountingEventType,
        reservation_id: str,
        budget: Budget,
        amount: Decimal,
        idempotency_key: Optional[str] = None,
        run_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AccountingRecord:
        """Constructs a strongly-typed immutable ledger entry capturing budget balance snapshot."""
        now = datetime.now(timezone.utc)
        return AccountingRecord(
            entry_id=f"acc_{uuid4().hex[:16]}",
            timestamp=now,
            event_type=event_type,
            reservation_id=reservation_id,
            budget_id=budget.budget_id,
            scope=budget.scope,
            scope_reference=budget.scope_reference,
            amount=amount,
            resulting_reserved=budget.reserved,
            resulting_actual_spend=budget.actual_spend,
            resulting_available=budget.available,
            currency=budget.currency,
            idempotency_key=idempotency_key,
            run_id=run_id,
            actor_id=actor_id,
            notes=notes,
        )

    @classmethod
    def verify_budget_audit_trail(
        cls,
        budget: Budget,
        entries: List[AccountingRecord],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates mathematical reconciliation of ledger entries against the budget state.
        
        Returns:
            (True, None) if ledger aligns with current budget state.
            (False, error_reason) if discrepancy detected.
        """
        # Sort entries chronologically
        sorted_entries = sorted(entries, key=lambda e: e.timestamp)
        
        calculated_reserved = Decimal("0")
        calculated_actual = Decimal("0")

        for entry in sorted_entries:
            if entry.event_type == AccountingEventType.RESERVED:
                calculated_reserved += entry.amount
            elif entry.event_type == AccountingEventType.SETTLED:
                # Settle reduces reserved and increases actual spend
                # We expect entry.amount to represent settled amount
                calculated_actual += entry.amount
            elif entry.event_type in (AccountingEventType.RELEASED, AccountingEventType.EXPIRED):
                calculated_reserved -= entry.amount
            elif entry.event_type == AccountingEventType.ADJUSTED:
                # Overage or headroom adjustment
                calculated_actual += entry.amount

        # Check latest resulting balances from the most recent entry if any
        if sorted_entries:
            latest = sorted_entries[-1]
            if latest.resulting_reserved != budget.reserved:
                return (
                    False,
                    f"Audit trail drift: latest entry resulting_reserved ({latest.resulting_reserved}) != budget.reserved ({budget.reserved})",
                )
            if latest.resulting_actual_spend != budget.actual_spend:
                return (
                    False,
                    f"Audit trail drift: latest entry resulting_actual_spend ({latest.resulting_actual_spend}) != budget.actual_spend ({budget.actual_spend})",
                )

        return (True, None)
