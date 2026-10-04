"""
ai/planning/creative_planner.py
===============================
Canonical Creative Planner for S28-05.

Transforms upstream creative reasoning artifacts:
- CreativeBrief (S28-03)
- RecipeDefinition / RecipeSelection (S28-03)
- NarrativePlan (S28-04)
- TasteDecision[] (S28-04)
- ResolvedCreativeGuidance (S28-04)
- DirectorRecommendationBundle (S28-04)
- Relevant Skills & Knowledge (S28-02)
- MediaIntelligence & UserStyleProfile (Optional)

Into a canonical, high-level, typed CreativePlan:
- CreativePlan = What should be made (creative proposal).
- CreativePlan ≠ Blueprint (advisory only, status=PROPOSED).
- Strictly preserves AudioMode constraints (MUSIC_ONLY, SILENT, etc.).
- Strict conflict safety: fails closed on unresolved conflicts.
- Zero low-level runtime details (no frame counts, components, or resolved asset IDs).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.conflict import ResolvedCreativeGuidance
from ai.contracts.creative.directors import DirectorRecommendationBundle
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    SceneIntent,
)
from ai.contracts.creative.recipe import RecipeDefinition
from ai.contracts.creative.skills_knowledge import (
    KnowledgeDescriptor,
    SkillDefinition,
)
from ai.contracts.creative.taste import TasteDecision
from ai.contracts.creative.feedback import EffectiveUserStyle, UserStyleProfile
from ai.memory.models import TrustedTenantContext
from ai.planning.errors import (
    AudioPolicyViolationError,
    CapabilitySafetyError,
    DurationPlanningError,
    InvalidCreativeBriefError,
    UnresolvedCreativeConflictError,
)
from ai.style.resolver import UserStyleResolver


class CreativePlanner:
    """
    Authoritative Planner for synthesizing upstream creative intelligence
    into a typed, validatable, advisory CreativePlan.
    """

    def __init__(self, planner_version: str = "1.0.0") -> None:
        self.planner_version = planner_version

    def plan(
        self,
        brief: CreativeBrief,
        narrative_plan: NarrativePlan,
        recipe: Optional[RecipeDefinition] = None,
        taste_decisions: Optional[List[TasteDecision]] = None,
        guidance: Optional[ResolvedCreativeGuidance] = None,
        director_bundle: Optional[DirectorRecommendationBundle] = None,
        skills: Optional[List[SkillDefinition]] = None,
        knowledge: Optional[List[KnowledgeDescriptor]] = None,
        media_intelligence: Optional[Any] = None,
        user_style: Optional[UserStyleProfile] = None,
        effective_user_style: Optional[EffectiveUserStyle] = None,
    ) -> CreativePlan:
        """
        Generates a canonical CreativePlan from upstream creative inputs.
        """
        start_time = time.perf_counter()

        # Resolve effective style through canonical precedence if raw profile supplied
        if effective_user_style is None and user_style is not None:
            trusted_ctx = TrustedTenantContext(
                workspace_id=brief.workspace_id,
                user_id=getattr(user_style, "user_id", None),
            )
            effective_user_style = UserStyleResolver.resolve_effective_style(
                context=trusted_ctx,
                brief=brief,
                profile=user_style,
            )

        # 1. Brief Validation & Prerequisites
        if not brief or not brief.brief_id:
            raise InvalidCreativeBriefError("CreativeBrief is required and must have a valid brief_id.")
        if not narrative_plan or not narrative_plan.beats:
            raise InvalidCreativeBriefError("NarrativePlan with at least one beat is required.")

        audio_mode = brief.constraints.audio_mode
        target_duration = brief.constraints.target_duration_seconds

        # 2. Strict Conflict Safety (Section 13)
        if guidance:
            if guidance.status == "FAILED_UNRESOLVED_CONFLICT":
                raise UnresolvedCreativeConflictError(
                    f"ResolvedCreativeGuidance has failed status '{guidance.status}' with unresolved conflicts."
                )
            if hasattr(guidance, "unresolved_conflicts") and len(guidance.unresolved_conflicts) > 0:
                conflict_descs = [c.description for c in guidance.unresolved_conflicts]
                raise UnresolvedCreativeConflictError(
                    f"Cannot generate CreativePlan: {len(guidance.unresolved_conflicts)} unresolved conflict(s) detected: {conflict_descs}"
                )

        # 3. Capability Safety & Recipe Alignment (Section 14 & 15)
        if recipe:
            if audio_mode == AudioMode.MUSIC_ONLY:
                forbidden_caps = {"TEXT_TO_SPEECH", "SPEECH_ALIGNMENT", "VOCAL_ISOLATION"}
                conflicting = set(recipe.required_capabilities).intersection(forbidden_caps)
                if conflicting:
                    raise CapabilitySafetyError(
                        f"Recipe '{recipe.recipe_id}' requires capabilities {conflicting} incompatible with AudioMode.MUSIC_ONLY."
                    )
            elif audio_mode == AudioMode.SILENT:
                forbidden_caps = {"TEXT_TO_SPEECH", "SPEECH_ALIGNMENT", "AUDIO_ENHANCE", "VOCAL_ISOLATION"}
                conflicting = set(recipe.required_capabilities).intersection(forbidden_caps)
                if conflicting:
                    raise CapabilitySafetyError(
                        f"Recipe '{recipe.recipe_id}' requires audio capabilities {conflicting} incompatible with AudioMode.SILENT."
                    )

        # 4. Duration Planning & Sanity (Section 19)
        narrative_total = narrative_plan.estimated_total_duration_sec
        # Allow +/- 20% or 5.0s tolerance between brief and narrative
        if target_duration > 0 and abs(narrative_total - target_duration) > max(5.0, target_duration * 0.20):
            raise DurationPlanningError(
                f"NarrativePlan duration ({narrative_total}s) deviates excessively from brief target duration ({target_duration}s)."
            )

        # 5. Index Director Recommendations & Guidance
        emotion_dir_by_beat: Dict[str, str] = {}
        motion_dir_by_scene: Dict[str, str] = {}
        narrative_dir_by_beat: Dict[str, str] = {}
        sfx_dir_by_beat: Dict[str, Any] = {}

        if guidance:
            for ed in getattr(guidance, "emotion_directions", []):
                emotion_dir_by_beat[ed.beat_or_scene_id] = ed.primary_emotion
            for md in getattr(guidance, "motion_directions", []):
                motion_dir_by_scene[md.scene_id] = md.motion_personality
            for nd in getattr(guidance, "narrative_directions", []):
                if nd.spoken_line:
                    narrative_dir_by_beat[nd.beat_id] = nd.spoken_line
            for sd in getattr(guidance, "sfx_directions", []):
                sfx_dir_by_beat[sd.beat_or_scene_id] = sd

        if director_bundle:
            for ed in getattr(director_bundle, "emotion_directions", []):
                emotion_dir_by_beat.setdefault(ed.beat_or_scene_id, ed.primary_emotion)
            for md in getattr(director_bundle, "motion_directions", []):
                motion_dir_by_scene.setdefault(md.scene_id, md.motion_personality)
            for nd in getattr(director_bundle, "narrative_directions", []):
                if nd.spoken_line:
                    narrative_dir_by_beat.setdefault(nd.beat_id, nd.spoken_line)
            for sd in getattr(director_bundle, "sfx_directions", []):
                sfx_dir_by_beat.setdefault(sd.beat_or_scene_id, sd)

        # 6. Map NarrativeBeats to SceneIntents (Section 8, 10, 11)
        raw_taste_decisions = taste_decisions or (guidance.taste_decisions if guidance else [])
        scenes: List[SceneIntent] = []
        num_beats = len(narrative_plan.beats)

        for idx, beat in enumerate(narrative_plan.beats):
            scene_id = f"scene_{idx + 1:03d}"
            beat_id = beat.beat_id or f"beat_{idx}"
            purpose = beat.phase.lower().strip()

            # Purpose validation
            if not purpose:
                purpose = "visual_progression"

            # Visual intent job mapping
            visual_job = self._derive_visual_job(purpose)

            # Mood / Emotion
            mood = (
                emotion_dir_by_beat.get(beat_id)
                or emotion_dir_by_beat.get(f"beat_{idx}")
                or emotion_dir_by_beat.get(scene_id)
                or beat.emotional_target
                or brief.interpreted_intent.tone
                or "dynamic"
            )

            # Motion personality (honoring EffectiveUserStyle if provided, but no invention)
            motion_personality = (
                motion_dir_by_scene.get(scene_id)
                or motion_dir_by_scene.get(beat_id)
                or motion_dir_by_scene.get(f"beat_{idx}")
                or (effective_user_style.motion_personality if effective_user_style and effective_user_style.motion_personality else None)
                or (user_style.preferred_motion_personality if user_style and user_style.preferred_motion_personality else "Cinematic")
            )

            # Spoken Text intent strictly adhering to AudioMode (Section 14 & 64 & 65)
            if audio_mode in (AudioMode.MUSIC_ONLY, AudioMode.SILENT):
                spoken_text: Optional[str] = None
            else:
                spoken_text = (
                    narrative_dir_by_beat.get(beat_id)
                    or narrative_dir_by_beat.get(f"beat_{idx}")
                    or narrative_dir_by_beat.get(scene_id)
                    or beat.key_message
                )
                if not spoken_text or not spoken_text.strip():
                    spoken_text = f"Scene focus: {purpose.replace('_', ' ').title()}."

            # Audio Intent (strictly adhering to canonical AudioMode and EffectiveUserStyle)
            audio_intent = self._derive_audio_intent(audio_mode, purpose, effective_user_style)

            # Asset Requirements (abstract tags, never concrete file paths or resolved asset IDs)
            asset_reqs = self._derive_asset_requirements(purpose, brief)

            # Template Requirements (abstract tags, never concrete selected template IDs)
            template_reqs = self._derive_template_requirements(purpose, visual_job)

            # Filter taste decisions applicable to this scene or beat
            scene_taste_decisions = [
                td for td in raw_taste_decisions
                if td.context_ref in (scene_id, beat_id, f"scene_{idx + 1}", "global_canvas")
            ]

            duration_sec = max(0.5, round(beat.estimated_duration_sec, 2))

            scene = SceneIntent(
                scene_id=scene_id,
                scene_index=idx,
                beat_id=beat_id,
                intent_label=purpose,
                mood=mood,
                motion_personality=motion_personality,
                primary_visual_job=visual_job,
                estimated_duration_sec=duration_sec,
                spoken_text=spoken_text,
                taste_decisions=scene_taste_decisions,
                asset_requirements=asset_reqs,
                audio_intent=audio_intent,
                template_requirements=template_reqs,
            )
            scenes.append(scene)

        # 7. Total Duration Exact Allocation
        total_duration = round(sum(s.estimated_duration_sec for s in scenes), 2)

        # If slight rounding delta exists between total_duration and sum, adjust last scene
        # to ensure perfect consistency with model_validator
        sum_check = sum(s.estimated_duration_sec for s in scenes)
        if abs(sum_check - total_duration) > 0.001 and len(scenes) > 0:
            diff = round(total_duration - sum_check, 2)
            scenes[-1] = scenes[-1].model_copy(
                update={"estimated_duration_sec": round(scenes[-1].estimated_duration_sec + diff, 2)}
            )

        now = datetime.now(timezone.utc)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        provenance = ProvenanceRecord(
            source="ai.planning.creative_planner",
            model_id=f"deterministic-creative-planner-{self.planner_version}",
            provider_id="clean-video-platform",
            timestamp=now,
            latency_ms=max(1, elapsed_ms),
        )

        title = (
            brief.interpreted_intent.key_takeaway
            or brief.interpreted_intent.goal
            or "Creative Video Production"
        )
        recipe_id = recipe.recipe_id if recipe else (guidance.recipe_id if guidance else "standard-narrative-flow")

        return CreativePlan(
            plan_id=f"cplan_{brief.brief_id}_{int(now.timestamp())}",
            brief_id=brief.brief_id,
            recipe_id=recipe_id,
            title=title,
            narrative_plan=narrative_plan,
            scenes=scenes,
            compositions=[],
            tier_decisions=[],
            total_estimated_duration_sec=total_duration,
            status=CreativePlanStatus.PROPOSED,
            provenance=provenance,
            created_at=now,
        )

    def _derive_visual_job(self, purpose: str) -> str:
        """Determines high-level visual job from narrative purpose."""
        p = purpose.lower()
        if "hook" in p:
            return "action"
        elif "problem" in p or "agitation" in p:
            return "mechanism"
        elif "proof" in p or "metric" in p:
            return "proof"
        elif "solution" in p or "explanation" in p:
            return "mechanism"
        elif "cta" in p or "call_to_action" in p:
            return "action"
        elif "payoff" in p or "benefit" in p:
            return "consequence"
        elif "progression" in p or "montage" in p:
            return "visual_progression"
        return "mechanism"

    def _derive_audio_intent(
        self,
        audio_mode: AudioMode,
        purpose: str,
        effective_user_style: Optional[EffectiveUserStyle] = None,
    ) -> str:
        """Determines audio intent strictly respecting AudioMode and EffectiveUserStyle."""
        if audio_mode == AudioMode.SILENT:
            return "silent_mode_no_audio"
        elif audio_mode == AudioMode.MUSIC_ONLY:
            if effective_user_style and effective_user_style.music_preference == "none":
                return "silent_mode_no_audio"
            return "dynamic_background_music_bed"
        elif audio_mode == AudioMode.VO_ONLY:
            return "focused_voiceover_track"
        elif audio_mode == AudioMode.VO_MUSIC:
            if effective_user_style and effective_user_style.music_preference == "none":
                return "focused_voiceover_track"
            return "voiceover_with_ducked_music_bed"
        elif audio_mode in (AudioMode.SOURCE_AUDIO, AudioMode.SOURCE_AUDIO_MUSIC):
            return "source_audio_synchronized"
        return "standard_voiceover_and_music"

    def _derive_asset_requirements(self, purpose: str, brief: CreativeBrief) -> List[str]:
        """Proposes high-level asset categories needed without inventing concrete IDs."""
        reqs: List[str] = []
        p = purpose.lower()
        if "hook" in p:
            reqs.append("hero_visual_anchor")
        elif "proof" in p:
            reqs.append("product_demo_or_metric_graphic")
        elif "problem" in p:
            reqs.append("pain_point_illustration")
        elif "cta" in p:
            reqs.append("brand_logo")
        elif "solution" in p:
            reqs.append("feature_showcase_visual")
        else:
            reqs.append("background_visual_canvas")
        return reqs

    def _derive_template_requirements(self, purpose: str, visual_job: str) -> List[str]:
        """Proposes high-level template capability hints without making tier or selector decisions."""
        hints: List[str] = []
        p = purpose.lower()
        if "hook" in p:
            hints.append("bold_typography_hook")
        elif "proof" in p:
            hints.append("stat_or_comparison_card")
        elif "cta" in p:
            hints.append("closing_cta_card")
        elif visual_job == "mechanism":
            hints.append("process_flow_or_diagram")
        else:
            hints.append("standard_motion_canvas")
        return hints
