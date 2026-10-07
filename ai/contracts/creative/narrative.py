"""
ai/contracts/creative/narrative.py
==================================
Canonical contracts for NarrativePlan and NarrativeBeat.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
- Semantic invariants: beat indices must be sequential and durations positive.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime
from ai.contracts.common import ProvenanceRecord


class NarrativeBeat(AIContractModel):
    """An individual story beat within a narrative progression."""
    beat_id: str = Field(description="Unique beat identifier")
    beat_index: int = Field(ge=0, description="0-indexed sequence position of this beat")
    phase: str = Field(description="Story phase (e.g., hook, setup, problem, mechanism, proof, cta, resolution)")
    emotional_target: str = Field(description="Target emotional tone (e.g., curiosity, trust, urgency, delight)")
    pacing: str = Field(description="Rhythmic pacing for this beat (e.g., fast, moderate, slow, pause)")
    estimated_duration_sec: float = Field(gt=0, description="Estimated duration in seconds")
    key_message: str = Field(description="Core message or narrative objective of this beat")
    visual_hook_description: Optional[str] = Field(default=None, description="Descriptive visual concept for the beat")
    sound_effect_cue: Optional[str] = Field(default=None, description="Recommended SFX or audio accent")


class NarrativePlan(AIContractModel):
    """
    Structured narrative arc ordering story beats before visual composition.
    Enforces sequential consistency across story beats.
    """
    narrative_id: str = Field(description="Unique identifier for this narrative plan")
    brief_id: str = Field(description="Associated CreativeBrief identifier")
    core_hook: str = Field(description="Opening hook statement or visual proposition")
    beats: List[NarrativeBeat] = Field(min_length=1, description="Ordered sequence of narrative beats")
    arc_structure: str = Field(description="Structural taxonomy (e.g., Three-Act, Hook-Proof-CTA, Living Canvas)")
    estimated_total_duration_sec: float = Field(gt=0, description="Sum of estimated beat durations")
    provenance: ProvenanceRecord = Field(description="Provenance trace of narrative planning")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of plan synthesis")

    @model_validator(mode="after")
    def validate_beats_consistency(self) -> NarrativePlan:
        """Verifies that beat indices are strictly ascending and durations align."""
        expected_index = 0
        calculated_total = 0.0
        for beat in self.beats:
            if beat.beat_index != expected_index:
                raise ValueError(
                    f"Beat indices must be strictly sequential starting at 0. "
                    f"Expected {expected_index}, got {beat.beat_index} on beat '{beat.beat_id}'"
                )
            expected_index += 1
            calculated_total += beat.estimated_duration_sec

        # Check total duration approximation within floating tolerance
        if abs(calculated_total - self.estimated_total_duration_sec) > 0.5:
            raise ValueError(
                f"estimated_total_duration_sec ({self.estimated_total_duration_sec}) does not match "
                f"sum of beat durations ({round(calculated_total, 2)})"
            )

        return self
