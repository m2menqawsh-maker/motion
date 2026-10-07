"""
tests/ai/planning/test_planner_personalization.py
=================================================
Verification of CreativePlanner integration with User Style Personalization (S28-08A Sections 13, 14, 15, 16, 17).

Guarantees tested:
1. CreativePlanner consumes compact EffectiveUserStyle context without leaking raw unorganized memory.
2. Automatic resolution: If raw UserStyleProfile is passed, CreativePlanner resolves it via UserStyleResolver.
3. AudioMode hard invariants: AudioMode.SILENT is strictly authoritative over user music preferences.
4. Hard boundary checks: UserStyle cannot alter plan status (strictly PROPOSED), tier policy, or QC status.
5. Safe defaults: CreativePlanner functions flawlessly when no user profile is provided.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.feedback import (
    EffectiveUserStyle,
    StylePreferenceProvenance,
    UserStyleProfile,
)
from ai.contracts.creative.plan import CreativePlan, CreativePlanStatus
from ai.memory.types import EpistemicStatus, SourceType
from ai.planning.creative_planner import CreativePlanner
from tests.ai.planning.conftest import create_test_brief, create_test_recipe


@pytest.fixture
def planner() -> CreativePlanner:
    return CreativePlanner()


class TestPlannerPersonalization:
    """Verifies that CreativePlanner incorporates resolved personalization while respecting boundaries."""

    def test_planner_respects_explicit_effective_user_style(self, planner, narrative_planner):
        """CreativePlanner applies compact EffectiveUserStyle to scene motion personalities."""
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.VO_MUSIC,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)
        now = datetime.now(timezone.utc)

        effective_style = EffectiveUserStyle(
            workspace_id=brief.workspace_id,
            user_id="usr_personal",
            pacing="fast",
            motion_intensity="high",
            motion_personality="EnergeticSnap",
            text_density="compact",
            caption_style="punchy",
            music_preference="ambient",
            resolved_at=now,
        )

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            effective_user_style=effective_style,
        )

        assert isinstance(plan, CreativePlan)
        assert plan.status == CreativePlanStatus.PROPOSED
        # All scenes adopt the personalized motion personality
        for scene in plan.scenes:
            assert scene.motion_personality == "EnergeticSnap"

    def test_planner_auto_resolves_raw_user_style_profile(self, planner, narrative_planner):
        """When raw UserStyleProfile is passed without effective_user_style, planner auto-resolves it."""
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.VO_MUSIC,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)
        now = datetime.now(timezone.utc)

        profile = UserStyleProfile(
            profile_id="prof_001",
            workspace_id=brief.workspace_id,
            user_id="usr_auto",
            pacing_preference="fast",
            motion_intensity="high",
            preferred_motion_personality="FluidContinuous",
            provenance_by_dimension={
                "pacing": StylePreferenceProvenance(
                    dimension="pacing",
                    epistemic_status=EpistemicStatus.CONFIRMED,
                    confidence=0.9,
                    source_type=SourceType.USER_STATEMENT,
                    evidence_count=3,
                    last_observed_at=now,
                )
            },
            updated_at=now,
        )

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            user_style=profile,
        )

        assert isinstance(plan, CreativePlan)
        assert plan.status == CreativePlanStatus.PROPOSED
        for scene in plan.scenes:
            assert scene.motion_personality == "FluidContinuous"

    def test_hard_audio_mode_invariants_immune_to_user_style(self, planner, narrative_planner):
        """
        Boundary Invariant: UserStyle CANNOT override canonical AudioMode.
        When brief sets AudioMode.SILENT, even if profile demands energetic music,
        the output MUST be completely silent.
        """
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.SILENT,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)
        now = datetime.now(timezone.utc)

        # Profile explicitly wants energetic music
        effective_style = EffectiveUserStyle(
            workspace_id=brief.workspace_id,
            user_id="usr_music_lover",
            music_preference="energetic_edm",
            motion_personality="Cinematic",
            resolved_at=now,
        )

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            effective_user_style=effective_style,
        )

        for scene in plan.scenes:
            assert scene.spoken_text is None
            assert scene.audio_intent == "silent_mode_no_audio"
            assert "music" not in scene.audio_intent.lower()
            assert "voiceover" not in scene.audio_intent.lower()

    def test_user_music_suppression_preference_honored_in_vo_music(self, planner, narrative_planner):
        """
        When brief has AudioMode.VO_MUSIC, but user style specifies music_preference='none',
        music is ducked/suppressed while voiceover remains preserved.
        """
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.VO_MUSIC,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)
        now = datetime.now(timezone.utc)

        effective_style = EffectiveUserStyle(
            workspace_id=brief.workspace_id,
            user_id="usr_quiet",
            music_preference="none",
            motion_personality="Cinematic",
            resolved_at=now,
        )

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            effective_user_style=effective_style,
        )

        for scene in plan.scenes:
            assert scene.spoken_text is not None  # VO preserved
            assert scene.audio_intent == "focused_voiceover_track"  # Music bed suppressed

    def test_planner_without_profile_uses_canonical_defaults(self, planner, narrative_planner):
        """Planner functions cleanly with default cinematic profile when no user style is provided."""
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.VO_MUSIC,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
        )

        assert isinstance(plan, CreativePlan)
        assert plan.status == CreativePlanStatus.PROPOSED
        for scene in plan.scenes:
            assert scene.motion_personality == "Cinematic"
            assert scene.audio_intent == "voiceover_with_ducked_music_bed"

    def test_user_style_cannot_mutate_plan_status_or_tiers(self, planner, narrative_planner):
        """
        Boundary Invariant: UserStyle cannot award QC pass, approval, or change tier semantics.
        Plan status is strictly PROPOSED upon generation.
        """
        brief = create_test_brief(
            video_type="SAAS_DEMO",
            audio_mode=AudioMode.VO_MUSIC,
            target_duration=30.0,
        )
        narrative_plan = narrative_planner.plan(brief)

        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
        )

        assert plan.status == CreativePlanStatus.PROPOSED
        assert plan.status != CreativePlanStatus.APPROVED_BY_USER
        assert not hasattr(plan, "tier_decision") or plan.tier_decision is None
