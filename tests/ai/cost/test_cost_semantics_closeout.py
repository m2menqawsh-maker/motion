"""
tests/ai/cost/test_cost_semantics_closeout.py
============================================
Closeout verification tests for S28-08C:
1. UNKNOWN cost cannot masquerade as free (UNKNOWN != FREE).
2. Partial cost coverage is transparently tracked and reported.
3. Heuristic thresholds (e.g. over-retrieval > 15) remain advisory warnings and cannot become hard authority.
4. Canonical policy thresholds preserve CRITICAL severity.
5. Premium model findings require canonical ModelRegistry policy evidence (no arbitrary accusations).
"""

from __future__ import annotations

import tempfile
from decimal import Decimal
from datetime import datetime, timezone
import pytest

from ai.contracts.creative.cost import (
    CostProvenance,
    CreativeUsageEvent,
    EfficiencyFindingType,
    EfficiencySeverity,
    ThresholdProvenance,
)
from ai.cost.accounting import CreativeCostEstimator
from ai.cost.analyzer import CreativeEfficiencyAnalyzer
from ai.cost.baseline import CANONICAL_EFFICIENCY_BASELINES, FormatBaseline
from ai.cost.collector import CreativeUsageCollector
from ai.memory.models import TrustedTenantContext
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def temp_collector():
    temp_db = tempfile.mktemp(suffix=".db")
    engine = DatabaseEngine(db_url=f"sqlite:///{temp_db}")
    trace_repo = SQLTraceRepository(engine=engine)
    return CreativeUsageCollector(trace_repository=trace_repo)


@pytest.fixture
def tenant_ctx():
    return TrustedTenantContext(
        workspace_id="ws_closeout_test",
        permitted_project_ids=["proj_closeout_01"],
    )


@pytest.fixture
def analyzer():
    return CreativeEfficiencyAnalyzer()


def test_unknown_cost_is_not_treated_as_free(temp_collector, tenant_ctx):
    """
    Guarantees: UNKNOWN != FREE.
    When a model has no pricing card, cost is recorded as 0 for aggregation,
    but provenance is marked UNKNOWN and cost_coverage_complete is set to False.
    """
    estimator = CreativeCostEstimator()
    # Unregistered model
    cost, version, prov = CreativeCostEstimator.compute_cost(
        "unregistered-frontier-model", input_tokens=1000, output_tokens=500
    )
    assert prov == CostProvenance.UNKNOWN
    assert cost is None

    ev = CreativeUsageEvent.create(
        workspace_id=tenant_ctx.workspace_id,
        project_id="proj_closeout_01",
        run_id="run_01",
        stage="CREATIVE_PLANNING",
        model="unregistered-frontier-model",
        input_tokens=1000,
        output_tokens=500,
        cost_provenance=prov,
        estimated_cost=cost,
    )
    temp_collector.record_event(tenant_ctx, ev)

    summary = temp_collector.summarize_project(tenant_ctx, "proj_closeout_01")
    assert summary.cost_coverage_complete is False
    assert summary.unknown_cost_event_count == 1
    assert summary.known_cost_event_count == 0
    # Even though estimated_cost is 0, coverage incomplete warning prevents masquerading as free
    assert summary.estimated_cost == Decimal("0.000000")


def test_partial_cost_coverage_reported_correctly(temp_collector, tenant_ctx, analyzer):
    """
    Guarantees: In a mixed workload (3 known pricing events, 2 unknown pricing events),
    the summary distinguishes the known total from full coverage, and the analyzer
    flags INCOMPLETE_COST_COVERAGE.
    """
    events = [
        # 3 known events
        CreativeUsageEvent.create(
            workspace_id=tenant_ctx.workspace_id,
            project_id="proj_closeout_01",
            run_id="run_01",
            stage="INTENT",
            model="openrouter-dev-model",
            input_tokens=500,
            output_tokens=100,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000500"),
        ),
        CreativeUsageEvent.create(
            workspace_id=tenant_ctx.workspace_id,
            project_id="proj_closeout_01",
            run_id="run_01",
            stage="NARRATIVE",
            model="openrouter-dev-model",
            input_tokens=800,
            output_tokens=200,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000800"),
        ),
        CreativeUsageEvent.create(
            workspace_id=tenant_ctx.workspace_id,
            project_id="proj_closeout_01",
            run_id="run_01",
            stage="RECIPE_SELECTION",
            model="openrouter-dev-model",
            input_tokens=300,
            output_tokens=50,
            cost_provenance=CostProvenance.ACTUAL,
            actual_cost=Decimal("0.000300"),
        ),
        # 2 unknown pricing events
        CreativeUsageEvent.create(
            workspace_id=tenant_ctx.workspace_id,
            project_id="proj_closeout_01",
            run_id="run_01",
            stage="CREATIVE_PLANNING",
            model="unknown-legacy-model",
            cost_provenance=CostProvenance.UNKNOWN,
            estimated_cost=Decimal("0.000000"),
        ),
        CreativeUsageEvent.create(
            workspace_id=tenant_ctx.workspace_id,
            project_id="proj_closeout_01",
            run_id="run_01",
            stage="TASTE",
            model="custom-internal-evaluator",
            cost_provenance=CostProvenance.UNKNOWN,
            estimated_cost=Decimal("0.000000"),
        ),
    ]

    for ev in events:
        temp_collector.record_event(tenant_ctx, ev)

    summary = temp_collector.summarize_project(tenant_ctx, "proj_closeout_01")
    assert summary.known_cost_event_count == 3
    assert summary.unknown_cost_event_count == 2
    assert summary.cost_coverage_complete is False
    assert summary.actual_cost == Decimal("0.000300")
    assert summary.estimated_cost == Decimal("0.001300")

    # Analyzer detects incomplete coverage
    findings = analyzer.analyze(events)
    coverage_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.INCOMPLETE_COST_COVERAGE]
    assert len(coverage_findings) == 1
    cf = coverage_findings[0]
    assert cf.severity == EfficiencySeverity.WARNING
    assert "UNKNOWN != FREE" in cf.summary
    assert cf.observed_value["unknown_cost_events"] == 2


def test_heuristic_threshold_cannot_become_hard_authority(analyzer):
    """
    Guarantees: Heuristic bounds (e.g. OVER_RETRIEVAL > 15) remain advisory WARNINGs
    annotated with ThresholdProvenance.HEURISTIC and cannot mutate or block production.
    """
    event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_01",
        stage="KNOWLEDGE_RETRIEVAL",
        operation_type="RETRIEVAL",
        retrieval_items=25,  # Exceeds heuristic bound 15
        cost_provenance=CostProvenance.ESTIMATED,
        estimated_cost=Decimal("0.000000"),
    )

    findings = analyzer.analyze([event])
    over_retrieval_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.OVER_RETRIEVAL]
    assert len(over_retrieval_findings) == 1
    f = over_retrieval_findings[0]

    # Must be advisory WARNING, never CRITICAL/BLOCKER
    assert f.severity == EfficiencySeverity.WARNING
    assert f.observed_value["threshold_provenance"] == ThresholdProvenance.HEURISTIC.value
    assert f.expected_bound["threshold_provenance"] == ThresholdProvenance.HEURISTIC.value
    assert "heuristic" in f.summary.lower()


def test_empirical_canonical_threshold_preserves_severity(analyzer):
    """
    Guarantees: Architectural invariants (REUSE selected + generation invoked)
    preserve CRITICAL severity as defined by canonical policy (S28-06).
    """
    events = [
        CreativeUsageEvent.create(
            workspace_id="ws_01",
            project_id="proj_01",
            stage="TIER_DECISION",
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000000"),
            details={"selected_tier": "REUSE"},
        ),
        CreativeUsageEvent.create(
            workspace_id="ws_01",
            project_id="proj_01",
            stage="GENERATION",
            operation_type="MEDIA_GENERATION",
            generation_count=1,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.010000"),
        ),
    ]

    findings = analyzer.analyze(events)
    unnecessary_gen = [f for f in findings if f.finding_type == EfficiencyFindingType.UNNECESSARY_GENERATION]
    assert len(unnecessary_gen) == 1
    assert unnecessary_gen[0].severity == EfficiencySeverity.CRITICAL


def test_premium_model_finding_requires_policy_evidence(analyzer):
    """
    Guarantees: An unknown or unclassified model is NOT falsely accused of being an
    UNNECESSARY_PREMIUM_CALL without canonical ModelRegistry evidence.
    """
    # 1. Unregistered model with moderate cost on deterministic stage: NO finding
    unregistered_event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_01",
        stage="INTENT",
        operation_type="AI_COMPLETION",
        model="custom-unregistered-nlp-model",
        estimated_cost=Decimal("0.008000"),
    )
    findings = analyzer.analyze([unregistered_event])
    premium_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.UNNECESSARY_PREMIUM_CALL]
    assert len(premium_findings) == 0

    # 2. Registered HIGH cost model on deterministic stage: Policy-backed finding
    registered_premium_event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_01",
        stage="INTENT",
        operation_type="AI_COMPLETION",
        model="claude-3-5-sonnet",  # ModelRegistry: cost_profile=CostTier.HIGH
        estimated_cost=Decimal("0.008000"),
    )
    findings_premium = analyzer.analyze([registered_premium_event])
    prem_findings = [f for f in findings_premium if f.finding_type == EfficiencyFindingType.UNNECESSARY_PREMIUM_CALL]
    assert len(prem_findings) == 1
    assert prem_findings[0].observed_value["cost_tier"] == "HIGH"
    assert prem_findings[0].observed_value["policy_basis"] == "ModelRegistry.cost_profile_and_quality"


def test_baseline_provenance_is_explicit():
    """
    Guarantees: Baseline format definitions explicitly state their epistemic authority
    as TEST_REFERENCE / EMPIRICAL_BASELINE rather than inflexible production SLAs.
    """
    for format_name, baseline in CANONICAL_EFFICIENCY_BASELINES.items():
        assert isinstance(baseline, FormatBaseline)
        assert baseline.provenance in (ThresholdProvenance.TEST_REFERENCE, ThresholdProvenance.EMPIRICAL_BASELINE)
        assert baseline.provenance != ThresholdProvenance.CANONICAL_POLICY
