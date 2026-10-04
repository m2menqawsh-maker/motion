"""
tests/ai/regression/test_regression_runner.py
=============================================
Verification of CreativeRegressionRunner orchestration, filtering, metrics aggregation,
and reproducibility.
"""

import pytest

from ai.contracts.creative.regression import CreativeEvalRun, EvalCategory, EvalSeverity
from ai.regression.runner import CreativeRegressionRunner


@pytest.fixture(scope="module")
def runner() -> CreativeRegressionRunner:
    return CreativeRegressionRunner()


def test_runner_executes_full_suite_successfully(runner: CreativeRegressionRunner):
    """Verifies that the canonical full regression run completes with a PASS verdict."""
    run: CreativeEvalRun = runner.run_all()
    assert isinstance(run, CreativeEvalRun)
    assert run.verdict == "PASS"
    assert run.cases_total >= 30
    assert run.passed_count == run.cases_total
    assert run.failed_count == 0
    assert run.pass_rate == 1.0
    assert run.started_at <= run.completed_at


def test_runner_category_filter(runner: CreativeRegressionRunner):
    """Verifies runner filters execution to a single category when requested."""
    intent_run = runner.run_all(category_filter=EvalCategory.INTENT.value)
    assert intent_run.verdict == "PASS"
    assert intent_run.cases_total == 5
    assert all(c.category == EvalCategory.INTENT.value for c in runner.last_case_grades)


def test_runner_severity_filter(runner: CreativeRegressionRunner):
    """Verifies runner filters execution to a specific severity level."""
    blocker_run = runner.run_all(severity_filter=EvalSeverity.BLOCKER.value)
    assert blocker_run.verdict == "PASS"
    assert blocker_run.cases_total >= 5
    assert all(c.severity == EvalSeverity.BLOCKER.value for c in runner.last_case_grades)


def test_runner_determinism_across_repeated_runs(runner: CreativeRegressionRunner):
    """Verifies that running the suite multiple times produces identical outcomes."""
    run1 = runner.run_all()
    run2 = runner.run_all()

    assert run1.verdict == run2.verdict == "PASS"
    assert run1.cases_total == run2.cases_total
    assert run1.passed_count == run2.passed_count
    assert run1.failed_count == run2.failed_count
    assert run1.pass_rate == run2.pass_rate
    assert run1.deliberately_bad_detected_count == run2.deliberately_bad_detected_count


def test_runner_aggregates_metrics_correctly(runner: CreativeRegressionRunner):
    """Verifies by_category and by_severity contain all expected keys with consistent sums."""
    run = runner.run_all()

    # Category checks
    for cat in EvalCategory:
        assert cat.value in run.by_category
        cat_stats = run.by_category[cat.value]
        assert cat_stats["total"] == cat_stats["passed"] + cat_stats["failed"]

    # Severity checks
    total_from_severities = sum(s["total"] for s in run.by_severity.values())
    assert total_from_severities == run.cases_total
