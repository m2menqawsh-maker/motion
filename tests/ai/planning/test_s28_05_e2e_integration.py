"""
tests/ai/planning/test_s28_05_e2e_integration.py
================================================
End-to-End Golden Integration Test Suite for S28-05 (Section 60 & 80).

Verifies the complete pipeline flow across 4 canonical video archetypes:
1. Simple SaaS / Product Ad (VO_MUSIC, 30s)
2. Talking Head / Interview Repurpose (VO_ONLY / SOURCE_AUDIO, 30s)
3. Dynamic Music Montage (MUSIC_ONLY, 25s)
4. Educational Explainer (VO_MUSIC, 45s)

Pipeline Flow:
CreativeBrief + Recipe + NarrativePlan + TasteDecisions + ResolvedCreativeGuidance
  ↓
CreativePlanner
  ↓
typed CreativePlan
  ↓
CreativePlanValidator -> VALID
  ↓
template decisions fixture + asset manifest + TemplateRegistryContract
  ↓
BlueprintCompiler
  ↓
Canonical BlueprintV2
  ↓
Core validate_blueprint_v2 -> PASS
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, List

from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.conflict import ResolvedCreativeGuidance
from ai.contracts.creative.directors import (
    DirectorRecommendationBundle,
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
)
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    ResolvedTemplateDecision,
)
from ai.contracts.creative.taste import TasteDecision
from ai.narrative.planner import NarrativePlanner
from ai.planning.compiler import BlueprintCompiler
from ai.planning.creative_planner import CreativePlanner
from ai.planning.validator import CreativePlanValidator
from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.template_contract import TemplateRegistryContract
from tests.ai.planning.conftest import (
    create_test_brief,
    create_test_manifest,
    create_test_recipe,
)


@pytest.fixture
def planner() -> CreativePlanner:
    return CreativePlanner()


@pytest.fixture
def validator() -> CreativePlanValidator:
    return CreativePlanValidator()


@pytest.fixture
def compiler() -> BlueprintCompiler:
    return BlueprintCompiler()


@pytest.fixture
def narrative_planner() -> NarrativePlanner:
    return NarrativePlanner()


@pytest.fixture
def template_registry() -> TemplateRegistryContract:
    return TemplateRegistryContract()


def assign_template_decisions(plan: CreativePlan, templates: List[str]) -> Dict[str, ResolvedTemplateDecision]:
    decisions = {}
    for idx, scene in enumerate(plan.scenes):
        t_id = templates[idx % len(templates)]
        decisions[scene.scene_id] = ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id=t_id,
            template_props={"scene_title": scene.intent_label},
        )
    return decisions


# ─── Golden Flow 1: SaaS Product Demo (VO_MUSIC, 30s) ──────────────────────────

def test_golden_flow_saas_product_demo(planner, validator, compiler, narrative_planner, template_registry):
    brief = create_test_brief(
        brief_id="brief_golden_saas",
        video_type="SAAS_DEMO",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=30.0,
        goal="Showcase automated zero-downtime database failover",
    )
    recipe = create_test_recipe(recipe_id="saas-demo-recipe", audio_mode=AudioMode.VO_MUSIC)
    narrative_plan = narrative_planner.plan(brief)

    # 1. Creative Planning
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan, recipe=recipe)
    assert plan.status == CreativePlanStatus.PROPOSED
    assert plan.total_estimated_duration_sec == 30.0

    # 2. Validation Gate
    val_res = validator.validate(plan=plan, brief=brief, recipe=recipe)
    assert val_res.valid is True, f"Validation failed: {val_res.errors}"

    # 3. Compilation Gate
    templates = ["rui-hook-card", "animatedtext-element", "codeblock-element", "animatedcounter-element", "rui-split-screen"]
    decisions = assign_template_decisions(plan, templates)
    manifest = create_test_manifest(project_id=brief.project_id)
    audio_assets = {"voiceover": "ast_vo_01", "music": "ast_bgm_01"}

    comp_res = compiler.compile(
        plan=plan,
        template_decisions=decisions,
        manifest=manifest,
        template_registry=template_registry,
        project_id=brief.project_id,
        fps=30,
        aspect_ratio="9:16",
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets=audio_assets,
    )

    assert comp_res.success is True
    bp = comp_res.blueprint
    assert bp["project_id"] == brief.project_id
    total_frames = sum(s["durationFrames"] for s in bp["scenes"])
    assert total_frames == 900  # 30s * 30fps = 900 frames

    # 4. Core Blueprint Validation
    core_val = validate_blueprint_v2(bp, expected_project_id=brief.project_id, manifest=manifest)
    assert core_val.ok is True, f"Core validation failed: {core_val.errors}"


# ─── Golden Flow 2: Talking Head Repurpose (VO_ONLY, 30s) ──────────────────────

def test_golden_flow_talking_head(planner, validator, compiler, narrative_planner, template_registry):
    brief = create_test_brief(
        brief_id="brief_golden_talking_head",
        video_type="TALKING_HEAD",
        audio_mode=AudioMode.VO_ONLY,
        target_duration=30.0,
        goal="Founder interview on remote work philosophy",
    )
    narrative_plan = narrative_planner.plan(brief)

    # 1. Creative Planning
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    assert plan.status == CreativePlanStatus.PROPOSED

    # 2. Validation Gate
    val_res = validator.validate(plan=plan, brief=brief)
    assert val_res.valid is True, f"Validation failed: {val_res.errors}"

    # 3. Compilation Gate
    templates = ["rui-hook-card", "animatedtext-element", "rui-split-screen"]
    decisions = assign_template_decisions(plan, templates)
    manifest = create_test_manifest(project_id=brief.project_id, asset_ids=["ast_vo_01"])
    audio_assets = {"voiceover": "ast_vo_01"}

    comp_res = compiler.compile(
        plan=plan,
        template_decisions=decisions,
        manifest=manifest,
        template_registry=template_registry,
        project_id=brief.project_id,
        fps=30,
        aspect_ratio="16:9",
        audio_mode=AudioMode.VO_ONLY,
        audio_assets=audio_assets,
    )

    assert comp_res.success is True
    bp = comp_res.blueprint
    assert bp["audio"].get("voiceover") is not None
    assert bp["audio"].get("music") is None

    core_val = validate_blueprint_v2(bp, expected_project_id=brief.project_id, manifest=manifest)
    assert core_val.ok is True


# ─── Golden Flow 3: Dynamic Music Montage (MUSIC_ONLY, 25s) ────────────────────

def test_golden_flow_music_montage(planner, validator, compiler, narrative_planner, template_registry):
    brief = create_test_brief(
        brief_id="brief_golden_montage",
        video_type="DYNAMIC_MONTAGE",
        audio_mode=AudioMode.MUSIC_ONLY,
        target_duration=25.0,
        goal="Energy drink summer vibes kinetic cut",
    )
    narrative_plan = narrative_planner.plan(brief)

    # 1. Creative Planning
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    assert plan.status == CreativePlanStatus.PROPOSED
    # Strict verification: no voiceover in plan scenes
    for scene in plan.scenes:
        assert scene.spoken_text is None
        assert "music" in scene.audio_intent.lower()

    # 2. Validation Gate
    val_res = validator.validate(plan=plan, brief=brief)
    assert val_res.valid is True, f"Validation failed: {val_res.errors}"

    # 3. Compilation Gate
    templates = ["rui-hook-card", "gradient-element", "animatedcounter-element"]
    decisions = assign_template_decisions(plan, templates)
    manifest = create_test_manifest(project_id=brief.project_id, asset_ids=["ast_bgm_01"])
    audio_assets = {"music": "ast_bgm_01"}

    comp_res = compiler.compile(
        plan=plan,
        template_decisions=decisions,
        manifest=manifest,
        template_registry=template_registry,
        project_id=brief.project_id,
        fps=30,
        aspect_ratio="9:16",
        audio_mode=AudioMode.MUSIC_ONLY,
        audio_assets=audio_assets,
    )

    assert comp_res.success is True
    bp = comp_res.blueprint
    assert bp["audio"].get("voiceover") is None
    assert bp["audio"].get("music") is not None
    assert bp["audio"]["music"].get("ducking") is None  # No ducking needed without VO

    core_val = validate_blueprint_v2(bp, expected_project_id=brief.project_id, manifest=manifest)
    assert core_val.ok is True


# ─── Golden Flow 4: Educational Explainer (VO_MUSIC, 45s) ──────────────────────

def test_golden_flow_educational_explainer(planner, validator, compiler, narrative_planner, template_registry):
    brief = create_test_brief(
        brief_id="brief_golden_explainer",
        video_type="EDUCATIONAL_EXPLAINER",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=45.0,
        goal="Explain how quantum encryption ensures data sovereignty",
    )
    narrative_plan = narrative_planner.plan(brief)

    # 1. Creative Planning
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)
    assert plan.status == CreativePlanStatus.PROPOSED
    assert plan.total_estimated_duration_sec == 45.0

    # 2. Validation Gate
    val_res = validator.validate(plan=plan, brief=brief)
    assert val_res.valid is True, f"Validation failed: {val_res.errors}"

    # 3. Compilation Gate
    templates = ["rui-hook-card", "codeblock-element", "animatedtext-element", "rui-split-screen"]
    decisions = assign_template_decisions(plan, templates)
    manifest = create_test_manifest(project_id=brief.project_id)
    audio_assets = {"voiceover": "ast_vo_01", "music": "ast_bgm_01"}

    comp_res = compiler.compile(
        plan=plan,
        template_decisions=decisions,
        manifest=manifest,
        template_registry=template_registry,
        project_id=brief.project_id,
        fps=30,
        aspect_ratio="16:9",
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets=audio_assets,
    )

    assert comp_res.success is True
    bp = comp_res.blueprint
    total_frames = sum(s["durationFrames"] for s in bp["scenes"])
    assert total_frames == 1350  # 45s * 30fps = 1350 frames

    core_val = validate_blueprint_v2(bp, expected_project_id=brief.project_id, manifest=manifest)
    assert core_val.ok is True
