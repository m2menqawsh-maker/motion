"""
ai/taste/evaluator.py
=====================
Evaluates TasteRule applicability against contextual creative parameters (S28-04).
"""

from __future__ import annotations

from typing import List, Tuple
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.taste import TasteContext, TasteRule
from ai.taste.contracts import TasteEvaluationResult


class TasteEvaluator:
    """
    Evaluates condition predicates and exception criteria for a TasteRule against a TasteContext.
    """

    def evaluate(self, rule: TasteRule, context: TasteContext, target_ref: str = "canvas_global") -> TasteEvaluationResult:
        """
        Determines if a TasteRule applies to the given context and target reference.
        """
        brief = context.brief
        intent = brief.interpreted_intent
        constraints = brief.constraints
        audio_mode = constraints.audio_mode
        evidence: List[str] = []

        # 1. Exception Check
        waived_reason = self._check_exceptions(rule, context, target_ref)
        if waived_reason:
            return TasteEvaluationResult(
                rule_id=rule.rule_id,
                is_applicable=False,
                confidence=1.0,
                evidence=[f"Waived by exception: {waived_reason}"],
                waived_by_exception=waived_reason,
            )

        # 2. Predicate Check
        applies_when = rule.applies_when or {}
        is_applicable = True

        for key, expected in applies_when.items():
            if key == "audio_mode":
                if isinstance(expected, str):
                    if audio_mode.value != expected:
                        is_applicable = False
                        break
                    evidence.append(f"AudioMode matches '{expected}'")

            elif key == "audio_mode_not":
                if isinstance(expected, str):
                    if audio_mode.value == expected:
                        is_applicable = False
                        break
                    evidence.append(f"AudioMode is not '{expected}' ({audio_mode.value})")

            elif key == "language":
                lang = (intent.language or "en").lower()
                if lang != str(expected).lower():
                    is_applicable = False
                    break
                evidence.append(f"Language is '{lang}'")

            elif key == "has_spoken_sentence":
                has_spoken = audio_mode in [
                    AudioMode.VO_ONLY,
                    AudioMode.VO_MUSIC,
                    AudioMode.SOURCE_AUDIO,
                    AudioMode.SOURCE_AUDIO_MUSIC,
                ]
                if has_spoken != bool(expected):
                    is_applicable = False
                    break
                evidence.append(f"Spoken voiceover active ({audio_mode.value})")

            elif key == "spoken_voiceover":
                has_spoken = audio_mode in [AudioMode.VO_ONLY, AudioMode.VO_MUSIC]
                if has_spoken != bool(expected):
                    is_applicable = False
                    break
                evidence.append(f"Spoken VO present ({audio_mode.value})")

            elif key == "has_visual_gesture":
                # True if any beat has a visual hook description or gestures
                has_v = any(bool(b.visual_hook_description) for b in context.narrative_plan.beats)
                if has_v != bool(expected):
                    is_applicable = False
                    break
                evidence.append("Visual gestures present in narrative plan")

            elif key == "has_palette":
                has_pal = len(constraints.brand_colors) > 0
                if has_pal != bool(expected):
                    is_applicable = False
                    break
                evidence.append(f"Brand color palette present ({len(constraints.brand_colors)} colors)")

            elif key == "has_motion_personality":
                evidence.append("Motion personality active")

            elif key == "multi_beat":
                is_multi = len(context.narrative_plan.beats) > 1
                if is_multi != bool(expected):
                    is_applicable = False
                    break
                evidence.append(f"Multi-beat narrative ({len(context.narrative_plan.beats)} beats)")

            elif key == "scene_density":
                if expected == "high":
                    is_high = len(context.narrative_plan.beats) >= 3 or context.narrative_plan.estimated_total_duration_sec > 10.0
                    if not is_high:
                        is_applicable = False
                        break
                    evidence.append("Scene density is high")

            elif key == "duration_sec_gt":
                if context.narrative_plan.estimated_total_duration_sec <= float(expected):
                    is_applicable = False
                    break
                evidence.append(f"Duration > {expected}s")

            elif key == "platform":
                platforms = [p.lower() for p in intent.target_platforms]
                aspects = constraints.aspect_ratios
                is_mobile = any("tiktok" in p or "shorts" in p or "reel" in p for p in platforms) or "9:16" in aspects
                if expected == "mobile" and not is_mobile:
                    is_applicable = False
                    break
                evidence.append("Targeting mobile platform / 9:16 format")

            elif key == "dense_scenes_count_gte":
                dense_count = sum(1 for b in context.narrative_plan.beats if b.pacing == "fast" or len(b.key_message.split()) > 8)
                if dense_count < int(expected):
                    is_applicable = False
                    break
                evidence.append(f"Dense scenes count ({dense_count}) >= {expected}")

            elif key == "sfx_density":
                if expected == "excessive":
                    sfx_count = sum(1 for b in context.narrative_plan.beats if b.sound_effect_cue)
                    if sfx_count <= 2:
                        is_applicable = False
                        break
                    evidence.append(f"Excessive SFX cue density detected ({sfx_count} cues)")

            elif key == "prefers_reduced_motion":
                has_pref = False
                if context.user_style_profile and getattr(context.user_style_profile, "prefers_reduced_motion", False):
                    has_pref = True
                elif getattr(context.brief.constraints, "prefers_reduced_motion", False):
                    has_pref = True
                elif "reduced" in str(getattr(context.brief.constraints, "motion_personality", "")).lower():
                    has_pref = True
                if has_pref != bool(expected):
                    is_applicable = False
                    break
                evidence.append("User requested reduced motion accessibility")

            else:
                val = getattr(context.brief.constraints, key, None)
                if val is None and context.user_style_profile:
                    val = getattr(context.user_style_profile, key, None)
                if val != expected:
                    is_applicable = False
                    break
                evidence.append(f"Predicate '{key}' matched ({val})")

        if is_applicable and not evidence:
            evidence.append(f"Rule conditions for '{rule.rule_id}' satisfied")

        confidence = 0.95 if is_applicable else 0.0
        return TasteEvaluationResult(
            rule_id=rule.rule_id,
            is_applicable=is_applicable,
            confidence=confidence,
            evidence=evidence if is_applicable else ["Criteria conditions not met"],
            waived_by_exception=None,
        )

    def _check_exceptions(self, rule: TasteRule, context: TasteContext, target_ref: str) -> Optional[str]:
        """Checks if current context qualifies for any of the rule's documented exceptions."""
        exceptions = rule.exceptions or []
        audio_mode = context.brief.constraints.audio_mode

        if "audio_mode_silent" in exceptions and audio_mode == AudioMode.SILENT:
            return "Audio mode is SILENT; sound design rules waived"

        if "silent_mode" in exceptions and audio_mode == AudioMode.SILENT:
            return "Audio mode is SILENT"

        if "ambient_montage" in exceptions and audio_mode == AudioMode.MUSIC_ONLY:
            return "Music montage without spoken voiceover"

        if "15s_ultra_fast_sprint" in exceptions and context.narrative_plan.estimated_total_duration_sec <= 15.0:
            return "15-second ultra-fast sprint requires sustained density without early visual rest"

        return None
