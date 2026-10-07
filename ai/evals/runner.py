"""
ai/evals/runner.py
==================
Execution Engine for AI Evaluation Platform (S27.20).

Invariants:
- Evaluates candidate models, prompts, or policies against versioned datasets.
- Disallows LLM Judge from being the sole evaluation authority.
- Captures quality, cost, and latency dimensions into typed EvalResultContract.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai.contracts.evals import (
    CandidateType,
    EvalDatasetContract,
    EvalResultContract,
    EvaluatorType,
)
from ai.evals.evaluators import EvaluatorBase, LLMJudgeEvaluator


class EvalRunner:
    """
    Executes candidates against test datasets and scores multi-dimensional outcomes.
    """

    def __init__(self, evaluators: List[EvaluatorBase]):
        if not evaluators:
            raise ValueError("EvalRunner requires at least one evaluator.")

        # Guard: LLM Judge must never be sole evaluator authority
        if len(evaluators) == 1 and isinstance(evaluators[0], LLMJudgeEvaluator):
            raise ValueError(
                "Violation: LLM Judge cannot be the sole evaluation authority for production gates. "
                "Combine with deterministic, schema-based, or code-based evaluators."
            )

        self.evaluators = evaluators

    def run_evaluation(
        self,
        candidate_id: str,
        candidate_version: str,
        candidate_type: CandidateType,
        dataset: EvalDatasetContract,
        executor_fn: Callable[[Dict[str, Any]], Any],
        cost_per_call: float = 0.01,
        min_pass_threshold: float = 0.80,
    ) -> EvalResultContract:
        """
        Executes candidate across all examples in the dataset.
        """
        example_scores: List[float] = []
        failure_reasons: List[str] = []
        latencies_ms: List[float] = []

        for example in dataset.examples:
            start_t = time.perf_counter()
            try:
                actual_output = executor_fn(example.input_payload)
            except Exception as exc:
                actual_output = None
                failure_reasons.append(f"Execution error on example '{example.example_id}': {exc}")
            latency = (time.perf_counter() - start_t) * 1000.0
            latencies_ms.append(latency)

            # Evaluate example across all configured evaluators
            ex_eval_scores: List[float] = []
            for ev in self.evaluators:
                score, reasons = ev.evaluate(actual_output, example)
                ex_eval_scores.append(score)
                failure_reasons.extend(reasons)

            avg_ex_score = sum(ex_eval_scores) / len(ex_eval_scores) if ex_eval_scores else 0.0
            example_scores.append(avg_ex_score)

        avg_quality = sum(example_scores) / len(example_scores) if example_scores else 0.0
        avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
        passed = (avg_quality >= min_pass_threshold) and (len(failure_reasons) == 0)

        evaluators_used = [ev.evaluator_type for ev in self.evaluators]

        return EvalResultContract(
            evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            candidate_type=candidate_type,
            candidate_id=candidate_id,
            candidate_version=candidate_version,
            passed=passed,
            quality_score=round(avg_quality, 4),
            cost_score=round(cost_per_call, 4),
            latency_ms=round(avg_latency, 2),
            evaluators_used=evaluators_used,
            created_at=datetime.now(timezone.utc),
            failure_reasons=failure_reasons[:20],  # Bound failure reasons length
            metrics={
                "example_count": len(dataset.examples),
                "pass_threshold": min_pass_threshold,
            },
        )
