"""
tests/ai/cost/test_efficiency_analyzer.py
=========================================
Unit tests for CreativeEfficiencyAnalyzer (S28-08C).

Verifies detection of:
- Unnecessary premium model invocations on deterministic tasks.
- Duplicate planning calls (distinguishing legitimate retries/fallbacks).
- Over-retrieval volume and duplicate chunks.
- Unnecessary media/template generation after REUSE was selected.
- CREATE tier escalations when valid REUSE candidates existed.
- Expensive repeated project failures.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.creative.cost import (
    CreativeUsageEvent,
    EfficiencyFindingType,
    EfficiencySeverity,
)
from ai.cost.analyzer import CreativeEfficiencyAnalyzer


@pytest.fixture
def analyzer():
    return CreativeEfficiencyAnalyzer()


def test_detect_unnecessary_premium_call(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that calling a premium model for a deterministic task (e.g. INTENT)
    is flagged as UNNECESSARY_PREMIUM_CALL.
    """
    event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_01",
        stage="INTENT",
        operation_type="AI_COMPLETION",
        model="gpt-4o",  # High-cost premium model for simple deterministic stage
        input_tokens=1000,
        output_tokens=500,
        estimated_cost=Decimal("0.012500"),
        details={"status": "SUCCESS"},
    )

    findings = analyzer.analyze([event])
    assert len(findings) == 1
    f = findings[0]
    assert f.finding_type == EfficiencyFindingType.UNNECESSARY_PREMIUM_CALL
    assert f.severity == EfficiencySeverity.WARNING
    assert "gpt-4o" in f.summary


def test_detect_high_cost_call(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that a call exceeding $0.05 is flagged as HIGH_COST_CALL_OBSERVED.
    """
    event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o",
        input_tokens=8000,
        output_tokens=4000,
        estimated_cost=Decimal("0.080000"),  # Exceeds $0.05
    )

    findings = analyzer.analyze([event])
    assert any(f.finding_type == EfficiencyFindingType.HIGH_COST_CALL_OBSERVED for f in findings)


def test_detect_duplicate_planning_without_retry(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that two identical planning calls with the same input_hash
    without retry/error reasons are flagged as DUPLICATE_PLANNING.
    """
    ev1 = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_dup",
        run_id="run_dup_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o-mini",
        input_tokens=1200,
        output_tokens=400,
        input_hash="hash_same_brief_01",
        details={"status": "SUCCESS"},
    )
    ev2 = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_dup",
        run_id="run_dup_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o-mini",
        input_tokens=1200,
        output_tokens=400,
        input_hash="hash_same_brief_01",  # Duplicate!
        details={"status": "SUCCESS"},
    )

    findings = analyzer.analyze([ev1, ev2])
    dup_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.DUPLICATE_PLANNING]
    assert len(dup_findings) == 1
    assert dup_findings[0].severity == EfficiencySeverity.CRITICAL


def test_legitimate_retry_is_not_flagged_as_duplicate(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that an intentional retry (with error or is_retry flag) is NOT flagged as waste.
    """
    ev1 = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_retry",
        run_id="run_retry_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o-mini",
        input_tokens=1200,
        output_tokens=0,
        input_hash="hash_same_brief_01",
        details={"status": "FAILED", "error": "RateLimitError"},
    )
    ev2 = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_retry",
        run_id="run_retry_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o-mini",
        input_tokens=1200,
        output_tokens=400,
        input_hash="hash_same_brief_01",
        details={"status": "SUCCESS", "is_retry": True, "retry_count": 1},
    )

    findings = analyzer.analyze([ev1, ev2])
    dup_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.DUPLICATE_PLANNING]
    assert len(dup_findings) == 0


def test_detect_over_retrieval(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that excessive retrieved chunks (>15) or duplicate chunks are flagged.
    """
    # 1. Volume overflow
    ev_overflow = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_ret",
        stage="KNOWLEDGE_RETRIEVAL",
        operation_type="RETRIEVAL",
        retrieval_items=25,  # Exceeds max 15
        details={"retrieved_ids": [f"doc_{i}" for i in range(25)]},
    )
    findings = analyzer.analyze([ev_overflow])
    assert any(f.finding_type == EfficiencyFindingType.OVER_RETRIEVAL for f in findings)

    # 2. Duplicate chunks
    ev_duplicates = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_ret",
        stage="KNOWLEDGE_RETRIEVAL",
        operation_type="RETRIEVAL",
        retrieval_items=4,
        details={"retrieved_ids": ["doc_A", "doc_B", "doc_A", "doc_C"]},
    )
    findings2 = analyzer.analyze([ev_duplicates])
    assert any(f.finding_type == EfficiencyFindingType.OVER_RETRIEVAL for f in findings2)


def test_detect_unnecessary_generation_after_reuse(analyzer: CreativeEfficiencyAnalyzer):
    """
    Critical Invariant:
    If REUSE was selected, invoking media or new template generation is a defect!
    """
    reuse_event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_reuse_gen",
        run_id="run_01",
        stage="TIER_DECISION",
        operation_type="DETERMINISTIC_COMPILATION",
        details={"tier": "REUSE", "template_id": "tmpl_header"},
    )
    gen_event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_reuse_gen",
        run_id="run_01",
        stage="MEDIA_GENERATION",
        operation_type="MEDIA_GENERATION",
        generation_count=1,
        details={"status": "SUCCESS"},
    )

    findings = analyzer.analyze([reuse_event, gen_event])
    gen_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.UNNECESSARY_GENERATION]
    assert len(gen_findings) == 1
    assert gen_findings[0].severity == EfficiencySeverity.CRITICAL


def test_detect_create_escalation_without_reason(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that choosing CREATE when an eligible REUSE candidate was available is flagged.
    """
    tier_event = CreativeUsageEvent.create(
        workspace_id="ws_01",
        project_id="proj_tier",
        stage="TIER_DECISION",
        operation_type="DETERMINISTIC_COMPILATION",
        details={
            "tier": "CREATE",
            "reuse_candidate_available": True,
            "reuse_score": 0.88,  # Valid matching candidate was available!
        },
    )

    findings = analyzer.analyze([tier_event])
    create_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.CREATE_ESCALATION_WITHOUT_REASON]
    assert len(create_findings) == 1
    assert create_findings[0].severity == EfficiencySeverity.CRITICAL


def test_detect_expensive_repeated_failures(analyzer: CreativeEfficiencyAnalyzer):
    """
    Verifies that >= 3 failed runs on the same project are flagged as EXPENSIVE_REPEATED_FAILURE.
    """
    events = [
        CreativeUsageEvent.create(
            workspace_id="ws_01",
            project_id="proj_fail_loop",
            run_id=f"run_fail_{i}",
            stage="CREATIVE_PLANNING",
            operation_type="AI_COMPLETION",
            estimated_cost=Decimal("0.020000"),
            details={"status": "FAILED", "error": "CompileError"},
        )
        for i in range(3)
    ]

    findings = analyzer.analyze(events)
    fail_findings = [f for f in findings if f.finding_type == EfficiencyFindingType.EXPENSIVE_REPEATED_FAILURE]
    assert len(fail_findings) == 1
    assert fail_findings[0].severity == EfficiencySeverity.WARNING
