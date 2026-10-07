"""
tests/ai/budget/test_scopes.py
==============================
Tests for multi-scope hierarchical budget enforcement and all-or-nothing atomicity (S27.5).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.contracts.errors import AIErrorCode
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetScope,
    ReservationRequest,
)


@pytest.fixture
def service() -> BudgetService:
    repo = InMemoryBudgetRepository()
    srv = BudgetService(repository=repo)
    now = datetime.now(timezone.utc)

    # Global Budget: $500
    srv.create_budget(
        Budget(
            budget_id="b_global",
            scope=BudgetScope.GLOBAL,
            scope_reference="global",
            limit=Decimal("500.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    # Workspace Budget: $100
    srv.create_budget(
        Budget(
            budget_id="b_ws",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_multi",
            limit=Decimal("100.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    # Project Budget: $10
    srv.create_budget(
        Budget(
            budget_id="b_proj",
            scope=BudgetScope.PROJECT,
            scope_reference="proj_video_01",
            limit=Decimal("10.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    # AIRun Budget: $3
    srv.create_budget(
        Budget(
            budget_id="b_run",
            scope=BudgetScope.AIRUN,
            scope_reference="run_stt_001",
            limit=Decimal("3.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    # Capability Budget: $2.00
    srv.create_budget(
        Budget(
            budget_id="b_cap",
            scope=BudgetScope.CAPABILITY,
            scope_reference="SPEECH_TO_TEXT",
            limit=Decimal("2.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    return srv


class TestMultiScopeBudgetEnforcement:

    def test_multi_scope_approval_when_all_scopes_allow(self, service: BudgetService):
        # Request for $1.50: All scopes (Global $500, WS $100, Proj $10, Run $3, Cap $2) allow!
        req = ReservationRequest(
            workspace_id="ws_multi",
            project_id="proj_video_01",
            run_id="run_stt_001",
            capability="SPEECH_TO_TEXT",
            amount=Decimal("1.50"),
            idempotency_key="multi_approve_001",
        )
        result = service.reserve(req)

        assert result.success is True
        assert result.reservation is not None
        assert len(result.reservation.budget_ids) == 5

        # Check all 5 budgets were atomically updated
        assert service.get_budget("b_global").reserved == Decimal("1.50")
        assert service.get_budget("b_ws").reserved == Decimal("1.50")
        assert service.get_budget("b_proj").reserved == Decimal("1.50")
        assert service.get_budget("b_run").reserved == Decimal("1.50")
        assert service.get_budget("b_cap").reserved == Decimal("1.50")

    def test_one_scope_denies_all_with_zero_partial_reservations(self, service: BudgetService):
        # Scenario from prompt:
        # Workspace ($100), Project ($10), AIRun ($3) allow $2.50.
        # But Capability STT ($2.00) DENIES $2.50!
        req = ReservationRequest(
            workspace_id="ws_multi",
            project_id="proj_video_01",
            run_id="run_stt_001",
            capability="SPEECH_TO_TEXT",
            amount=Decimal("2.50"),
            idempotency_key="multi_deny_001",
        )
        result = service.reserve(req)

        assert result.success is False
        assert result.reservation is None
        assert result.error is not None
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert result.denial_scope == BudgetScope.CAPABILITY
        assert result.available_amount == Decimal("2.00")
        assert result.required_amount == Decimal("2.50")

        # CRITICAL: Verify NO scope was partially reserved!
        # All balances must remain strictly 0.00!
        assert service.get_budget("b_global").reserved == Decimal("0.00")
        assert service.get_budget("b_ws").reserved == Decimal("0.00")
        assert service.get_budget("b_proj").reserved == Decimal("0.00")
        assert service.get_budget("b_run").reserved == Decimal("0.00")
        assert service.get_budget("b_cap").reserved == Decimal("0.00")

    def test_run_scope_denies_when_exceeding_run_limit(self, service: BudgetService):
        # Request for $3.50:
        # Capability not specified, but AIRun limit is $3.00.
        req = ReservationRequest(
            workspace_id="ws_multi",
            project_id="proj_video_01",
            run_id="run_stt_001",
            amount=Decimal("3.50"),
            idempotency_key="multi_run_deny_001",
        )
        result = service.reserve(req)

        assert result.success is False
        assert result.denial_scope == BudgetScope.AIRUN
        assert service.get_budget("b_ws").reserved == Decimal("0.00")
        assert service.get_budget("b_proj").reserved == Decimal("0.00")
        assert service.get_budget("b_run").reserved == Decimal("0.00")
