"""
ai/contracts/creative/plan.py
=============================
Canonical contracts for CreativePlan, SceneIntent, CompositionPlan, and CreativeTierDecision.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- CreativePlan = What we want to create creatively (CreativePlan ≠ Blueprint).
- CreativePlan is an advisory proposal (status: PROPOSED); never executes directly as Blueprint.
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.narrative import NarrativePlan
from ai.contracts.creative.taste import TasteDecision


class CreativeTier(str, Enum):
    """Canonical creativity tiers (S28-01A / S28-06)."""
    REUSE = "REUSE"      # Canonical registered template from template catalog
    COMPOSE = "COMPOSE"  # Composed from Lego primitive blocks in elements/scenes
    CREATE = "CREATE"    # Custom innovative component candidate


class CreativePlanStatus(str, Enum):
    """Proposal lifecycle state for creative plans."""
    PROPOSED = "PROPOSED"
    APPROVED_BY_USER = "APPROVED_BY_USER"
    REJECTED = "REJECTED"


class SceneIntent(AIContractModel):
    """Creative intent and aesthetic parameters for an individual scene."""
    scene_id: str = Field(description="Unique scene identifier (e.g., 'scene_001')")
    scene_index: int = Field(ge=0, description="Sequential position of this scene")
    beat_id: Optional[str] = Field(default=None, description="Linked NarrativeBeat ID if derived from beat")
    intent_label: str = Field(description="Scene purpose (e.g., 'hook', 'problem_statement', 'cta')")
    mood: str = Field(description="Scene mood (e.g., 'energetic', 'thoughtful')")
    motion_personality: str = Field(description="Motion personality profile (e.g., 'Cinematic', 'Energetic')")
    primary_visual_job: str = Field(description="Visual job (e.g., 'proof', 'mechanism', 'consequence', 'action')")
    estimated_duration_sec: float = Field(gt=0, description="Scene duration in seconds")
    spoken_text: Optional[str] = Field(default=None, description="Voiceover line or text delivered in scene")
    taste_decisions: List[TasteDecision] = Field(default_factory=list, description="Taste decisions governing this scene")
    asset_requirements: List[str] = Field(default_factory=list, description="High-level asset requirements (e.g., ['product_demo_screen', 'brand_logo'])")
    audio_intent: Optional[str] = Field(default=None, description="Audio treatment intent (e.g., 'ambient_music_with_whoosh', 'silence')")
    template_requirements: List[str] = Field(default_factory=list, description="Template capability/category requirements (e.g., ['text_with_device', 'minimal_quote'])")


class CompositionLayer(AIContractModel):
    """A visual layer within a multi-layer composition hierarchy."""
    layer_type: str = Field(description="Layer category: 'primary' (100%), 'secondary' (30-50%), or 'ambient' (10-20%)")
    element_ref: str = Field(description="Reference to template, asset, or primitive component")
    properties: Dict[str, JsonValue] = Field(default_factory=dict, description="Layer-specific motion and style props")


class CompositionPlan(AIContractModel):
    """Spatial, layer, and choreography plan for a scene."""
    composition_id: str = Field(description="Unique composition plan identifier")
    scene_id: str = Field(description="Associated scene identifier")
    base_template_or_primitive: str = Field(description="Primary visual anchor or template")
    layers: List[CompositionLayer] = Field(default_factory=list, description="Staged composition layers")
    layout_zone: str = Field(default="full", description="Layout zone on canvas (e.g., 'full', 'top_split', 'bottom_card')")
    camera_motion: Optional[str] = Field(default=None, description="Camera directive (e.g., 'dive_into_word', 'static', 'whip_pan')")
    gestural_elements: List[str] = Field(default_factory=list, description="Visual gestures (e.g., ['Neon Ring', 'Marker Underline'])")
    sfx_bindings: List[Dict[str, JsonValue]] = Field(default_factory=list, description="SFX cues bound to visual moments")
    transition: Optional[str] = Field(default=None, description="Optional transition out (e.g., 'fade', 'slide')")
    effects: List[str] = Field(default_factory=list, description="Optional registered effects applied")


class ReuseCandidateScore(AIContractModel):
    """Detailed score and eligibility evaluation for a template candidate in REUSE search."""
    template_id: str = Field(description="Canonical template ID")
    eligible: bool = Field(description="Whether template passed all hard compatibility filters")
    hard_filter_failures: List[str] = Field(default_factory=list, description="Reasons for hard filter rejection")
    fit_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall suitability fit score (0.0 - 1.0)")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Component scores (style, motion, content, duration, media)")
    sufficient: bool = Field(default=False, description="Whether template passes sufficiency threshold for direct REUSE")


class ReuseEvaluationResult(AIContractModel):
    """Structured audit evidence of REUSE search and suitability evaluation."""
    need_description: str = Field(description="Description of requested scene intent or creative need")
    candidates_checked: List[str] = Field(default_factory=list, description="All registered templates evaluated")
    eligible_candidates: List[str] = Field(default_factory=list, description="Candidates passing hard compatibility filters")
    ranked_candidates: List[ReuseCandidateScore] = Field(default_factory=list, description="Ranked candidates with scores")
    selected_candidate: Optional[str] = Field(default=None, description="Selected canonical template ID if REUSE sufficient")
    rejection_reasons: Dict[str, List[str]] = Field(default_factory=dict, description="Reasons for candidate rejections")
    sufficiency: bool = Field(description="Whether REUSE was found to be sufficient")
    rationale: str = Field(description="Human/audit readable summary of REUSE evaluation")


class ComposeComponentRef(AIContractModel):
    """Reference and role of a registered primitive component in a composition."""
    component_id: str = Field(description="Canonical registered element or effect ID")
    component_type: str = Field(description="Component category: element, effect, transition, overlay, ui-block")
    role: str = Field(description="Role within composition (e.g. background, hero_text, stat_display, transition)")
    props: Dict[str, JsonValue] = Field(default_factory=dict, description="Props bound to this component")


class ComposeEvaluationResult(AIContractModel):
    """Structured audit evidence of COMPOSE planning and suitability evaluation."""
    need_description: str = Field(description="Description of requested scene intent or creative need")
    components_checked: List[str] = Field(default_factory=list, description="Registered Lego components considered")
    eligible_components: List[str] = Field(default_factory=list, description="Registered components passing compatibility")
    composition_plan: Optional[CompositionPlan] = Field(default=None, description="Synthesized CompositionPlan if valid")
    rejection_reasons: List[str] = Field(default_factory=list, description="Reasons why composition could not satisfy need")
    sufficiency: bool = Field(description="Whether COMPOSE was found to be sufficient")
    rationale: str = Field(description="Human/audit readable summary of COMPOSE evaluation")


class CreativeTierDecision(AIContractModel):
    """Explicit decision selecting the implementation tier for a scene."""
    decision_id: str = Field(description="Unique decision identifier")
    scene_id: str = Field(description="Target scene identifier")
    selected_tier: strict_enum(CreativeTier) = Field(description="Selected implementation tier (REUSE, COMPOSE, CREATE)")
    rationale: str = Field(description="Justification for why this tier is optimal for this scene")
    template_ref: Optional[str] = Field(default=None, description="Template identifier if REUSE")
    composite_elements: List[str] = Field(default_factory=list, description="List of primitive elements if COMPOSE")
    needs_create_evaluation: bool = Field(default=False, description="Flag indicating candidate creation was evaluated prior to selecting CREATE")
    # S28-06 Evidence & Audit Extensions
    requested_need: Optional[str] = Field(default=None, description="Creative need or intent description")
    reuse_candidates_checked: List[str] = Field(default_factory=list, description="IDs of registered templates evaluated for REUSE")
    reuse_result: Optional[ReuseEvaluationResult] = Field(default=None, description="Structured REUSE evaluation evidence")
    compose_candidates_checked: List[str] = Field(default_factory=list, description="IDs of components evaluated for COMPOSE")
    compose_result: Optional[ComposeEvaluationResult] = Field(default=None, description="Structured COMPOSE evaluation evidence")
    composition_plan: Optional[CompositionPlan] = Field(default=None, description="Resolved composition plan if COMPOSE")

    @model_validator(mode="after")
    def validate_tier_evidence(self) -> CreativeTierDecision:
        if self.selected_tier == CreativeTier.CREATE:
            if not self.needs_create_evaluation:
                raise ValueError(
                    "Invalid CreativeTierDecision: selected_tier is CREATE, but needs_create_evaluation is False."
                )
            if self.reuse_result is None or self.reuse_result.sufficiency:
                raise ValueError(
                    "Invalid CreativeTierDecision: selected_tier is CREATE, but REUSE evidence is missing or marked sufficient."
                )
            if self.compose_result is None or self.compose_result.sufficiency:
                raise ValueError(
                    "Invalid CreativeTierDecision: selected_tier is CREATE, but COMPOSE evidence is missing or marked sufficient."
                )
        return self


class CreativePlan(AIContractModel):
    """
    Canonical creative proposal specifying what we want to create creatively.
    Advisory artifact: requires user approval before compiling to Blueprint v2.
    """
    plan_id: str = Field(description="Unique plan identifier")
    brief_id: str = Field(description="Associated CreativeBrief identifier")
    recipe_id: str = Field(description="Associated RecipeDefinition identifier")
    title: str = Field(description="Working title of the video")
    narrative_plan: NarrativePlan = Field(description="Underlying narrative arc")
    scenes: List[SceneIntent] = Field(min_length=1, description="Sequential scene intents")
    compositions: List[CompositionPlan] = Field(default_factory=list, description="Spatial composition plans")
    tier_decisions: List[CreativeTierDecision] = Field(default_factory=list, description="Tier decisions per scene")
    total_estimated_duration_sec: float = Field(gt=0, description="Total planned duration in seconds")
    status: strict_enum(CreativePlanStatus) = Field(
        default=CreativePlanStatus.PROPOSED,
        description="Creative proposal status (never automatically APPROVED)"
    )
    provenance: ProvenanceRecord = Field(description="Provenance trace of creative planning")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of plan generation")

    @model_validator(mode="after")
    def validate_scene_durations(self) -> CreativePlan:
        """Verifies scene sequencing and duration sum."""
        total_calc = sum(s.estimated_duration_sec for s in self.scenes)
        if abs(total_calc - self.total_estimated_duration_sec) > 0.5:
            raise ValueError(
                f"total_estimated_duration_sec ({self.total_estimated_duration_sec}) does not match "
                f"sum of scene durations ({round(total_calc, 2)})"
            )
        return self


class CreativePlanValidationResult(AIContractModel):
    """Structured result of CreativePlan validation (S28-05)."""
    valid: bool = Field(description="Whether the CreativePlan is valid and ready for compilation")
    errors: List[str] = Field(default_factory=list, description="Explicit failure messages if invalid")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warning advisories")
    checked_invariants: List[str] = Field(default_factory=list, description="Audit checklist of verified invariants")


class ResolvedTemplateDecision(AIContractModel):
    """External/trusted template decision input for BlueprintCompiler (S28-05)."""
    scene_id: str = Field(description="Target scene identifier")
    template_id: str = Field(description="Canonical template ID from template catalog")
    template_props: Dict[str, JsonValue] = Field(default_factory=dict, description="Resolved template properties")


class BlueprintCompilationResult(AIContractModel):
    """Structured result of Blueprint compilation (S28-05)."""
    success: bool = Field(description="Whether compilation succeeded")
    blueprint: Optional[Dict[str, JsonValue]] = Field(default=None, description="Canonical Blueprint v2 data dictionary")
    compiler_version: str = Field(default="1.0.0", description="Compiler version")
    errors: List[str] = Field(default_factory=list, description="Compilation errors if failed")
    warnings: List[str] = Field(default_factory=list, description="Compilation warnings")

