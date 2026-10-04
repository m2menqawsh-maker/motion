"""
tests/ai/budget/test_settlement.py
==================================
Unit tests for reservation settlement, overage policies, and provider failure handling (S27.5).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.contracts.errors import AIErrorCode
from ai.contracts.usage import UsageRecord
from ai.budget.policy import BudgetPolicy
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetExceededError,
    BudgetOverageError,
    BudgetScope,
    ReservationRequest,
    ReservationStatus,
)


@pytest.fixture
def repo() -> InMemoryBudgetRepository:
    return InMemoryBudgetRepository()


@pytest.fixture
def service(repo: InMemoryBudgetRepository) -> BudgetService:
    now = datetime.now(timezone.utc)
    srv = BudgetService(repository=repo)
    srv.create_budget(
        Budget(
            budget_id="b_settle",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_settle",
            limit=Decimal("20.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )
    return srv


class TestBudgetSettlement:

    def test_actual_less_than_reserved_releases_difference(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("10.00"),
            idempotency_key="settle_under",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Budget state after reservation: reserved = 10, actual = 0, available = 10
        b_after_res = service.get_budget("b_settle")
        assert b_after_res.reserved == Decimal("10.00")
        assert b_after_res.available == Decimal("10.00")

        # Settle with actual = $7.00
        result = service.settle(res_id, actual_cost=Decimal("7.00"))

        assert result.success is True
        assert result.actual_cost == Decimal("7.00")
        assert result.released_cost == Decimal("3.00")
        assert result.reservation.status == ReservationStatus.SETTLED
        assert result.reservation.settled_amount == Decimal("7.00")

        # Budget state after settlement:
        # reserved should decrease to 0.00
        # actual_spend should increase to 7.00
        # available should be limit(20) - actual(7) - reserved(0) = 13.00
        b_after_settle = service.get_budget("b_settle")
        assert b_after_settle.reserved == Decimal("0.00")
        assert b_after_settle.actual_spend == Decimal("7.00")
        assert b_after_settle.available == Decimal("13.00")

    def test_actual_equal_reserved_exact_settlement(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("5.00"),
            idempotency_key="settle_exact",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        result = service.settle(res_id, actual_cost=Decimal("5.00"))
        assert result.success is True
        assert result.released_cost == Decimal("0.00")

        budget = service.get_budget("b_settle")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("5.00")
        assert budget.available == Decimal("15.00")

    def test_actual_greater_than_reserved_rejected_by_default_strict_policy(self, service: BudgetService):
        # By default, allow_overage_within_limit is False (Strict: no overage)
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("5.00"),
            idempotency_key="settle_overage_strict",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Actual = $6.00 (exceeds $5.00 reservation)
        with pytest.raises(BudgetOverageError) as exc_info:
            service.settle(res_id, actual_cost=Decimal("6.00"))

        assert exc_info.value.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert "overage is forbidden" in exc_info.value.error.message

        # Reservation remains active and uncorrupted
        res_record = service.repository.get_reservation(res_id)
        assert res_record.status == ReservationStatus.ACTIVE

    def test_actual_greater_than_reserved_with_bounded_absorption_policy(self, repo: InMemoryBudgetRepository):
        # Configure policy to permit bounded overage if budget limit allows
        permissive_policy = BudgetPolicy(allow_overage_within_limit=True)
        service = BudgetService(repository=repo, policy=permissive_policy)

        now = datetime.now(timezone.utc)
        service.create_budget(
            Budget(
                budget_id="b_overage_test",
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_overage",
                limit=Decimal("20.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        req = ReservationRequest(
            workspace_id="ws_overage",
            amount=Decimal("5.00"),
            idempotency_key="settle_overage_allowed",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Settle with $7.00 (within $20.00 total limit)
        result = service.settle(res_id, actual_cost=Decimal("7.00"))
        assert result.success is True
        assert result.actual_cost == Decimal("7.00")

        budget = service.get_budget("b_overage_test")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("7.00")
        assert budget.available == Decimal("13.00")

    def test_actual_greater_than_reserved_exceeding_hard_limit_fails(self, repo: InMemoryBudgetRepository):
        permissive_policy = BudgetPolicy(allow_overage_within_limit=True)
        service = BudgetService(repository=repo, policy=permissive_policy)

        now = datetime.now(timezone.utc)
        service.create_budget(
            Budget(
                budget_id="b_hard_limit",
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_hard_limit",
                limit=Decimal("10.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        req = ReservationRequest(
            workspace_id="ws_hard_limit",
            amount=Decimal("8.00"),
            idempotency_key="settle_exceed_hard",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Attempt to settle for $12.00, which exceeds the $10.00 limit
        with pytest.raises(BudgetExceededError) as exc_info:
            service.settle(res_id, actual_cost=Decimal("12.00"))

        assert exc_info.value.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert "exceeds hard budget limit" in exc_info.value.error.message

        # Hard limit invariant was NOT violated
        budget = service.get_budget("b_hard_limit")
        assert budget.actual_spend + budget.reserved <= budget.limit

    def test_settlement_with_usage_record(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("4.00"),
            idempotency_key="settle_usage_001",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        usage = UsageRecord(input_tokens=1000, output_tokens=500, total_tokens=1500)
        result = service.settle(res_id, actual_cost=Decimal("3.50"), usage=usage)

        assert result.success is True
        assert result.reservation.metadata.get("usage") is not None
        assert result.reservation.metadata["usage"]["total_tokens"] == 1500

    def test_provider_failure_before_charge_releases_full_amount(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("5.00"),
            idempotency_key="prov_fail_001",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Provider failed before execution started; cancel with $0 actual spend
        result = service.cancel(res_id, actual_cost=Decimal("0.00"))
        assert result.success is True
        assert result.released_amount == Decimal("5.00")

        budget = service.get_budget("b_settle")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("0.00")
        assert budget.available == Decimal("20.00")

    def test_provider_failure_with_actual_partial_charge(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("6.00"),
            idempotency_key="prov_fail_partial",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        # Provider failed halfway through streaming but charged $1.50
        result = service.cancel(res_id, actual_cost=Decimal("1.50"))
        assert result.success is True
        assert result.actual_cost == Decimal("1.50")
        assert result.released_cost == Decimal("4.50")

        budget = service.get_budget("b_settle")
        assert budget.reserved == Decimal("0.00")
        assert budget.actual_spend == Decimal("1.50")
        assert budget.available == Decimal("18.50")

    def test_negative_actual_cost_rejected(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("5.00"),
            idempotency_key="neg_settle",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        with pytest.raises(ValueError, match="cannot be negative"):
            service.settle(res_id, actual_cost=Decimal("-1.00"))

    def test_float_actual_cost_rejected(self, service: BudgetService):
        req = ReservationRequest(
            workspace_id="ws_settle",
            amount=Decimal("5.00"),
            idempotency_key="float_settle",
        )
        res = service.reserve(req)
        res_id = res.reservation.reservation_id

        with pytest.raises(TypeError, match="must be Decimal, not float"):
            service.settle(res_id, actual_cost=3.5)
