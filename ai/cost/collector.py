"""
ai/cost/collector.py
====================
Usage Telemetry Collector & Attribution Service for Creative Intelligence (S28-08C).

Invariants:
- Zero second database: Strictly reuses and persists to canonical S27 TraceRepository.
- Multi-tenant isolation: Strictly verifies TrustedTenantContext.
    * Workspace A cannot read or aggregate Workspace B data.
    * Cross-tenant and unpermitted project queries fail closed with TenantAuthorizationError.
- No sensitive data archiving: Does not persist raw prompts, scripts, or provider keys.
- Strict Decimal monetary arithmetic.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from ai.contracts.creative.cost import (
    CostProvenance,
    CreativeProjectCostSummary,
    CreativeUsageEvent,
)
from ai.cost.errors import TenantAuthorizationError
from ai.memory.models import TrustedTenantContext
from ai.observability.repository import TraceRepository
from scripts.core.ai_trace_repository import SQLTraceRepository

logger = logging.getLogger(__name__)
QUANTIZE_PRECISION = Decimal("0.000001")

PLANNING_STAGES: Set[str] = {
    "INTENT",
    "RECIPE_SELECTION",
    "SKILL_ROUTING",
    "NARRATIVE",
    "TASTE",
    "CREATIVE_PLANNING",
    "TIER_DECISION",
    "STYLE_RESOLUTION",
    "PLANNING",
}


class CreativeUsageCollector:
    """
    Authoritative collection, query, and attribution service for creative usage events.
    """

    def __init__(self, trace_repository: Optional[TraceRepository] = None) -> None:
        self.trace_repo = trace_repository or SQLTraceRepository()

    def record_event(
        self,
        context: TrustedTenantContext,
        event: CreativeUsageEvent,
    ) -> CreativeUsageEvent:
        """
        Records a fine-grained CreativeUsageEvent into canonical telemetry.
        Enforces tenant and project access boundaries.
        """
        # Multi-tenant isolation check
        if context.workspace_id != event.workspace_id:
            raise TenantAuthorizationError(
                f"Cross-tenant event rejection: caller is in workspace '{context.workspace_id}', "
                f"but event claims workspace '{event.workspace_id}'."
            )

        if event.project_id and not context.can_access_project(event.project_id):
            raise TenantAuthorizationError(
                f"Project boundary violation: workspace '{context.workspace_id}' "
                f"is not authorized to record events for project '{event.project_id}'."
            )

        # Convert to canonical TraceSpanRecord and persist to trace repository
        span = event.to_span()
        self.trace_repo.save_span(span)
        return event

    def list_events_for_project(
        self,
        context: TrustedTenantContext,
        project_id: str,
    ) -> List[CreativeUsageEvent]:
        """
        Retrieves all CreativeUsageEvents for a project within caller's workspace.
        Fails closed on unauthorized project access.
        """
        if not context.can_access_project(project_id):
            raise TenantAuthorizationError(
                f"Cross-tenant read denied: workspace '{context.workspace_id}' "
                f"cannot access project '{project_id}'."
            )

        spans = self.trace_repo.list_spans_for_project(
            project_id=project_id,
            workspace_id=context.workspace_id,
        )
        return [CreativeUsageEvent.from_span(s) for s in spans]

    def list_events_for_run(
        self,
        context: TrustedTenantContext,
        run_id: str,
    ) -> List[CreativeUsageEvent]:
        """
        Retrieves all CreativeUsageEvents for a creative or AI run.
        """
        spans = self.trace_repo.list_spans_for_run(
            run_id=run_id,
            workspace_id=context.workspace_id,
        )
        events: List[CreativeUsageEvent] = []
        for s in spans:
            if s.project_id and not context.can_access_project(s.project_id):
                continue
            events.append(CreativeUsageEvent.from_span(s))
        return events

    def summarize_project(
        self,
        context: TrustedTenantContext,
        project_id: str,
    ) -> CreativeProjectCostSummary:
        """
        Synthesizes authoritative CreativeProjectCostSummary for a given project.
        Enforces tenant isolation, aggregates tokens, AI calls, generation calls,
        tier distributions, stage breakdowns, and strictly distinguishes actual from estimated costs.
        """
        events = self.list_events_for_project(context=context, project_id=project_id)

        distinct_runs: Set[str] = set()
        planning_tokens = 0
        retrieval_tokens = 0
        ai_calls = 0
        generation_calls = 0
        reuse_count = 0
        compose_count = 0
        create_count = 0
        total_latency_ms = 0.0

        actual_cost_total = Decimal("0")
        estimated_cost_total = Decimal("0")
        known_cost_events = 0
        unknown_cost_events = 0

        # Breakdowns
        tier_costs: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        tier_counts: Dict[str, int] = defaultdict(int)

        stage_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": 0.0,
                "cost": Decimal("0"),
            }
        )

        model_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": Decimal("0"),
            }
        )

        provider_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "cost": Decimal("0"),
            }
        )

        status_costs: Dict[str, Decimal] = {
            "SUCCESS": Decimal("0"),
            "FAILED": Decimal("0"),
            "RETRY": Decimal("0"),
        }

        pricing_version: Optional[str] = None

        for ev in events:
            if ev.run_id:
                distinct_runs.add(ev.run_id)

            if ev.pricing_version and not pricing_version:
                pricing_version = ev.pricing_version

            ev_in = ev.input_tokens or 0
            ev_out = ev.output_tokens or 0
            ev_tokens = ev_in + ev_out
            ev_latency = ev.latency_ms or 0.0
            total_latency_ms += ev_latency

            # Stage accounting
            stg = (ev.stage or ev.subsystem or "UNSPECIFIED").upper()
            if stg in PLANNING_STAGES or "PLAN" in stg:
                planning_tokens += ev_tokens

            if stg in ("KNOWLEDGE_RETRIEVAL", "RETRIEVAL") or ev.operation_type == "RETRIEVAL":
                retrieval_tokens += ev_tokens or ev.retrieval_items

            if ev.operation_type in ("AI_COMPLETION", "COMPLETION") or ev.model:
                ai_calls += ev.request_count

            if ev.generation_count > 0 or ev.operation_type in ("MEDIA_GENERATION", "TEMPLATE_GENERATION"):
                generation_calls += (ev.generation_count or ev.request_count)

            # Costs & Provenance
            ev_actual = ev.actual_cost or Decimal("0")
            ev_est = ev.estimated_cost or Decimal("0")
            actual_cost_total += ev_actual
            estimated_cost_total += ev_est

            if ev.cost_provenance == CostProvenance.UNKNOWN or (ev.actual_cost is None and ev.estimated_cost is None and ev.cost_provenance != CostProvenance.ACTUAL):
                unknown_cost_events += 1
            else:
                known_cost_events += 1

            # Tier metrics from details or stage
            details = ev.details or {}
            tier_val = details.get("tier") or details.get("selected_tier")
            if not tier_val and ev.stage == "TIER_DECISION":
                tier_val = details.get("decision")
            if tier_val:
                t_str = str(tier_val).upper()
                if "REUSE" in t_str:
                    reuse_count += 1
                    tier_counts["REUSE"] += 1
                    tier_costs["REUSE"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))
                elif "COMPOSE" in t_str:
                    compose_count += 1
                    tier_counts["COMPOSE"] += 1
                    tier_costs["COMPOSE"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))
                elif "CREATE" in t_str:
                    create_count += 1
                    tier_counts["CREATE"] += 1
                    tier_costs["CREATE"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))

            # Breakdowns aggregation
            stage_metrics[stg]["calls"] += ev.request_count
            stage_metrics[stg]["input_tokens"] += ev_in
            stage_metrics[stg]["output_tokens"] += ev_out
            stage_metrics[stg]["latency_ms"] += round(ev_latency, 2)
            stage_metrics[stg]["cost"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))

            if ev.model:
                model_metrics[ev.model]["calls"] += ev.request_count
                model_metrics[ev.model]["input_tokens"] += ev_in
                model_metrics[ev.model]["output_tokens"] += ev_out
                model_metrics[ev.model]["cost"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))

            if ev.provider:
                provider_metrics[ev.provider]["calls"] += ev.request_count
                provider_metrics[ev.provider]["cost"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))

            # Status breakdown
            is_retry = bool(details.get("is_retry") or details.get("retry_count", 0) > 0)
            status_val = str(details.get("status", "SUCCESS")).upper()
            if is_retry:
                status_costs["RETRY"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))
            elif "FAIL" in status_val or "ERROR" in status_val:
                status_costs["FAILED"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))
            else:
                status_costs["SUCCESS"] += (ev.actual_cost or ev.estimated_cost or Decimal("0"))

        total_scenes = reuse_count + compose_count + create_count

        tier_breakdown: Dict[str, Any] = {
            "REUSE": {
                "count": reuse_count,
                "rate": round(reuse_count / max(1, total_scenes), 4) if total_scenes > 0 else 0.0,
                "cost": str(tier_costs["REUSE"].quantize(QUANTIZE_PRECISION)),
                "avg_cost": str((tier_costs["REUSE"] / max(1, reuse_count)).quantize(QUANTIZE_PRECISION)) if reuse_count > 0 else "0.000000",
            },
            "COMPOSE": {
                "count": compose_count,
                "rate": round(compose_count / max(1, total_scenes), 4) if total_scenes > 0 else 0.0,
                "cost": str(tier_costs["COMPOSE"].quantize(QUANTIZE_PRECISION)),
                "avg_cost": str((tier_costs["COMPOSE"] / max(1, compose_count)).quantize(QUANTIZE_PRECISION)) if compose_count > 0 else "0.000000",
            },
            "CREATE": {
                "count": create_count,
                "rate": round(create_count / max(1, total_scenes), 4) if total_scenes > 0 else 0.0,
                "cost": str(tier_costs["CREATE"].quantize(QUANTIZE_PRECISION)),
                "avg_cost": str((tier_costs["CREATE"] / max(1, create_count)).quantize(QUANTIZE_PRECISION)) if create_count > 0 else "0.000000",
            },
        }

        stage_breakdown: Dict[str, Any] = {
            k: {
                "calls": v["calls"],
                "input_tokens": v["input_tokens"],
                "output_tokens": v["output_tokens"],
                "latency_ms": round(v["latency_ms"], 2),
                "cost": str(v["cost"].quantize(QUANTIZE_PRECISION)),
            }
            for k, v in stage_metrics.items()
        }

        model_breakdown: Dict[str, Any] = {
            k: {
                "calls": v["calls"],
                "input_tokens": v["input_tokens"],
                "output_tokens": v["output_tokens"],
                "cost": str(v["cost"].quantize(QUANTIZE_PRECISION)),
            }
            for k, v in model_metrics.items()
        }

        provider_breakdown: Dict[str, Any] = {
            k: {
                "calls": v["calls"],
                "cost": str(v["cost"].quantize(QUANTIZE_PRECISION)),
            }
            for k, v in provider_metrics.items()
        }

        status_breakdown: Dict[str, Any] = {
            "successful_runs_cost": str(status_costs["SUCCESS"].quantize(QUANTIZE_PRECISION)),
            "failed_runs_cost": str(status_costs["FAILED"].quantize(QUANTIZE_PRECISION)),
            "retried_runs_cost": str(status_costs["RETRY"].quantize(QUANTIZE_PRECISION)),
        }

        return CreativeProjectCostSummary(
            workspace_id=context.workspace_id,
            project_id=project_id,
            run_count=len(distinct_runs),
            planning_tokens=planning_tokens,
            retrieval_tokens=retrieval_tokens,
            ai_calls=ai_calls,
            generation_calls=generation_calls,
            reuse_count=reuse_count,
            compose_count=compose_count,
            create_count=create_count,
            total_latency_ms=round(total_latency_ms, 2),
            actual_cost=actual_cost_total.quantize(QUANTIZE_PRECISION),
            estimated_cost=estimated_cost_total.quantize(QUANTIZE_PRECISION),
            currency="USD",
            pricing_version=pricing_version or "2026.09.v1",
            cost_coverage_complete=(unknown_cost_events == 0),
            known_cost_event_count=known_cost_events,
            unknown_cost_event_count=unknown_cost_events,
            tier_breakdown=tier_breakdown,
            stage_breakdown=stage_breakdown,
            model_breakdown=model_breakdown,
            provider_breakdown=provider_breakdown,
            status_breakdown=status_breakdown,
        )
