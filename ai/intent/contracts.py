"""
ai/intent/contracts.py
======================
Contracts and models for Intent Understanding and Evaluation (S28-03).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.creative.brief import AudioMode, FieldProvenance, ProvenanceType


class ContradictoryRequestError(ValueError):
    """Raised when contradictory constraints or requirements are detected in a user request."""
    pass


class IntentParseResult(AIContractModel):
    """Structured extraction of user creative intent and epistemic provenance."""
    user_request_raw: str = Field(description="Raw user prompt")
    detected_language: str = Field(description="Primary detected language (AR, EN, or MIXED)")
    goal: str = Field(description="Synthesized primary goal")
    video_type: Optional[str] = Field(default=None, description="Categorical video type")
    target_platforms: List[str] = Field(default_factory=list, description="Target platforms")
    audio_mode: strict_enum(AudioMode) = Field(description="Governing audio mode")
    target_duration_seconds: Optional[float] = Field(default=None, description="Target duration in seconds")
    min_duration_seconds: Optional[float] = Field(default=None, description="Min duration in seconds")
    max_duration_seconds: Optional[float] = Field(default=None, description="Max duration in seconds")
    style: Optional[str] = Field(default=None, description="Stylistic direction (e.g. CLEAN, BOLD)")
    pace: Optional[str] = Field(default=None, description="Pacing profile (e.g. FAST, MODERATE)")
    tone: str = Field(default="neutral", description="Emotional or narrative tone")
    brand_colors: List[str] = Field(default_factory=list, description="Extracted brand color hex codes")
    key_takeaway: str = Field(default="", description="Core message to convey")
    call_to_action: Optional[str] = Field(default=None, description="Explicit CTA")
    field_provenance: Dict[str, FieldProvenance] = Field(
        default_factory=dict,
        description="Epistemic provenance for each key field"
    )
    detected_contradictions: List[str] = Field(
        default_factory=list,
        description="Contradictions detected between user statements"
    )


class IntentEvaluationCase(AIContractModel):
    """Individual benchmark test case for Intent Understanding."""
    case_id: str
    user_request: str
    language: str
    category: str  # short, vague, detailed, contradictory
    expected_intent: Optional[str] = None
    expected_audio_mode: Optional[str] = None
    expected_platform: Optional[str] = None
    expected_pace: Optional[str] = None
    expected_style: Optional[str] = None
    expected_provenance_types: Dict[str, str] = Field(default_factory=dict)
    has_contradiction: bool = False
    context_assets: Optional[List[Dict[str, Any]]] = None
    workspace_constraints: Optional[Dict[str, Any]] = None


class IntentEvaluationReport(AIContractModel):
    """Machine-readable report summarizing intent parser evaluation metrics."""
    total_cases: int
    intent_accuracy: float = Field(ge=0.0, le=1.0)
    field_accuracy: float = Field(ge=0.0, le=1.0)
    per_field_accuracy: Dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy broken down per individual brief field (video_type, platform, duration, language, audio_mode, style, pace)"
    )
    wrong_explicit_field_count: int = Field(
        default=0,
        description="Number of fields where the system incorrectly extracted a wrong EXPLICIT value"
    )
    unsupported_inferred_or_defaulted_field_count: int = Field(
        default=0,
        description="Number of fields where the system made an unsupported inference or unwarranted default"
    )
    unsupported_inference_rate: float = Field(ge=0.0, le=1.0)
    contradiction_detection_rate: float = Field(ge=0.0, le=1.0)
    cases_passed: int
    cases_failed: int
    failure_details: List[Dict[str, Any]] = Field(default_factory=list)

