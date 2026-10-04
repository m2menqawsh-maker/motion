"""
ai/observability/repository.py
==============================
Abstract repository boundary for AI execution trace persistence (S27.19).

Invariants:
- Abstract interface only; never imports raw DB drivers or executes SQL in ai/* (ADR-004 DEC-01).
- Concrete implementations in scripts/core/ handle SQLite storage, indexing, and multi-tenant scoping.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ai.contracts.observability import AITrace, TraceSpanRecord


class TraceRepository(ABC):
    """Authoritative storage boundary for AI execution traces and discrete spans."""

    @abstractmethod
    def save_span(self, span: TraceSpanRecord) -> TraceSpanRecord:
        """Persists a sanitized execution span."""
        raise NotImplementedError

    @abstractmethod
    def get_trace(
        self,
        trace_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AITrace]:
        """Retrieves an aggregated trace by trace_id, scoped to workspace_id if provided."""
        raise NotImplementedError

    @abstractmethod
    def get_trace_for_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AITrace]:
        """Retrieves an aggregated trace for an AIRun."""
        raise NotImplementedError

    @abstractmethod
    def list_spans_for_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSpanRecord]:
        """Lists all discrete spans belonging to an AIRun."""
        raise NotImplementedError

    @abstractmethod
    def list_spans_for_project(
        self,
        project_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSpanRecord]:
        """Lists all discrete spans belonging to a project."""
        raise NotImplementedError
