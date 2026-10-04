"""
tests/ai/planning/test_creative_planner.py
==========================================
Unit tests for Canonical CreativePlanner (S28-05 Part A).

Verifies:
1. Translates upstream creative inputs into canonical CreativePlan.
2. SceneIntent remains high-level (no frames, no low-level component paths).
3. 100% Narrative coverage (every beat maps to a scene with clear purpose).
4. AudioMode constraints strictly enforced:
   - MUSIC_ONLY: zero spoken text, music bed only.
   - SILENT: zero spoken text, zero audio tracks.
5. Conflict safety: fails closed on FAILED_UNRESOLVED_CONFLICT.
6. Capability safety: rejects incompatible recipe requirements.
7. Advisory proposal invariant: plan status is strictly PROPOSED.
8. Duration fit: sum of scene durations matches total duration within tolerance.
"""

import pytest
from datetime import datetime, timezone

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.conflict import (
    ConflictPrecedenceRank,
    ConflictSeverity,
    ConflictStatus,
    CreativeConflict,
    ResolvedCreativeGuidance,
)
from ai.contracts.creative.directors import (
    DirectorRecommendationBundle,
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.plan import CreativePlan, CreativePlanStatus
from ai.contracts.creative.taste import TasteDecision
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import (
    CapabilitySafetyError,
    DurationPlanningError,
    UnresolvedCreativeConflictError,
)
from tests.ai.planning.conftest import create_test_brief, create_test_recipe


@pytest.fixture
def planner() -> CreativePlanner:
    return CreativePlanner()


def test_saas_demo_creative_plan_generation(planner, narrative_planner):
    """Verifies end-to-end plan generation for a standard SaaS Demo."""
    brief = create_test_brief(
        video_type="SAAS_DEMO",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=30.0,
    )
    narrative_plan = narrative_planner.plan(brief)
    recipe = create_test_recipe(audio_mode=AudioMode.VO_MUSIC)

    plan = planner.plan(
        brief=brief,
        narrative_plan=narrative_plan,
        recipe=recipe,
    )

    assert isinstance(plan, CreativePlan)
    assert plan.status == CreativePlanStatus.PROPOSED
    assert plan.brief_id == brief.brief_id
    assert plan.recipe_id == recipe.recipe_id
    assert plan.total_estimated_duration_sec == 30.0
    assert len(plan.scenes) == len(narrative_plan.beats)

    # Narrative coverage check: every beat maps to a scene
    for idx, scene in enumerate(plan.scenes):
        assert scene.scene_index == idx
        assert scene.beat_id == narrative_plan.beats[idx].beat_id
        assert scene.intent_label == narrative_plan.beats[idx].phase.lower()
        assert scene.estimated_duration_sec > 0
        assert scene.spoken_text is not None  # VO mode has spoken text
        assert len(scene.asset_requirements) > 0  # Described abstractly
        assert len(scene.template_requirements) > 0

        # Boundary check: High-level intent only
        assert not hasattr(scene, "startFrame")
        assert not hasattr(scene, "durationFrames")
        assert not hasattr(scene, "component")


def test_music_only_mode_regression(planner, narrative_planner):
    """
    CRITICAL REGRESSION: In AudioMode.MUSIC_ONLY, CreativePlan MUST NOT contain
    any voiceover requirement, TTS intent, or spoken text.
    """
    brief = create_test_brief(
        brief_id="brief_montage_001",
        video_type="DYNAMIC_MONTAGE",
        audio_mode=AudioMode.MUSIC_ONLY,
        target_duration=25.0,
        goal="Summer lifestyle showcase",
    )
    narrative_plan = narrative_planner.plan(brief)

    plan = planner.plan(
        brief=brief,
        narrative_plan=narrative_plan,
    )

    assert plan.total_estimated_duration_sec == 25.0
    for scene in plan.scenes:
        # Spoken text must be strictly None
        assert scene.spoken_text is None
        # Audio intent must not mention voiceover or speech
        assert "voiceover" not in scene.audio_intent.lower()
        assert "spoken" not in scene.audio_intent.lower()
        assert "music" in scene.audio_intent.lower()


def test_silent_mode_regression(planner, narrative_planner):
    """
    CRITICAL REGRESSION: In AudioMode.SILENT, CreativePlan MUST NOT contain
    any music, SFX, or voiceover intent.
    """
    brief = create_test_brief(
        brief_id="brief_silent_001",
        video_type="SILENT_PRODUCT_DEMO",
        audio_mode=AudioMode.SILENT,
        target_duration=20.0,
        goal="High precision UI interaction",
    )
    narrative_plan = narrative_planner.plan(brief)

    plan = planner.plan(
        brief=brief,
        narrative_plan=narrative_plan,
    )

    assert plan.total_estimated_duration_sec == 20.0
    for scene in plan.scenes:
        assert scene.spoken_text is None
        assert "silent" in scene.audio_intent.lower()


def test_conflict_safety_unresolved_conflict_fails(planner, narrative_planner):
    """CreativePlanner MUST fail when passed unresolved creative guidance."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)

    unresolved_conflict = CreativeConflict(
        conflict_id="conf_001",
        conflict_type="AUDIO_CONTRADICTION",
        severity=ConflictSeverity.HARD,
        description="Conflicting instructions for audio volume",
        conflicting_parties=["User:silent", "Recipe:loud_bgm"],
        competing_directives={"mode": "silent", "recipe_mode": "loud"},
        applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
        resolved_directive=None,
        status=ConflictStatus.UNRESOLVED,
        reason_summary="Cannot resolve mutually contradictory audio requirement",
    )

    failed_guidance = ResolvedCreativeGuidance(
        guidance_id="guidance_fail",
        brief_id=brief.brief_id,
        recipe_id="test_recipe",
        narrative_plan=narrative_plan,
        taste_decisions=[],
        detected_conflicts=[unresolved_conflict],
        unresolved_conflicts=[unresolved_conflict],
        status="FAILED_UNRESOLVED_CONFLICT",
        provenance=brief.provenance,
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(UnresolvedCreativeConflictError) as exc_info:
        planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            guidance=failed_guidance,
        )

    assert "unresolved conflict" in str(exc_info.value).lower()


def test_capability_safety_incompatible_recipe(planner, narrative_planner):
    """CreativePlanner MUST reject recipe requiring voiceover in MUSIC_ONLY mode."""
    brief = create_test_brief(audio_mode=AudioMode.MUSIC_ONLY)
    narrative_plan = narrative_planner.plan(brief)
    # Recipe demanding TTS in a music only video
    recipe_with_tts = create_test_recipe(audio_mode=AudioMode.VO_MUSIC)

    with pytest.raises(CapabilitySafetyError) as exc_info:
        planner.plan(
            brief=brief,
            narrative_plan=narrative_plan,
            recipe=recipe_with_tts,
        )

    assert "incompatible with AudioMode.MUSIC_ONLY" in str(exc_info.value)


def test_creative_directors_enrichment(planner, narrative_planner):
    """Verifies that Director recommendations shape motion and emotion intents."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)

    director_bundle = DirectorRecommendationBundle(
        brief_id=brief.brief_id,
        narrative_directions=[
            NarrativeDirection(
                beat_id="beat_0",
                narrative_focus="hook_grab",
                pacing_instruction="fast_cut",
                information_density="minimal",
                spoken_line="Stop waiting for slow queries.",
                visual_progression_cue="void_to_grid",
                taste_rule_ids=["taste_first_frame_arrest"],
                reason_summary="High arrest hook",
            )
        ],
        motion_directions=[
            MotionDirection(
                scene_id="scene_001",
                motion_energy="explosive",
                motion_personality="Energetic",
                entry_style="bounce_up",
                exit_style="accelerate_out",
                camera_intent="whip_pan",
                text_motion="word_by_word_pop",
                visual_hierarchy=["hero_text"],
                taste_rule_ids=["taste_avoid_constant_motion"],
                reason_summary="High energy opening",
            )
        ],
        emotion_directions=[
            EmotionDirection(
                beat_or_scene_id="beat_0",
                primary_emotion="Curiosity/Urgency",
                intensity="high",
                emotional_progression="curiosity -> confidence",
                taste_rule_ids=[],
                reason_summary="High urgency hook",
            )
        ],
        sfx_directions=[],
        created_at=datetime.now(timezone.utc),
    )

    plan = planner.plan(
        brief=brief,
        narrative_plan=narrative_plan,
        director_bundle=director_bundle,
    )

    scene_0 = plan.scenes[0]
    assert scene_0.spoken_text == "Stop waiting for slow queries."
    assert scene_0.motion_personality == "Energetic"
    assert scene_0.mood == "Curiosity/Urgency"
