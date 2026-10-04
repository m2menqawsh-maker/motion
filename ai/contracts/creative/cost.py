"""
ai/contracts/creative/cost.py
=============================
Authoritative contracts for Creative Intelligence Cost Observability,
Attribution, and Efficiency Hardening (S28-08C).

Invariants:
- Quality / Correctness first: Cost layer observes and flags; zero runtime mutation authority.
- No parallel cost ledger: strictly reuses and integrates with canonical S27 telemetry.
- Monetary amounts use StrictDecimal precision; binary floating-point authority is strictly banned.
- Explicit epistemic separation between ACTUAL, ESTIMATED, and UNKNOWN cost values.
- Multi-tenant isolation: all events and summaries are tenant-scoped.
- Data minimization: captures hashes, counts, and metrics without storing raw prompts or scripts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import Field, JsonValue

from ai.contracts.base import (
    AIContractModel,
    StrictDecimal,
    TzAwareDatetime,
    strict_enum,
)
from ai.contracts.observability import SpanType, TraceSpanRecord


class ThresholdProvenance(str, Enum):
    """Authority and epistemic status of an efficiency threshold or baseline."""
    CANONICAL_POLICY = "CANONICAL_POLICY"       # Enforced by platform architecture or explicit product policy (e.g. S28-06 tier progression)
    EMPIRICAL_BASELINE = "EMPIRICAL_BASELINE"   # Measured from representative production / benchmark workloads
    TEST_REFERENCE = "TEST_REFERENCE"           # Fixture reference assumption for tests and synthetic audit runs
    HEURISTIC = "HEURISTIC"                     # Diagnostic rule-of-thumb; purely advisory observation, never hard authority


ThresholdProvenanceEnum = strict_enum(ThresholdProvenance)


class CostProvenance(str, Enum):
    """Epistemic basis and certainty of a monetary cost figure."""
    ACTUAL = "ACTUAL"         # Directly reported by provider billing or authoritative invoice
    ESTIMATED = "ESTIMATED"   # Computed from measured tokens/units and registered rate cards
    UNKNOWN = "UNKNOWN"       # Unmeasured or non-monetized resource consumption (UNKNOWN != FREE)


CostProvenanceEnum = strict_enum(CostProvenance)


class EfficiencyFindingType(str, Enum):
    """Categories of detected waste or inefficiency in creative execution."""
    UNNECESSARY_PREMIUM_CALL = "UNNECESSARY_PREMIUM_CALL"
    DUPLICATE_PLANNING = "DUPLICATE_PLANNING"
    OVER_RETRIEVAL = "OVER_RETRIEVAL"
    UNNECESSARY_GENERATION = "UNNECESSARY_GENERATION"
    CREATE_ESCALATION_WITHOUT_REASON = "CREATE_ESCALATION_WITHOUT_REASON"
    HIGH_COST_CALL_OBSERVED = "HIGH_COST_CALL_OBSERVED"
    EXPENSIVE_REPEATED_FAILURE = "EXPENSIVE_REPEATED_FAILURE"
    INCOMPLETE_COST_COVERAGE = "INCOMPLETE_COST_COVERAGE"


EfficiencyFindingTypeEnum = strict_enum(EfficiencyFindingType)


class EfficiencySeverity(str, Enum):
    """Impact severity of an efficiency finding."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


EfficiencySeverityEnum = strict_enum(EfficiencySeverity)


class CreativeUsageEvent(AIContractModel):
    """
    Canonical fine-grained consumption and telemetry event for Creative operations.
    Can be converted to/from canonical S27 TraceSpanRecord to prevent duplicate ledgers.
    """
    event_id: str = Field(
        min_length=1,
        description="Unique usage event identifier",
    )
    workspace_id: str = Field(min_length=1, description="Tenant workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier")
    run_id: Optional[str] = Field(default=None, description="Creative run or evaluation run identifier")
    stage: Optional[str] = Field(default=None, description="Creative pipeline stage (e.g. INTENT, PLANNING, RETRIEVAL)")
    subsystem: Optional[str] = Field(default=None, description="Subsystem emitting telemetry (e.g. intent, narrative, style)")
    operation_type: str = Field(default="AI_COMPLETION", min_length=1, description="Operational classification")
    provider: Optional[str] = Field(default=None, description="Provider providing the capability (e.g. openai, gemini)")
    model: Optional[str] = Field(default=None, description="Underlying model identifier used")
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Input/prompt token count")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Output/completion token count")
    cached_input_tokens: Optional[int] = Field(default=None, ge=0, description="Tokens read from prompt cache")
    cache_hit: Optional[bool] = Field(default=None, description="Whether prompt cache was hit")
    request_count: int = Field(default=1, ge=0, description="Total API/RPC request count")
    generation_count: int = Field(default=0, ge=0, description="Media or template generation count")
    retrieval_items: int = Field(default=0, ge=0, description="Number of knowledge/asset/template items retrieved")
    latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Execution duration in milliseconds")
    cost_provenance: CostProvenanceEnum = Field(default=CostProvenance.ESTIMATED, description="Basis of cost calculation")
    estimated_cost: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Estimated monetary cost")
    actual_cost: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Authoritative actual cost")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")
    pricing_version: Optional[str] = Field(default=None, description="Model rate card / pricing version used")
    created_at: TzAwareDatetime = Field(
        description="UTC creation timestamp",
    )
    input_hash: Optional[str] = Field(
        default=None,
        description="Deterministic hash of operational inputs for duplicate detection (no raw prompts)",
    )
    details: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Sanitized non-sensitive diagnostic attributes",
    )

    @classmethod
    def create(
        cls,
        workspace_id: str,
        stage: Optional[str] = None,
        subsystem: Optional[str] = None,
        operation_type: str = "AI_COMPLETION",
        **kwargs: Any,
    ) -> CreativeUsageEvent:
        """Convenience constructor that generates unique event_id and timezone-aware created_at."""
        event_id = kwargs.pop("event_id", f"use_{uuid4().hex[:12]}")
        created_at = kwargs.pop("created_at", datetime.now(timezone.utc))
        return cls(
            event_id=event_id,
            workspace_id=workspace_id,
            stage=stage,
            subsystem=subsystem,
            operation_type=operation_type,
            created_at=created_at,
            **kwargs,
        )

    def to_span(self) -> TraceSpanRecord:
        """Translates usage event into canonical S27 TraceSpanRecord for persistent storage."""
        span_type = SpanType.PROVIDER_CALL
        if self.operation_type == "RETRIEVAL":
            span_type = SpanType.MEMORY_RETRIEVAL
        elif self.operation_type in ("MEDIA_GENERATION", "TEMPLATE_GENERATION"):
            span_type = SpanType.TOOL_CALL
        elif self.operation_type == "DETERMINISTIC_COMPILATION":
            span_type = SpanType.VALIDATION

        attrs: Dict[str, Any] = {
            "stage": self.stage,
            "subsystem": self.subsystem,
            "operation_type": self.operation_type,
            "cost_provenance": self.cost_provenance.value if hasattr(self.cost_provenance, "value") else str(self.cost_provenance),
            "currency": self.currency,
            "request_count": self.request_count,
            "generation_count": self.generation_count,
            "retrieval_items": self.retrieval_items,
        }
        if self.cached_input_tokens is not None:
            attrs["cached_input_tokens"] = self.cached_input_tokens
        if self.pricing_version:
            attrs["pricing_version"] = self.pricing_version
        if self.input_hash:
            attrs["input_hash"] = self.input_hash
        if self.details:
            attrs["details"] = self.details

        return TraceSpanRecord(
            span_id=self.event_id,
            trace_id=self.run_id or f"trc_{self.event_id}",
            parent_span_id=None,
            span_type=span_type,
            name=f"{self.stage or self.subsystem or 'operation'}:{self.operation_type}",
            run_id=self.run_id or "run_unspecified",
            step_id=None,
            activity_id=None,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            capability=self.subsystem,
            provider=self.provider,
            model=self.model,
            prompt_id=None,
            prompt_version=None,
            started_at=self.created_at,
            ended_at=None,
            duration_ms=self.latency_ms,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_hit=self.cache_hit,
            retry_count=0,
            fallback=False,
            estimated_cost=self.estimated_cost,
            actual_cost=self.actual_cost,
            quality_score=None,
            status="SUCCESS",
            error_code=None,
            attributes=attrs,
        )

    @classmethod
    def from_span(cls, span: TraceSpanRecord) -> CreativeUsageEvent:
        """Reconstructs CreativeUsageEvent from canonical S27 TraceSpanRecord."""
        attrs = span.attributes or {}
        provenance_str = attrs.get("cost_provenance", CostProvenance.ESTIMATED.value)
        try:
            provenance = CostProvenance(provenance_str)
        except ValueError:
            provenance = CostProvenance.ESTIMATED

        return cls(
            event_id=span.span_id,
            workspace_id=span.workspace_id,
            project_id=span.project_id,
            run_id=span.run_id,
            stage=attrs.get("stage"),
            subsystem=attrs.get("subsystem") or span.capability,
            operation_type=attrs.get("operation_type", "AI_COMPLETION"),
            provider=span.provider,
            model=span.model,
            input_tokens=span.input_tokens,
            output_tokens=span.output_tokens,
            cached_input_tokens=attrs.get("cached_input_tokens"),
            cache_hit=span.cache_hit,
            request_count=attrs.get("request_count", 1),
            generation_count=attrs.get("generation_count", 0),
            retrieval_items=attrs.get("retrieval_items", 0),
            latency_ms=span.duration_ms,
            cost_provenance=provenance,
            estimated_cost=span.estimated_cost,
            actual_cost=span.actual_cost,
            currency=attrs.get("currency", "USD"),
            pricing_version=attrs.get("pricing_version"),
            created_at=span.started_at,
            input_hash=attrs.get("input_hash"),
            details=attrs.get("details", {}),
        )


class CreativeProjectCostSummary(AIContractModel):
    """
    Authoritative aggregated cost and resource consumption summary for a project.
    Strictly distinguishes actual billed spend from calculated estimates.
    """
    workspace_id: str = Field(min_length=1, description="Tenant workspace identifier")
    project_id: str = Field(min_length=1, description="Project identifier")
    run_count: int = Field(default=0, ge=0, description="Total creative runs evaluated")
    planning_tokens: int = Field(default=0, ge=0, description="Tokens consumed during creative planning stages")
    retrieval_tokens: int = Field(default=0, ge=0, description="Tokens or volume consumed in retrieval stages")
    ai_calls: int = Field(default=0, ge=0, description="Total AI model invocations")
    generation_calls: int = Field(default=0, ge=0, description="Total media/template generation invocations")
    reuse_count: int = Field(default=0, ge=0, description="Total scenes resolved via REUSE tier")
    compose_count: int = Field(default=0, ge=0, description="Total scenes resolved via COMPOSE tier")
    create_count: int = Field(default=0, ge=0, description="Total scenes resolved via CREATE tier")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Cumulative latency in milliseconds")
    actual_cost: StrictDecimal = Field(default=Decimal("0.000000"), ge=Decimal(0), description="Actual settled spend")
    estimated_cost: StrictDecimal = Field(default=Decimal("0.000000"), ge=Decimal(0), description="Estimated calculated spend")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")
    pricing_version: Optional[str] = Field(default="2026.09.v1", description="Pricing schedule version applied")
    cost_coverage_complete: bool = Field(default=True, description="True if 100% of events have known cost provenance")
    known_cost_event_count: int = Field(default=0, ge=0, description="Events with known ACTUAL or ESTIMATED cost")
    unknown_cost_event_count: int = Field(default=0, ge=0, description="Events where cost is UNKNOWN (pricing unavailable)")
    tier_breakdown: Dict[str, JsonValue] = Field(default_factory=dict, description="Counts, rates, and costs by tier")
    stage_breakdown: Dict[str, JsonValue] = Field(default_factory=dict, description="Metrics broken down by pipeline stage")
    model_breakdown: Dict[str, JsonValue] = Field(default_factory=dict, description="Calls, tokens, and costs by model")
    provider_breakdown: Dict[str, JsonValue] = Field(default_factory=dict, description="Calls and costs by provider")
    status_breakdown: Dict[str, JsonValue] = Field(default_factory=dict, description="Cost split across successful, failed, and retried runs")


class EfficiencyFinding(AIContractModel):
    """
    Non-mutating diagnostic finding identifying waste, drift, or excessive expenditure.
    """
    finding_id: str = Field(
        min_length=1,
        description="Unique finding identifier",
    )
    workspace_id: str = Field(min_length=1, description="Tenant workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier")
    run_id: Optional[str] = Field(default=None, description="Associated run identifier")
    finding_type: EfficiencyFindingTypeEnum = Field(description="Classification of efficiency issue")
    severity: EfficiencySeverityEnum = Field(description="Severity impact level")
    observed_value: JsonValue = Field(description="Empirically measured metric or value")
    expected_bound: JsonValue = Field(description="Acceptable policy or baseline bound")
    evidence_refs: List[str] = Field(default_factory=list, description="IDs of spans or events proving the issue")
    summary: str = Field(min_length=1, description="Human-readable explanation of the finding")

    @classmethod
    def create(
        cls,
        workspace_id: str,
        finding_type: EfficiencyFindingType,
        severity: EfficiencySeverity,
        observed_value: JsonValue,
        expected_bound: JsonValue,
        summary: str,
        finding_id: Optional[str] = None,
        project_id: Optional[str] = None,
        run_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> EfficiencyFinding:
        """Convenience constructor that generates unique finding_id."""
        return cls(
            finding_id=finding_id or f"eff_{uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id=project_id,
            run_id=run_id,
            finding_type=finding_type,
            severity=severity,
            observed_value=observed_value,
            expected_bound=expected_bound,
            evidence_refs=evidence_refs or [],
            summary=summary,
        )


class CreativeCostAuditRun(AIContractModel):
    """
    Authoritative machine-readable report generated by the Creative Cost Audit CLI.
    """
    run_id: str = Field(min_length=1, description="Unique audit execution run identifier")
    policy_version: str = Field(default="S28-08C", description="Auditing policy version tag")
    projects_evaluated: int = Field(default=0, ge=0, description="Total distinct projects audited")
    usage_totals: Dict[str, JsonValue] = Field(default_factory=dict, description="System-wide aggregated usage totals")
    cost_totals: Dict[str, JsonValue] = Field(default_factory=dict, description="System-wide aggregated cost totals")
    latency_summary: Dict[str, JsonValue] = Field(default_factory=dict, description="Latency percentiles and totals")
    tier_distribution: Dict[str, JsonValue] = Field(default_factory=dict, description="REUSE / COMPOSE / CREATE distributions")
    cost_coverage_complete: bool = Field(default=True, description="Whether all audited events have known cost coverage")
    known_cost_event_count: int = Field(default=0, ge=0, description="Total audited events with known cost provenance")
    unknown_cost_event_count: int = Field(default=0, ge=0, description="Total audited events with UNKNOWN cost provenance")
    findings: List[EfficiencyFinding] = Field(default_factory=list, description="All efficiency findings detected")
    started_at: TzAwareDatetime = Field(description="Audit start timestamp")
    completed_at: TzAwareDatetime = Field(description="Audit completion timestamp")
    verdict: str = Field(default="PASS", description="Audit verdict (PASS, WARNING, FAIL)")
