"""
tests/ai/evals/test_creative_evals_s28_04.py
===========================================
Pytest suite executing the S28-04 Creative Evaluation Suite and Exit Gates.

Verifies:
1. All 8 Golden Creative Scenarios pass composite rubric thresholds (>= 0.75).
2. All 7 Deliberately Bad Outputs are caught and flagged by evaluation gates.
3. Pairwise comparison prefers Golden candidates over degraded candidates.
4. Human-labeled calibration achieves >= 80% agreement.
5. Overall S28-04 Exit Gate is green (gate_status == "PASS").
"""

import pytest
from ai.evals.creative_evals_s28_04 import S28_04_EvalRunner


@pytest.fixture(scope="module")
def eval_report():
    runner = S28_04_EvalRunner()
    report = runner.run_all_evaluations()
    runner.save_report(report)
    return report


def test_all_golden_scenarios_pass(eval_report):
    golden_results = eval_report.golden_scenario_results
    assert len(golden_results) >= 6, "Must evaluate at least 6 golden scenarios"

    for sc_id, res in golden_results.items():
        assert res["passed"] is True, f"Golden scenario '{sc_id}' failed: {res['scores']}"
        assert res["scores"]["composite_score"] >= 0.75, f"Score too low for '{sc_id}'"


def test_all_deliberately_bad_outputs_detected(eval_report):
    bad_results = eval_report.bad_output_detection_results
    assert len(bad_results) >= 7, "Must evaluate at least 7 deliberately bad outputs"

    for bad_id, res in bad_results.items():
        assert res["detected_by_gate"] is True, f"Bad output '{bad_id}' was not detected by gate!"


def test_pairwise_evaluations_prefer_golden_candidates(eval_report):
    pairwise_results = eval_report.pairwise_results
    assert len(pairwise_results) >= 2

    for p in pairwise_results:
        assert p["preferred_candidate"] == "A", (
            f"Pairwise comparison for '{p['scenario_id']}' did not prefer Golden Candidate A: {p}"
        )
        assert p["margin"] >= 0.05


def test_human_calibration_agreement_rate(eval_report):
    calib = eval_report.calibration_result
    assert calib["calibrated"] is True
    assert calib["agreement_rate"] >= 0.80, f"Agreement rate too low: {calib['agreement_rate']}"


def test_overall_s28_04_gate_status_pass(eval_report):
    assert eval_report.gate_status == "PASS"
