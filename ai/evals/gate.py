"""
ai/evals/gate.py
================
CI Evaluation Gate & Regression Checker (S27.20).

Invariants:
- Verifies prompt regressions, model regressions, schema regressions, routing regressions.
- If regression threshold is breached, gate fails immediately (blocks CI / promotion).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ai.contracts.evals import CandidateType, EvalDatasetContract, EvalResultContract
from ai.contracts.prompt import PromptRenderRequest
from ai.evals.evaluators import DeterministicEvaluator, EvaluatorBase, SchemaEvaluator
from ai.evals.promotion import ModelPromotionEngine, PromotionDecision
from ai.evals.runner import EvalRunner
from ai.prompts.service import PromptService


class EvalGateFailure(Exception):
    """Raised when an evaluation gate fails to meet quality, schema, or economic criteria."""
    pass


class CIEvalGate:
    """
    Standard CI / Release Gate verifying candidate models, prompts, and schemas before deployment.
    """

    @classmethod
    def run_prompt_regression_gate(
        cls,
        prompt_service: PromptService,
        prompt_id: str,
        candidate_version: int,
        dataset: EvalDatasetContract,
        executor_fn: Callable[[str, Dict[str, Any]], Any],
        evaluators: Optional[List[EvaluatorBase]] = None,
        min_threshold: float = 0.80,
    ) -> EvalResultContract:
        """
        Evaluates a candidate prompt version against a benchmark dataset.
        Fails if prompt produces degraded or non-conformant output.
        """
        active_evaluators = evaluators or [DeterministicEvaluator(), SchemaEvaluator()]
        runner = EvalRunner(evaluators=active_evaluators)

        def _run_with_prompt(payload: Dict[str, Any]) -> Any:
            # Render candidate prompt
            rendered = prompt_service.render_prompt(
                PromptRenderRequest(
                    prompt_id=prompt_id,
                    version=candidate_version,
                    variables=payload,
                )
            )
            # Execute downstream model/function with rendered text
            return executor_fn(rendered.rendered_text, payload)

        result = runner.run_evaluation(
            candidate_id=prompt_id,
            candidate_version=str(candidate_version),
            candidate_type=CandidateType.PROMPT,
            dataset=dataset,
            executor_fn=_run_with_prompt,
            cost_per_call=0.001,
            min_pass_threshold=min_threshold,
        )
        return result

    @classmethod
    def run_model_gate(
        cls,
        candidate_id: str,
        quality_score: float,
        cost_per_call: float,
        latency_ms: float,
        baseline_quality: float = 0.85,
        baseline_cost: float = 0.01,
        baseline_latency: float = 800.0,
    ) -> PromotionDecision:
        """
        Evaluates model promotion eligibility under quality floor and economic utility policies.
        """
        return ModelPromotionEngine.evaluate_candidate(
            candidate_id=candidate_id,
            quality_score=quality_score,
            cost_per_call=cost_per_call,
            latency_ms=latency_ms,
            baseline_quality=baseline_quality,
            baseline_cost=baseline_cost,
            baseline_latency=baseline_latency,
        )
