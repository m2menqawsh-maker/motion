"""
ai/contracts/creative/recipe.py
===============================
Canonical contracts for RecipeDefinition, RecipeStage, and RecipeSelection.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Recipe = What happens and in what order (Recipe ≠ Prompt, Recipe ≠ Provider).
- Provider neutrality: zero hardcoded third-party provider SDKs or vendor names.
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, ProvenanceRecord
from ai.contracts.creative.brief import AudioMode


class RecipeStage(AIContractModel):
    """An execution stage within a production recipe."""
    stage_id: str = Field(description="Stage identifier (e.g., 'stage_brief', 'stage_storyboard')")
    title: str = Field(description="Human-readable stage title")
    actions: List[str] = Field(min_length=1, description="List of concrete actions performed in this stage")
    required_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Provider-neutral capabilities needed for this stage"
    )
    artifacts: List[str] = Field(default_factory=list, description="Expected deliverable artifact identifiers")
    paid_generation: bool = Field(default=False, description="Flag indicating if stage consumes paid AI generation")


class RecipeDefinition(AIContractModel):
    """
    Formal recipe definition specifying stages, topology, routing, and deliverables.
    Adheres strictly to provider neutrality: capabilities over vendors.
    """
    recipe_id: str = Field(description="Unique recipe identifier (e.g., 'living-canvas-explainer')")
    name: str = Field(description="Human-readable recipe name")
    version: str = Field(default="1.0.0", description="Semver version of this recipe")
    description: str = Field(description="Comprehensive description of what this recipe produces")
    best_for: List[str] = Field(min_length=1, description="Recommended use cases")
    not_for: List[str] = Field(default_factory=list, description="Anti-patterns or unsuited use cases")
    platforms: List[str] = Field(min_length=1, description="Supported social/distribution platforms")
    aspect_ratios: List[str] = Field(min_length=1, description="Supported aspect ratios (e.g., ['9:16', '16:9'])")
    duration_seconds_min: float = Field(gt=0, description="Minimum recommended duration")
    duration_seconds_max: float = Field(gt=0, description="Maximum recommended duration")
    duration_seconds_target: float = Field(gt=0, description="Target optimal duration")
    stages: List[RecipeStage] = Field(min_length=1, description="Ordered sequence of production stages")
    owner: str = Field(default="CreativePlatform", description="Owning team or authority responsible for recipe maintenance")
    supported_intents: List[str] = Field(default_factory=list, description="Supported canonical intent or video types")
    supported_platforms: List[str] = Field(default_factory=list, description="Explicit supported platforms")
    supported_audio_modes: List[strict_enum(AudioMode)] = Field(default_factory=list, description="Supported audio modes")
    required_skills: List[str] = Field(default_factory=list, description="IDs of skills required")
    required_knowledge: List[str] = Field(default_factory=list, description="Knowledge IDs required by this recipe")
    required_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Provider-neutral capabilities required across the entire recipe"
    )
    optional_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Optional capabilities that may be utilized by this recipe"
    )
    forbidden_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities strictly forbidden in this recipe"
    )
    phases: List[str] = Field(default_factory=list, description="Ordered production phases")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite assets or tool dependencies")
    quality_profile: Optional[str] = Field(default="STANDARD", description="Target quality profile")
    budget_profile: Optional[str] = Field(default="STANDARD", description="Target budget profile")
    fallback_strategy: Optional[str] = Field(default=None, description="Typed fallback strategy or alternative recipe ID")
    routing_keywords: List[str] = Field(min_length=1, description="Keywords matching user intent to this recipe")
    routing_negative_keywords: List[str] = Field(default_factory=list, description="Keywords that disqualify this recipe")
    deliverables: List[str] = Field(min_length=1, description="Expected end-product deliverables")

    @model_validator(mode="after")
    def validate_duration_bounds(self) -> RecipeDefinition:
        if self.duration_seconds_min > self.duration_seconds_max:
            raise ValueError(
                f"duration_seconds_min ({self.duration_seconds_min}) cannot exceed "
                f"duration_seconds_max ({self.duration_seconds_max})"
            )
        if not (self.duration_seconds_min <= self.duration_seconds_target <= self.duration_seconds_max):
            raise ValueError(
                f"duration_seconds_target ({self.duration_seconds_target}) must fall between "
                f"min ({self.duration_seconds_min}) and max ({self.duration_seconds_max})"
            )
        return self


class RecipeSelection(AIContractModel):
    """
    Record of a recipe routing decision matching a CreativeBrief to a specific RecipeDefinition.
    """
    selection_id: str = Field(description="Unique selection decision identifier")
    brief_id: str = Field(description="Associated CreativeBrief identifier")
    selected_recipe_id: str = Field(description="ID of the chosen RecipeDefinition")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score of the match [0.0 - 1.0]")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords from the brief that triggered match")
    alternative_recipe_ids: List[str] = Field(default_factory=list, description="Fallback or runner-up recipe IDs")
    selection_rationale: str = Field(description="Explainable justification for the selection")
    required_skills: List[str] = Field(default_factory=list, description="IDs of skills required by selected recipe")
    required_knowledge: List[str] = Field(default_factory=list, description="IDs of knowledge descriptors required by selected recipe")
    excluded_recipe_ids: Dict[str, str] = Field(default_factory=dict, description="Disqualified candidate recipe IDs with rejection rationale")
    selection_reasons: List[str] = Field(default_factory=list, description="Audit-ready selection evidence lines")
    provenance: ProvenanceRecord = Field(description="Provenance trace of the routing decision")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of selection")
