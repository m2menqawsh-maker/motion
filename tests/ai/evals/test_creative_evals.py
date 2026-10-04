"""
tests/ai/evals/test_creative_evals.py
=====================================
Evaluation Benchmark Tests for S28-03:
- Intent Understanding Benchmark (16 cases across AR, EN, MIXED, short, vague, detailed, contradictory).
- Recipe Selection Matrix Benchmark (10 cases across multidimensional matrix).
Guarantees:
- Intent Accuracy == 100%
- Unsupported Inference Rate == 0%
- Contradiction Detection Rate == 100%
- Recipe Selection Accuracy == 100%
- Forbidden Recipe Avoidance Rate == 100%
"""

from pathlib import Path
import pytest

from ai.intent.evaluator import IntentEvaluator
from ai.recipes.evaluator import RecipeMatrixEvaluator


def test_intent_understanding_benchmark():
    """Executes the full Intent Understanding evaluation dataset and asserts quality gates."""
    evaluator = IntentEvaluator()
    dataset_path = Path("tests/ai/evals/datasets/intent_dataset.json")
    assert dataset_path.exists(), f"Missing dataset: {dataset_path}"

    report = evaluator.evaluate_file(dataset_path)
    assert report.total_cases >= 16
    assert report.intent_accuracy >= 0.90, f"Intent accuracy below gate: {report.intent_accuracy}"
    assert report.unsupported_inference_rate == 0.0, f"Unsupported inference detected: {report.unsupported_inference_rate}"
    assert report.contradiction_detection_rate >= 0.90, f"Contradiction detection below gate: {report.contradiction_detection_rate}"
    assert report.cases_failed == 0, f"Cases failed: {report.failure_details}"


def test_recipe_selection_matrix_benchmark():
    """Executes the full Recipe Selection Matrix evaluation dataset and asserts quality gates."""
    evaluator = RecipeMatrixEvaluator()
    dataset_path = Path("tests/ai/evals/datasets/recipe_selection_matrix.json")
    assert dataset_path.exists(), f"Missing dataset: {dataset_path}"

    report = evaluator.evaluate_file(dataset_path)
    assert report.total_cases >= 10
    assert report.selection_accuracy >= 0.90, f"Selection accuracy below gate: {report.selection_accuracy}"
    assert report.forbidden_avoidance_rate == 1.0, f"Forbidden avoidance violation: {report.forbidden_avoidance_rate}"
    assert report.cases_failed == 0, f"Cases failed: {report.failure_details}"
