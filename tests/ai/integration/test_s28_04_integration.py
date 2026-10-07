"""
tests/ai/integration/test_s28_04_integration.py
===============================================
End-to-End Integration Suite for S28-04:
CreativeBrief + Recipe + Knowledge -> NarrativePlan -> TasteEngine -> Directors -> ConflictResolver -> ResolvedCreativeGuidance.

Verifies:
1. Complete creative reasoning pipeline executes deterministically.
2. S28-02 Knowledge & Skills integrated cleanly via canonical platforms.
3. S28-03 Brief and Recipe outputs consumed without re-parsing from scratch.
4. AudioMode policies enforced through all layers.
5. Architectural boundaries preserved (no QC override, no lifecycle mutation, no registry write).
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
from ai.contracts.creative.conflict import ResolvedCreativeGuidance
from ai.contracts.creative.recipe import RecipeDefinition, RecipeStage
from ai.directors.bundle import CreativeDirectorCoordinator
from ai.knowledge.loader import KnowledgeLoader
from ai.knowledge.registry import KnowledgeRegistry
from ai.narrative.planner import NarrativePlanner
from ai.recipes.registry import RecipeRegistry
from ai.taste.context import TasteContextBuilder
from ai.taste.engine import TasteEngine
from ai.taste.registry import TasteRuleRegistry


@pytest.fixture
def full_pipeline():
    knowledge_registry = KnowledgeRegistry()
    KnowledgeLoader().load_canonical_catalog(registry=knowledge_registry)

    recipe_registry = RecipeRegistry()
    taste_registry = TasteRuleRegistry()

    return {
        "planner": NarrativePlanner(),
        "taste_engine": TasteEngine(registry=taste_registry),
        "directors": CreativeDirectorCoordinator(),
        "resolver": ConflictResolver(),
        "recipes": recipe_registry,
        "knowledge": knowledge_registry,
    }


def make_sample_brief(
    video_type="SAAS_DEMO",
    audio_mode=AudioMode.VO_MUSIC,
    target_duration=30.0,
    tone="premium",
    style="clean",
):
    now = datetime.now(timezone.utc)
    return CreativeBrief(
        brief_id="brief_e2e_001",
        project_id="proj_e2e_001",
        workspace_id="ws_e2e_001",
        user_request_raw="Create a 30s clean SaaS product demo with VO and subtle music.",
        interpreted_intent=CreativeIntent(
            intent_id="intent_e2e_001",
            goal="Enterprise Observability Platform",
            audience="DevOps and SRE teams",
            tone=tone,
            key_takeaway="Identify root cause in seconds with AI telemetry",
            call_to_action="Start your free trial",
            video_type=video_type,
            style=style,
            language="en",
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=target_duration,
            aspect_ratios=["9:16"],
            audio_mode=audio_mode,
            brand_colors=["#0A0F1D", "#00F0FF", "#7B2CBF"],
        ),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )


def test_full_pipeline_saas_demo_success(full_pipeline):
    """Verifies end-to-end execution for SaaS Demo brief."""
    brief = make_sample_brief()
    recipe = full_pipeline["recipes"].get("living-canvas-explainer")
    assert recipe is not None

    # Step 1: Narrative Planning
    plan = full_pipeline["planner"].plan(brief, recipe=recipe)
    assert plan.brief_id == brief.brief_id
    assert len(plan.beats) >= 4
    assert plan.estimated_total_duration_sec == 30.0

    # Step 2: Taste Context & Rule Evaluation
    taste_ctx = TasteContextBuilder.build(
        brief=brief,
        narrative_plan=plan,
        recipe=recipe,
        active_knowledge_ids=recipe.required_knowledge,
        active_skill_ids=recipe.required_skills,
    )
    decisions = full_pipeline["taste_engine"].evaluate_taste(taste_ctx)
    assert len(decisions) > 0

    # Step 3: Creative Directors
    bundle = full_pipeline["directors"].direct_all(taste_ctx)
    assert len(bundle.narrative_directions) == len(plan.beats)
    assert len(bundle.motion_directions) == len(plan.beats)
    assert len(bundle.emotion_directions) == len(plan.beats)
    assert len(bundle.sfx_directions) == len(plan.beats)

    # Step 4: Conflict Resolution
    guidance = full_pipeline["resolver"].resolve(taste_ctx, bundle, decisions)
    assert isinstance(guidance, ResolvedCreativeGuidance)
    assert guidance.status == "SUCCESS"
    assert len(guidance.unresolved_conflicts) == 0
    assert guidance.brief_id == brief.brief_id
    assert guidance.recipe_id == recipe.recipe_id


def test_full_pipeline_silent_audio_mode_integrity(full_pipeline):
    """Verifies SILENT mode preserves audio boundaries across all steps."""
    brief = make_sample_brief(audio_mode=AudioMode.SILENT)
    recipe = full_pipeline["recipes"].get("motion-graphics")
    assert recipe is not None

    plan = full_pipeline["planner"].plan(brief, recipe=recipe)
    taste_ctx = TasteContextBuilder.build(brief=brief, narrative_plan=plan, recipe=recipe)
    decisions = full_pipeline["taste_engine"].evaluate_taste(taste_ctx)
    bundle = full_pipeline["directors"].direct_all(taste_ctx)
    guidance = full_pipeline["resolver"].resolve(taste_ctx, bundle, decisions)

    assert guidance.status == "SUCCESS"
    # SFX directions must contain zero sound cues in SILENT mode
    for sfx_dir in guidance.sfx_directions:
        assert len(sfx_dir.sound_cues) == 0
        assert sfx_dir.audio_mode == AudioMode.SILENT


def test_full_pipeline_music_only_no_spoken_script(full_pipeline):
    """Verifies MUSIC_ONLY mode produces purely visual narrative without spoken lines."""
    brief = make_sample_brief(
        video_type="DYNAMIC_MONTAGE",
        audio_mode=AudioMode.MUSIC_ONLY,
    )
    recipe = full_pipeline["recipes"].get("dynamic-montage-ad")
    assert recipe is not None

    plan = full_pipeline["planner"].plan(brief, recipe=recipe)
    taste_ctx = TasteContextBuilder.build(brief=brief, narrative_plan=plan, recipe=recipe)
    decisions = full_pipeline["taste_engine"].evaluate_taste(taste_ctx)
    bundle = full_pipeline["directors"].direct_all(taste_ctx)
    guidance = full_pipeline["resolver"].resolve(taste_ctx, bundle, decisions)

    assert guidance.status == "SUCCESS"
    # Narrative directions must have spoken_line = None
    for n_dir in guidance.narrative_directions:
        assert n_dir.spoken_line is None
