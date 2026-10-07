"""
ai/observability/tracer.py
==========================
Hierarchical Trace Context and Span Engine for AI Operations (S27.19).

Invariants:
- Correlates run_id -> step_id -> activity_id -> trace_id -> span_id -> parent_span_id.
- Captures capability, model, prompt_version, token usage, cost, latency, cache, fallback, retry.
- All exported spans are sanitized through the redaction layer before persistence.
- Provides comprehensive E2E trace summary answering all diagnostic questions.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Generator, List, Optional

from ai.contracts.base import StrictDecimal, TzAwareDatetime
from ai.contracts.observability import AITrace, SpanType, TraceSpanRecord
from ai.observability.redaction import redact_telemetry_payload
from ai.observability.repository import TraceRepository
from scripts.core.ai_trace_repository import SQLTraceRepository


class SpanContext:
    """Active span builder and collector."""

    def __init__(
        self,
        span_id: str,
        trace_id: str,
        parent_span_id: Optional[str],
        span_type: SpanType,
        name: str,
        run_id: str,
        workspace_id: str,
        project_id: Optional[str] = None,
        step_id: Optional[str] = None,
        activity_id: Optional[str] = None,
    ):
        self.span_id = span_id
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.span_type = span_type
        self.name = name
        self.run_id = run_id
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.step_id = step_id
        self.activity_id = activity_id

        self.capability: Optional[str] = None
        self.provider: Optional[str] = None
        self.model: Optional[str] = None
        self.prompt_id: Optional[str] = None
        self.prompt_version: Optional[str] = None

        self.started_at: datetime = datetime.now(timezone.utc)
        self.ended_at: Optional[datetime] = None
        self.duration_ms: Optional[float] = None

        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None
        self.cache_hit: Optional[bool] = None
        self.retry_count: int = 0
        self.fallback: bool = False
        self.estimated_cost: Optional[Decimal] = None
        self.actual_cost: Optional[Decimal] = None
        self.quality_score: Optional[float] = None
        self.status: str = "SUCCESS"
        self.error_code: Optional[str] = None
        self.attributes: Dict[str, Any] = {}

    def set_capability(self, capability: str) -> None:
        self.capability = capability

    def set_model(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model

    def set_prompt(self, prompt_id: str, prompt_version: str) -> None:
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version

    def set_tokens(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def set_cache_hit(self, cache_hit: bool) -> None:
        self.cache_hit = cache_hit

    def set_retry(self, retry_count: int) -> None:
        self.retry_count = retry_count

    def set_fallback(self, fallback: bool) -> None:
        self.fallback = fallback

    def set_cost(self, estimated: Optional[Decimal], actual: Optional[Decimal] = None) -> None:
        self.estimated_cost = estimated
        self.actual_cost = actual if actual is not None else estimated

    def set_quality(self, score: float) -> None:
        self.quality_score = score

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_error(self, error_code: str, error_message: Optional[str] = None) -> None:
        self.status = "ERROR"
        self.error_code = error_code
        if error_message:
            self.attributes["error_message"] = error_message

    def finish(self) -> TraceSpanRecord:
        self.ended_at = datetime.now(timezone.utc)
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000.0

        # Sanitize attributes through redaction layer
        clean_attrs = redact_telemetry_payload(self.attributes)

        return TraceSpanRecord(
            span_id=self.span_id,
            trace_id=self.trace_id,
            parent_span_id=self.parent_span_id,
            span_type=self.span_type,
            name=self.name,
            run_id=self.run_id,
            step_id=self.step_id,
            activity_id=self.activity_id,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            capability=self.capability,
            provider=self.provider,
            model=self.model,
            prompt_id=self.prompt_id,
            prompt_version=self.prompt_version,
            started_at=self.started_at,
            ended_at=self.ended_at,
            duration_ms=round(self.duration_ms, 2) if self.duration_ms is not None else None,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_hit=self.cache_hit,
            retry_count=self.retry_count,
            fallback=self.fallback,
            estimated_cost=self.estimated_cost,
            actual_cost=self.actual_cost,
            quality_score=self.quality_score,
            status=self.status,
            error_code=self.error_code,
            attributes=clean_attrs,
        )


class AITracer:
    """
    Central tracer maintaining distributed trace context and span hierarchy for an AIRun.
    """

    def __init__(
        self,
        run_id: str,
        workspace_id: str,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        repository: Optional[TraceRepository] = None,
    ):
        self.run_id = run_id
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.trace_id = trace_id or f"trc_{uuid.uuid4().hex[:16]}"
        self._repository = repository or SQLTraceRepository()
        self._span_stack: List[str] = []
        self._recorded_spans: List[TraceSpanRecord] = []

    @contextlib.contextmanager
    def start_span(
        self,
        name: str,
        span_type: SpanType,
        step_id: Optional[str] = None,
        activity_id: Optional[str] = None,
    ) -> Generator[SpanContext, None, None]:
        parent_id = self._span_stack[-1] if self._span_stack else None
        span_id = f"spn_{uuid.uuid4().hex[:12]}"
        self._span_stack.append(span_id)

        ctx = SpanContext(
            span_id=span_id,
            trace_id=self.trace_id,
            parent_span_id=parent_id,
            span_type=span_type,
            name=name,
            run_id=self.run_id,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            step_id=step_id,
            activity_id=activity_id,
        )

        try:
            yield ctx
        except Exception as exc:
            ctx.set_error(error_code=type(exc).__name__, error_message=str(exc))
            raise
        finally:
            record = ctx.finish()
            self._recorded_spans.append(record)
            self._repository.save_span(record)
            self._span_stack.pop()

    def get_trace(self) -> AITrace:
        """Returns aggregated trace containing all spans."""
        persisted = self._repository.list_spans_for_run(self.run_id, self.workspace_id)
        return AITrace(
            trace_id=self.trace_id,
            run_id=self.run_id,
            workspace_id=self.workspace_id,
            spans=persisted or self._recorded_spans,
        )

    def summarize(self) -> Dict[str, Any]:
        """
        Answers the 9 canonical diagnostic observability questions:
        1. How much did the run cost?
        2. What capability was requested?
        3. Why was Model X selected?
        4. Did a cache hit occur?
        5. Did a fallback occur?
        6. How many retries occurred?
        7. Where was time spent?
        8. Which prompt version was used?
        9. Which artifact was produced?
        """
        spans = self._recorded_spans

        # 1. Total cost
        total_estimated = Decimal("0.00")
        total_actual = Decimal("0.00")
        for s in spans:
            if s.estimated_cost is not None:
                total_estimated += s.estimated_cost
            if s.actual_cost is not None:
                total_actual += s.actual_cost

        # 2. Capability
        capabilities = [s.capability for s in spans if s.capability]
        primary_capability = capabilities[0] if capabilities else None

        # 3. Model selection & routing reason
        route_spans = [s for s in spans if s.span_type == SpanType.MODEL_ROUTE]
        selected_model = None
        route_reason = None
        if route_spans:
            selected_model = route_spans[0].model
            route_reason = route_spans[0].attributes.get("routing_reason") or route_spans[0].attributes.get("reason_code")

        # 4. Cache hit
        cache_spans = [s for s in spans if s.span_type == SpanType.CACHE_LOOKUP]
        cache_hit = any(s.cache_hit for s in cache_spans) if cache_spans else False

        # 5. Fallback occurred
        fallback_occurred = any(s.fallback for s in spans)

        # 6. Retry count
        total_retries = sum(s.retry_count for s in spans)

        # 7. Latency breakdown
        latency_breakdown = {s.name: s.duration_ms for s in spans if s.duration_ms is not None}
        total_duration = sum(latency_breakdown.values())

        # 8. Prompt version
        prompt_spans = [s for s in spans if s.prompt_id or s.prompt_version]
        prompt_id = prompt_spans[0].prompt_id if prompt_spans else None
        prompt_version = prompt_spans[0].prompt_version if prompt_spans else None

        # 9. Artifact produced
        artifact_spans = [s for s in spans if s.span_type == SpanType.ARTIFACT_PERSISTENCE]
        output_artifact = artifact_spans[0].attributes.get("artifact_ref") if artifact_spans else None

        return {
            "run_cost": {
                "estimated_cost": str(total_estimated),
                "actual_cost": str(total_actual),
            },
            "requested_capability": primary_capability,
            "model_selection": {
                "model": selected_model,
                "reason": route_reason,
            },
            "cache_hit": cache_hit,
            "fallback_occurred": fallback_occurred,
            "retry_count": total_retries,
            "time_spent_ms": {
                "total_duration_ms": round(total_duration, 2),
                "spans": latency_breakdown,
            },
            "prompt_used": {
                "prompt_id": prompt_id,
                "prompt_version": prompt_version,
            },
            "artifact_produced": output_artifact,
        }
