"""
scripts/core/ai_trace_repository.py
===================================
SQLite-backed persistent implementation of TraceRepository (S27.19).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ to satisfy S27.0 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, and transactions.
- Enforces multi-tenant isolation and strict span correlation.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ai.contracts.observability import AITrace, SpanType, TraceSpanRecord
from ai.observability.repository import TraceRepository
from scripts.core.database import DatabaseEngine, get_database_engine


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_trace_spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    span_type TEXT NOT NULL,
    name TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_id TEXT,
    activity_id TEXT,
    workspace_id TEXT NOT NULL,
    project_id TEXT,
    capability TEXT,
    provider TEXT,
    model TEXT,
    prompt_id TEXT,
    prompt_version TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_hit INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    fallback INTEGER NOT NULL DEFAULT 0,
    estimated_cost TEXT,
    actual_cost TEXT,
    quality_score REAL,
    status TEXT NOT NULL DEFAULT 'SUCCESS',
    error_code TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ai_trace_spans_run ON ai_trace_spans(run_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_ai_trace_spans_trace ON ai_trace_spans(trace_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_ai_trace_spans_project ON ai_trace_spans(project_id, workspace_id);
"""


class SQLTraceRepository(TraceRepository):
    """Production persistent storage for AI telemetry traces and spans."""

    def __init__(self, engine: Optional[DatabaseEngine] = None):
        self.engine = engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.engine.transaction("IMMEDIATE") as conn:
            for statement in SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    @staticmethod
    def _row_to_span(row: Any) -> TraceSpanRecord:
        data: Dict[str, Any] = dict(row)
        attrs = json.loads(data["attributes_json"]) if data.get("attributes_json") else {}
        cache_hit = bool(data["cache_hit"]) if data.get("cache_hit") is not None else None
        fallback = bool(data["fallback"]) if data.get("fallback") is not None else False

        return TraceSpanRecord(
            span_id=data["span_id"],
            trace_id=data["trace_id"],
            parent_span_id=data.get("parent_span_id"),
            span_type=SpanType(data["span_type"]),
            name=data["name"],
            run_id=data["run_id"],
            step_id=data.get("step_id"),
            activity_id=data.get("activity_id"),
            workspace_id=data["workspace_id"],
            project_id=data.get("project_id"),
            capability=data.get("capability"),
            provider=data.get("provider"),
            model=data.get("model"),
            prompt_id=data.get("prompt_id"),
            prompt_version=data.get("prompt_version"),
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            duration_ms=data.get("duration_ms"),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            cache_hit=cache_hit,
            retry_count=data.get("retry_count", 0),
            fallback=fallback,
            estimated_cost=Decimal(data["estimated_cost"]) if data.get("estimated_cost") else None,
            actual_cost=Decimal(data["actual_cost"]) if data.get("actual_cost") else None,
            quality_score=data.get("quality_score"),
            status=data.get("status", "SUCCESS"),
            error_code=data.get("error_code"),
            attributes=attrs,
        )

    def save_span(self, span: TraceSpanRecord) -> TraceSpanRecord:
        attrs_json = json.dumps(span.attributes)
        cache_hit_val = 1 if span.cache_hit is True else (0 if span.cache_hit is False else None)
        fallback_val = 1 if span.fallback else 0

        with self.engine.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ai_trace_spans (
                    span_id, trace_id, parent_span_id, span_type, name,
                    run_id, step_id, activity_id, workspace_id, project_id,
                    capability, provider, model, prompt_id, prompt_version,
                    started_at, ended_at, duration_ms, input_tokens, output_tokens,
                    cache_hit, retry_count, fallback, estimated_cost, actual_cost,
                    quality_score, status, error_code, attributes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.span_id,
                    span.trace_id,
                    span.parent_span_id,
                    span.span_type.value,
                    span.name,
                    span.run_id,
                    span.step_id,
                    span.activity_id,
                    span.workspace_id,
                    span.project_id,
                    span.capability,
                    span.provider,
                    span.model,
                    span.prompt_id,
                    span.prompt_version,
                    span.started_at.isoformat(),
                    span.ended_at.isoformat() if span.ended_at else None,
                    span.duration_ms,
                    span.input_tokens,
                    span.output_tokens,
                    cache_hit_val,
                    span.retry_count,
                    fallback_val,
                    str(span.estimated_cost) if span.estimated_cost is not None else None,
                    str(span.actual_cost) if span.actual_cost is not None else None,
                    span.quality_score,
                    span.status,
                    span.error_code,
                    attrs_json,
                ),
            )
        return span

    def list_spans_for_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSpanRecord]:
        conn = self.engine.get_connection()
        try:
            if workspace_id:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE run_id = ? AND workspace_id = ? ORDER BY started_at ASC",
                    (run_id, workspace_id),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE run_id = ? ORDER BY started_at ASC",
                    (run_id,),
                )
            rows = cur.fetchall()
            return [self._row_to_span(r) for r in rows]
        finally:
            conn.close()

    def list_spans_for_project(
        self,
        project_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[TraceSpanRecord]:
        conn = self.engine.get_connection()
        try:
            if workspace_id:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE project_id = ? AND workspace_id = ? ORDER BY started_at ASC",
                    (project_id, workspace_id),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE project_id = ? ORDER BY started_at ASC",
                    (project_id,),
                )
            rows = cur.fetchall()
            return [self._row_to_span(r) for r in rows]
        finally:
            conn.close()

    def get_trace_for_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AITrace]:
        spans = self.list_spans_for_run(run_id, workspace_id)
        if not spans:
            return None
        return AITrace(
            trace_id=spans[0].trace_id,
            run_id=run_id,
            workspace_id=spans[0].workspace_id,
            spans=spans,
        )

    def get_trace(
        self,
        trace_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AITrace]:
        conn = self.engine.get_connection()
        try:
            if workspace_id:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE trace_id = ? AND workspace_id = ? ORDER BY started_at ASC",
                    (trace_id, workspace_id),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM ai_trace_spans WHERE trace_id = ? ORDER BY started_at ASC",
                    (trace_id,),
                )
            rows = cur.fetchall()
            if not rows:
                return None
            spans = [self._row_to_span(r) for r in rows]
            return AITrace(
                trace_id=trace_id,
                run_id=spans[0].run_id,
                workspace_id=spans[0].workspace_id,
                spans=spans,
            )
        finally:
            conn.close()
