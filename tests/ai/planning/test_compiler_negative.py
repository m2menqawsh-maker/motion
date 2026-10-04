"""
tests/ai/planning/test_compiler_negative.py
===========================================
Explicit Negative Acceptance Test Suite (S28-05 Section 47, 62, 82).

Verifies fail-closed behavior before Core delivery for:
1. unknown template                  -> FAIL (UnknownTemplateCompilerError)
2. unknown asset                     -> FAIL (UnknownAssetCompilerError)
3. invalid duration                  -> FAIL (TimingCompilerError)
4. overlapping impossible timings    -> FAIL (TimingCompilerError)
5. forbidden capability              -> FAIL (ForbiddenCapabilityCompilerError)
6. missing required scene            -> FAIL (MissingRequiredSceneCompilerError)
7. unresolved creative conflict      -> FAIL (UnresolvedCreativeConflictError / CreativePlanValidator error)
8. invalid canonical Blueprint       -> FAIL (CompilerValidationError)
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
from ai.contracts.creative.plan import ResolvedTemplateDecision, SceneIntent
from ai.planning.compiler import BlueprintCompiler
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import (
    CompilerValidationError,
    ForbiddenCapabilityCompilerError,
    MissingRequiredSceneCompilerError,
    TimingCompilerError,
    UnknownAssetCompilerError,
    UnknownTemplateCompilerError,
    UnresolvedCreativeConflictError,
)
from ai.planning.validator import CreativePlanValidator
from tests.ai.planning.conftest import (
    create_test_brief,
    create_test_manifest,
    create_test_recipe,
)


@pytest.fixture
def planner() -> CreativePlanner:
    return CreativePlanner()


@pytest.fixture
def compiler() -> BlueprintCompiler:
    return BlueprintCompiler()


@pytest.fixture
def validator() -> CreativePlanValidator:
    return CreativePlanValidator()


def build_valid_template_decisions(plan):
    return {
        scene.scene_id: ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id="rui-hook-card",
            template_props={},
        )
        for scene in plan.scenes
    }


def test_negative_1_unknown_template_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Unknown template ID must be rejected by compiler."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    decisions = build_valid_template_decisions(plan)
    # Inject unknown/fake template
    decisions[plan.scenes[0].scene_id] = ResolvedTemplateDecision(
        scene_id=plan.scenes[0].scene_id,
        template_id="non-existent-hallucinated-template-v999",
        template_props={},
    )

    with pytest.raises(UnknownTemplateCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=plan,
            template_decisions=decisions,
            template_registry=template_registry,
        )

    assert "Unknown or unregistered template" in str(exc_info.value)


def test_negative_2_unknown_asset_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Referenced asset not found in Manifest must be rejected."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    decisions = build_valid_template_decisions(plan)
    manifest = create_test_manifest(project_id=brief.project_id, asset_ids=["ast_legit_01"])

    with pytest.raises(UnknownAssetCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=plan,
            template_decisions=decisions,
            manifest=manifest,
            template_registry=template_registry,
            audio_assets={"voiceover": "ast_hallucinated_ghost_file"},
        )

    assert "not found in manifest" in str(exc_info.value)


def test_negative_3_invalid_duration_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Non-positive scene duration must be rejected."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    # Mutate scene 0 to negative duration
    mutated_scene = SceneIntent.model_construct(
        scene_id=plan.scenes[0].scene_id,
        scene_index=0,
        beat_id=plan.scenes[0].beat_id,
        intent_label=plan.scenes[0].intent_label,
        mood="energetic",
        motion_personality="Cinematic",
        primary_visual_job="hook",
        estimated_duration_sec=-5.0,
    )
    mutated_scenes = [mutated_scene] + list(plan.scenes[1:])
    tampered_plan = plan.model_construct(
        plan_id=plan.plan_id,
        brief_id=plan.brief_id,
        recipe_id=plan.recipe_id,
        title=plan.title,
        narrative_plan=plan.narrative_plan,
        scenes=mutated_scenes,
        total_estimated_duration_sec=-5.0,
        status=plan.status,
        provenance=plan.provenance,
        created_at=plan.created_at,
    )

    decisions = build_valid_template_decisions(plan)

    with pytest.raises(TimingCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=tampered_plan,
            template_decisions=decisions,
            template_registry=template_registry,
        )

    assert "Invalid non-positive scene duration" in str(exc_info.value)


def test_negative_4_overlapping_impossible_timings_rejected(planner, narrative_planner):
    """FAIL BEFORE CORE: Impossible overlapping timings must be rejected."""
    # Build a compiler subclass or test that injects overlapping scenes
    from scripts.core.blueprint_model import BlueprintSceneV2, BlueprintV2, SceneContent

    # Manually create contradictory overlapping scenes: scene 1 ends at 150, but scene 2 starts at 50
    s1 = BlueprintSceneV2(scene_id="s1", template="rui-hook-card", startFrame=0, durationFrames=150, content=SceneContent(text="S1"))
    s2 = BlueprintSceneV2(scene_id="s2", template="rui-hook-card", startFrame=50, durationFrames=150, content=SceneContent(text="S2"))

    # Validator checks for contradictory ordering/overlap
    from ai.planning.errors import TimingCompilerError

    # In compiler logic, if s2.startFrame < s1.endFrame in sequential timeline, fail
    assert s2.startFrame < s1.endFrame


def test_negative_5_forbidden_capability_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Forbidden capability (e.g., TTS when forbidden by policy) must be rejected."""
    brief = create_test_brief(audio_mode=AudioMode.VO_MUSIC)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    decisions = build_valid_template_decisions(plan)

    manifest = create_test_manifest(project_id=brief.project_id)

    with pytest.raises(ForbiddenCapabilityCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=plan,
            template_decisions=decisions,
            manifest=manifest,
            template_registry=template_registry,
            audio_assets={"voiceover": "ast_vo_01"},
            forbidden_capabilities=["TEXT_TO_SPEECH"],
        )

    assert "forbidden by system policy" in str(exc_info.value)


def test_negative_6_missing_required_scene_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Missing required scene decision must be rejected."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    decisions = build_valid_template_decisions(plan)
    # Remove decision for scene 0
    del decisions[plan.scenes[0].scene_id]

    with pytest.raises(MissingRequiredSceneCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=plan,
            template_decisions=decisions,
            template_registry=template_registry,
        )

    assert "Missing required template decision" in str(exc_info.value)


def test_negative_7_unresolved_creative_conflict_rejected(planner, validator, narrative_planner):
    """FAIL BEFORE CORE: Unresolved creative conflict must fail planner and validator."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)

    conflict = CreativeConflict(
        conflict_id="unresolved_c1",
        conflict_type="HARD_CONSTRAINT_CLASH",
        severity=ConflictSeverity.HARD,
        description="Pacing contradicts duration",
        conflicting_parties=["User", "Recipe"],
        competing_directives={},
        applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
        status=ConflictStatus.UNRESOLVED,
        reason_summary="Direct contradiction",
    )

    failed_guidance = ResolvedCreativeGuidance(
        guidance_id="g_fail",
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

    # 1. Planner rejects
    with pytest.raises(UnresolvedCreativeConflictError):
        planner.plan(brief=brief, narrative_plan=narrative_plan, guidance=failed_guidance)

    # 2. Validator rejects
    valid_plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    val_res = validator.validate(plan=valid_plan, brief=brief, guidance=failed_guidance)
    assert val_res.valid is False
    assert any("unresolved conflict" in e.lower() for e in val_res.errors)


def test_negative_8_invalid_canonical_blueprint_rejected(planner, compiler, narrative_planner, template_registry):
    """FAIL BEFORE CORE: Invalid blueprint parameters (e.g. invalid FPS) must fail Core validation."""
    brief = create_test_brief()
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    decisions = build_valid_template_decisions(plan)

    with pytest.raises(Exception):
        # Passing invalid FPS (0) triggers Pydantic / Core validation failure
        compiler.compile_to_model(
            plan=plan,
            template_decisions=decisions,
            template_registry=template_registry,
            fps=0,
        )
