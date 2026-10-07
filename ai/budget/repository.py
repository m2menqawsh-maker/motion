"""
ai/budget/repository.py
=======================
Repository boundaries and transactional persistence abstractions for Budget & Cost Engine (S27.5).

Persisted Entity Boundaries:
- Budgets (accounts for global, workspace, project, run, capability)
- ReservationRecords (active, settled, released, expired reservations)
- AccountingRecords (immutable append-only audit trail)

Status:
- Production persistence adapter: DEFERRED (SQLAlchemy / PostgreSQL AI Schema)
- In-memory transactional adapter: IMPLEMENTED (thread-safe, atomic compare-and-reserve, rollback support)

Invariants:
- Never imports raw SQL drivers (sqlite3, psycopg2, asyncpg, etc.) as mandated by S27.0 guards.
- All operations within an atomic transaction must commit together or roll back cleanly.
"""

from __future__ import annotations

import copy
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Tuple

from ai.budget.types import (
    AccountingRecord,
    Budget,
    BudgetScope,
    ReservationRecord,
    ReservationStatus,
)


class BudgetRepository(ABC):
    """
    Authoritative abstraction for budget and reservation persistence.
    """

    @abstractmethod
    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Retrieves a single budget by its canonical ID."""
        raise NotImplementedError

    @abstractmethod
    def get_budgets_for_scopes(self, scopes: List[Tuple[BudgetScope | str, str]]) -> List[Budget]:
        """Retrieves active budgets matching the specified scope pairs [(scope, reference), ...]."""
        raise NotImplementedError

    @abstractmethod
    def save_budget(self, budget: Budget) -> None:
        """Persists or updates a budget account."""
        raise NotImplementedError

    @abstractmethod
    def get_reservation(self, reservation_id: str) -> Optional[ReservationRecord]:
        """Retrieves a reservation by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_reservation_by_idempotency_key(self, idempotency_key: str) -> Optional[ReservationRecord]:
        """Retrieves a reservation by its idempotency deduplication key."""
        raise NotImplementedError

    @abstractmethod
    def save_reservation(self, reservation: ReservationRecord) -> None:
        """Persists or updates a reservation record."""
        raise NotImplementedError

    @abstractmethod
    def append_accounting_entry(self, entry: AccountingRecord) -> None:
        """Appends an immutable accounting event to the audit ledger."""
        raise NotImplementedError

    @abstractmethod
    def get_accounting_entries(
        self,
        reservation_id: Optional[str] = None,
        budget_id: Optional[str] = None,
    ) -> List[AccountingRecord]:
        """Queries accounting ledger entries with optional filters."""
        raise NotImplementedError

    @abstractmethod
    def get_active_expired_reservations(self, as_of: datetime) -> List[ReservationRecord]:
        """Finds all ACTIVE reservations whose expires_at is <= as_of."""
        raise NotImplementedError

    @abstractmethod
    @contextmanager
    def atomic_transaction(self) -> Iterator[None]:
        """Provides an atomic, transactional context with rollback on failure."""
        raise NotImplementedError


class _StagedState:
    """Internal unit-of-work container for staged modifications in an in-memory transaction."""
    def __init__(
        self,
        budgets: Dict[str, Budget],
        reservations: Dict[str, ReservationRecord],
        reservations_by_idempotency: Dict[str, str],
        accounting_ledger: List[AccountingRecord],
    ):
        self.budgets = dict(budgets)
        self.reservations = dict(reservations)
        self.reservations_by_idempotency = dict(reservations_by_idempotency)
        self.accounting_ledger = list(accounting_ledger)


class InMemoryBudgetRepository(BudgetRepository):
    """
    Thread-safe, transactional in-memory implementation of BudgetRepository.
    Guarantees atomic compare-and-reserve with complete rollback on failure.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._local = threading.local()
        self._budgets: Dict[str, Budget] = {}
        self._reservations: Dict[str, ReservationRecord] = {}
        self._reservations_by_idempotency: Dict[str, str] = {}
        self._accounting_ledger: List[AccountingRecord] = []

    def _get_active_tx(self) -> Optional[_StagedState]:
        return getattr(self._local, "tx", None)

    @contextmanager
    def atomic_transaction(self) -> Iterator[None]:
        """
        Acquires reentrant mutex and creates a staged unit-of-work.
        Commits all changes on clean exit, or rolls back entirely on exception.
        """
        with self._lock:
            parent_tx = self._get_active_tx()
            if parent_tx is not None:
                # Nested transaction within same thread; reuse active unit-of-work
                yield
                return

            staged = _StagedState(
                budgets=self._budgets,
                reservations=self._reservations,
                reservations_by_idempotency=self._reservations_by_idempotency,
                accounting_ledger=self._accounting_ledger,
            )
            self._local.tx = staged
            try:
                yield
                # Transaction succeeded: commit staged changes
                self._budgets = staged.budgets
                self._reservations = staged.reservations
                self._reservations_by_idempotency = staged.reservations_by_idempotency
                self._accounting_ledger = staged.accounting_ledger
            finally:
                self._local.tx = None

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        with self._lock:
            tx = self._get_active_tx()
            store = tx.budgets if tx else self._budgets
            return store.get(budget_id)

    def get_budgets_for_scopes(self, scopes: List[Tuple[BudgetScope | str, str]]) -> List[Budget]:
        with self._lock:
            tx = self._get_active_tx()
            store = tx.budgets if tx else self._budgets
            normalized_targets = {
                (s.value if isinstance(s, BudgetScope) else str(s), ref)
                for s, ref in scopes
            }
            results = []
            for b in store.values():
                b_scope_str = b.scope.value if isinstance(b.scope, BudgetScope) else str(b.scope)
                if (b_scope_str, b.scope_reference) in normalized_targets:
                    results.append(b)
            return results

    def save_budget(self, budget: Budget) -> None:
        with self._lock:
            tx = self._get_active_tx()
            if tx:
                tx.budgets[budget.budget_id] = budget
            else:
                self._budgets[budget.budget_id] = budget

    def get_reservation(self, reservation_id: str) -> Optional[ReservationRecord]:
        with self._lock:
            tx = self._get_active_tx()
            store = tx.reservations if tx else self._reservations
            return store.get(reservation_id)

    def get_reservation_by_idempotency_key(self, idempotency_key: str) -> Optional[ReservationRecord]:
        with self._lock:
            tx = self._get_active_tx()
            idempotency_map = tx.reservations_by_idempotency if tx else self._reservations_by_idempotency
            res_store = tx.reservations if tx else self._reservations
            res_id = idempotency_map.get(idempotency_key)
            if res_id:
                return res_store.get(res_id)
            return None

    def save_reservation(self, reservation: ReservationRecord) -> None:
        with self._lock:
            tx = self._get_active_tx()
            if tx:
                tx.reservations[reservation.reservation_id] = reservation
                tx.reservations_by_idempotency[reservation.idempotency_key] = reservation.reservation_id
            else:
                self._reservations[reservation.reservation_id] = reservation
                self._reservations_by_idempotency[reservation.idempotency_key] = reservation.reservation_id

    def append_accounting_entry(self, entry: AccountingRecord) -> None:
        with self._lock:
            tx = self._get_active_tx()
            if tx:
                tx.accounting_ledger.append(entry)
            else:
                self._accounting_ledger.append(entry)

    def get_accounting_entries(
        self,
        reservation_id: Optional[str] = None,
        budget_id: Optional[str] = None,
    ) -> List[AccountingRecord]:
        with self._lock:
            tx = self._get_active_tx()
            ledger = tx.accounting_ledger if tx else self._accounting_ledger
            results = ledger
            if reservation_id is not None:
                results = [e for e in results if e.reservation_id == reservation_id]
            if budget_id is not None:
                results = [e for e in results if e.budget_id == budget_id]
            return list(results)

    def get_active_expired_reservations(self, as_of: datetime) -> List[ReservationRecord]:
        with self._lock:
            tx = self._get_active_tx()
            res_store = tx.reservations if tx else self._reservations
            results = []
            for r in res_store.values():
                if r.status == ReservationStatus.ACTIVE and r.expires_at is not None and r.expires_at <= as_of:
                    results.append(r)
            return results
