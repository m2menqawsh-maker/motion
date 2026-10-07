"""
tests/ai/regression/test_all_eval_categories.py
===============================================
Verifies dataset presence, test coverage, and execution across all 13 required creative categories:
1. INTENT
2. KNOWLEDGE_RETRIEVAL
3. SKILL_ROUTING
4. RECIPE_SELECTION
5. AUDIO_MODE
6. NARRATIVE
7. TASTE
8. CREATIVE_PLAN
9. TEMPLATE_SELECTION
10. TIER_SELECTION
11. COMPOSITION
12. CANDIDATE_DECISION
13. STYLE_ADHERENCE
"""

import pytest

from ai.contracts.creative.regression import EvalCategory
from ai.regression.datasets import get_all_creative_eval_cases
from ai.regression.runner import CreativeRegressionRunner


@pytest.fixture(scope="module")
def runner() -> CreativeRegressionRunner:
    return CreativeRegressionRunner()


def test_dataset_contains_cases_for_every_category():
    """Guarantees zero categories are missing from the canonical evaluation dataset."""
    all_cases = get_all_creative_eval_cases()
    categories_present = {c.category.value for c in all_cases}
    all_expected = {cat.value for cat in EvalCategory}

    missing = all_expected - categories_present
    assert not missing, f"Missing evaluation cases for categories: {missing}"
    assert len(all_cases) >= 30, f"Expected comprehensive dataset, got {len(all_cases)} cases"


@pytest.mark.parametrize("category", [c.value for c in EvalCategory])
def test_each_category_executes_and_passes(runner: CreativeRegressionRunner, category: str):
    """Executes regression runner filtered to each category independently."""
    result = runner.run_all(category_filter=category)
    assert result.verdict == "PASS", f"Category {category} failed regression: {result.regressions}"
    assert result.cases_total > 0, f"Category {category} has no test cases"
    assert result.passed_count == result.cases_total, (
        f"Category {category} had {result.failed_count} failures"
    )
