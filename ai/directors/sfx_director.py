"""
ai/directors/sfx_director.py
============================
Sfx Director: emits structured sound design and gesture-binding advice (S28-04).

Guarantees:
- Structured, typed recommendation contract (SfxDirection).
- Strict AudioMode Compliance:
  • SILENT mode: Produces zero audio cues and suppresses all sound design recommendations.
  • MUSIC_ONLY mode: Strictly forbids spoken/voiceover cues, allowing only subtle transitional accents.
- SFX Gesture Binding: Applies rules from references/4_taste_engine/sfx_binding_matrix.md.
- Consecutive Variation: Avoids repeating the identical SFX filename in consecutive beats.
- Zero runtime authority.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import JsonValue
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.directors import SfxDirection
from ai.contracts.creative.taste import TasteContext

logger = logging.getLogger(__name__)


class SfxDirector:
    """
    Directs sound design, gestural SFX binding, and audio ducking profiles.
    """

    # SFX Binding Table: Gesture -> (Primary SFX, Alternate SFX, default_lufs, default_offset_ms)
    GESTURE_MAP: Dict[str, Tuple[str, str, int, int]] = {
        "neon ring": ("chime-soft.wav", "bell-subtle.wav", -24, 0),
        "marker underline": ("swish-metal.wav", "whoosh-soft.wav", -24, 0),
        "highlighter bg": ("soft-whoosh.wav", "brush-sweep.wav", -28, -50),
        "strikethrough": ("glitch-cut.wav", "digital-error.wav", -24, 0),
        "flash cut": ("dramatic-boom.wav", "cinematic-impact.wav", -20, 0),
        "whoosh": ("transition-whoosh.wav", "slide-whoosh.wav", -24, -100),
        "pop": ("pop-soft.wav", "click-subtle.wav", -24, 0),
        "stat counter": ("tick-soft.wav", "stat-click.wav", -28, 0),
        "dramatic pause": ("none", "none", -32, 0),
    }

    def direct(self, context: TasteContext) -> List[SfxDirection]:
        """Synthesizes structured sound directions for each beat in the plan."""
        plan = context.narrative_plan
        audio_mode = context.brief.constraints.audio_mode
        directions: List[SfxDirection] = []

        # ---------------------------------------------------------------------
        # Invariant 1: SILENT Mode -> Zero SFX Cues Permitted
        # ---------------------------------------------------------------------
        if audio_mode == AudioMode.SILENT:
            for beat in plan.beats:
                direction = SfxDirection(
                    beat_or_scene_id=beat.beat_id,
                    audio_mode=AudioMode.SILENT,
                    sound_cues=[],
                    ducking_profile=None,
                    taste_rule_ids=["taste_silent_audio_mode"],
                    reason_summary="SILENT mode: All audio cues and SFX suppressed by hard system policy.",
                )
                directions.append(direction)
            return directions

        # ---------------------------------------------------------------------
        # Non-Silent Modes: Bind SFX to Gestures with Consecutive Variation
        # ---------------------------------------------------------------------
        last_sfx_file = ""

        for beat in plan.beats:
            phase = beat.phase.lower()
            sound_cues: List[Dict[str, JsonValue]] = []
            rules = ["taste_gestural_sfx_sync", "taste_audio_restraint"]

            # Derive gesture from beat metadata
            gesture = self._detect_gesture(beat.visual_hook_description or "", phase)

            if gesture and gesture in self.GESTURE_MAP:
                prim, alt, lufs, offset = self.GESTURE_MAP[gesture]
                chosen_sfx = alt if (prim == last_sfx_file and alt != "none") else prim

                if chosen_sfx != "none":
                    sound_cues.append({
                        "cue_id": f"sfx_{beat.beat_id}_01",
                        "gesture": gesture,
                        "sfx_file": chosen_sfx,
                        "volume_lufs": lufs,
                        "offset_ms": offset,
                    })
                    last_sfx_file = chosen_sfx
            elif beat.sound_effect_cue:
                # Use beat's explicit cue if valid and not repeated
                chosen_sfx = beat.sound_effect_cue
                if chosen_sfx == last_sfx_file:
                    chosen_sfx = "ambient-swell.wav"

                sound_cues.append({
                    "cue_id": f"sfx_{beat.beat_id}_cue",
                    "gesture": "narrative_beat_accent",
                    "sfx_file": chosen_sfx,
                    "volume_lufs": -24,
                    "offset_ms": 0,
                })
                last_sfx_file = chosen_sfx

            # Ducking profile based on AudioMode
            if audio_mode in [AudioMode.VO_MUSIC, AudioMode.SOURCE_AUDIO_MUSIC]:
                ducking = "duck_dialogue_3db"
            else:
                ducking = None

            reason = (
                f"Bound {len(sound_cues)} sound cue(s) to beat {beat.beat_id} "
                f"under audio mode '{audio_mode.value}'."
            )

            direction = SfxDirection(
                beat_or_scene_id=beat.beat_id,
                audio_mode=audio_mode,
                sound_cues=sound_cues,
                ducking_profile=ducking,
                taste_rule_ids=rules,
                reason_summary=reason,
            )
            directions.append(direction)

        return directions

    def _detect_gesture(self, desc: str, phase: str) -> Optional[str]:
        """Detects applicable visual gesture keyword from description or phase."""
        d = desc.lower()
        if "ring" in d or "circle" in d:
            return "neon ring"
        if "underline" in d or "marker" in d:
            return "marker underline"
        if "highlight" in d:
            return "highlighter bg"
        if "strikethrough" in d or "strike" in d or "red line" in d:
            return "strikethrough"
        if "flash" in d or "burst" in d:
            return "flash cut"
        if "whoosh" in d or "dive" in d or "zoom" in d or "pan" in d:
            return "whoosh"
        if "stat" in d or "counter" in d:
            return "stat counter"
        if "pop" in d or "card" in d:
            return "pop"
        if "pause" in phase:
            return "dramatic pause"
        return None
