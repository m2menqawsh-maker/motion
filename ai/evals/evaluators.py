"""
ai/evals/evaluators.py
======================
Evaluator implementations for AI Evaluation Platform (S27.20).

Invariants:
- Deterministic, schema-based, code-based, and human-labeled ground truth evaluators.
- LLM Judge can be used as an auxiliary evaluator, but is NEVER permitted to be the sole authority.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai.contracts.evals import EvaluatorType


class EvaluatorBase(ABC):
    """Base class for all evaluators."""

    @property
    @abstractmethod
    def evaluator_type(self) -> EvaluatorType:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        """
        Returns: (quality_score from 0.0 to 1.0, list of failure reasons if any)
        """
        raise NotImplementedError


class DeterministicEvaluator(EvaluatorBase):
    """Evaluates exact or structural match against expected output."""

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.DETERMINISTIC

    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        expected = getattr(example, "expected_output", None)
        if expected is None:
            return 1.0, []

        if actual_output == expected:
            return 1.0, []

        # Check dictionary subset
        if isinstance(actual_output, dict) and isinstance(expected, dict):
            matched = 0
            total = len(expected)
            reasons = []
            for k, exp_val in expected.items():
                if k in actual_output and actual_output[k] == exp_val:
                    matched += 1
                else:
                    reasons.append(f"Field '{k}' mismatch: expected '{exp_val}', got '{actual_output.get(k)}'")
            score = matched / total if total > 0 else 0.0
            return score, reasons

        return 0.0, [f"Output mismatch: expected '{expected}', got '{actual_output}'"]


class SchemaEvaluator(EvaluatorBase):
    """Validates structural conformity to required schema or expected fields."""

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.SCHEMA_BASED

    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        expected_schema = getattr(example, "expected_schema", None)
        if not expected_schema:
            return 1.0, []

        if not isinstance(actual_output, dict):
            return 0.0, ["Output is not a valid structured dictionary/JSON object"]

        required_fields = [f.strip() for f in expected_schema.split(",") if f.strip()]
        missing = [f for f in required_fields if f not in actual_output or actual_output[f] is None]
        if missing:
            return 0.0, [f"Missing required schema fields: {missing}"]

        return 1.0, []


class CodeBasedEvaluator(EvaluatorBase):
    """Executes arbitrary domain validation logic via assertion predicates."""

    def __init__(self, predicate: Optional[Callable[[Any], bool]] = None, rule_name: str = "domain_code_rule"):
        self._predicate = predicate
        self._rule_name = rule_name

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.CODE_BASED

    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        if self._predicate is None:
            return 1.0, []
        try:
            passed = bool(self._predicate(actual_output))
            if passed:
                return 1.0, []
            return 0.0, [f"Failed code rule '{self._rule_name}'"]
        except Exception as e:
            return 0.0, [f"Code evaluation error on '{self._rule_name}': {e}"]


class HumanLabelEvaluator(EvaluatorBase):
    """Evaluates against verified human-annotated ground truth."""

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.HUMAN_LABEL

    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        ground_truth = getattr(example, "ground_truth_label", None)
        if not ground_truth:
            return 1.0, []

        # If actual_output is a string or contains a label field
        actual_label = actual_output.get("label") if isinstance(actual_output, dict) else str(actual_output)
        if str(actual_label).strip().lower() == str(ground_truth).strip().lower():
            return 1.0, []
        return 0.0, [f"Human ground truth mismatch: expected '{ground_truth}', got '{actual_label}'"]


class LLMJudgeEvaluator(EvaluatorBase):
    """
    Advisory LLM Judge evaluating subjective quality, fluency, or tone.
    Mandatory invariant: Can never be the sole authority for promotion.
    """

    def __init__(self, judge_score_fn: Optional[Callable[[Any, Any], float]] = None):
        self._judge_fn = judge_score_fn or (lambda actual, ex: 0.90)

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.LLM_JUDGE

    def evaluate(self, actual_output: Any, example: Any) -> Tuple[float, List[str]]:
        try:
            score = float(self._judge_fn(actual_output, example))
            score = max(0.0, min(1.0, score))
            reasons = [] if score >= 0.8 else [f"LLM Judge gave low score: {score:.2f}"]
            return score, reasons
        except Exception as exc:
            return 0.0, [f"LLM Judge evaluation failed: {exc}"]
