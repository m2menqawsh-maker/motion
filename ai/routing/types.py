"""
ai/routing/types.py
===================
Canonical typed structures, enums, and diagnostic contracts for the Model Router (S27.4).

Invariants:
- All cost metrics strictly use Decimal (never binary floats).
- Reason codes are finite, typed, and observable.
- Diagnostics record explainability without leaking sensitive credentials.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import QualityTarget, QualityTargetEnum
from ai.contracts.model import ModelSelection
from ai.models.types import CostTierEnum, LatencyTierEnum


class RoutingReasonCode(str, Enum):
    """Authoritative, machine-readable reason classifications for model routing outcomes."""
    BEST_BALANCED_UTILITY = "BEST_BALANCED_UTILITY"
    LOWEST_COST_MEETING_TARGET = "LOWEST_COST_MEETING_TARGET"
    HIGHEST_QUALITY_WITHIN_BUDGET = "HIGHEST_QUALITY_WITHIN_BUDGET"
    LOW_LATENCY_REQUIRED = "LOW_LATENCY_REQUIRED"
    PRIVACY_FILTERED = "PRIVACY_FILTERED"
    LANGUAGE_MATCH = "LANGUAGE_MATCH"
    REGION_MATCH = "REGION_MATCH"
    FALLBACK_PEER = "FALLBACK_PEER"
    FALLBACK_PROVIDER_OUTAGE = "FALLBACK_PROVIDER_OUTAGE"
    FALLBACK_RATE_LIMITED = "FALLBACK_RATE_LIMITED"
    FALLBACK_TIMEOUT = "FALLBACK_TIMEOUT"
    ESCALATED_QUALITY_UPGRADE = "ESCALATED_QUALITY_UPGRADE"
    ESCALATED_SCHEMA_REPAIR = "ESCALATED_SCHEMA_REPAIR"
    SINGLE_COMPLIANT_CANDIDATE = "SINGLE_COMPLIANT_CANDIDATE"


class QualityStatus(str, Enum):
    """Quality validation assessment state."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


RoutingReasonCodeEnum = strict_enum(RoutingReasonCode)
QualityStatusEnum = strict_enum(QualityStatus)


class WorkloadEstimate(AIContractModel):
    """
    Typed expectation of compute consumption for an impending capability invocation.
    Enables precise, deterministic cost estimation prior to model execution.
    """
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Estimated prompt/input tokens")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Estimated completion/output tokens")
    audio_seconds: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Estimated audio duration in seconds")
    video_seconds: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Estimated video duration in seconds")
    image_count: Optional[int] = Field(default=None, ge=0, description="Estimated count of generated/analyzed images")
    character_count: Optional[int] = Field(default=None, ge=0, description="Estimated count of text characters for TTS")
    request_count: int = Field(default=1, ge=1, description="Number of discrete API calls required")


class CandidateDiagnostic(AIContractModel):
    """
    Auditable diagnostic record capturing why a model candidate was chosen or rejected.
    """
    candidate_key: str = Field(description="Resolved candidate identifier (model_id or model_id@deployment_id)")
    model_id: str = Field(description="Canonical model identifier")
    provider_id: str = Field(description="Provider identifier")
    deployment_id: Optional[str] = Field(default=None, description="Deployment identifier if applicable")
    eligible: bool = Field(description="Whether the candidate passed all hard constraints")
    rejection_reasons: List[str] = Field(default_factory=list, description="List of unmet hard constraints")
    utility_score: Optional[Decimal] = Field(default=None, description="Calculated utility ranking score if eligible")
    estimated_cost: Optional[Decimal] = Field(default=None, description="Estimated execution cost")
    quality_profile: Optional[QualityTargetEnum] = Field(default=None, description="Quality tier of candidate")
    cost_profile: Optional[CostTierEnum] = Field(default=None, description="Cost tier of candidate")
    latency_profile: Optional[LatencyTierEnum] = Field(default=None, description="Latency tier of candidate")
    reliability: Optional[float] = Field(default=None, description="Historical reliability score")


class RoutingDecision(AIContractModel):
    """
    Full auditable container for a routing decision, including selection and candidate diagnostics.
    """
    selection: ModelSelection = Field(description="Canonical ModelSelection contract")
    diagnostics: List[CandidateDiagnostic] = Field(default_factory=list, description="Diagnostic audit trail for all evaluated candidates")
    policy_id: str = Field(description="Identifier of routing policy applied")
    policy_version: str = Field(description="Version of routing policy applied")
    evaluated_candidates_count: int = Field(ge=0, description="Total candidates evaluated")
    eligible_candidates_count: int = Field(ge=0, description="Candidates satisfying all hard constraints")


class QualityEvaluation(AIContractModel):
    """
    Generic domain assessment of capability output quality used to trigger escalation.
    """
    status: QualityStatusEnum = Field(description="Quality assessment outcome")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Assessor confidence score")
    reason: Optional[str] = Field(default=None, description="Description of quality deficit or achievement")
    metrics: Dict[str, JsonValue] = Field(default_factory=dict, description="Structured evaluation metrics")


class RouterError(Exception):
    """Base exception for Model Router errors."""
    pass


class NoEligibleModelError(RouterError):
    """Raised when no registered model satisfies all hard constraints."""
    def __init__(self, capability: str, reasons: List[str]):
        super().__init__(
            f"No eligible model found for capability '{capability}'. Constraints violated: {'; '.join(reasons)}"
        )
        self.capability = capability
        self.reasons = reasons
