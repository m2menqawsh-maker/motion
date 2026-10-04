"""
ai/directors/motion_director.py
===============================
Motion Director: emits structured motion energy, choreography, and camera directives (S28-04).

Guarantees:
- Structured, typed recommendation contract (MotionDirection).
- Does not author Remotion code or final timeline frame numbers.
- Tailors motion personality to brief and taste rules (Cinematic, Energetic, Playful, Corporate).
- Respects language (enforces RTL tracking for Arabic content).
- Zero runtime authority: recommends, never executes direct registry or lifecycle changes.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from ai.contracts.creative.directors import MotionDirection
from ai.contracts.creative.taste import TasteContext

logger = logging.getLogger(__name__)


class MotionDirector:
    """
    Directs camera motion, visual element hierarchy, text entrance choreography, and motion personality.
    """

    def direct(self, context: TasteContext) -> List[MotionDirection]:
        """Synthesizes motion directions for each beat in the plan."""
        brief = context.brief
        intent = brief.interpreted_intent
        lang = (intent.language or "en").lower()
        tone = (intent.tone or "").lower()
        style = (intent.style or "").lower()
        plan = context.narrative_plan

        # Determine motion archetype
        personality = self._resolve_motion_personality(tone, style)

        directions: List[MotionDirection] = []
        for beat in plan.beats:
            phase = beat.phase.lower()

            energy, entry, exit_style, camera = self._resolve_choreography_for_beat(
                phase=phase,
                personality=personality,
                pacing=beat.pacing,
            )

            # Arabic language requires RTL kinetic tracking
            if lang == "ar":
                text_motion = "rtl_kinetic_tracking"
            elif personality == "Energetic":
                text_motion = "word_by_word_pop"
            elif personality == "Playful":
                text_motion = "bouncy_spring_reveal"
            else:
                text_motion = "smooth_fade_tracking"

            # Visual hierarchy adhering to Director's signature §14 (Hero text + Peripheral elements)
            hierarchy = ["hero_text", "peripheral_elements", "background_canvas"]

            direction = MotionDirection(
                scene_id=beat.beat_id,
                motion_energy=energy,
                motion_personality=personality,
                entry_style=entry,
                exit_style=exit_style,
                camera_intent=camera,
                text_motion=text_motion,
                visual_hierarchy=hierarchy,
                taste_rule_ids=[
                    "taste_motion_personality_curves",
                    "taste_avoid_constant_motion",
                    "taste_double_variance",
                ],
                reason_summary=(
                    f"Beat {beat.beat_id} choreographed under '{personality}' personality "
                    f"with {energy} energy and {camera} camera intent."
                ),
            )
            directions.append(direction)

        return directions

    def _resolve_motion_personality(self, tone: str, style: str) -> str:
        """Maps tone and style keywords to the four canonical motion archetypes."""
        combined = f"{tone} {style}".lower()
        if any(w in combined for w in ["playful", "fun", "bouncy", "whimsical", "cute"]):
            return "Playful"
        if any(w in combined for w in ["energetic", "dynamic", "fast", "bold", "hype", "sprint"]):
            return "Energetic"
        if any(w in combined for w in ["premium", "luxury", "cinematic", "calm", "elegant", "sophisticated"]):
            return "Cinematic"
        return "Corporate"

    def _resolve_choreography_for_beat(
        self,
        phase: str,
        personality: str,
        pacing: str,
    ) -> Tuple[str, str, str, str]:
        """Resolves (energy, entry_style, exit_style, camera_intent) per beat phase and archetype."""
        if personality == "Cinematic":
            energy = "calm"
            entry = "slow_fade_scale_subtle"
            exit_style = "fade_out_smooth"
            if "hook" in phase:
                camera = "dive_into_word"
            elif "cta" in phase or "payoff" in phase:
                camera = "static"
            else:
                camera = "slow_dolly_zoom"

        elif personality == "Energetic":
            energy = "dynamic" if pacing != "fast" else "explosive"
            entry = "snap_edge_overshoot"
            exit_style = "accelerate_out"
            if "hook" in phase:
                camera = "dive_into_word"
            elif "proof" in phase or "peak" in phase:
                camera = "whip_pan"
            else:
                camera = "dynamic_punch_zoom"

        elif personality == "Playful":
            energy = "dynamic"
            entry = "bounce_up_from_below"
            exit_style = "wobble_settle"
            camera = "curved_arc_pan"

        else:  # Corporate
            energy = "controlled"
            entry = "slide_right_opacity"
            exit_style = "clean_stop"
            camera = "slow_dolly_zoom" if "hook" in phase else "static"

        return energy, entry, exit_style, camera
