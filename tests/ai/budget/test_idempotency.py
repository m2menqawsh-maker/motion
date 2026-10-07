"""
tests/ai/budget/test_idempotency.py
==================================
Tests for idempotency deduplication across reserve, settle, and release (S27.5).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetScope,
    ReservationRequest,
    ReservationStatus,
)


@pytest.fixture
def service() -> BudgetService:
    repo = InMemoryBudgetRepository()
    srv = BudgetService(repository=repo)
    now = datetime.now(timezone.utc)
    srv.create_budget(
        Budget(
            budget_id="b_idem",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_idem",
            limit=Decimal("50.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )
    return srv


class TestIdempotency:

    def test_idempotent_reserve_sequential(self, service: BudgetService):
        req1 = ReservationRequest(
            workspace_id="ws_idem",
            amount=Decimal("5.00"),
            idempotency_key="idem_key_001",
        )
        res1 = service.reserve(req1)
        assert res1.success is True
        res_id = res1.reservation.reservation_id

        # Repeated reservation call with identical idempotency key
        req2 = ReservationRequest(
            workspace_id="ws_idem",
            amount=Decimal("5.00"),
            idempotency_key="idem_key_001",
        )
        res2 = service.reserve(req2)
        assert res2.success is True
        assert res2.reservation.reservation_id == res_id

        # Ensure budget was reserved ONLY ONCE ($5.00, not $10.00!)
        budget = service.get_budget("b_idem")
        assert budget.reserved == Decimal("5.00")
        assert budget.available == Decimal("45.00")

    def test_idempotent_reserve_concurrent(self, service: BudgetService):
        # 10 concurrent threads submitting identical idempotency key
        key = "concurrent_idem_key_999"

        def _do_reserve():
            req = ReservationRequest(
                workspace_id="ws_idem",
                amount=Decimal("4.00"),
                idempotency_key=key,
            )
            return service.reserve(req)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_do_reserve) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(r.success for r in results)
        reservation_ids = {r.reservation.reservation_id for r in results}
        assert len(reservation_ids) == 1, "All concurrent requests must resolve to the identical reservation ID"

        # Balance reserved exactly once
        budget = service.get_budget("b_idem")
        assert budget.reserved == Decimal("4.00")
        assert budget.available == Decimal("46.00")

    def test_idempotent_settlement(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_idem",
            amount=Decimal("10.00"),
            idempotency_key="idem_settle_001",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Settle once
        s1 = service.settle(res_id, actual_cost=Decimal("8.00"))
        assert s1.success is True
        assert s1.actual_cost == Decimal("8.00")
        assert s1.released_cost == Decimal("2.00")

        # Settle second time with identical actual cost
        s2 = service.settle(res_id, actual_cost=Decimal("8.00"))
        assert s2.success is True
        assert s2.reservation.status == ReservationStatus.SETTLED

        # Budget balances must NOT be credited or debited twice
        budget = service.get_budget("b_idem")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("8.00")
        assert budget.available == Decimal("42.00")

    def test_conflicting_second_settlement_rejected(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_idem",
            amount=Decimal("10.00"),
            idempotency_key="idem_settle_conflict",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        service.settle(res_id, actual_cost=Decimal("8.00"))

        # Settle second time with DIFFERENT amount
        s2 = service.settle(res_id, actual_cost=Decimal("9.00"))
        assert s2.success is False
        assert "conflicting amount" in s2.error.message

    def test_idempotent_release(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_idem",
            amount=Decimal("6.00"),
            idempotency_key="idem_rel_001",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # First release returns funds
        r1 = service.release(res_id)
        assert r1.success is True
        assert r1.released_amount == Decimal("6.00")

        # Second release is idempotent safe no-op
        r2 = service.release(res_id)
        assert r2.success is True
        assert r2.released_amount == Decimal("0.00")

        # Balance reserved is 0, available is 50.00 (not 56.00!)
        budget = service.get_budget("b_idem")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("0.00")
        assert budget.available == Decimal("50.00")
