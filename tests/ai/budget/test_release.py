"""
tests/ai/budget/test_release.py
===============================
Unit tests for reservation release, cancellation, and TTL expiration (S27.5).
"""

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
            budget_id="b_rel",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_rel",
            limit=Decimal("30.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )
    return srv


class TestBudgetReleaseAndExpiration:

    def test_release_active_reservation(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_rel",
            amount=Decimal("10.00"),
            idempotency_key="rel_001",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        assert service.get_budget("b_rel").reserved == Decimal("10.00")

        result = service.release(res_id)
        assert result.success is True
        assert result.released_amount == Decimal("10.00")
        assert result.reservation.status == ReservationStatus.RELEASED

        budget = service.get_budget("b_rel")
        assert budget.reserved == Decimal("0.00")
        assert budget.available == Decimal("30.00")

    def test_cannot_release_settled_reservation(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_rel",
            amount=Decimal("5.00"),
            idempotency_key="rel_settled",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        service.settle(res_id, actual_cost=Decimal("5.00"))

        result = service.release(res_id)
        assert result.success is False
        assert "Cannot release reservation with status 'SETTLED'" in result.error.message

    def test_expire_stale_reservations(self, service: BudgetService):
        now = datetime.now(timezone.utc)

        # 1. Create a reservation with TTL = 10 seconds
        req1 = ReservationRequest(
            workspace_id="ws_rel",
            amount=Decimal("8.00"),
            idempotency_key="exp_001",
            ttl_seconds=10,
        )
        res1 = service.reserve(req1)
        res_id1 = res1.reservation.reservation_id

        # 2. Create another reservation with TTL = 600 seconds (long TTL)
        req2 = ReservationRequest(
            workspace_id="ws_rel",
            amount=Decimal("5.00"),
            idempotency_key="exp_002",
            ttl_seconds=600,
        )
        res2 = service.reserve(req2)
        res_id2 = res2.reservation.reservation_id

        # Initial reserved = $13.00
        assert service.get_budget("b_rel").reserved == Decimal("13.00")

        # Simulate time moving forward 15 seconds (so res1 is expired, res2 is not)
        sweep_time = now + timedelta(seconds=15)
        sweep_result = service.expire_stale_reservations(as_of=sweep_time)

        assert sweep_result.expired_count == 1
        assert sweep_result.released_amount == Decimal("8.00")
        assert res_id1 in sweep_result.expired_reservation_ids

        # Check res1 is EXPIRED
        record1 = service.repository.get_reservation(res_id1)
        assert record1.status == ReservationStatus.EXPIRED

        # Check res2 remains ACTIVE
        record2 = service.repository.get_reservation(res_id2)
        assert record2.status == ReservationStatus.ACTIVE

        # Budget balance updated: res1 ($8.00) released, res2 ($5.00) remains reserved
        budget = service.get_budget("b_rel")
        assert budget.reserved == Decimal("5.00")
        assert budget.available == Decimal("25.00")

        # Repeated sweep at same time yields 0 additional expirations (exactly once!)
        sweep2 = service.expire_stale_reservations(as_of=sweep_time)
        assert sweep2.expired_count == 0
        assert sweep2.released_amount == Decimal("0.00")
