"""
tests/ai/regression/test_regression_contracts.py
================================================
Contract immutability, schema validity, and enum integrity for S28-08B regression contracts.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from ai.contracts.creative.regression import (
    EvalCategory,
    GradingMethod,
    EvalSeverity,
    TraceAssertionType,
    TraceAssertion,
    TraceAssertionResult,
    CreativeEvalCase,
    CreativeCaseGrade,
    PairwiseGradeResult,
    JudgeCalibrationRecord,
    CreativeEvalRun,
)


def test_eval_categories_enum_has_all_13_canonical_domains():
    """Verifies that all 13 mandated creative evaluation categories exist."""
    required_categories = {
        "INTENT",
        "KNOWLEDGE_RETRIEVAL",
        "SKILL_ROUTING",
        "RECIPE_SELECTION",
        "AUDIO_MODE",
        "NARRATIVE",
        "TASTE",
        "CREATIVE_PLAN",
        "TEMPLATE_SELECTION",
        "TIER_SELECTION",
        "COMPOSITION",
        "CANDIDATE_DECISION",
        "STYLE_ADHERENCE",
    }
    actual_categories = {c.value for c in EvalCategory}
    assert required_categories == actual_categories


def test_eval_severity_enum_levels():
    """Verifies severity levels ordered by criticality."""
    expected = {"BLOCKER", "CRITICAL", "MAJOR", "MINOR"}
    actual = {s.value for s in EvalSeverity}
    assert expected == actual


def test_trace_assertion_type_enum():
    """Verifies all trace assertion primitives."""
    expected = {
        "EVENT_EXISTS",
        "EVENT_ABSENT",
        "ORDERED_BEFORE",
        "SELECTED_VALUE_EQUALS",
        "SELECTED_VALUE_IN_SET",
        "FORBIDDEN_TRANSITION_ABSENT",
        "TOOL_INVOCATION_COUNT_IN_RANGE",
    }
    actual = {t.value for t in TraceAssertionType}
    assert expected == actual


def test_trace_assertion_immutability():
    """Verifies TraceAssertion is frozen and forbids extra fields."""
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_EXISTS,
        target_event_or_span="recipe_selected",
        expected_value="rec_01",
    )
    with pytest.raises(ValidationError):
        assertion.expected_value = "rec_02"  # Frozen check

    with pytest.raises(ValidationError):
        TraceAssertion(
            assertion_type=TraceAssertionType.EVENT_EXISTS,
            target_event_or_span="foo",
            unexpected_field="bar",  # Extra forbid check
        )


def test_creative_eval_case_creation_and_defaults():
    """Verifies CreativeEvalCase validation and default values."""
    case = CreativeEvalCase(
        case_id="case_test_01",
        category=EvalCategory.INTENT,
        input_fixture={"user_request": "test"},
        grading_method=GradingMethod.EXACT,
        severity=EvalSeverity.CRITICAL,
    )
    assert case.version == "1.0.0"
    assert case.tags == []
    assert case.input_fixture == {"user_request": "test"}
    assert case.expected_decisions == {}
    assert case.allowed_outputs == []
    assert case.forbidden_outputs == []
    assert case.trace_assertions == []
    assert case.retrieval_k == 3
    assert not case.is_deliberately_bad


def test_creative_eval_run_verdict_validation():
    """Verifies CreativeEvalRun validates required fields and computes stats."""
    now = datetime.now(timezone.utc)
    run = CreativeEvalRun(
        run_id="run_001",
        suite_version="S28-08B",
        cases_total=10,
        passed_count=10,
        failed_count=0,
        pass_rate=1.0,
        by_category={"INTENT": {"total": 10, "passed": 10, "failed": 0}},
        by_severity={"CRITICAL": {"total": 10, "passed": 10, "failed": 0}},
        started_at=now,
        completed_at=now,
        verdict="PASS",
    )
    assert run.verdict == "PASS"
    assert run.pass_rate == 1.0
    dumped = run.model_dump(mode="json")
    assert dumped["run_id"] == "run_001"
    assert dumped["verdict"] == "PASS"


def test_pairwise_grade_result_valid_values():
    """Verifies PairwiseGradeResult contract constraints."""
    result = PairwiseGradeResult(
        scenario_id="sc_01",
        preferred_candidate="A",
        margin=0.25,
        per_dimension_deltas={"brief_adherence": 0.3},
        rationale="Candidate A followed tone constraint better",
    )
    assert result.preferred_candidate == "A"
    assert result.margin == 0.25

    with pytest.raises(ValidationError):
        PairwiseGradeResult(
            scenario_id="sc_01",
            preferred_candidate="A",
            margin=1.5,  # Must be <= 1.0
            rationale="Invalid margin",
        )
