"""
ai/regression/__init__.py
========================
Creative Regression Suite & Trace Grading Package (S28-08B).

Authoritative exports:
- CreativeRegressionRunner: Orchestrates multi-category regression and trace evaluation.
- CreativeTraceGrader: Observational trace assertion grader.
- RetrievalGrader: Precision@K, Recall@K, and MRR metrics engine.
- RubricGrader: S28-04 rubrics, pairwise, and calibration wrapper.
- Case datasets & contracts.
"""

from ai.regression.contracts import (
    CreativeCaseGrade,
    CreativeEvalCase,
    CreativeEvalRun,
    EvalCategory,
    EvalCategoryEnum,
    EvalSeverity,
    EvalSeverityEnum,
    GradingMethod,
    GradingMethodEnum,
    JudgeCalibrationRecord,
    PairwiseGradeResult,
    TraceAssertion,
    TraceAssertionResult,
    TraceAssertionType,
    TraceAssertionTypeEnum,
)
from ai.regression.datasets import (
    get_all_creative_eval_cases,
    get_audio_mode_cases,
    get_candidate_decision_cases,
    get_composition_cases,
    get_creative_plan_cases,
    get_intent_cases,
    get_knowledge_retrieval_cases,
    get_narrative_cases,
    get_recipe_selection_cases,
    get_skill_routing_cases,
    get_style_adherence_cases,
    get_taste_cases,
    get_template_selection_cases,
    get_tier_selection_cases,
)
from ai.regression.retrieval_grader import (
    RetrievalGrader,
    calculate_mrr,
    calculate_precision_at_k,
    calculate_recall_at_k,
)
from ai.regression.rubric_grader import RubricGrader
from ai.regression.runner import CreativeRegressionRunner
from ai.regression.trace_grader import CreativeTraceGrader, normalize_trace_records

__all__ = [
    "CreativeCaseGrade",
    "CreativeEvalCase",
    "CreativeEvalRun",
    "CreativeRegressionRunner",
    "CreativeTraceGrader",
    "EvalCategory",
    "EvalCategoryEnum",
    "EvalSeverity",
    "EvalSeverityEnum",
    "GradingMethod",
    "GradingMethodEnum",
    "JudgeCalibrationRecord",
    "PairwiseGradeResult",
    "RetrievalGrader",
    "RubricGrader",
    "TraceAssertion",
    "TraceAssertionResult",
    "TraceAssertionType",
    "TraceAssertionTypeEnum",
    "calculate_mrr",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "get_all_creative_eval_cases",
    "get_audio_mode_cases",
    "get_candidate_decision_cases",
    "get_composition_cases",
    "get_creative_plan_cases",
    "get_intent_cases",
    "get_knowledge_retrieval_cases",
    "get_narrative_cases",
    "get_recipe_selection_cases",
    "get_skill_routing_cases",
    "get_style_adherence_cases",
    "get_taste_cases",
    "get_template_selection_cases",
    "get_tier_selection_cases",
    "normalize_trace_records",
]
