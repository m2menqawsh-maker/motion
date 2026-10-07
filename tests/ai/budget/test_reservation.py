"""
tests/ai/budget/test_reservation.py
===================================
Unit tests for atomic reservation and basic scope enforcement (S27.5).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from ai.contracts.errors import AIErrorCode
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetScope,
    CostProfile,
    ReservationRequest,
    ReservationStatus,
)


@pytest.fixture
def repo() -> InMemoryBudgetRepository:
    return InMemoryBudgetRepository()


@pytest.fixture
def service(repo: InMemoryBudgetRepository) -> BudgetService:
    return BudgetService(repository=repo)


@pytest.fixture
def workspace_budget(service: BudgetService) -> Budget:
    now = datetime.now(timezone.utc)
    budget = Budget(
        budget_id="b_ws_001",
        scope=BudgetScope.WORKSPACE,
        scope_reference="ws_test",
        limit=Decimal("10.00"),
        valid_from=now - timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    return service.create_budget(budget)


class TestBudgetReservation:

    def test_valid_single_scope_reservation(self, service, workspace_budget):
        req = ReservationRequest(
            workspace_id="ws_test",
            amount=Decimal("2.50"),
            idempotency_key="req_valid_001",
        )
        result = service.reserve(req)

        assert result.success is True
        assert result.reservation is not None
        assert result.reservation.reserved_amount == Decimal("2.50")
        assert result.reservation.status == ReservationStatus.ACTIVE
        assert result.reservation.workspace_id == "ws_test"

        # Check repository state
        updated_budget = service.get_budget("b_ws_001")
        assert updated_budget.reserved == Decimal("2.50")
        assert updated_budget.actual_spend == Decimal("0.00")
        assert updated_budget.available == Decimal("7.50")

    def test_exact_budget_reservation(self, service, workspace_budget):
        req = ReservationRequest(
            workspace_id="ws_test",
            amount=Decimal("10.00"),
            idempotency_key="req_exact_001",
        )
        result = service.reserve(req)

        assert result.success is True
        updated_budget = service.get_budget("b_ws_001")
        assert updated_budget.reserved == Decimal("10.00")
        assert updated_budget.available == Decimal("0.00")

    def test_insufficient_budget_denies_with_budget_exceeded(self, service, workspace_budget):
        req = ReservationRequest(
            workspace_id="ws_test",
            amount=Decimal("10.50"),
            idempotency_key="req_exceed_001",
        )
        result = service.reserve(req)

        assert result.success is False
        assert result.reservation is None
        assert result.error is not None
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert result.denial_scope == BudgetScope.WORKSPACE
        assert result.available_amount == Decimal("10.00")
        assert result.required_amount == Decimal("10.50")
        assert "Budget exceeded for scope" in result.error.message

        # Budget state remains completely untouched
        unchanged_budget = service.get_budget("b_ws_001")
        assert unchanged_budget.reserved == Decimal("0.00")
        assert unchanged_budget.available == Decimal("10.00")

    def test_disabled_budget_rejected(self, service):
        now = datetime.now(timezone.utc)
        budget = Budget(
            budget_id="b_disabled",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_disabled",
            limit=Decimal("50.00"),
            enabled=False,
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
        service.create_budget(budget)

        req = ReservationRequest(
            workspace_id="ws_disabled",
            amount=Decimal("5.00"),
            idempotency_key="req_dis_001",
        )
        result = service.reserve(req)
        assert result.success is False
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert "disabled" in result.error.message

    def test_expired_budget_rejected(self, service):
        now = datetime.now(timezone.utc)
        budget = Budget(
            budget_id="b_expired",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_expired",
            limit=Decimal("50.00"),
            valid_from=now - timedelta(days=10),
            valid_until=now - timedelta(seconds=1),
            created_at=now - timedelta(days=10),
            updated_at=now,
        )
        service.create_budget(budget)

        req = ReservationRequest(
            workspace_id="ws_expired",
            amount=Decimal("5.00"),
            idempotency_key="req_exp_001",
        )
        result = service.reserve(req)
        assert result.success is False
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert "expired" in result.error.message

    def test_future_budget_rejected(self, service):
        now = datetime.now(timezone.utc)
        budget = Budget(
            budget_id="b_future",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_future",
            limit=Decimal("50.00"),
            valid_from=now + timedelta(days=2),
            created_at=now,
            updated_at=now,
        )
        service.create_budget(budget)

        req = ReservationRequest(
            workspace_id="ws_future",
            amount=Decimal("5.00"),
            idempotency_key="req_fut_001",
        )
        result = service.reserve(req)
        assert result.success is False
        assert "not yet active" in result.error.message

    def test_negative_monetary_amount_rejected(self):
        with pytest.raises(ValidationError):
            ReservationRequest(
                workspace_id="ws_test",
                amount=Decimal("-1.00"),
                idempotency_key="req_neg",
            )

    def test_float_monetary_input_rejected(self):
        with pytest.raises(ValidationError):
            ReservationRequest(
                workspace_id="ws_test",
                amount=1.50,  # float is strictly forbidden!
                idempotency_key="req_float",
            )

    def test_currency_mismatch_rejected(self):
        with pytest.raises(ValidationError):
            ReservationRequest(
                workspace_id="ws_test",
                amount=Decimal("2.00"),
                currency="EUR",
                idempotency_key="req_curr",
            )

    def test_missing_budget_denied(self, service):
        req = ReservationRequest(
            workspace_id="ws_non_existent",
            amount=Decimal("1.00"),
            idempotency_key="req_nobudget",
        )
        result = service.reserve(req)
        assert result.success is False
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert "No budget account exists" in result.error.message
