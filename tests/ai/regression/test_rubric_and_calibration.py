"""
tests/ai/regression/test_rubric_and_calibration.py
==================================================
Tests for structured rubric grading, pairwise evaluation, and judge calibration against human ground truth.
"""

import pytest

from ai.contracts.creative.regression import PairwiseGradeResult, JudgeCalibrationRecord
from ai.regression.rubric_grader import RubricGrader


@pytest.fixture
def grader() -> RubricGrader:
    return RubricGrader()


def test_rubric_scoring_thresholds(grader: RubricGrader):
    """Verifies rubric scoring evaluates multi-dimensional creative quality."""
    scores = {
        "brief_adherence": 0.85,
        "narrative_coherence": 0.80,
        "pacing": 0.90,
        "visual_intent": 0.75,
        "overdesign_avoidance": 0.95,
    }
    thresholds = {
        "brief_adherence": 0.70,
        "narrative_coherence": 0.70,
        "pacing": 0.70,
    }
    passed, reasons = grader.grade_rubric_scores(scores, thresholds)
    assert passed
    assert len(reasons) == 0

    # Failure when metric falls below threshold
    failing_thresholds = {"overdesign_avoidance": 0.98}
    passed_fail, reasons_fail = grader.grade_rubric_scores(scores, failing_thresholds)
    assert not passed_fail
    assert len(reasons_fail) == 1
    assert "overdesign_avoidance" in reasons_fail[0]


def test_pairwise_candidate_evaluation(grader: RubricGrader):
    """Verifies structured pairwise comparison (A vs B) returns transparent grading without hidden CoT."""
    candidate_a = {
        "brief_adherence": 0.90,
        "narrative_coherence": 0.85,
        "pacing": 0.80,
        "visual_intent": 0.85,
    }
    candidate_b = {
        "brief_adherence": 0.70,
        "narrative_coherence": 0.65,
        "pacing": 0.60,
        "visual_intent": 0.70,
    }

    result: PairwiseGradeResult = grader.evaluate_pairwise(
        scenario_id="sc_saas_hook",
        scores_a=candidate_a,
        scores_b=candidate_b,
    )
    assert isinstance(result, PairwiseGradeResult)
    assert result.preferred_candidate == "A"
    assert result.margin > 0.15
    assert result.per_dimension_deltas["brief_adherence"] == pytest.approx(0.20, rel=1e-3)
    assert "CoT" not in result.rationale  # Explicit transparent rationale


def test_pairwise_tie_detection(grader: RubricGrader):
    """Verifies that nearly identical candidate quality produces a TIE."""
    cand_1 = {"brief_adherence": 0.80, "pacing": 0.80}
    cand_2 = {"brief_adherence": 0.81, "pacing": 0.79}

    result = grader.evaluate_pairwise("sc_tie", cand_1, cand_2)
    assert result.preferred_candidate == "TIE"
    assert result.margin <= 0.05


def test_judge_calibration_against_ground_truth(grader: RubricGrader):
    """Verifies evaluator calibration against a canonical set of human-labeled decisions."""
    # Canonical human-labeled ground truth pairs
    ground_truth = [
        {"scenario_id": "sc_01", "human_preferred": "A"},
        {"scenario_id": "sc_02", "human_preferred": "B"},
        {"scenario_id": "sc_03", "human_preferred": "A"},
    ]
    # Simulated evaluator decisions matching all 3
    evaluator_decisions = [
        {"scenario_id": "sc_01", "preferred_candidate": "A"},
        {"scenario_id": "sc_02", "preferred_candidate": "B"},
        {"scenario_id": "sc_03", "preferred_candidate": "A"},
    ]

    record: JudgeCalibrationRecord = grader.calibrate_against_ground_truth(
        ground_truth=ground_truth,
        evaluator_decisions=evaluator_decisions,
        min_agreement_threshold=0.80,
    )
    assert record.total_calibration_pairs == 3
    assert record.agreement_count == 3
    assert record.agreement_rate == 1.0
    assert record.calibrated is True
    assert len(record.disagreements) == 0


def test_judge_calibration_failure_when_disagreement_exceeds_threshold(grader: RubricGrader):
    """Verifies calibration flag is False and disagreements tracked when evaluator drifts from ground truth."""
    ground_truth = [
        {"scenario_id": "sc_01", "human_preferred": "A"},
        {"scenario_id": "sc_02", "human_preferred": "B"},
    ]
    # Evaluator disagrees on sc_02
    evaluator_decisions = [
        {"scenario_id": "sc_01", "preferred_candidate": "A"},
        {"scenario_id": "sc_02", "preferred_candidate": "A"},
    ]

    record = grader.calibrate_against_ground_truth(
        ground_truth=ground_truth,
        evaluator_decisions=evaluator_decisions,
        min_agreement_threshold=0.80,
    )
    assert record.agreement_count == 1
    assert record.agreement_rate == 0.50
    assert record.calibrated is False
    assert len(record.disagreements) == 1
    assert record.disagreements[0]["scenario_id"] == "sc_02"
