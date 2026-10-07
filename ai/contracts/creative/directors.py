"""
ai/contracts/creative/directors.py
==================================
Canonical structured recommendation contracts for Creative Directors (S28-04).

Guarantees:
- Structured, typed recommendations (Directors never return freeform text paragraphs).
- Provider neutrality: zero vendor SDK dependencies.
- Strict validation policy: unexpected fields forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
- Directors have zero runtime authority (cannot approve QC, mutate lifecycle, write registry, or authorize tools).
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.creative.brief import AudioMode


class NarrativeDirection(AIContractModel):
    """Structured editorial and narrative recommendation emitted by NarrativeDirector."""
    beat_id: str = Field(description="Target NarrativeBeat identifier")
    narrative_focus: str = Field(description="Editorial focus (e.g., 'hook_grab', 'problem_statement', 'proof_reveal', 'action_cta')")
    pacing_instruction: str = Field(description="Rhythmic pacing direction (e.g., 'accelerate_cut', 'deliberate_pause', 'rhythmic_build')")
    information_density: str = Field(description="Density target (e.g., 'minimal', 'balanced', 'dense')")
    spoken_line: Optional[str] = Field(default=None, description="Proposed voiceover sentence if spoken mode applies")
    visual_progression_cue: str = Field(description="Visual storyline requirement (e.g., 'reveal_canvas_from_void', 'cutout_assemble')")
    taste_rule_ids: List[str] = Field(default_factory=list, description="Associated TasteRule IDs influencing this direction")
    reason_summary: str = Field(default="", description="Auditable rationale summary")


class MotionDirection(AIContractModel):
    """Structured motion and animation choreography recommendation emitted by MotionDirector."""
    scene_id: str = Field(description="Target scene or beat identifier")
    motion_energy: str = Field(description="Motion energy profile ('calm', 'controlled', 'dynamic', 'explosive', 'urgent')")
    motion_personality: str = Field(description="Governing motion archetype ('Cinematic', 'Energetic', 'Playful', 'Corporate')")
    entry_style: str = Field(description="Element entrance choreography (e.g., 'fade_in_scale', 'slide_up', 'snap_edge', 'bounce_up')")
    exit_style: str = Field(description="Element exit choreography (e.g., 'accelerate_out', 'fade_out', 'static_hold')")
    camera_intent: str = Field(description="Camera motion intent (e.g., 'dive_into_word', 'whip_pan', 'slow_zoom', 'static')")
    text_motion: str = Field(description="Text reveal choreography (e.g., 'rtl_kinetic_tracking', 'word_by_word_pop', 'smooth_fade')")
    visual_hierarchy: List[str] = Field(default_factory=list, description="Visual element stacking order ('hero_text', 'peripheral_icon', etc.)")
    taste_rule_ids: List[str] = Field(default_factory=list, description="Associated TasteRule IDs influencing this direction")
    reason_summary: str = Field(default="", description="Auditable rationale summary")


class EmotionDirection(AIContractModel):
    """Structured emotional tone and energy curve recommendation emitted by EmotionDirector."""
    beat_or_scene_id: str = Field(description="Target beat or scene identifier")
    primary_emotion: str = Field(description="Core targeted emotion (e.g., 'Joy/Delight', 'Calm/Serenity', 'Urgency/Alert', 'Confidence', 'Curiosity')")
    intensity: str = Field(description="Emotional intensity ('low', 'medium', 'high')")
    emotional_progression: str = Field(description="Arc trajectory (e.g., 'tension -> curiosity -> resolution')")
    color_pairing_hint: Optional[str] = Field(default=None, description="Suggested accent palette pairing based on emotion psychology")
    taste_rule_ids: List[str] = Field(default_factory=list, description="Associated TasteRule IDs influencing this direction")
    reason_summary: str = Field(default="", description="Auditable rationale summary")


class SfxDirection(AIContractModel):
    """Structured sound design and gesture-binding recommendation emitted by SfxDirector."""
    beat_or_scene_id: str = Field(description="Target beat or scene identifier")
    audio_mode: strict_enum(AudioMode) = Field(description="Governing AudioMode policy (must be strictly respected)")
    sound_cues: List[Dict[str, JsonValue]] = Field(default_factory=list, description="Bound sound effect cues paired with visual gestures")
    ducking_profile: Optional[str] = Field(default=None, description="Audio ducking instruction (e.g., 'duck_dialogue_3db', 'none')")
    taste_rule_ids: List[str] = Field(default_factory=list, description="Associated TasteRule IDs influencing this direction")
    reason_summary: str = Field(default="", description="Auditable rationale summary")


class DirectorRecommendationBundle(AIContractModel):
    """Consolidated bundle of all creative director recommendations for a brief."""
    brief_id: str = Field(description="Associated CreativeBrief identifier")
    narrative_directions: List[NarrativeDirection] = Field(default_factory=list, description="Narrative director recommendations")
    motion_directions: List[MotionDirection] = Field(default_factory=list, description="Motion director recommendations")
    emotion_directions: List[EmotionDirection] = Field(default_factory=list, description="Emotion director recommendations")
    sfx_directions: List[SfxDirection] = Field(default_factory=list, description="SFX director recommendations")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of recommendations synthesis")
