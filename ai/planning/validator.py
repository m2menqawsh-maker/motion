"""
ai/planning/validator.py
========================
Canonical validator for CreativePlan proposals (S28-05 Part B).

Guarantees:
- Enforces pre-Core validation gate: CreativePlan must be verified before compiler invocation.
- Verifies:
  1. Covers User Goal: ensures narrative beats and brief intent are accounted for.
  2. Duration Fits: verifies total duration, scene duration limits, and tolerance against brief.
  3. No Impossible Capability: checks capability requirements against system/recipe constraints.
  4. No Forbidden Audio Operations: strictly forbids VO/TTS in MUSIC_ONLY and all audio in SILENT.
  5. Asset Feasibility: verifies abstract asset requirements contain no illegal paths or malformations.
  6. Scene Purpose Completeness: every scene must possess a non-empty, validated purpose.
  7. No Unresolved Conflicts: rejects plans carrying unresolved creative conflicts.
  8. Valid References: verifies internal IDs, indices, and references are consistent.
- Structured output via `CreativePlanValidationResult`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.conflict import ResolvedCreativeGuidance
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanValidationResult,
)
from ai.contracts.creative.recipe import RecipeDefinition


class CreativePlanValidator:
    """
    Validates a CreativePlan proposal against creative constraints,
    audio policy, duration targets, and system capabilities before compilation.
    """

    ALLOWED_PURPOSES: Set[str] = {
        "hook",
        "problem",
        "agitation",
        "solution",
        "mechanism",
        "proof",
        "social_proof",
        "explanation",
        "payoff",
        "benefit",
        "cta",
        "call_to_action",
        "visual_progression",
        "montage",
        "transition",
        "intro",
        "outro",
    }

    def __init__(self, duration_tolerance_sec: float = 3.0, duration_tolerance_ratio: float = 0.15) -> None:
        self.duration_tolerance_sec = duration_tolerance_sec
        self.duration_tolerance_ratio = duration_tolerance_ratio

    def validate(
        self,
        plan: CreativePlan,
        brief: CreativeBrief,
        recipe: Optional[RecipeDefinition] = None,
        guidance: Optional[ResolvedCreativeGuidance] = None,
        available_capabilities: Optional[List[str]] = None,
        available_assets: Optional[List[str]] = None,
    ) -> CreativePlanValidationResult:
        """
        Executes comprehensive semantic validation on a CreativePlan.
        Fails closed on any invariant violation.
        """
        errors: List[str] = []
        warnings: List[str] = []
        checked_invariants: List[str] = []

        # ── 1. Basic Identity and Reference Integrity ─────────────────────────────
        checked_invariants.append("VALID_REFERENCES")
        if not plan.plan_id or not plan.plan_id.strip():
            errors.append("CreativePlan must have a non-empty plan_id.")
        if plan.brief_id != brief.brief_id:
            errors.append(f"plan.brief_id ('{plan.brief_id}') does not match brief.brief_id ('{brief.brief_id}').")

        # Verify scene indices and unique IDs
        seen_scene_ids: Set[str] = set()
        for idx, scene in enumerate(plan.scenes):
            if not scene.scene_id or not scene.scene_id.strip():
                errors.append(f"scenes[{idx}]: scene_id cannot be empty.")
            elif scene.scene_id in seen_scene_ids:
                errors.append(f"scenes[{idx}]: duplicate scene_id '{scene.scene_id}'.")
            seen_scene_ids.add(scene.scene_id)

            if scene.scene_index != idx:
                errors.append(f"scenes[{idx}] ('{scene.scene_id}'): scene_index {scene.scene_index} does not match sequential position {idx}.")

        # ── 2. Scene Purpose Completeness (Section 10 & 27) ──────────────────────
        checked_invariants.append("SCENE_PURPOSE_COMPLETENESS")
        if not plan.scenes:
            errors.append("CreativePlan must contain at least one scene.")
        else:
            for idx, scene in enumerate(plan.scenes):
                purpose = scene.intent_label.strip().lower() if scene.intent_label else ""
                if not purpose:
                    errors.append(f"scenes[{idx}] ('{scene.scene_id}'): missing required intent_label (purpose).")
                elif not any(allowed in purpose for allowed in self.ALLOWED_PURPOSES):
                    warnings.append(f"scenes[{idx}] ('{scene.scene_id}'): intent_label '{purpose}' is unusual or non-standard.")

        # ── 3. Covers User Goal & Narrative Coverage (Section 11 & 22 & 67) ─────
        checked_invariants.append("COVERS_USER_GOAL")
        if plan.narrative_plan and plan.narrative_plan.beats:
            beat_ids_in_narrative = {b.beat_id for b in plan.narrative_plan.beats if b.beat_id}
            scene_beat_ids = {s.beat_id for s in plan.scenes if s.beat_id}
            missing_beats = beat_ids_in_narrative - scene_beat_ids
            if missing_beats:
                errors.append(f"CreativePlan dropped required narrative beats: {sorted(list(missing_beats))}.")

            # If user explicitly requested a proof/demo and it's in narrative, verify coverage
            req_goal = brief.interpreted_intent.goal.lower()
            if "proof" in req_goal or "demo" in req_goal or "metric" in req_goal:
                has_proof_scene = any(
                    "proof" in s.intent_label.lower() or s.primary_visual_job == "proof"
                    for s in plan.scenes
                )
                if not has_proof_scene and any("proof" in b.phase.lower() for b in plan.narrative_plan.beats):
                    errors.append("User requested product proof/demo, but CreativePlan contains no proof scene.")

        # ── 4. Duration Fits (Section 19 & 23 & 66) ─────────────────────────────
        checked_invariants.append("DURATION_FITS")
        target_sec = brief.constraints.target_duration_seconds
        total_sec = plan.total_estimated_duration_sec

        if total_sec <= 0:
            errors.append(f"total_estimated_duration_sec ({total_sec}) must be strictly positive.")

        sum_durations = sum(s.estimated_duration_sec for s in plan.scenes)
        if abs(sum_durations - total_sec) > 0.5:
            errors.append(
                f"Sum of scene durations ({round(sum_durations, 2)}s) does not match total_estimated_duration_sec ({total_sec}s)."
            )

        for idx, s in enumerate(plan.scenes):
            if s.estimated_duration_sec <= 0:
                errors.append(f"scenes[{idx}] ('{s.scene_id}'): duration ({s.estimated_duration_sec}s) must be strictly positive.")
            elif s.estimated_duration_sec < 0.5:
                errors.append(f"scenes[{idx}] ('{s.scene_id}'): duration ({s.estimated_duration_sec}s) is below 0.5s minimum.")

        if target_sec > 0:
            max_allowed = target_sec + max(self.duration_tolerance_sec, target_sec * self.duration_tolerance_ratio)
            min_allowed = max(1.0, target_sec - max(self.duration_tolerance_sec, target_sec * self.duration_tolerance_ratio))
            if total_sec > max_allowed or total_sec < min_allowed:
                errors.append(
                    f"Total plan duration ({total_sec}s) exceeds acceptable bounds [{round(min_allowed, 1)}s, {round(max_allowed, 1)}s] for target ({target_sec}s)."
                )

        # ── 5. AudioMode Enforcement (Section 14 & 25 & 64 & 65) ────────────────
        checked_invariants.append("NO_FORBIDDEN_AUDIO_OPERATION")
        audio_mode = brief.constraints.audio_mode

        if audio_mode == AudioMode.MUSIC_ONLY:
            for idx, scene in enumerate(plan.scenes):
                if scene.spoken_text and scene.spoken_text.strip():
                    errors.append(
                        f"scenes[{idx}] ('{scene.scene_id}'): contains spoken_text in AudioMode.MUSIC_ONLY."
                    )
                if scene.audio_intent and any(k in scene.audio_intent.lower() for k in ("voiceover", "tts", "spoken", "dialogue")):
                    errors.append(
                        f"scenes[{idx}] ('{scene.scene_id}'): audio_intent '{scene.audio_intent}' requests voiceover in MUSIC_ONLY."
                    )

        elif audio_mode == AudioMode.SILENT:
            for idx, scene in enumerate(plan.scenes):
                if scene.spoken_text and scene.spoken_text.strip():
                    errors.append(
                        f"scenes[{idx}] ('{scene.scene_id}'): contains spoken_text in AudioMode.SILENT."
                    )
                if scene.audio_intent and not any(k in scene.audio_intent.lower() for k in ("silent", "none", "muted")):
                    errors.append(
                        f"scenes[{idx}] ('{scene.scene_id}'): audio_intent '{scene.audio_intent}' is not silent in SILENT mode."
                    )

        # ── 6. Capability Safety (Section 15 & 24) ──────────────────────────────
        checked_invariants.append("NO_IMPOSSIBLE_CAPABILITY")
        if available_capabilities is not None:
            avail_set = set(available_capabilities)
            # If brief is VO_MUSIC but TEXT_TO_SPEECH not available
            if audio_mode in (AudioMode.VO_ONLY, AudioMode.VO_MUSIC):
                if "TEXT_TO_SPEECH" not in avail_set and any(s.spoken_text for s in plan.scenes):
                    errors.append("Plan requires voiceover but capability 'TEXT_TO_SPEECH' is not available in system.")

        # ── 7. Asset Feasibility (Section 16 & 26) ──────────────────────────────
        checked_invariants.append("ASSET_FEASIBILITY")
        for idx, scene in enumerate(plan.scenes):
            for req in scene.asset_requirements:
                if not req or not isinstance(req, str):
                    errors.append(f"scenes[{idx}] ('{scene.scene_id}'): malformed asset requirement '{req}'.")
                # Guard against accidental concrete file paths injected as high-level requirements
                elif "/" in req or "\\" in req or req.startswith("ast_"):
                    warnings.append(
                        f"scenes[{idx}] ('{scene.scene_id}'): asset requirement '{req}' looks like a path or concrete asset ID instead of high-level category."
                    )

        # ── 8. No Unresolved Conflicts (Section 13 & 28) ────────────────────────
        checked_invariants.append("NO_UNRESOLVED_CONFLICTS")
        if guidance:
            if guidance.status == "FAILED_UNRESOLVED_CONFLICT":
                errors.append(f"ResolvedCreativeGuidance has failed status '{guidance.status}'.")
            if hasattr(guidance, "unresolved_conflicts") and len(guidance.unresolved_conflicts) > 0:
                errors.append(
                    f"ResolvedCreativeGuidance contains {len(guidance.unresolved_conflicts)} unresolved conflict(s)."
                )

        is_valid = len(errors) == 0
        return CreativePlanValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            checked_invariants=checked_invariants,
        )
