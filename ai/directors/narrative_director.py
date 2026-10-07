"""
ai/directors/narrative_director.py
==================================
Narrative Director: emits structured editorial, pacing, and beat alignment guidance (S28-04).

Guarantees:
- Structured, typed recommendation contract (NarrativeDirection).
- Does not rebuild IntentParser or RecipeSelector.
- Strictly adheres to AudioMode (suppresses spoken script lines in MUSIC_ONLY and SILENT modes).
- Zero runtime authority: recommends and guides, never approves QC or mutates lifecycle.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.directors import NarrativeDirection
from ai.contracts.creative.taste import TasteContext

logger = logging.getLogger(__name__)


class NarrativeDirector:
    """
    Directs editorial arc, beat pacing, and information density following NarrativePlan synthesis.
    """

    def direct(self, context: TasteContext) -> List[NarrativeDirection]:
        """Synthesizes structured narrative directions for each beat in the plan."""
        plan = context.narrative_plan
        audio_mode = context.brief.constraints.audio_mode
        directions: List[NarrativeDirection] = []

        is_spoken_mode = audio_mode in [
            AudioMode.VO_ONLY,
            AudioMode.VO_MUSIC,
            AudioMode.SOURCE_AUDIO,
            AudioMode.SOURCE_AUDIO_MUSIC,
        ]

        for beat in plan.beats:
            phase = beat.phase.lower()

            # Editorial focus and density calibration
            if any(p in phase for p in ["hook", "spark", "intro", "visual_hook"]):
                focus = "hook_grab"
                pacing = "accelerate_cut"
                density = "minimal"
                visual_cue = "Bold visual headline with immediate visual tension"
            elif any(p in phase for p in ["problem", "agitation"]):
                focus = "problem_statement"
                pacing = "rhythmic_build"
                density = "balanced"
                visual_cue = "Visual friction demonstrating friction or broken workflow"
            elif any(p in phase for p in ["solution", "mechanism", "foundation"]):
                focus = "mechanism_reveal"
                pacing = "deliberate_pause"
                density = "dense"
                visual_cue = "Smooth architectural or interface breakdown showing solution"
            elif any(p in phase for p in ["proof", "example", "energy_peak"]):
                focus = "proof_demonstration"
                pacing = "accelerate_cut"
                density = "balanced"
                visual_cue = "Concrete metric, stat counter, or dynamic collage proof"
            elif any(p in phase for p in ["cta", "payoff", "summary", "wrap_up"]):
                focus = "action_cta"
                pacing = "deliberate_pause"
                density = "minimal"
                visual_cue = "Clean hero typography resting on elegant dark brand background"
            else:
                focus = "thematic_development"
                pacing = "rhythmic_build"
                density = "balanced"
                visual_cue = "Thematic visual progression aligned with key takeaway"

            # Spoken line assignment respecting AudioMode
            spoken_line = beat.key_message if is_spoken_mode else None

            direction = NarrativeDirection(
                beat_id=beat.beat_id,
                narrative_focus=focus,
                pacing_instruction=pacing,
                information_density=density,
                spoken_line=spoken_line,
                visual_progression_cue=visual_cue,
                taste_rule_ids=["taste_beat_density", "taste_visual_rest"],
                reason_summary=f"Directing {beat.phase} towards {focus} with {pacing} pacing.",
            )
            directions.append(direction)

        return directions
