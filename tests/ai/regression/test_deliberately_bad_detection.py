"""
tests/ai/regression/test_deliberately_bad_detection.py
=====================================================
Negative Gates Verification: Proves that the Creative Regression Suite fails
when defective creative decisions or forbidden traces are encountered.
"""

import pytest

from ai.contracts.creative.regression import (
    CreativeEvalCase,
    EvalCategory,
    EvalSeverity,
    GradingMethod,
    TraceAssertion,
    TraceAssertionType,
)
from ai.regression.runner import CreativeRegressionRunner
from ai.regression.trace_grader import CreativeTraceGrader


@pytest.fixture
def runner() -> CreativeRegressionRunner:
    return CreativeRegressionRunner()


def test_suite_detects_deliberate_bad_cases_in_canonical_dataset(runner: CreativeRegressionRunner):
    """Verifies that all 5 deliberately bad cases in the canonical dataset are caught."""
    run_result = runner.run_all()
    assert run_result.deliberately_bad_total_count >= 5
    assert run_result.deliberately_bad_detected_count == run_result.deliberately_bad_total_count


def test_suite_fails_when_forbidden_tool_is_invoked(runner: CreativeRegressionRunner):
    """Proves suite catches forbidden tool invocations (e.g. TTS tool under SILENT mode)."""
    grader = CreativeTraceGrader()

    # Trace erroneously invoking voiceover synthesis under SILENT mode
    corrupted_trace = [
        {"name": "audio_mode_evaluated", "audio_mode": "SILENT"},
        {"name": "tool_invoked", "tool": "voiceover_synthesis", "duration": 4.5},
    ]

    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_ABSENT,
        target_event_or_span="tool_invoked",
        field_path="tool",
        forbidden_values=["tts_generate", "voiceover_synthesis"],
        description="SILENT mode must never invoke audio generation tools",
    )

    passed, results = grader.grade_trace(corrupted_trace, [assertion])
    assert not passed, "Trace grader failed to flag forbidden tool invocation!"
    assert any("Expected event 'tool_invoked' to be absent" in r.details for r in results)


def test_suite_fails_when_create_bypasses_reuse(runner: CreativeRegressionRunner):
    """Proves suite catches tier selection bypass (CREATE selected despite REUSE match)."""
    case = CreativeEvalCase(
        case_id="synthetic_bypass_failure",
        category=EvalCategory.TIER_SELECTION,
        input_fixture={"scene_intent": "statistic"},
        expected_decisions={"selected_tier": "REUSE"},
        grading_method=GradingMethod.EXACT,
        severity=EvalSeverity.CRITICAL,
    )
    # Synthetic output with defect: selected CREATE instead of REUSE
    defective_output = {"selected_tier": "CREATE", "bypass_denied": False}
    grade = runner.grade_single_case(case, actual_output_override=defective_output, trace_override=[])
    assert not grade.passed
    assert any("Decision 'selected_tier' mismatch" in r for r in grade.reasons)


def test_suite_fails_when_rubric_drops_below_threshold(runner: CreativeRegressionRunner):
    """Proves suite catches sub-threshold creative narrative or taste quality."""
    case = CreativeEvalCase(
        case_id="synthetic_weak_narrative",
        category=EvalCategory.NARRATIVE,
        input_fixture={"video_type": "SAAS_DEMO"},
        rubric_thresholds={"hook_relevance": 0.75, "pacing": 0.80},
        grading_method=GradingMethod.RUBRIC_SCORE,
        severity=EvalSeverity.CRITICAL,
    )
    defective_scores = {"hook_relevance": 0.40, "pacing": 0.50}
    grade = runner.grade_single_case(case, actual_output_override=defective_scores, trace_override=[])
    assert not grade.passed
    assert len(grade.reasons) == 2
