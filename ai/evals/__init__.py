"""
ai/evals/__init__.py
====================
AI Evaluation Platform & Model/Prompt Promotion Gates (S27.20).
"""

from ai.contracts.evals import (
    BenchmarkDebtContract,
    CandidateType,
    EvalDatasetContract,
    EvalExample,
    EvalResultContract,
    EvaluatorType,
    ModelPromotionState,
)
from ai.evals.datasets import (
    build_audio_dataset,
    build_memory_retrieval_dataset,
    build_planning_dataset,
    build_routing_dataset,
    build_speech_dataset,
    build_structured_outputs_dataset,
    build_tool_selection_dataset,
    build_vision_dataset,
)
from ai.evals.deferred import get_deferred_benchmark, list_deferred_benchmarks
from ai.evals.evaluators import (
    CodeBasedEvaluator,
    DeterministicEvaluator,
    EvaluatorBase,
    HumanLabelEvaluator,
    LLMJudgeEvaluator,
    SchemaEvaluator,
)
from ai.evals.gate import CIEvalGate, EvalGateFailure
from ai.evals.promotion import ModelPromotionEngine, PromotionDecision
from ai.evals.runner import EvalRunner

__all__ = [
    "CandidateType",
    "EvaluatorType",
    "ModelPromotionState",
    "EvalExample",
    "EvalDatasetContract",
    "EvalResultContract",
    "BenchmarkDebtContract",
    "build_audio_dataset",
    "build_memory_retrieval_dataset",
    "build_planning_dataset",
    "build_routing_dataset",
    "build_speech_dataset",
    "build_structured_outputs_dataset",
    "build_tool_selection_dataset",
    "build_vision_dataset",
    "get_deferred_benchmark",
    "list_deferred_benchmarks",
    "EvaluatorBase",
    "DeterministicEvaluator",
    "SchemaEvaluator",
    "CodeBasedEvaluator",
    "HumanLabelEvaluator",
    "LLMJudgeEvaluator",
    "EvalRunner",
    "ModelPromotionEngine",
    "PromotionDecision",
    "CIEvalGate",
    "EvalGateFailure",
]
