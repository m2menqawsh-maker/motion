"""
ai/contracts/creative/conflict.py
=================================
Canonical contracts for CreativeConflict and ResolvedCreativeGuidance (S28-04).

Guarantees:
- Explicit conflict detection and resolution tracking.
- Precedence hierarchy:
  1. HARD_SYSTEM_CONSTRAINT (AudioMode, authorization, core bounds)
  2. USER_EXPLICIT_REQUIREMENT (User brief explicit intent/constraints)
  3. RECIPE_CONSTRAINT (Recipe workflow capabilities/bounds)
  4. DIRECTOR_RECOMMENDATION (Creative Director structured advice)
  5. SOFT_TASTE_PREFERENCE (Advisory style rules)
- Unresolvable hard conflicts result in explicit status FAILED_UNRESOLVED_CONFLICT
  rather than silently proceeding with contradictory directives.
- Strict validation policy: unexpected fields forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.directors import (
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.narrative import NarrativePlan
from ai.contracts.creative.taste import TasteDecision


class ConflictPrecedenceRank(str, Enum):
    """Hierarchical precedence authority for resolving competing creative directives."""
    HARD_SYSTEM_CONSTRAINT = "HARD_SYSTEM_CONSTRAINT"
    USER_EXPLICIT_REQUIREMENT = "USER_EXPLICIT_REQUIREMENT"
    RECIPE_CONSTRAINT = "RECIPE_CONSTRAINT"
    DIRECTOR_RECOMMENDATION = "DIRECTOR_RECOMMENDATION"
    SOFT_TASTE_PREFERENCE = "SOFT_TASTE_PREFERENCE"


class ConflictSeverity(str, Enum):
    """Classification of conflict impact."""
    HARD = "HARD"
    CREATIVE_TENSION = "CREATIVE_TENSION"


class ConflictStatus(str, Enum):
    """Lifecycle status of a detected creative conflict."""
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class CreativeConflict(AIContractModel):
    """
    Structured representation of a detected creative contradiction or tension.
    Records conflicting parties, competing directives, applied precedence, and outcome.
    """
    conflict_id: str = Field(description="Unique conflict identifier")
    conflict_type: str = Field(description="Categorical conflict type (e.g., 'PACING_MISMATCH', 'STYLE_TENSION', 'AUDIO_MODE_VIOLATION')")
    severity: strict_enum(ConflictSeverity) = Field(description="Conflict severity (HARD vs CREATIVE_TENSION)")
    description: str = Field(description="Clear explanation of what is in contradiction")
    conflicting_parties: List[str] = Field(description="Identities of conflicting sources (e.g., ['Recipe:fast_paced', 'User:calm_premium'])")
    competing_directives: Dict[str, JsonValue] = Field(description="Concrete competing values or directives")
    applied_precedence: strict_enum(ConflictPrecedenceRank) = Field(description="Authority precedence applied during resolution")
    resolved_directive: Optional[Dict[str, JsonValue]] = Field(default=None, description="The winning directive chosen by resolution policy")
    status: strict_enum(ConflictStatus) = Field(description="Resolution status ('RESOLVED' or 'UNRESOLVED')")
    reason_summary: str = Field(description="Auditable summary explaining why resolution was chosen without hidden CoT")


class ResolvedCreativeGuidance(AIContractModel):
    """
    Consolidated output of S28-04 Narrative Intelligence, Taste Engine,
    Creative Directors, and Conflict Resolution.
    Advisory guidance ready for S28-05 Creative Planning.
    """
    guidance_id: str = Field(description="Unique guidance run identifier")
    brief_id: str = Field(description="Associated CreativeBrief identifier")
    recipe_id: str = Field(description="Associated recipe identifier")
    narrative_plan: NarrativePlan = Field(description="Underlying narrative arc")
    taste_decisions: List[TasteDecision] = Field(description="Applied taste decisions from TasteEngine")
    narrative_directions: List[NarrativeDirection] = Field(default_factory=list, description="Narrative director guidance")
    motion_directions: List[MotionDirection] = Field(default_factory=list, description="Motion director guidance")
    emotion_directions: List[EmotionDirection] = Field(default_factory=list, description="Emotion director guidance")
    sfx_directions: List[SfxDirection] = Field(default_factory=list, description="SFX director guidance")
    detected_conflicts: List[CreativeConflict] = Field(default_factory=list, description="All detected creative conflicts")
    unresolved_conflicts: List[CreativeConflict] = Field(default_factory=list, description="Any unresolved conflicts")
    status: str = Field(default="SUCCESS", description="Guidance resolution status ('SUCCESS' or 'FAILED_UNRESOLVED_CONFLICT')")
    provenance: ProvenanceRecord = Field(description="Provenance trace of creative intelligence execution")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of guidance generation")
