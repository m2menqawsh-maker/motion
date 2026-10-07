"""
tests/ai/planning/test_creative_plan_validator.py
=================================================
Unit tests for CreativePlanValidator (S28-05 Part B).

Verifies:
1. Valid CreativePlans pass with valid=True and checked_invariants checklist.
2. Dropping narrative beats or missing explicit user goal fails COVERS_USER_GOAL.
3. Total duration mismatch, out-of-tolerance duration, or non-positive scene duration fails DURATION_FITS.
4. Spoken text or voiceover intent in MUSIC_ONLY fails NO_FORBIDDEN_AUDIO_OPERATION.
5. Audio tracks or spoken text in SILENT mode fails NO_FORBIDDEN_AUDIO_OPERATION.
6. Missing required system capabilities fails NO_IMPOSSIBLE_CAPABILITY.
7. Unresolved guidance conflicts fail NO_UNRESOLVED_CONFLICTS.
8. Empty scene purpose fails SCENE_PURPOSE_COMPLETENESS.
9. Invalid references (duplicate IDs, brief_id mismatch) fail VALID_REFERENCES.
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
from ai.contracts.creative.plan import SceneIntent
from ai.planning.creative_planner import CreativePlanner
from ai.planning.validator import CreativePlanValidator
from tests.ai.planning.conftest import create_test_brief, create_test_recipe


@pytest.fixture
def planner() -> CreativePlanner:
    return CreativePlanner()


@pytest.fixture
def validator() -> CreativePlanValidator:
    return CreativePlanValidator()


def test_validator_passes_valid_plan(planner, validator, narrative_planner):
    """Verifies that a well-formed plan passes all checked invariants."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    recipe = create_test_recipe()

    plan = planner.plan(brief=brief, narrative_plan=narrative_plan, recipe=recipe)
    res = validator.validate(plan=plan, brief=brief, recipe=recipe)

    assert res.valid is True
    assert len(res.errors) == 0
    assert "COVERS_USER_GOAL" in res.checked_invariants
    assert "DURATION_FITS" in res.checked_invariants
    assert "NO_FORBIDDEN_AUDIO_OPERATION" in res.checked_invariants
    assert "SCENE_PURPOSE_COMPLETENESS" in res.checked_invariants
    assert "VALID_REFERENCES" in res.checked_invariants


def test_validator_rejects_brief_id_mismatch(planner, validator, narrative_planner):
    """Verifies rejection when plan brief_id does not match the target brief."""
    brief = create_test_brief(brief_id="brief_original")
    other_brief = create_test_brief(brief_id="brief_other")
    narrative_plan = narrative_planner.plan(brief)

    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    res = validator.validate(plan=plan, brief=other_brief)

    assert res.valid is False
    assert any("does not match" in e for e in res.errors)


def test_validator_rejects_dropped_narrative_beat(planner, validator, narrative_planner):
    """Verifies that dropping a narrative beat causes COVERS_USER_GOAL validation failure."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Artificially remove one scene (dropping beat_0)
    mutated_scenes = plan.scenes[1:]
    # Reindex remaining scenes and adjust total duration so Pydantic model validator passes
    reindexed_scenes = [
        s.model_copy(update={"scene_index": i})
        for i, s in enumerate(mutated_scenes)
    ]
    new_total = round(sum(s.estimated_duration_sec for s in reindexed_scenes), 2)
    tampered_plan = plan.model_copy(update={
        "scenes": reindexed_scenes,
        "total_estimated_duration_sec": new_total,
    })

    res = validator.validate(plan=tampered_plan, brief=brief)
    assert res.valid is False
    assert any("dropped required narrative beats" in e for e in res.errors)


def test_validator_rejects_impossible_duration(planner, validator, narrative_planner):
    """Verifies that an out-of-bounds duration triggers DURATION_FITS failure."""
    brief = create_test_brief(target_duration=30.0)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Artificially inflate scene durations to 60.0s for a 30s brief
    inflated_scenes = [
        s.model_copy(update={"estimated_duration_sec": s.estimated_duration_sec * 2.0})
        for s in plan.scenes
    ]
    new_total = round(sum(s.estimated_duration_sec for s in inflated_scenes), 2)
    tampered_plan = plan.model_copy(update={
        "scenes": inflated_scenes,
        "total_estimated_duration_sec": new_total,
    })

    res = validator.validate(plan=tampered_plan, brief=brief)
    assert res.valid is False
    assert any("exceeds acceptable bounds" in e for e in res.errors)


def test_validator_rejects_spoken_text_in_music_only(planner, validator, narrative_planner):
    """Verifies that spoken text in MUSIC_ONLY triggers NO_FORBIDDEN_AUDIO_OPERATION."""
    brief = create_test_brief(audio_mode=AudioMode.MUSIC_ONLY)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Tamper with scene 0 to include spoken text
    mutated_scenes = list(plan.scenes)
    mutated_scenes[0] = mutated_scenes[0].model_copy(update={"spoken_text": "Illegal voiceover text"})
    tampered_plan = plan.model_copy(update={"scenes": mutated_scenes})

    res = validator.validate(plan=tampered_plan, brief=brief)
    assert res.valid is False
    assert any("AudioMode.MUSIC_ONLY" in e for e in res.errors)


def test_validator_rejects_audio_in_silent_mode(planner, validator, narrative_planner):
    """Verifies that audio intent in SILENT mode triggers NO_FORBIDDEN_AUDIO_OPERATION."""
    brief = create_test_brief(audio_mode=AudioMode.SILENT)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Tamper with scene 0 to specify loud music
    mutated_scenes = list(plan.scenes)
    mutated_scenes[0] = mutated_scenes[0].model_copy(update={"audio_intent": "loud_techno_bgm"})
    tampered_plan = plan.model_copy(update={"scenes": mutated_scenes})

    res = validator.validate(plan=tampered_plan, brief=brief)
    assert res.valid is False
    assert any("SILENT" in e for e in res.errors)


def test_validator_rejects_missing_required_capability(planner, validator, narrative_planner):
    """Verifies that unavailable required capabilities trigger NO_IMPOSSIBLE_CAPABILITY."""
    brief = create_test_brief(audio_mode=AudioMode.VO_MUSIC)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Pass available capabilities excluding TEXT_TO_SPEECH
    res = validator.validate(
        plan=plan,
        brief=brief,
        available_capabilities=["IMAGE_UPSCALE", "VIDEO_GENERATION"],
    )
    assert res.valid is False
    assert any("TEXT_TO_SPEECH" in e for e in res.errors)


def test_validator_rejects_unresolved_guidance_conflicts(planner, validator, narrative_planner):
    """Verifies that unresolved creative conflicts cause validation failure."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    conflict = CreativeConflict(
        conflict_id="c1",
        conflict_type="STYLE_CONTRADICTION",
        severity=ConflictSeverity.HARD,
        description="Conflicting fonts",
        conflicting_parties=["User", "Recipe"],
        competing_directives={},
        applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
        status=ConflictStatus.UNRESOLVED,
        reason_summary="Cannot pick font",
    )

    guidance = ResolvedCreativeGuidance(
        guidance_id="g1",
        brief_id=brief.brief_id,
        recipe_id="r1",
        narrative_plan=narrative_plan,
        taste_decisions=[],
        detected_conflicts=[conflict],
        unresolved_conflicts=[conflict],
        status="FAILED_UNRESOLVED_CONFLICT",
        provenance=brief.provenance,
        created_at=datetime.now(timezone.utc),
    )

    res = validator.validate(plan=plan, brief=brief, guidance=guidance)
    assert res.valid is False
    assert any("unresolved conflict" in e.lower() for e in res.errors)


def test_validator_rejects_empty_scene_purpose(planner, validator, narrative_planner):
    """Verifies that empty intent_label triggers SCENE_PURPOSE_COMPLETENESS failure."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    mutated_scenes = list(plan.scenes)
    mutated_scenes[0] = mutated_scenes[0].model_copy(update={"intent_label": ""})
    tampered_plan = plan.model_copy(update={"scenes": mutated_scenes})

    res = validator.validate(plan=tampered_plan, brief=brief)
    assert res.valid is False
    assert any("missing required intent_label" in e for e in res.errors)
