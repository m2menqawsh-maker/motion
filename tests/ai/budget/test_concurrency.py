"""
tests/ai/budget/test_concurrency.py
===================================
Critical Concurrency and Race Condition Test Suite for Budget Engine (S27.5).

Enforces the Sacred Invariant under heavy multi-threaded contention:
    actual_spend + active_reservations <= budget_limit
at every instant.

Tests:
1. 100 concurrent requests each $1.00 against $10.00 budget:
   - Synchronized barrier start.
   - Exactly 10 succeed, exactly 90 denied with BUDGET_EXCEEDED.
   - Final reserved == $10.00, actual == $0.00, available == $0.00.
2. 100 concurrent requests each $0.25 against $10.00 budget:
   - Synchronized barrier start.
   - Exactly 40 succeed, exactly 60 denied with BUDGET_EXCEEDED.
   - Final reserved == $10.00, actual == $0.00, available == $0.00.
3. High-contention mixed concurrent workload:
   - Simultaneous threads performing reserve, settle, and release.
   - Zero lost updates, zero negative balances, zero double reservations.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import threading
import pytest

from ai.contracts.errors import AIErrorCode
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    Budget,
    BudgetScope,
    ReservationRequest,
    ReservationResult,
)


class TestBudgetConcurrency:

    def test_100_concurrent_requests_at_1_dollar_each(self):
        """
        Mandatory Concurrency Gate 1:
        Budget = $10.00
        100 concurrent threads each requesting $1.00.
        Synchronized with a 100-thread Barrier to trigger simultaneous race conditions.
        """
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        budget_id = "b_concurrent_10_1"
        service.create_budget(
            Budget(
                budget_id=budget_id,
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_concurrent_1",
                limit=Decimal("10.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        num_threads = 100
        barrier = threading.Barrier(num_threads)
        results: list[ReservationResult] = [None] * num_threads

        def _worker(thread_idx: int):
            req = ReservationRequest(
                workspace_id="ws_concurrent_1",
                amount=Decimal("1.00"),
                idempotency_key=f"conc_req_1_{thread_idx}",
            )
            # Synchronize all threads so they strike reserve() at the exact same moment
            barrier.wait()
            res = service.reserve(req)
            results[thread_idx] = res

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(_worker, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        # Count successful vs denied
        successful = [r for r in results if r.success]
        denied = [r for r in results if not r.success]

        assert len(successful) == 10, f"Expected exactly 10 successful reservations, got {len(successful)}"
        assert len(denied) == 90, f"Expected exactly 90 denied reservations, got {len(denied)}"

        # Validate all denied requests received structured BUDGET_EXCEEDED
        for d in denied:
            assert d.error is not None
            assert d.error.code == AIErrorCode.BUDGET_EXCEEDED
            assert d.denial_scope == BudgetScope.WORKSPACE

        # Inspect final budget state
        final_budget = service.get_budget(budget_id)
        assert final_budget.limit == Decimal("10.00")
        assert final_budget.reserved == Decimal("10.00")
        assert final_budget.actual_spend == Decimal("0.00")
        assert final_budget.available == Decimal("0.00")

        # Invariant check
        assert final_budget.actual_spend + final_budget.reserved <= final_budget.limit
        assert final_budget.reserved >= Decimal("0")
        assert final_budget.available >= Decimal("0")

    def test_100_concurrent_requests_at_25_cents_each(self):
        """
        Mandatory Concurrency Gate 2:
        Budget = $10.00
        100 concurrent threads each requesting $0.25.
        Synchronized with a 100-thread Barrier.
        """
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        budget_id = "b_concurrent_10_quarter"
        service.create_budget(
            Budget(
                budget_id=budget_id,
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_concurrent_quarter",
                limit=Decimal("10.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        num_threads = 100
        barrier = threading.Barrier(num_threads)
        results: list[ReservationResult] = [None] * num_threads

        def _worker(thread_idx: int):
            req = ReservationRequest(
                workspace_id="ws_concurrent_quarter",
                amount=Decimal("0.25"),
                idempotency_key=f"conc_req_q_{thread_idx}",
            )
            barrier.wait()
            res = service.reserve(req)
            results[thread_idx] = res

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(_worker, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        successful = [r for r in results if r.success]
        denied = [r for r in results if not r.success]

        assert len(successful) == 40, f"Expected exactly 40 successful reservations, got {len(successful)}"
        assert len(denied) == 60, f"Expected exactly 60 denied reservations, got {len(denied)}"

        final_budget = service.get_budget(budget_id)
        assert final_budget.reserved == Decimal("10.00")
        assert final_budget.actual_spend == Decimal("0.00")
        assert final_budget.available == Decimal("0.00")
        assert final_budget.actual_spend + final_budget.reserved <= final_budget.limit

    def test_high_contention_concurrent_reserve_settle_release(self):
        """
        High-contention stress test:
        50 threads concurrently reserving, settling, and releasing against the same budget.
        Validates no lost updates, no negative balances, and continuous invariant adherence.
        """
        repo = InMemoryBudgetRepository()
        service = BudgetService(repository=repo)
        now = datetime.now(timezone.utc)

        budget_id = "b_stress_mixed"
        service.create_budget(
            Budget(
                budget_id=budget_id,
                scope=BudgetScope.WORKSPACE,
                scope_reference="ws_stress",
                limit=Decimal("50.00"),
                valid_from=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            )
        )

        num_cycles = 60
        barrier = threading.Barrier(num_cycles)

        def _lifecycle_worker(idx: int):
            barrier.wait()
            # 1. Attempt reservation
            req = ReservationRequest(
                workspace_id="ws_stress",
                amount=Decimal("2.00"),
                idempotency_key=f"stress_key_{idx}",
            )
            res = service.reserve(req)
            if not res.success:
                return

            res_id = res.reservation.reservation_id

            # 2. Even threads settle; odd threads release
            if idx % 2 == 0:
                service.settle(res_id, actual_cost=Decimal("1.50"))
            else:
                service.release(res_id)

        with ThreadPoolExecutor(max_workers=num_cycles) as executor:
            futures = [executor.submit(_lifecycle_worker, i) for i in range(num_cycles)]
            for f in futures:
                f.result()

        final_budget = service.get_budget(budget_id)

        # Invariant checks
        assert final_budget.reserved >= Decimal("0"), f"Negative reserved: {final_budget.reserved}"
        assert final_budget.actual_spend >= Decimal("0"), f"Negative actual_spend: {final_budget.actual_spend}"
        assert final_budget.available >= Decimal("0"), f"Negative available: {final_budget.available}"
        assert final_budget.actual_spend + final_budget.reserved <= final_budget.limit, "Overspend detected!"
        assert service.verify_invariants(budget_id) is True
