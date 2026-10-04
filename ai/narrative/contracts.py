"""
ai/narrative/contracts.py
=========================
Narrative Intelligence contract re-exports and domain types (S28-04).
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan


class NarrativeEvaluationError(Exception):
    """Base error in narrative evaluation."""
    pass


class InvalidNarrativePlanError(NarrativeEvaluationError):
    """Raised when generated NarrativePlan fails consistency or brief adherence."""
    pass


class NarrativeMetricsResult(AIContractModel):
    """Evaluated metric scores for a NarrativePlan."""
    plan_id: str = Field(description="Evaluated NarrativePlan identifier")
    goal_coverage: float = Field(ge=0.0, le=1.0, description="Goal alignment score [0.0 - 1.0]")
    logical_flow: float = Field(ge=0.0, le=1.0, description="Logical progression score [0.0 - 1.0]")
    hook_relevance: float = Field(ge=0.0, le=1.0, description="Relevance of opening hook [0.0 - 1.0]")
    redundancy_score: float = Field(ge=0.0, le=1.0, description="Redundancy penalty score (0.0 is zero redundancy)")
    duration_fit: float = Field(ge=0.0, le=1.0, description="Duration fit alignment score [0.0 - 1.0]")
    narrative_type_appropriateness: float = Field(ge=0.0, le=1.0, description="Appropriateness for video type [0.0 - 1.0]")
    passed: bool = Field(description="Whether metrics satisfy passing thresholds")
    details: Dict[str, JsonValue] = Field(default_factory=dict, description="Detailed analysis notes per metric")
