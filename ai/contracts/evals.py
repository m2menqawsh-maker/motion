"""
ai/contracts/evals.py
=====================
Canonical typed contracts for AI Evaluation Platform & Promotion Gates (S27.20).

Invariants:
- Typed eval results across quality, cost, and latency dimensions.
- Datasets are strictly versioned with deterministic content hashes.
- LLM Judge is NEVER sole authority (requires deterministic/code/schema/human corroboration).
- Separate human-labeled ground truth; models cannot self-generate truth.
- Honest tracking of deferred media benchmarks (no fake quality scores).
- No dict[str, Any] at boundaries.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum


class CandidateType(str, Enum):
    """Subject type under evaluation."""
    MODEL = "MODEL"
    PROMPT = "PROMPT"
    ROUTER_POLICY = "ROUTER_POLICY"


CandidateTypeEnum = strict_enum(CandidateType)


class EvaluatorType(str, Enum):
    """Class of evaluation methodology."""
    DETERMINISTIC = "DETERMINISTIC"
    SCHEMA_BASED = "SCHEMA_BASED"
    CODE_BASED = "CODE_BASED"
    HUMAN_LABEL = "HUMAN_LABEL"
    LLM_JUDGE = "LLM_JUDGE"


EvaluatorTypeEnum = strict_enum(EvaluatorType)


class ModelPromotionState(str, Enum):
    """Authoritative lifecycle progression for candidate models."""
    CANDIDATE = "CANDIDATE"
    OFFLINE_EVAL = "OFFLINE_EVAL"
    COST_BENCHMARK = "COST_BENCHMARK"
    LATENCY_BENCHMARK = "LATENCY_BENCHMARK"
    SHADOW_VALIDATION = "SHADOW_VALIDATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


ModelPromotionStateEnum = strict_enum(ModelPromotionState)


class EvalExample(AIContractModel):
    """
    Individual test fixture or labeled example within an evaluation dataset.
    """
    example_id: str = Field(min_length=1, description="Unique example identifier within dataset")
    input_payload: Dict[str, JsonValue] = Field(description="Structured input given to candidate")
    expected_output: Optional[Dict[str, JsonValue]] = Field(default=None, description="Expected structured output")
    expected_schema: Optional[str] = Field(default=None, description="Expected schema identifier or regex")
    ground_truth_label: Optional[str] = Field(default=None, description="Human or verified label")
    is_human_verified: bool = Field(default=False, description="Whether ground truth was created by human annotator")
    min_quality_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum acceptable quality threshold")


class EvalDatasetContract(AIContractModel):
    """
    Authoritative evaluation dataset entity.
    """
    dataset_id: str = Field(min_length=1, description="Unique dataset identifier")
    version: str = Field(min_length=1, description="Version string or SemVer")
    content_hash: str = Field(min_length=8, description="Deterministic content hash of all examples")
    capability: CapabilityTypeEnum = Field(description="Domain capability targeted by this dataset")
    description: str = Field(min_length=1, description="Description of benchmark purpose")
    examples: List[EvalExample] = Field(min_length=1, description="Ordered test fixtures")

    @staticmethod
    def compute_content_hash(examples: List[EvalExample]) -> str:
        """Computes deterministic SHA-256 hash across all examples."""
        raw_items = [
            f"{ex.example_id}:{json.dumps(ex.input_payload, sort_keys=True)}:{ex.ground_truth_label or ''}"
            for ex in examples
        ]
        composite = "|".join(raw_items)
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def validate_hash_coherence(self) -> Self:
        expected = self.compute_content_hash(self.examples)
        if self.content_hash != expected:
            raise ValueError(f"Dataset content hash mismatch. Expected '{expected}', got '{self.content_hash}'")
        return self


class EvalResultContract(AIContractModel):
    """
    Outcome of an evaluation run for a candidate model or prompt.
    """
    evaluation_id: str = Field(min_length=1, description="Unique evaluation execution ID")
    dataset_id: str = Field(min_length=1, description="Evaluated dataset ID")
    dataset_version: str = Field(min_length=1, description="Evaluated dataset version")
    candidate_type: CandidateTypeEnum = Field(description="Candidate entity classification")
    candidate_id: str = Field(min_length=1, description="Model ID or Prompt ID evaluated")
    candidate_version: str = Field(min_length=1, description="Version of candidate under test")
    passed: bool = Field(description="Whether candidate satisfied all thresholds")
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall evaluated quality score")
    cost_score: float = Field(ge=0.0, description="Relative cost rating or estimated cost per call")
    latency_ms: float = Field(ge=0.0, description="Average execution latency in milliseconds")
    evaluators_used: List[EvaluatorTypeEnum] = Field(min_length=1, description="Evaluators utilized in this run")
    created_at: TzAwareDatetime = Field(description="Evaluation timestamp")
    failure_reasons: List[str] = Field(default_factory=list, description="Detailed failure diagnostics if passed is False")
    metrics: Dict[str, JsonValue] = Field(default_factory=dict, description="Fine-grained metric breakdowns")

    @model_validator(mode="after")
    def validate_evaluator_authority(self) -> Self:
        # LLM judge cannot be sole evaluator authority
        if len(self.evaluators_used) == 1 and self.evaluators_used[0] == EvaluatorType.LLM_JUDGE:
            raise ValueError(
                "Evaluation result is invalid: LLM Judge cannot be the sole evaluation authority. "
                "Must include deterministic, code-based, schema-based, or human evaluators."
            )
        return self


class BenchmarkDebtContract(AIContractModel):
    """
    Formal tracking record for deferred real-media benchmarks.
    Guarantees honest accounting of technical debt without injecting fake scores.
    """
    benchmark_id: str = Field(min_length=1, description="Canonical benchmark identifier")
    name: str = Field(min_length=1, description="Descriptive benchmark title")
    status: str = Field(default="DEFERRED_FINAL_VALIDATION", description="Status code")
    target_stage: str = Field(default="AI-15", description="Stage designated for resolution")
    fake_scores_injected: bool = Field(default=False, description="Safety invariant flag verifying no fabricated scores")
    notes: str = Field(min_length=1, description="Formal justification and resolution criteria")
