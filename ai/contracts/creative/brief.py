"""
ai/contracts/creative/brief.py
==============================
Canonical contracts for CreativeBrief, CreativeIntent, and CreativeConstraints.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
- Semantic constraints: contradictory duration constraints are strictly rejected.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, model_validator, field_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import ProvenanceRecord


class AudioMode(str, Enum):
    """Governed canonical audio presentation modes (S28-01A)."""
    MUSIC_ONLY = "MUSIC_ONLY"
    VO_ONLY = "VO_ONLY"
    VO_MUSIC = "VO_MUSIC"
    SOURCE_AUDIO = "SOURCE_AUDIO"
    SOURCE_AUDIO_MUSIC = "SOURCE_AUDIO_MUSIC"
    SILENT = "SILENT"


class ProvenanceType(str, Enum):
    """Epistemic provenance category for individual brief dimensions (S28-03)."""
    EXPLICIT = "EXPLICIT"    # Explicitly stated by the user
    INFERRED = "INFERRED"    # Inferred from context, assets, or media intelligence
    DEFAULTED = "DEFAULTED"  # Standard platform/workspace default applied
    UNKNOWN = "UNKNOWN"      # Insufficient evidence to establish with certainty


class FieldProvenance(AIContractModel):
    """Tracks origin, epistemic classification, and rationale for a single brief field."""
    source_type: strict_enum(ProvenanceType) = Field(description="Epistemic provenance category")
    rationale: Optional[str] = Field(default=None, description="Explanation or citation for inferred or defaulted value")
    raw_reference: Optional[str] = Field(default=None, description="Exact phrase or asset attribute from which value was derived")


class CreativeIntent(AIContractModel):
    """High-level creative goal, audience, tone, and strategic intent."""
    intent_id: str = Field(description="Unique identifier for this creative intent record")
    goal: str = Field(description="Primary objective (e.g., product explainer, brand awareness, conversion ad)")
    audience: str = Field(description="Target audience demographic or psychographic profile")
    tone: str = Field(description="Intended emotional or stylistic tone (e.g., cinematic, energetic, technical)")
    key_takeaway: str = Field(description="Core concept or value proposition the viewer should retain")
    call_to_action: Optional[str] = Field(default=None, description="Explicit CTA text or action desired")
    target_platforms: List[str] = Field(default_factory=list, description="Target distribution platforms (e.g., youtube_shorts, tiktok)")
    video_type: Optional[str] = Field(default=None, description="Categorical video type (e.g., SAAS_DEMO, DYNAMIC_MONTAGE, EXPLAINER)")
    style: Optional[str] = Field(default=None, description="Creative style guideline (e.g., CLEAN, BOLD, MINIMAL)")
    pace: Optional[str] = Field(default=None, description="Pacing profile (e.g., FAST, MODERATE, DYNAMIC)")
    language: Optional[str] = Field(default=None, description="Primary language of the video content (e.g., AR, EN)")


class CreativeConstraints(AIContractModel):
    """
    Technical and stylistic boundaries for the creative generation.
    Enforces validation against contradictory constraints.
    """
    min_duration_seconds: Optional[float] = Field(default=None, ge=1.0, description="Minimum duration limit in seconds")
    max_duration_seconds: Optional[float] = Field(default=None, ge=1.0, description="Maximum duration limit in seconds")
    target_duration_seconds: Optional[float] = Field(default=None, ge=1.0, description="Ideal target duration in seconds")
    aspect_ratios: List[str] = Field(default_factory=lambda: ["9:16"], description="Permitted aspect ratios (e.g. ['9:16', '16:9'])")
    audio_mode: strict_enum(AudioMode) = Field(default=AudioMode.VO_MUSIC, description="Audio mode governing the sound architecture")
    brand_colors: List[str] = Field(default_factory=list, description="List of hexadecimal color codes (#RRGGBB)")
    excluded_templates: List[str] = Field(default_factory=list, description="Template IDs explicitly forbidden from use")
    forbidden_words: List[str] = Field(default_factory=list, description="Words or phrases strictly forbidden from scripts")
    safe_zone_margin_px: Optional[int] = Field(default=None, ge=0, description="Margin in pixels for UI safe zones")

    @field_validator("brand_colors")
    @classmethod
    def validate_hex_colors(cls, colors: List[str]) -> List[str]:
        hex_regex = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
        for color in colors:
            if not hex_regex.match(color):
                raise ValueError(f"Invalid hexadecimal color format: '{color}'")
        return colors

    @model_validator(mode="after")
    def validate_contradictory_constraints(self) -> CreativeConstraints:
        """Enforces that duration boundaries are mathematically consistent."""
        min_d = self.min_duration_seconds
        max_d = self.max_duration_seconds
        target_d = self.target_duration_seconds

        if min_d is not None and max_d is not None:
            if min_d > max_d:
                raise ValueError(
                    f"Contradictory constraints: min_duration_seconds ({min_d}) "
                    f"cannot exceed max_duration_seconds ({max_d})"
                )

        if target_d is not None:
            if min_d is not None and target_d < min_d:
                raise ValueError(
                    f"Contradictory constraints: target_duration_seconds ({target_d}) "
                    f"cannot be less than min_duration_seconds ({min_d})"
                )
            if max_d is not None and target_d > max_d:
                raise ValueError(
                    f"Contradictory constraints: target_duration_seconds ({target_d}) "
                    f"cannot exceed max_duration_seconds ({max_d})"
                )

        return self


class CreativeBrief(AIContractModel):
    """
    Canonical, structured creative brief representing the interpreted intent
    and boundary constraints derived from the user request.
    """
    brief_id: str = Field(description="Unique brief identifier")
    project_id: str = Field(description="Associated project identifier")
    workspace_id: str = Field(description="Owning workspace identifier")
    user_request_raw: str = Field(description="Original, unmodified user request prompt")
    interpreted_intent: CreativeIntent = Field(description="Structured interpretation of the creative direction")
    constraints: CreativeConstraints = Field(description="Technical and stylistic boundary constraints")
    provenance: ProvenanceRecord = Field(description="Provenance trace of brief interpretation")
    field_provenance: Dict[str, FieldProvenance] = Field(
        default_factory=dict,
        description="Per-field epistemic provenance mapping for key brief dimensions"
    )
    detected_contradictions: List[str] = Field(
        default_factory=list,
        description="Contradictions detected between user statements or constraints during parsing"
    )
    created_at: TzAwareDatetime = Field(description="UTC timestamp of brief synthesis")
    version: str = Field(default="1.0.0", description="Contract version")
