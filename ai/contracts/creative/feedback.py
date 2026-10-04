"""
ai/contracts/creative/feedback.py
=================================
Canonical contracts for UserStyleProfile, CreativeFeedback, and Style Resolution.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
- Multi-tier provenance: EXPLICIT, CONFIRMED, and INFERRED tracking per dimension.
- Deterministic precedence tracing: explicit auditable trail of all style overrides.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.memory import EpistemicStatus, MemoryScope, SourceType


class FeedbackCategory(str, Enum):
    """Categorical classification of user feedback."""
    PACING = "PACING"
    MOTION = "MOTION"
    MUSIC = "MUSIC"
    CAPTION = "CAPTION"
    VISUAL = "VISUAL"
    TRANSITION = "TRANSITION"
    VOICE = "VOICE"
    GENERAL = "GENERAL"


class FeedbackTargetType(str, Enum):
    """Target entity or level of abstraction targeted by feedback."""
    SCENE = "SCENE"
    PROJECT = "PROJECT"
    TEMPLATE = "TEMPLATE"
    VIDEO_TYPE = "VIDEO_TYPE"
    GENERAL_STYLE = "GENERAL_STYLE"


class FeedbackSentiment(str, Enum):
    """Sentiment direction of creative feedback."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    CONSTRUCTIVE = "CONSTRUCTIVE"


class WinningSource(str, Enum):
    """Authority rank determining the winning creative direction."""
    CURRENT_REQUEST = "CURRENT_REQUEST"
    BRAND_CONSTRAINT = "BRAND_CONSTRAINT"
    CONFIRMED_USER_PREFERENCE = "CONFIRMED_USER_PREFERENCE"
    INFERRED_PREFERENCE = "INFERRED_PREFERENCE"
    GLOBAL_DEFAULT = "GLOBAL_DEFAULT"


class FeedbackClassification(AIContractModel):
    """
    Structured domain classification of a user critique or feedback event.
    Provides verified signals for memory policy evaluation without mutating core state.
    """
    classification_id: str = Field(description="Unique classification identifier")
    feedback_id: str = Field(description="Associated feedback event identifier")
    workspace_id: str = Field(description="Authoritative workspace boundary")
    user_id: Optional[str] = Field(default=None, description="Authoritative user identifier")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier if scoped")
    target_type: strict_enum(FeedbackTargetType) = Field(description="Scope target of feedback (e.g. SCENE, PROJECT, GENERAL_STYLE)")
    target_reference: Optional[str] = Field(default=None, description="Target entity ID such as scene_id or template_id")
    category: strict_enum(FeedbackCategory) = Field(description="Creative category (PACING, MOTION, MUSIC, etc.)")
    sentiment: strict_enum(FeedbackSentiment) = Field(description="Sentiment polarity")
    preference_dimension: Optional[str] = Field(default=None, description="Specific style dimension (e.g., 'pacing', 'motion_intensity')")
    proposed_value: Optional[str] = Field(default=None, description="Extracted preference value (e.g., 'fast', 'calm', 'low')")
    scope: strict_enum(MemoryScope) = Field(description="Recommended memory boundary scope (USER, PROJECT, etc.)")
    confidence: float = Field(ge=0.0, le=1.0, description="Domain-controlled confidence score")
    source: strict_enum(SourceType) = Field(description="Provenance source type")
    is_explicit_general_rule: bool = Field(default=False, description="True if user explicitly stated a general rule")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of classification")


class StylePreferenceProvenance(AIContractModel):
    """
    Provenance and confidence record for an individual style preference dimension.
    Distinguishes user-declared facts (EXPLICIT), repeated evidence (CONFIRMED),
    and behavioral hypotheses (INFERRED).
    """
    dimension: str = Field(description="Preference dimension (e.g., 'pacing', 'motion_intensity')")
    epistemic_status: strict_enum(EpistemicStatus) = Field(description="Epistemic status: EXPLICIT, CONFIRMED, or INFERRED")
    confidence: float = Field(ge=0.0, le=1.0, description="Domain-controlled confidence score")
    source_type: strict_enum(SourceType) = Field(description="Origin source type")
    evidence_count: int = Field(default=1, ge=1, description="Number of observed evidence instances")
    last_observed_at: TzAwareDatetime = Field(description="UTC timestamp of the most recent evidence observation")
    source_id: Optional[str] = Field(default=None, description="Originating feedback_id or memory_id")
    rationale: Optional[str] = Field(default=None, description="Auditable provenance note without hidden reasoning")


class UserStyleProfile(AIContractModel):
    """
    Persistent creative preferences associated with a user or workspace,
    informing future CreativeBrief interpretation and NarrativePlanning.
    """
    profile_id: str = Field(description="Unique profile identifier")
    workspace_id: str = Field(description="Associated workspace identifier")
    user_id: Optional[str] = Field(default=None, description="Associated user identifier if user-scoped")
    preferred_motion_personality: Optional[str] = Field(
        default=None,
        description="Preferred motion profile (e.g., 'Cinematic', 'Energetic', 'Technical', 'Playful')"
    )
    motion_intensity: Optional[str] = Field(
        default=None,
        description="Motion dynamics preference (e.g., 'low', 'medium', 'high')"
    )
    preferred_color_palette: List[str] = Field(
        default_factory=list,
        description="List of favored brand hexadecimal color codes"
    )
    pacing_preference: Optional[str] = Field(
        default=None,
        description="Rhythmic pacing preference (e.g., 'fast', 'deliberate', 'calm')"
    )
    text_density: Optional[str] = Field(
        default=None,
        description="Text density preference (e.g., 'minimal', 'balanced', 'dense')"
    )
    caption_style: Optional[str] = Field(
        default=None,
        description="Caption styling preference (e.g., 'compact', 'prominent', 'karaoke')"
    )
    music_tendencies: Optional[str] = Field(
        default=None,
        description="Musical style tendency (e.g., 'ambient', 'upbeat', 'none')"
    )
    transition_preference: Optional[str] = Field(
        default=None,
        description="Transition preference (e.g., 'subtle_dissolve', 'whip_pan', 'hard_cut')"
    )
    visual_complexity: Optional[str] = Field(
        default=None,
        description="Visual complexity level (e.g., 'minimal', 'rich', 'clean')"
    )
    preferred_voices: List[str] = Field(
        default_factory=list,
        description="Favored voice profile IDs"
    )
    disliked_patterns: List[str] = Field(
        default_factory=list,
        description="Styles or patterns explicitly disliked"
    )
    taste_preferences: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Custom taste overrides or preferences"
    )
    provenance_by_dimension: Dict[str, StylePreferenceProvenance] = Field(
        default_factory=dict,
        description="Per-dimension provenance and confidence tracking"
    )
    updated_at: TzAwareDatetime = Field(description="UTC timestamp of profile update")


class CreativeFeedback(AIContractModel):
    """
    Structured user feedback on a creative plan, storyboard, or rendered preview.
    Provides signal for aesthetic refinement without mutating core state.
    """
    feedback_id: str = Field(description="Unique feedback event identifier")
    project_id: str = Field(description="Associated project identifier")
    workspace_id: Optional[str] = Field(default=None, description="Associated workspace identifier")
    user_id: Optional[str] = Field(default=None, description="Associated user identifier")
    plan_id: Optional[str] = Field(default=None, description="Target CreativePlan identifier if applicable")
    user_rating: Optional[int] = Field(default=None, ge=1, le=5, description="1 to 5 star satisfaction score")
    liked_aspects: List[str] = Field(default_factory=list, description="Aspects praised (e.g., ['typography', 'rhythm'])")
    disliked_aspects: List[str] = Field(default_factory=list, description="Aspects criticized (e.g., ['pacing_too_fast'])")
    critique_text: Optional[str] = Field(default=None, description="Freeform qualitative feedback")
    target_type: Optional[strict_enum(FeedbackTargetType)] = Field(default=None, description="Target entity type")
    target_reference: Optional[str] = Field(default=None, description="Target entity ID")
    classification: Optional[FeedbackClassification] = Field(default=None, description="Structured classification of this feedback")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of feedback entry")


class StyleDecisionTrace(AIContractModel):
    """
    Auditable trace record for a single style dimension resolution.
    Documents what was considered, what won, whether an override occurred, and why.
    """
    dimension: str = Field(description="Style dimension evaluated")
    considered_value: Optional[str] = Field(default=None, description="Stored preference value considered")
    considered_source: Optional[str] = Field(default=None, description="Provenance or status of considered preference")
    considered_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence of considered preference")
    applied_value: Optional[str] = Field(default=None, description="Effective style value chosen")
    is_overridden: bool = Field(default=False, description="True if a higher-priority source overrode stored preference")
    override_reason: Optional[str] = Field(default=None, description="Auditable reason for override")
    winning_source: strict_enum(WinningSource) = Field(description="Precedence tier that dictated the applied value")


class EffectiveUserStyle(AIContractModel):
    """
    Compact, structured context delivered to CreativePlanner containing only
    preferences relevant to the current request with full provenance and trace records.
    Never dumps raw unorganized memory history into model context.
    """
    profile_id: Optional[str] = Field(default=None, description="Underlying profile identifier if resolved from stored profile")
    workspace_id: str = Field(description="Authoritative workspace boundary")
    user_id: Optional[str] = Field(default=None, description="Authoritative user boundary")
    pacing: Optional[str] = Field(default=None, description="Effective pacing profile")
    motion_intensity: Optional[str] = Field(default=None, description="Effective motion intensity")
    motion_personality: Optional[str] = Field(default=None, description="Effective motion personality")
    text_density: Optional[str] = Field(default=None, description="Effective text density")
    caption_style: Optional[str] = Field(default=None, description="Effective caption style")
    music_preference: Optional[str] = Field(default=None, description="Effective music direction")
    transition_style: Optional[str] = Field(default=None, description="Effective transition style")
    visual_complexity: Optional[str] = Field(default=None, description="Effective visual complexity")
    preferred_color_palette: List[str] = Field(default_factory=list, description="Favored brand hexadecimal color codes")
    preferred_voices: List[str] = Field(default_factory=list, description="Favored voice profile IDs")
    disliked_patterns: List[str] = Field(default_factory=list, description="Forbidden or disliked stylistic patterns")
    trace_records: List[StyleDecisionTrace] = Field(default_factory=list, description="Auditable precedence decision traces per dimension")
    resolved_at: TzAwareDatetime = Field(description="UTC timestamp when effective style was resolved")
