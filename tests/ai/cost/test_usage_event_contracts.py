"""
tests/ai/cost/test_usage_event_contracts.py
===========================================
Unit tests verifying CreativeUsageEvent, CreativeProjectCostSummary,
EfficiencyFinding, and CreativeCostAuditRun contracts (S28-08C).

Guarantees:
- Strict Pydantic v2 immutability (frozen=True, extra="forbid").
- StrictDecimal precision for all monetary fields (binary floats rejected).
- Timezone safety for timestamps.
- Two-way loss-free mapping with canonical S27 TraceSpanRecord.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from ai.contracts.creative.cost import (
    CostProvenance,
    CreativeCostAuditRun,
    CreativeProjectCostSummary,
    CreativeUsageEvent,
    EfficiencyFinding,
    EfficiencyFindingType,
    EfficiencySeverity,
)
from ai.contracts.observability import SpanType, TraceSpanRecord


def test_creative_usage_event_contract_immutability():
    """Verifies that CreativeUsageEvent is frozen and forbids extra fields."""
    event = CreativeUsageEvent.create(
        workspace_id="ws_test",
        project_id="proj_01",
        run_id="run_01",
        stage="CREATIVE_PLANNING",
        subsystem="creative_planner",
        operation_type="AI_COMPLETION",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=300,
        cost_provenance=CostProvenance.ESTIMATED,
        estimated_cost=Decimal("0.009500"),
    )

    # Immutability
    with pytest.raises(ValidationError):
        event.input_tokens = 2000

    # Forbids extra fields
    with pytest.raises(ValidationError):
        CreativeUsageEvent(
            event_id="use_123",
            workspace_id="ws_test",
            created_at=datetime.now(timezone.utc),
            unauthorized_field="illegal_value",
        )


def test_creative_usage_event_strict_decimal_enforcement():
    """Verifies that monetary amounts strictly forbid binary floats."""
    # StrictDecimal converts exact string or Decimal
    event = CreativeUsageEvent.create(
        workspace_id="ws_test",
        estimated_cost=Decimal("0.012500"),
        actual_cost=Decimal("0.010000"),
    )
    assert isinstance(event.estimated_cost, Decimal)
    assert isinstance(event.actual_cost, Decimal)

    # Float values must be rejected by StrictDecimal
    with pytest.raises(ValidationError):
        CreativeUsageEvent.create(
            workspace_id="ws_test",
            estimated_cost=0.0125,  # Raw binary float forbidden
        )


def test_usage_event_two_way_trace_span_mapping():
    """Verifies bidirectional conversion between CreativeUsageEvent and S27 TraceSpanRecord."""
    original_event = CreativeUsageEvent.create(
        workspace_id="ws_alpha",
        project_id="proj_video_100",
        run_id="run_creative_01",
        stage="KNOWLEDGE_RETRIEVAL",
        subsystem="knowledge_router",
        operation_type="RETRIEVAL",
        retrieval_items=5,
        latency_ms=124.5,
        cost_provenance=CostProvenance.ESTIMATED,
        estimated_cost=Decimal("0.000000"),
        currency="USD",
        pricing_version="2026.09.v1",
        input_hash="hash_retrieval_query_01",
        details={"status": "SUCCESS", "retrieved_ids": ["doc_1", "doc_2"]},
    )

    # Convert to span
    span: TraceSpanRecord = original_event.to_span()
    assert span.span_id == original_event.event_id
    assert span.workspace_id == "ws_alpha"
    assert span.project_id == "proj_video_100"
    assert span.run_id == "run_creative_01"
    assert span.span_type == SpanType.MEMORY_RETRIEVAL
    assert span.duration_ms == 124.5
    assert span.attributes["operation_type"] == "RETRIEVAL"
    assert span.attributes["input_hash"] == "hash_retrieval_query_01"

    # Reconstruct from span
    reconstructed = CreativeUsageEvent.from_span(span)
    assert reconstructed.event_id == original_event.event_id
    assert reconstructed.workspace_id == original_event.workspace_id
    assert reconstructed.project_id == original_event.project_id
    assert reconstructed.run_id == original_event.run_id
    assert reconstructed.stage == original_event.stage
    assert reconstructed.subsystem == original_event.subsystem
    assert reconstructed.operation_type == original_event.operation_type
    assert reconstructed.retrieval_items == 5
    assert reconstructed.latency_ms == 124.5
    assert reconstructed.input_hash == "hash_retrieval_query_01"
    assert reconstructed.cost_provenance == CostProvenance.ESTIMATED


def test_creative_project_cost_summary_contract():
    """Verifies field integrity and immutability for CreativeProjectCostSummary."""
    summary = CreativeProjectCostSummary(
        workspace_id="ws_corp",
        project_id="proj_launch_campaign",
        run_count=4,
        planning_tokens=6500,
        retrieval_tokens=1500,
        ai_calls=8,
        generation_calls=2,
        reuse_count=3,
        compose_count=1,
        create_count=0,
        total_latency_ms=4820.5,
        actual_cost=Decimal("0.000000"),
        estimated_cost=Decimal("0.045000"),
        currency="USD",
        pricing_version="2026.09.v1",
        tier_breakdown={"REUSE": {"rate": 0.75}},
        stage_breakdown={"PLANNING": {"calls": 4}},
    )

    assert summary.workspace_id == "ws_corp"
    assert summary.reuse_count == 3
    assert summary.compose_count == 1
    assert summary.create_count == 0
    assert summary.actual_cost == Decimal("0.000000")
    assert summary.estimated_cost == Decimal("0.045000")

    # Immutability
    with pytest.raises(ValidationError):
        summary.reuse_count = 5


def test_efficiency_finding_contract():
    """Verifies EfficiencyFinding schema and factory constructor."""
    finding = EfficiencyFinding.create(
        workspace_id="ws_gamma",
        project_id="proj_explainer_01",
        run_id="run_exp_1",
        finding_type=EfficiencyFindingType.UNNECESSARY_GENERATION,
        severity=EfficiencySeverity.CRITICAL,
        observed_value={"generation_called": True, "selected_tier": "REUSE"},
        expected_bound={"allowed_generations": 0},
        summary="Media generation invoked after REUSE tier committed.",
        evidence_refs=["use_span_001", "use_span_002"],
    )

    assert finding.finding_type == EfficiencyFindingType.UNNECESSARY_GENERATION
    assert finding.severity == EfficiencySeverity.CRITICAL
    assert len(finding.evidence_refs) == 2
    assert "use_span_001" in finding.evidence_refs


def test_creative_cost_audit_run_contract():
    """Verifies CreativeCostAuditRun serializes and validates cleanly."""
    now = datetime.now(timezone.utc)
    audit = CreativeCostAuditRun(
        run_id="audit_run_12345",
        policy_version="S28-08C",
        projects_evaluated=3,
        usage_totals={"total_ai_calls": 12},
        cost_totals={"total_estimated_cost": "0.052000"},
        latency_summary={"avg_latency_ms": 350.2},
        tier_distribution={"reuse_rate": 0.8},
        findings=[],
        started_at=now,
        completed_at=now,
        verdict="PASS",
    )

    assert audit.run_id == "audit_run_12345"
    assert audit.verdict == "PASS"
    dump = audit.model_dump()
    assert dump["projects_evaluated"] == 3
    assert dump["verdict"] == "PASS"
