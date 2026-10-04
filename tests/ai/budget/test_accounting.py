"""
tests/ai/budget/test_accounting.py
==================================
Unit tests for immutable accounting ledger, event emission, and audit trail verification (S27.5).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.budget.accounting import AccountingEngine
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    AccountingEventType,
    Budget,
    BudgetScope,
    ReservationRequest,
)


@pytest.fixture
def service() -> BudgetService:
    repo = InMemoryBudgetRepository()
    srv = BudgetService(repository=repo)
    now = datetime.now(timezone.utc)
    srv.create_budget(
        Budget(
            budget_id="b_audit",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_audit",
            limit=Decimal("50.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )
    return srv


class TestAccountingLedger:

    def test_full_lifecycle_accounting_trail(self, service: BudgetService):
        # 1. Reserve
        req = ReservationRequest(
            workspace_id="ws_audit",
            amount=Decimal("15.00"),
            idempotency_key="audit_001",
            run_id="run_audit_01",
            actor_id="user_admin",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # 2. Settle partial ($10.00 actual out of $15.00)
        service.settle(res_id, actual_cost=Decimal("10.00"), actor_id="user_admin")

        # Query all entries for this reservation
        entries = service.repository.get_accounting_entries(reservation_id=res_id)
        assert len(entries) == 2

        # First entry: RESERVED
        e1 = entries[0]
        assert e1.event_type == AccountingEventType.RESERVED
        assert e1.amount == Decimal("15.00")
        assert e1.resulting_reserved == Decimal("15.00")
        assert e1.resulting_actual_spend == Decimal("0.00")
        assert e1.resulting_available == Decimal("35.00")
        assert e1.actor_id == "user_admin"
        assert e1.run_id == "run_audit_01"

        # Second entry: SETTLED
        e2 = entries[1]
        assert e2.event_type == AccountingEventType.SETTLED
        assert e2.amount == Decimal("10.00")
        assert e2.resulting_reserved == Decimal("0.00")
        assert e2.resulting_actual_spend == Decimal("10.00")
        assert e2.resulting_available == Decimal("40.00")

    def test_release_emits_released_accounting_entry(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_audit",
            amount=Decimal("5.00"),
            idempotency_key="audit_rel",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        service.release(res_id, actor_id="operator", reason="User cancelled generation")

        entries = service.repository.get_accounting_entries(reservation_id=res_id)
        assert len(entries) == 2
        assert entries[1].event_type == AccountingEventType.RELEASED
        assert entries[1].amount == Decimal("5.00")
        assert entries[1].resulting_reserved == Decimal("0.00")
        assert entries[1].resulting_available == Decimal("50.00")
        assert "User cancelled" in entries[1].notes

    def test_audit_trail_mathematical_verification(self, service: BudgetService):
        # Perform multiple operations on the budget
        req1 = ReservationRequest(workspace_id="ws_audit", amount=Decimal("10.00"), idempotency_key="k1")
        res1 = service.reserve(req1)
        service.settle(res1.reservation.reservation_id, actual_cost=Decimal("8.00"))

        req2 = ReservationRequest(workspace_id="ws_audit", amount=Decimal("12.00"), idempotency_key="k2")
        res2 = service.reserve(req2)
        service.release(res2.reservation.reservation_id)

        req3 = ReservationRequest(workspace_id="ws_audit", amount=Decimal("5.00"), idempotency_key="k3")
        service.reserve(req3)

        budget = service.get_budget("b_audit")
        entries = service.repository.get_accounting_entries(budget_id="b_audit")

        # Verify mathematical consistency
        is_valid, error = AccountingEngine.verify_budget_audit_trail(budget, entries)
        assert is_valid is True
        assert error is None
