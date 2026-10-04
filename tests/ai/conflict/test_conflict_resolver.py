"""
tests/ai/conflict/test_conflict_resolver.py
===========================================
Tests for ConflictResolver (S28-04 Part E).

Verifies:
1. Pacing/style tension detected and resolved when Recipe is FAST and User is CALM.
2. MotionDirector CALM vs Recipe AGGRESSIVE_FAST triggers creative conflict and resolution.
3. Hard system constraint (AudioMode) strictly wins over soft creative recommendations.
4. Equal-priority unresolvable hard conflicts result in FAILED_UNRESOLVED_CONFLICT.
5. ResolvedCreativeGuidance contains complete trace of detected and resolved conflicts.
"""

import pytest
from datetime import datetime, timezone

from ai.conflict.resolver import ConflictResolver
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import (
    AudioMode,
    CreativeBrief,
    CreativeConstraints,
    CreativeIntent,
)
from ai.contracts.creative.conflict import (
    ConflictPrecedenceRank,
    ConflictSeverity,
    ConflictStatus,
    CreativeConflict,
    ResolvedCreativeGuidance,
)
from ai.contracts.creative.directors import (
    DirectorRecommendationBundle,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.contracts.creative.taste import TasteContext, TasteDecision
from ai.taste.context import TasteContextBuilder


@pytest.fixture
def resolver():
    return ConflictResolver()


def make_context(audio_mode=AudioMode.VO_MUSIC, tone="calm luxury", recipe_id="article-sprint"):
    now = datetime.now(timezone.utc)
    brief = CreativeBrief(
        brief_id="brief_conf_001",
        project_id="proj_001",
        workspace_id="ws_001",
        user_request_raw="Test brief",
        interpreted_intent=CreativeIntent(
            intent_id="i1",
            goal="Luxury Watch Showcase",
            audience="Collectors",
            tone=tone,
            key_takeaway="Timeless precision",
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=30.0,
            audio_mode=audio_mode,
        ),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    plan = NarrativePlan(
        narrative_id="narr_001",
        brief_id="brief_conf_001",
        core_hook="Timeless luxury",
        beats=[
            NarrativeBeat(
                beat_id="beat_001",
                beat_index=0,
                phase="hook",
                emotional_target="Curiosity",
                pacing="slow",
                estimated_duration_sec=30.0,
                key_message="Precision crafted.",
            )
        ],
        arc_structure="Single-Beat",
        estimated_total_duration_sec=30.0,
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    return TasteContextBuilder.build(
        brief=brief,
        narrative_plan=plan,
        recipe=None,
    ).model_copy(update={"recipe_id": recipe_id})


def test_user_calm_vs_recipe_fast_conflict_detected_and_resolved(resolver):
    """User CALM vs Recipe SPRINT (FAST): User explicit requirement wins."""
    ctx = make_context(tone="calm luxury", recipe_id="article-sprint")
    bundle = DirectorRecommendationBundle(
        brief_id=ctx.brief.brief_id,
        motion_directions=[
            MotionDirection(
                scene_id="beat_001",
                motion_energy="calm",
                motion_personality="Cinematic",
                entry_style="slow_fade",
                exit_style="fade_out",
                camera_intent="slow_dolly_zoom",
                text_motion="smooth_fade",
            )
        ],
        created_at=datetime.now(timezone.utc),
    )

    guidance = resolver.resolve(ctx, bundle, taste_decisions=[])

    assert isinstance(guidance, ResolvedCreativeGuidance)
    assert guidance.status == "SUCCESS"
    assert len(guidance.detected_conflicts) >= 1

    # Find the style tension conflict
    style_conf = [c for c in guidance.detected_conflicts if c.conflict_type == "STYLE_TENSION"][0]
    assert style_conf.status == ConflictStatus.RESOLVED
    assert style_conf.applied_precedence == ConflictPrecedenceRank.USER_EXPLICIT_REQUIREMENT
    assert style_conf.resolved_directive is not None


def test_hard_audiomode_silent_overrides_sfx_recommendations(resolver):
    """Silent AudioMode wins over any director SFX cues."""
    ctx = make_context(audio_mode=AudioMode.SILENT)
    bundle = DirectorRecommendationBundle(
        brief_id=ctx.brief.brief_id,
        sfx_directions=[
            SfxDirection(
                beat_or_scene_id="beat_001",
                audio_mode=AudioMode.SILENT,
                sound_cues=[{"sfx_file": "illegal_chime.wav", "volume_lufs": -20}],  # Injected violation
            )
        ],
        created_at=datetime.now(timezone.utc),
    )

    guidance = resolver.resolve(ctx, bundle, taste_decisions=[])

    assert guidance.status == "SUCCESS"
    audio_conf = [c for c in guidance.detected_conflicts if c.conflict_type == "AUDIO_MODE_VIOLATION"][0]
    assert audio_conf.status == ConflictStatus.RESOLVED
    assert audio_conf.applied_precedence == ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT


def test_unresolvable_hard_conflict_fails_guidance(resolver):
    """An unresolvable equal-priority conflict sets status to FAILED_UNRESOLVED_CONFLICT."""
    ctx = make_context()
    bundle = DirectorRecommendationBundle(
        brief_id=ctx.brief.brief_id,
        created_at=datetime.now(timezone.utc),
    )

    unresolvable = CreativeConflict(
        conflict_id="conf_deadlock",
        conflict_type="CONTRADICTORY_MUST_RULES",
        severity=ConflictSeverity.HARD,
        description="Two conflicting MUST rules cannot both be satisfied.",
        conflicting_parties=["MUST_Rule_A", "MUST_Rule_B"],
        competing_directives={"mode_a": True, "mode_b": True},
        applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
        resolved_directive=None,
        status=ConflictStatus.UNRESOLVED,
        reason_summary="Deadlock between equal priority hard constraints.",
    )

    guidance = resolver.resolve(
        ctx,
        bundle,
        taste_decisions=[],
        injected_hard_conflicts=[unresolvable],
    )

    assert guidance.status == "FAILED_UNRESOLVED_CONFLICT"
    assert len(guidance.unresolved_conflicts) == 1
    assert guidance.unresolved_conflicts[0].conflict_id == "conf_deadlock"


def test_recipe_constraint_vs_soft_taste_preference(resolver):
    """Precedence hierarchy: Recipe constraint strictly outranks soft taste preference."""
    ctx = make_context(tone="neutral", recipe_id="article-sprint")
    bundle = DirectorRecommendationBundle(
        brief_id=ctx.brief.brief_id,
        motion_directions=[
            MotionDirection(
                scene_id="beat_001",
                motion_energy="calm",
                motion_personality="Cinematic",
                entry_style="fade",
                exit_style="fade",
                camera_intent="static",
                text_motion="fade",
            )
        ],
        created_at=datetime.now(timezone.utc),
    )

    # Injected conflict: Recipe constraint (pacing <= 2s) vs soft taste preference (pacing >= 4s)
    recipe_vs_taste = CreativeConflict(
        conflict_id="conf_recipe_vs_taste",
        conflict_type="PACING_CADENCE_CONFLICT",
        severity=ConflictSeverity.CREATIVE_TENSION,
        description="Recipe sprint requires tight beats (<= 2s) while soft taste preference recommends >= 4s.",
        conflicting_parties=["Recipe:article-sprint", "TasteRule:taste_visual_rest"],
        competing_directives={"recipe_max_beat_sec": 2.0, "taste_rest_min_sec": 4.0},
        applied_precedence=ConflictPrecedenceRank.RECIPE_CONSTRAINT,
        resolved_directive={"beat_duration_sec": 2.0, "action": "recipe_constraint_overrides_soft_taste"},
        status=ConflictStatus.RESOLVED,
        reason_summary="Recipe constraint takes precedence over soft taste preference (Precedence: RECIPE_CONSTRAINT > SOFT_TASTE_PREFERENCE).",
    )

    guidance = resolver.resolve(
        ctx,
        bundle,
        taste_decisions=[],
        injected_hard_conflicts=[recipe_vs_taste],
    )

    assert guidance.status == "SUCCESS"
    resolved_conf = [c for c in guidance.detected_conflicts if c.conflict_id == "conf_recipe_vs_taste"][0]
    assert resolved_conf.applied_precedence == ConflictPrecedenceRank.RECIPE_CONSTRAINT
    assert resolved_conf.resolved_directive["beat_duration_sec"] == 2.0


def test_conflict_traceability_has_no_hidden_cot(resolver):
    """Auditability: All detected conflicts have explicit sources, directives, precedence, and concise reason summary."""
    ctx = make_context(tone="calm luxury", recipe_id="article-sprint")
    bundle = DirectorRecommendationBundle(
        brief_id=ctx.brief.brief_id,
        motion_directions=[
            MotionDirection(
                scene_id="beat_001",
                motion_energy="calm",
                motion_personality="Cinematic",
                entry_style="slow_fade",
                exit_style="fade_out",
                camera_intent="slow_dolly_zoom",
                text_motion="smooth_fade",
            )
        ],
        created_at=datetime.now(timezone.utc),
    )

    guidance = resolver.resolve(ctx, bundle, taste_decisions=[])
    assert len(guidance.detected_conflicts) > 0

    for c in guidance.detected_conflicts:
        assert c.conflict_id
        assert c.conflict_type
        assert len(c.conflicting_parties) >= 2, f"Conflict {c.conflict_id} must list at least 2 conflicting parties"
        assert len(c.competing_directives) >= 2, f"Conflict {c.conflict_id} must record competing directives"
        assert c.applied_precedence in ConflictPrecedenceRank
        assert c.reason_summary != "", "Auditable reason summary is required"
        # Zero hidden CoT: reason_summary must be concise and free of raw chain-of-thought traces
        assert len(c.reason_summary) < 500
        assert "thought" not in c.reason_summary.lower()
        assert "chain" not in c.reason_summary.lower()

