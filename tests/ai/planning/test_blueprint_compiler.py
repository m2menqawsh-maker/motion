"""
tests/ai/planning/test_blueprint_compiler.py
============================================
Unit & Determinism tests for BlueprintCompiler (S28-05 Part C).

Verifies:
1. Translates high-level CreativePlan + template decisions + assets -> canonical BlueprintV2.
2. Determinism test: 100% structural equality across repeated runs with identical inputs.
3. Frames & Timing: converts desired durations into exact frame counts and contiguous startFrames.
4. AudioPlan compilation:
   - SILENT -> audio is None.
   - MUSIC_ONLY -> music track only, voiceover strictly absent.
   - VO_ONLY -> voiceover track only, music absent.
   - VO_MUSIC -> voiceover + music bed with ducking.
5. Template Registry authority: validates templates against canonical catalog.
6. Manifest Asset authority: validates asset references against manifest.
7. Core validation: compiled Blueprint passes scripts.core.blueprint_validator.validate_blueprint_v2.
"""

import hashlib
import json
import pytest

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    BlueprintCompilationResult,
    ResolvedTemplateDecision,
)
from ai.planning.compiler import BlueprintCompiler
from ai.planning.creative_planner import CreativePlanner
from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_validator import validate_blueprint_v2
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


def build_template_decisions_for_plan(plan) -> dict:
    """Helper fixture resolving canonical templates for each scene in plan."""
    available_templates = [
        "rui-hook-card",
        "animatedtext-element",
        "rui-split-screen",
        "codeblock-element",
        "animatedcounter-element",
    ]
    decisions = {}
    for idx, scene in enumerate(plan.scenes):
        t_id = available_templates[idx % len(available_templates)]
        decisions[scene.scene_id] = ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id=t_id,
            template_props={"title": scene.intent_label, "accent_color": "#00F5FF"},
        )
    return decisions


def test_compiler_translates_plan_to_canonical_blueprint(planner, compiler, narrative_planner, template_registry):
    """Verifies complete translation from CreativePlan to canonical BlueprintV2."""
    brief = create_test_brief(
        video_type="SAAS_DEMO",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=30.0,
    )
    narrative_plan = narrative_planner.plan(brief)
    recipe = create_test_recipe()
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan, recipe=recipe)

    template_decisions = build_template_decisions_for_plan(plan)
    manifest = create_test_manifest(project_id=brief.project_id)
    audio_assets = {"voiceover": "ast_vo_01", "music": "ast_bgm_01"}

    result = compiler.compile(
        plan=plan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=template_registry,
        project_id=brief.project_id,
        fps=30,
        aspect_ratio="9:16",
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets=audio_assets,
    )

    assert isinstance(result, BlueprintCompilationResult)
    assert result.success is True
    assert result.blueprint is not None

    bp_data = result.blueprint
    assert bp_data["blueprint_version"] == "2.0.0"
    assert bp_data["project_id"] == brief.project_id
    assert bp_data["fps"] == 30
    assert bp_data["aspect_ratio"] == "9:16"
    assert len(bp_data["scenes"]) == len(plan.scenes)

    # Core validation check
    val_res = validate_blueprint_v2(bp_data, expected_project_id=brief.project_id, manifest=manifest)
    assert val_res.ok is True, f"Core validation failed: {val_res.errors}"


def test_compiler_timing_and_frames_conversion(planner, compiler, narrative_planner, template_registry):
    """Verifies that scene durations in seconds are accurately converted to contiguous frames."""
    brief = create_test_brief(target_duration=30.0)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    template_decisions = build_template_decisions_for_plan(plan)
    manifest = create_test_manifest(project_id=brief.project_id)

    bp = compiler.compile_to_model(
        plan=plan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=template_registry,
        fps=30,
    )

    assert isinstance(bp, BlueprintV2)
    expected_start = 0
    total_frames = 0

    for idx, scene in enumerate(bp.scenes):
        assert scene.startFrame == expected_start
        assert scene.durationFrames >= 1
        expected_frames = max(1, round(plan.scenes[idx].estimated_duration_sec * 30))
        assert scene.durationFrames == expected_frames
        expected_start += scene.durationFrames
        total_frames += scene.durationFrames

    assert bp.total_duration_frames == total_frames


def test_compiler_audio_modes(planner, compiler, narrative_planner, template_registry):
    """Verifies AudioPlan compilation across AudioModes."""
    # 1. SILENT mode -> audio is None
    brief_silent = create_test_brief(audio_mode=AudioMode.SILENT)
    narrative_silent = narrative_planner.plan(brief_silent)
    plan_silent = planner.plan(brief=brief_silent, narrative_plan=narrative_silent)
    decisions_silent = build_template_decisions_for_plan(plan_silent)

    bp_silent = compiler.compile_to_model(
        plan=plan_silent,
        template_decisions=decisions_silent,
        template_registry=template_registry,
        audio_mode=AudioMode.SILENT,
    )
    assert bp_silent.audio is None

    # 2. MUSIC_ONLY mode -> music track present, voiceover track None
    brief_music = create_test_brief(audio_mode=AudioMode.MUSIC_ONLY)
    narrative_music = narrative_planner.plan(brief_music)
    plan_music = planner.plan(brief=brief_music, narrative_plan=narrative_music)
    decisions_music = build_template_decisions_for_plan(plan_music)
    manifest_music = create_test_manifest(project_id=brief_music.project_id)

    bp_music = compiler.compile_to_model(
        plan=plan_music,
        template_decisions=decisions_music,
        manifest=manifest_music,
        template_registry=template_registry,
        audio_mode=AudioMode.MUSIC_ONLY,
        audio_assets={"music": "ast_bgm_01"},
    )
    assert bp_music.audio is not None
    assert bp_music.audio.voiceover is None
    assert bp_music.audio.music is not None
    assert bp_music.audio.music.asset_ref == "ast_bgm_01"

    # 3. VO_ONLY mode -> voiceover track present, music track None
    bp_vo = compiler.compile_to_model(
        plan=plan_music,  # reuse plan
        template_decisions=decisions_music,
        manifest=manifest_music,
        template_registry=template_registry,
        audio_mode=AudioMode.VO_ONLY,
        audio_assets={"voiceover": "ast_vo_01"},
    )
    assert bp_vo.audio is not None
    assert bp_vo.audio.voiceover is not None
    assert bp_vo.audio.voiceover.asset_ref == "ast_vo_01"
    assert bp_vo.audio.music is None

    # 4. VO_MUSIC mode -> both present with ducking
    bp_vo_music = compiler.compile_to_model(
        plan=plan_music,
        template_decisions=decisions_music,
        manifest=manifest_music,
        template_registry=template_registry,
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets={"voiceover": "ast_vo_01", "music": "ast_bgm_01"},
    )
    assert bp_vo_music.audio is not None
    assert bp_vo_music.audio.voiceover is not None
    assert bp_vo_music.audio.music is not None
    assert bp_vo_music.audio.music.ducking is not None
    assert bp_vo_music.audio.music.ducking.enabled is True


def test_compiler_determinism_100_percent(planner, compiler, narrative_planner, template_registry):
    """
    CRITICAL DETERMINISM ACCEPTANCE TEST (Section 38 & 81):
    Same CreativePlan + same Template Decisions + same Manifest + same compiler config
    MUST yield 100% identical canonical Blueprint across 20 repeated runs.
    """
    brief = create_test_brief(target_duration=30.0)
    narrative_plan = narrative_planner.plan(brief)
    plan = planner.plan(brief=brief, narrative_plan=narrative_plan)

    template_decisions = build_template_decisions_for_plan(plan)
    manifest = create_test_manifest(project_id=brief.project_id)
    audio_assets = {"voiceover": "ast_vo_01", "music": "ast_bgm_01"}

    digests = []
    canonical_json_first = None

    for run_idx in range(20):
        result = compiler.compile(
            plan=plan,
            template_decisions=template_decisions,
            manifest=manifest,
            template_registry=template_registry,
            project_id=brief.project_id,
            fps=30,
            aspect_ratio="9:16",
            audio_mode=AudioMode.VO_MUSIC,
            audio_assets=audio_assets,
        )

        canonical_json = json.dumps(result.blueprint, sort_keys=True, separators=(',', ':'))
        h = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        digests.append(h)

        if canonical_json_first is None:
            canonical_json_first = canonical_json
        else:
            assert canonical_json == canonical_json_first, f"Structural drift detected at run {run_idx}!"

    # 100% identical hashes across all 20 runs
    assert len(set(digests)) == 1
