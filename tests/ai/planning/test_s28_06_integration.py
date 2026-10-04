"""
tests/ai/planning/test_s28_06_integration.py
============================================
Authoritative End-to-End Integration Test Suite for S28-06:
- Case 1: REUSE -> CreativeTierDecision -> BlueprintCompiler -> validate_blueprint_v2 PASS
- Case 2: COMPOSE -> CompositionPlan -> BlueprintCompiler (layers + effects) -> validate_blueprint_v2 PASS
- Case 3: CREATE-needed -> compilation halts on NeedsCreateEscalationCompilerError (NO code gen)
- Case 4: Heterogeneous multi-scene workflow (REUSE + COMPOSE) compiling to valid BlueprintV2
- Case 5: Anti-Bypass enforcement workflow (CREATE request denied -> REUSE compiled successfully)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Dict, List

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    CreativeTier,
    SceneIntent,
)
from ai.narrative.planner import NarrativePlanner
from ai.planning.compiler import BlueprintCompiler
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import NeedsCreateEscalationCompilerError
from ai.planning.tier_policy import CreativeTierPolicy
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.probe_planner import derive_probe_frame_plan
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from tests.ai.planning.conftest import (
    create_test_brief,
    create_test_manifest,
    create_test_recipe,
)


@pytest.fixture
def tier_policy() -> CreativeTierPolicy:
    return CreativeTierPolicy()


@pytest.fixture
def compiler() -> BlueprintCompiler:
    return BlueprintCompiler()


@pytest.fixture
def narrative_planner() -> NarrativePlanner:
    return NarrativePlanner()


@pytest.fixture
def creative_planner() -> CreativePlanner:
    return CreativePlanner()


def test_integration_case_1_reuse_to_blueprint_validation(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """Case 1: Standard metric need -> REUSE decision -> Blueprint compiled -> validate_blueprint_v2 PASS."""
    brief = create_test_brief(brief_id="brief_c1", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    # Use metric intent compatible with registered templates
    scene = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "statistic",
            "primary_visual_job": "proof",
            "template_requirements": ["metric"],
        }
    )
    decision = tier_policy.decide(scene_intent=scene, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.REUSE
    assert decision.template_ref is not None

    single_scene_plan = base_plan.model_copy(
        update={
            "scenes": [scene],
            "total_estimated_duration_sec": scene.estimated_duration_sec,
            "tier_decisions": [decision],
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    blueprint = compiler.compile_to_model(
        plan=single_scene_plan,
        template_decisions=[decision],
        manifest=manifest,
        project_id=brief.project_id,
        aspect_ratio="9:16",
        audio_assets={"voiceover": "ast_vo_01", "background_music": "ast_bgm_01"},
    )

    assert blueprint is not None
    assert len(blueprint.scenes) == 1
    assert blueprint.scenes[0].template == decision.template_ref

    val_res = validate_blueprint_v2(blueprint)
    assert val_res.ok is True, f"Validation errors: {val_res.errors}"


def test_integration_case_2_compose_to_blueprint_validation(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """Case 2: Composite split requirement -> COMPOSE decision -> Blueprint compiled with layers -> validate PASS."""
    brief = create_test_brief(brief_id="brief_c2", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    # Craft composite scene intent requiring composition
    comp_scene = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "comparison",
            "primary_visual_job": "comparison",
            "template_requirements": ["split_screen_dual_view_custom_layout"],
        }
    )
    decision = tier_policy.decide(scene_intent=comp_scene, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.COMPOSE
    assert decision.composition_plan is not None

    single_scene_plan = base_plan.model_copy(
        update={
            "scenes": [comp_scene],
            "total_estimated_duration_sec": comp_scene.estimated_duration_sec,
            "tier_decisions": [decision],
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    blueprint = compiler.compile_to_model(
        plan=single_scene_plan,
        template_decisions=[decision],
        manifest=manifest,
        project_id=brief.project_id,
        aspect_ratio="9:16",
        audio_assets={"voiceover": "ast_vo_01", "background_music": "ast_bgm_01"},
    )

    assert blueprint is not None
    assert len(blueprint.scenes) == 1
    compiled_scene = blueprint.scenes[0]
    assert compiled_scene.template == decision.composition_plan.base_template_or_primitive
    assert compiled_scene.transition is not None
    assert len(compiled_scene.effects) > 0

    val_res = validate_blueprint_v2(blueprint)
    assert val_res.ok is True, f"Validation errors: {val_res.errors}"


def test_integration_case_3_create_escalation_stops_cleanly(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """Case 3: Unsatisfiable need -> CREATE decision -> BlueprintCompiler halts on NeedsCreateEscalationCompilerError."""
    brief = create_test_brief(brief_id="brief_c3", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    # Impossible scene intent outside Lego primitives
    impossible_scene = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "novel_3d_simulation_neural_avatar",
            "primary_visual_job": "action",
            "template_requirements": ["unsupported_quantum_rendering"],
        }
    )
    decision = tier_policy.decide(scene_intent=impossible_scene, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.CREATE
    assert decision.needs_create_evaluation is True

    single_scene_plan = base_plan.model_copy(
        update={
            "scenes": [impossible_scene],
            "total_estimated_duration_sec": impossible_scene.estimated_duration_sec,
            "tier_decisions": [decision],
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    with pytest.raises(NeedsCreateEscalationCompilerError) as exc_info:
        compiler.compile_to_model(
            plan=single_scene_plan,
            template_decisions=[decision],
            manifest=manifest,
            project_id=brief.project_id,
        )

    err_msg = str(exc_info.value)
    assert "requires CREATE escalation (S28-07)" in err_msg
    assert "Compilation stopped awaiting candidate template creation" in err_msg


def test_integration_case_4_heterogeneous_plan_e2e(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """Case 4: Multi-scene plan with heterogeneous tiers (Scene 0: REUSE, Scene 1: COMPOSE) compiles cleanly."""
    brief = create_test_brief(brief_id="brief_c4", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    # Scene 0: REUSE (metric counter)
    scene_0 = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "statistic",
            "primary_visual_job": "proof",
            "template_requirements": ["metric"],
        }
    )
    # Scene 1: COMPOSE (composite split comparison)
    scene_1 = base_plan.scenes[1].model_copy(
        update={
            "intent_label": "comparison",
            "primary_visual_job": "comparison",
            "template_requirements": ["split_screen_dual_view_custom_layout"],
        }
    )
    scenes = [scene_0, scene_1]

    decisions = [tier_policy.decide(scene_intent=si, aspect_ratio="9:16") for si in scenes]
    assert decisions[0].selected_tier == CreativeTier.REUSE
    assert decisions[1].selected_tier == CreativeTier.COMPOSE

    multi_plan = base_plan.model_copy(
        update={
            "scenes": scenes,
            "total_estimated_duration_sec": scene_0.estimated_duration_sec + scene_1.estimated_duration_sec,
            "tier_decisions": decisions,
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    blueprint = compiler.compile_to_model(
        plan=multi_plan,
        template_decisions=decisions,
        manifest=manifest,
        project_id=brief.project_id,
        aspect_ratio="9:16",
        audio_assets={"voiceover": "ast_vo_01", "background_music": "ast_bgm_01"},
    )

    assert blueprint is not None
    assert len(blueprint.scenes) == 2
    assert blueprint.scenes[0].template == decisions[0].template_ref
    assert blueprint.scenes[1].template == decisions[1].composition_plan.base_template_or_primitive

    val_res = validate_blueprint_v2(blueprint)
    assert val_res.ok is True, f"Validation errors: {val_res.errors}"


def test_integration_case_5_anti_bypass_enforcement_in_compilation(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """Case 5: Caller requested CREATE, but REUSE was sufficient. Policy denies bypass, and compiler outputs valid Blueprint."""
    brief = create_test_brief(brief_id="brief_c5", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    scene = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "statistic",
            "primary_visual_job": "proof",
            "template_requirements": ["metric"],
        }
    )
    # Caller attempts to force CREATE tier
    decision = tier_policy.decide(
        scene_intent=scene,
        requested_tier=CreativeTier.CREATE,
        aspect_ratio="9:16",
    )
    # Policy enforces REUSE
    assert decision.selected_tier == CreativeTier.REUSE
    assert "Anti-Bypass Enforcement" in decision.rationale

    single_scene_plan = base_plan.model_copy(
        update={
            "scenes": [scene],
            "total_estimated_duration_sec": scene.estimated_duration_sec,
            "tier_decisions": [decision],
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    blueprint = compiler.compile_to_model(
        plan=single_scene_plan,
        template_decisions=[decision],
        manifest=manifest,
        project_id=brief.project_id,
        aspect_ratio="9:16",
        audio_assets={"voiceover": "ast_vo_01", "background_music": "ast_bgm_01"},
    )

    assert blueprint is not None
    assert len(blueprint.scenes) == 1
    assert blueprint.scenes[0].template == decision.template_ref

    val_res = validate_blueprint_v2(blueprint)
    assert val_res.ok is True, f"Validation errors: {val_res.errors}"


def test_integration_compose_e2e_render_smoke_and_probe_plan(
    tier_policy: CreativeTierPolicy,
    compiler: BlueprintCompiler,
    narrative_planner: NarrativePlanner,
    creative_planner: CreativePlanner,
):
    """
    COMPOSE E2E + Render Smoke Probe (S28-06A Requirements 4 & 5):
    - SceneIntent has explicit need requiring composition (split screen)
    - REUSE is insufficient (no single template matches the dual layout req)
    - COMPOSE synthesizes valid CompositionPlan with registered Lego components
    - BlueprintCompiler compiles plan into canonical BlueprintV2
    - Core validation (validate_blueprint_v2) passes
    - Canonical probe frame planner derives complete, deterministic probe frame plan (LED-047/048)
    """
    brief = create_test_brief(brief_id="brief_compose_e2e", video_type="SAAS_DEMO")
    narrative = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    base_plan = creative_planner.plan(brief=brief, narrative_plan=narrative, recipe=recipe)
    manifest = create_test_manifest(project_id=brief.project_id)

    comp_scene = base_plan.scenes[0].model_copy(
        update={
            "intent_label": "comparison",
            "primary_visual_job": "comparison",
            "template_requirements": ["split_screen_dual_view_custom_layout"],
        }
    )
    decision = tier_policy.decide(scene_intent=comp_scene, aspect_ratio="9:16")

    # 1. Decision verification
    assert decision.selected_tier == CreativeTier.COMPOSE
    assert decision.composition_plan is not None
    assert decision.needs_create_evaluation is False

    single_scene_plan = base_plan.model_copy(
        update={
            "scenes": [comp_scene],
            "total_estimated_duration_sec": comp_scene.estimated_duration_sec,
            "tier_decisions": [decision],
            "status": CreativePlanStatus.APPROVED_BY_USER,
        }
    )

    # 2. Compile to canonical BlueprintV2
    blueprint = compiler.compile_to_model(
        plan=single_scene_plan,
        template_decisions=[decision],
        manifest=manifest,
        project_id=brief.project_id,
        aspect_ratio="9:16",
        audio_assets={"voiceover": "ast_vo_01", "background_music": "ast_bgm_01"},
    )
    assert blueprint is not None

    # 3. Core Blueprint validation
    val_res = validate_blueprint_v2(blueprint)
    assert val_res.ok is True, f"Validation errors: {val_res.errors}"

    # 4. Probe Frame Planner derivation (smoke probe verification)
    probe_plan = derive_probe_frame_plan(blueprint)
    assert probe_plan.project_id == brief.project_id
    assert probe_plan.fps == 30
    assert len(probe_plan.samples) >= 3  # Start, Middle, End
    sample_reasons = [s.reason for s in probe_plan.samples]
    assert "SCENE_START" in sample_reasons
    assert "SCENE_MIDDLE" in sample_reasons
    assert "SCENE_END" in sample_reasons

