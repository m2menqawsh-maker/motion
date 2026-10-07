"""
ai/directors/emotion_director.py
================================
Emotion Director: emits structured emotional progression and color pairing advice (S28-04).

Guarantees:
- Structured, typed recommendation contract (EmotionDirection).
- Uses emotion-to-motion mapping rules from references/4_taste_engine/emotion-mapping.md.
- Recommends emotional progression without inventing ungrounded user requirements.
- Zero runtime authority.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from ai.contracts.creative.directors import EmotionDirection
from ai.contracts.creative.taste import TasteContext

logger = logging.getLogger(__name__)


class EmotionDirector:
    """
    Directs emotional trajectory, target emotion per beat, and psychological color hints.
    """

    def direct(self, context: TasteContext) -> List[EmotionDirection]:
        """Synthesizes structured emotion directions for each beat in the plan."""
        plan = context.narrative_plan
        directions: List[EmotionDirection] = []

        for i, beat in enumerate(plan.beats):
            phase = beat.phase.lower()
            target_emotion = beat.emotional_target or "Confidence"

            # Derive intensity based on position in arc
            if i == 0:
                intensity = "high"
                progression = "hook_curiosity -> audience_focus"
                color_hint = "Electric Teal / Neon Accent on Dark Base"
            elif i == len(plan.beats) - 1:
                intensity = "high"
                progression = "resolution -> confident_action"
                color_hint = "Emerald Green / Pure Brand Accent for Success"
            elif any(p in phase for p in ["problem", "agitation"]):
                intensity = "medium"
                progression = "curiosity -> tension"
                color_hint = "Crimson Accent or Warning Amber"
            elif any(p in phase for p in ["solution", "mechanism", "foundation"]):
                intensity = "medium"
                progression = "tension -> relief_and_delight"
                color_hint = "Deep Indigo & Soft White"
            else:
                intensity = "medium"
                progression = "delight -> confidence"
                color_hint = "Teal / Cyan Modern Clarity"

            direction = EmotionDirection(
                beat_or_scene_id=beat.beat_id,
                primary_emotion=target_emotion,
                intensity=intensity,
                emotional_progression=progression,
                color_pairing_hint=color_hint,
                taste_rule_ids=["taste_color_discipline"],
                reason_summary=(
                    f"Directing beat {beat.beat_id} to '{target_emotion}' ({intensity} intensity) "
                    f"with trajectory '{progression}'."
                ),
            )
            directions.append(direction)

        return directions
