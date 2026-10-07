"""
tests/ai/budget/test_invariants.py
==================================
Unit tests for the Sacred Invariants and failure injection rollback (S27.5).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
import pytest

from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetScope,
    ReservationRequest,
)


class TestBudgetInvariants:

    def test_invariant_checker_validates_healthy_budget(self):
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        budget = Budget(
            budget_id="b_inv_01",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_inv",
            limit=Decimal("100.00"),
            reserved=Decimal("30.00"),
            actual_spend=Decimal("40.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
        service.create_budget(budget)

        assert service.verify_invariants("b_inv_01") is True
        assert budget.available == Decimal("30.00")

    def test_invariant_holds_over_arbitrary_transaction_sequence(self):
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        budget_id = "b_rand_seq"
        service.create_budget(
            Budget(
                budget_id=budget_id,
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_rand",
                limit=Decimal("100.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        active_res_ids = []
        random.seed(42)

        for i in range(100):
            action = random.choice(["reserve", "settle", "release"])

            if action == "reserve" or not active_res_ids:
                amount = Decimal(str(random.randint(1, 15)))
                req = ReservationRequest(
                    workspace_id="ws_rand",
                    amount=amount,
                    idempotency_key=f"rand_req_{i}",
                )
                res = service.reserve(req)
                if res.success:
                    active_res_ids.append((res.reservation.reservation_id, amount))
            elif action == "settle" and active_res_ids:
                res_id, reserved_amt = active_res_ids.pop(0)
                # Settle with actual <= reserved
                actual = Decimal(str(random.randint(0, int(reserved_amt))))
                service.settle(res_id, actual_cost=actual)
            elif action == "release" and active_res_ids:
                res_id, _ = active_res_ids.pop(0)
                service.release(res_id)

            # Invariant check after every single operation
            assert service.verify_invariants(budget_id) is True

    def test_failure_injection_rolls_back_multi_scope_transaction(self):
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        # Setup 2 scopes: Workspace and Project
        service.create_budget(
            Budget(
                budget_id="b_ws_fail",
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_fail",
                limit=Decimal("50.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )
        service.create_budget(
            Budget(
                budget_id="b_proj_fail",
                scope=BudgetScope.PROJECT,
                scope_reference="proj_fail",
                limit=Decimal("50.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        # Monkey-patch save_reservation to simulate transient storage crash after budget mutations
        original_save_reservation = repo.save_reservation

        def _exploding_save_reservation(res):
            raise IOError("Simulated persistence failure during reservation write!")

        repo.save_reservation = _exploding_save_reservation

        req = ReservationRequest(
            workspace_id="ws_fail",
            project_id="proj_fail",
            amount=Decimal("10.00"),
            idempotency_key="injected_failure_001",
        )

        # Operation must fail due to injected error
        with pytest.raises(IOError, match="Simulated persistence failure"):
            service.reserve(req)

        # Restore original function
        repo.save_reservation = original_save_reservation

        # CRITICAL: Verify that the atomic unit-of-work rolled back cleanly!
        # Neither budget should have its reserved balance mutated!
        ws_budget = service.get_budget("b_ws_fail")
        proj_budget = service.get_budget("b_proj_fail")

        assert ws_budget.reserved == Decimal("0.00"), "Workspace budget was not rolled back!"
        assert proj_budget.reserved == Decimal("0.00"), "Project budget was not rolled back!"
        assert repo.get_reservation_by_idempotency_key("injected_failure_001") is None
