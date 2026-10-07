"""
tests/ai/regression/test_personalization_regression.py
======================================================
Regression tests for Personalization & Feedback Precedence (S28-08A Integration).

Critical guarantees:
1. Current explicit request strictly supersedes stored preferences.
2. Hard brand constraints strictly supersede user style preferences.
3. Confirmed preferences strictly supersede inferred preferences.
4. Transient local scene critique does not mutate global user profile directly.
5. All precedence decisions produce structured StyleDecisionTrace records.
"""

import pytest

from ai.contracts.creative.regression import EvalCategory
from ai.regression.runner import CreativeRegressionRunner


@pytest.fixture
def runner() -> CreativeRegressionRunner:
    return CreativeRegressionRunner()


def test_personalization_suite_cases_pass(runner: CreativeRegressionRunner):
    """Executes all personalization evaluation cases and verifies 100% pass rate."""
    result = runner.run_all(category_filter=EvalCategory.STYLE_ADHERENCE.value)
    assert result.verdict == "PASS"
    assert result.cases_total >= 3
    assert result.passed_count == result.cases_total
    assert len(result.regressions) == 0


def test_current_request_wins_over_stored_preference(runner: CreativeRegressionRunner):
    """Direct verification that current prompt beats stored fast/high-intensity style."""
    result = runner.run_all(category_filter=EvalCategory.STYLE_ADHERENCE.value)
    grades = [g for g in runner.last_case_grades if g.case_id == "style_01_current_request_overrides_stored_preference"]
    assert len(grades) == 1
    grade = grades[0]
    assert grade.passed
    assert all(r.passed for r in grade.trace_results)


def test_brand_constraints_supersede_inferred_preferences(runner: CreativeRegressionRunner):
    """Direct verification that workspace brand rules override inferred user tendencies."""
    result = runner.run_all(category_filter=EvalCategory.STYLE_ADHERENCE.value)
    grades = [g for g in runner.last_case_grades if g.case_id == "style_02_brand_constraint_overrides_inferred_preference"]
    assert len(grades) == 1
    assert grades[0].passed


def test_local_critique_does_not_mutate_global_profile(runner: CreativeRegressionRunner):
    """Direct verification that one-off critique requires explicit confirmation before global write."""
    result = runner.run_all(category_filter=EvalCategory.STYLE_ADHERENCE.value)
    grades = [g for g in runner.last_case_grades if g.case_id == "style_03_single_scene_critique_not_permanent_global_rule"]
    assert len(grades) == 1
    assert grades[0].passed
