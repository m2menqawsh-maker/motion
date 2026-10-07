"""
ai/contracts/creative/regression.py
===================================
Canonical typed contracts for Creative Regression Suite & Trace Grading (S28-08B).

Invariants:
- Evaluates system decisions (intent, retrieval, routing, recipe, audio mode, narrative, taste,
  creative plan, template, tier, composition, candidates, personalization) rather than only render success.
- Multi-dimensional grading: deterministic exact/set/range, retrieval metrics (Precision@K, Recall@K, MRR),
  trace assertions, rubric scoring, and pairwise grading.
- Zero runtime authority: observation and grading only; no mutation of production lifecycle or registries.
- Strict Pydantic v2 immutability, timezone safety, and schema validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum


class EvalCategory(str, Enum):
    """Subsystem evaluation domain category."""
    INTENT = "INTENT"
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    SKILL_ROUTING = "SKILL_ROUTING"
    RECIPE_SELECTION = "RECIPE_SELECTION"
    AUDIO_MODE = "AUDIO_MODE"
    NARRATIVE = "NARRATIVE"
    TASTE = "TASTE"
    CREATIVE_PLAN = "CREATIVE_PLAN"
    TEMPLATE_SELECTION = "TEMPLATE_SELECTION"
    TIER_SELECTION = "TIER_SELECTION"
    COMPOSITION = "COMPOSITION"
    CANDIDATE_DECISION = "CANDIDATE_DECISION"
    STYLE_ADHERENCE = "STYLE_ADHERENCE"


EvalCategoryEnum = strict_enum(EvalCategory)


class GradingMethod(str, Enum):
    """Evaluation methodology applied to a case."""
    EXACT = "EXACT"
    SET_MEMBERSHIP = "SET_MEMBERSHIP"
    RANGE = "RANGE"
    RANKING_RETRIEVAL = "RANKING_RETRIEVAL"
    TRACE_ASSERTION = "TRACE_ASSERTION"
    RUBRIC_SCORE = "RUBRIC_SCORE"
    PAIRWISE = "PAIRWISE"


GradingMethodEnum = strict_enum(GradingMethod)


class EvalSeverity(str, Enum):
    """Failure impact severity classification."""
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


EvalSeverityEnum = strict_enum(EvalSeverity)


class TraceAssertionType(str, Enum):
    """Types of deterministic assertions against execution traces."""
    EVENT_EXISTS = "EVENT_EXISTS"
    EVENT_ABSENT = "EVENT_ABSENT"
    ORDERED_BEFORE = "ORDERED_BEFORE"
    SELECTED_VALUE_EQUALS = "SELECTED_VALUE_EQUALS"
    SELECTED_VALUE_IN_SET = "SELECTED_VALUE_IN_SET"
    FORBIDDEN_TRANSITION_ABSENT = "FORBIDDEN_TRANSITION_ABSENT"
    TOOL_INVOCATION_COUNT_IN_RANGE = "TOOL_INVOCATION_COUNT_IN_RANGE"


TraceAssertionTypeEnum = strict_enum(TraceAssertionType)


class TraceAssertion(AIContractModel):
    """
    Deterministic assertion evaluated against execution traces.
    """
    assertion_type: TraceAssertionTypeEnum = Field(description="Assertion operator")
    target_event_or_span: str = Field(description="Primary event or span name under test")
    secondary_target: Optional[str] = Field(
        default=None,
        description="Secondary event or span for ORDERED_BEFORE (primary must precede secondary)"
    )
    field_path: Optional[str] = Field(
        default=None,
        description="Dot-notated field path within event or span attributes"
    )
    expected_value: Optional[JsonValue] = Field(
        default=None,
        description="Expected exact value for SELECTED_VALUE_EQUALS"
    )
    allowed_values: Optional[List[JsonValue]] = Field(
        default=None,
        description="Acceptable set of values for SELECTED_VALUE_IN_SET"
    )
    forbidden_values: Optional[List[JsonValue]] = Field(
        default=None,
        description="Values that must never occur"
    )
    min_count: Optional[int] = Field(
        default=None,
        description="Minimum occurrences for count assertions"
    )
    max_count: Optional[int] = Field(
        default=None,
        description="Maximum occurrences for count assertions"
    )
    description: str = Field(
        default="",
        description="Human-readable description of assertion rationale"
    )


class TraceAssertionResult(AIContractModel):
    """Outcome of evaluating a single TraceAssertion."""
    assertion_type: str = Field(description="TraceAssertionType string")
    target: str = Field(description="Target event or span")
    passed: bool = Field(description="Whether assertion held true")
    details: str = Field(description="Diagnostic explanation of result")


class CreativeEvalCase(AIContractModel):
    """
    Canonical evaluation case contract for the Creative Regression Suite.
    """
    case_id: str = Field(min_length=1, description="Unique evaluation case identifier")
    version: str = Field(default="1.0.0", description="Case contract version")
    category: EvalCategoryEnum = Field(description="Subsystem evaluation category")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    input_fixture: Dict[str, JsonValue] = Field(description="Input payload given to target workflow")
    expected_constraints: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Hard constraints that must be observed"
    )
    expected_decisions: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Expected system decisions (e.g. recipe_id, tier, winning_source)"
    )
    allowed_outputs: List[JsonValue] = Field(
        default_factory=list,
        description="Allowed outputs for set-membership or retrieval matching"
    )
    forbidden_outputs: List[JsonValue] = Field(
        default_factory=list,
        description="Forbidden outputs that immediately fail the case"
    )
    grading_method: GradingMethodEnum = Field(description="Evaluation methodology to apply")
    severity: EvalSeverityEnum = Field(
        default=EvalSeverity.CRITICAL,
        description="Severity weighting if this case fails"
    )
    source: str = Field(default="canonical", description="Provenance origin of this case")
    is_deliberately_bad: bool = Field(
        default=False,
        description="Whether this case injects a defect to prove suite negative gate detection"
    )
    trace_assertions: List[TraceAssertion] = Field(
        default_factory=list,
        description="Trace assertions to verify for this case"
    )
    rubric_thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="Thresholds for rubric evaluation (composite, brief_adherence, etc.)"
    )
    retrieval_k: int = Field(default=3, ge=1, description="K for retrieval metrics")
    min_precision_at_k: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_recall_at_k: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_mrr: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class CreativeCaseGrade(AIContractModel):
    """Detailed grading result for an individual CreativeEvalCase."""
    case_id: str = Field(description="Evaluated case ID")
    category: str = Field(description="Evaluation category")
    severity: str = Field(description="Case severity")
    grading_method: str = Field(description="Grading method used")
    passed: bool = Field(description="Whether case passed all criteria")
    score: float = Field(ge=0.0, le=1.0, description="Normalized score [0.0 - 1.0]")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Per-dimension scores")
    reasons: List[str] = Field(default_factory=list, description="Failure diagnostic reasons")
    trace_results: List[TraceAssertionResult] = Field(default_factory=list, description="Trace assertion outcomes")
    retrieved_items: List[str] = Field(default_factory=list, description="Items retrieved if applicable")
    expected_items: List[str] = Field(default_factory=list, description="Expected items if applicable")
    is_deliberately_bad: bool = Field(default=False, description="Flag indicating negative test case")
    detected_deliberate_bad: bool = Field(
        default=False,
        description="True if deliberately bad case was successfully caught by the eval"
    )
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class PairwiseGradeResult(AIContractModel):
    """Structured pairwise comparison outcome (A vs B)."""
    scenario_id: str = Field(description="Scenario ID evaluated")
    preferred_candidate: str = Field(description="'A', 'B', 'TIE', or 'INSUFFICIENT_EVIDENCE'")
    margin: float = Field(ge=0.0, le=1.0, description="Score delta between candidates")
    per_dimension_deltas: Dict[str, float] = Field(default_factory=dict)
    rationale: str = Field(description="Transparent structured explanation (no hidden CoT)")


class JudgeCalibrationRecord(AIContractModel):
    """Tracking metrics comparing evaluator/judge against human-labeled ground truth."""
    total_calibration_pairs: int = Field(ge=0)
    agreement_count: int = Field(ge=0)
    agreement_rate: float = Field(ge=0.0, le=1.0)
    disagreements: List[Dict[str, JsonValue]] = Field(default_factory=list)
    calibrated: bool = Field(description="Whether agreement meets minimum threshold (e.g. >= 0.80)")
    calibration_method: str = Field(default="DETERMINISTIC_RUBRICS")


class CreativeEvalRun(AIContractModel):
    """
    Authoritative machine-readable summary of a Creative Regression Suite run.
    """
    run_id: str = Field(min_length=1, description="Unique execution run identifier")
    suite_version: str = Field(default="S28-08B", description="Regression suite version")
    cases_total: int = Field(ge=0, description="Total cases executed")
    passed_count: int = Field(ge=0, description="Count of passed cases")
    failed_count: int = Field(ge=0, description="Count of failed cases")
    pass_rate: float = Field(ge=0.0, le=1.0, description="Ratio of passed cases")
    by_category: Dict[str, Dict[str, JsonValue]] = Field(
        default_factory=dict,
        description="Metrics summary aggregated by EvalCategory"
    )
    by_severity: Dict[str, Dict[str, JsonValue]] = Field(
        default_factory=dict,
        description="Metrics summary aggregated by EvalSeverity"
    )
    regressions: List[Dict[str, JsonValue]] = Field(
        default_factory=list,
        description="Specific cases that regressed or failed"
    )
    trace_failures: List[Dict[str, JsonValue]] = Field(
        default_factory=list,
        description="Trace assertions that failed"
    )
    deliberately_bad_detected_count: int = Field(default=0)
    deliberately_bad_total_count: int = Field(default=0)
    judge_calibration: Optional[JudgeCalibrationRecord] = Field(
        default=None,
        description="Calibration statistics if judge evaluation was executed"
    )
    started_at: TzAwareDatetime = Field(description="Execution start timestamp")
    completed_at: TzAwareDatetime = Field(description="Execution completion timestamp")
    verdict: str = Field(description="'PASS' or 'FAIL'")
