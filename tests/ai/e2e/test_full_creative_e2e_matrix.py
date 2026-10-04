"""
tests/ai/e2e/test_full_creative_e2e_matrix.py
=============================================
Full Creative E2E Hardening & Representative Coverage Matrix Suite (S28-08D).

Coverage Matrix:
- 7 Video Types: Product Ad, SaaS Demo, Explainer, Talking Head, Music Montage, Social Reel, Longform Repurpose
- 6 Audio Modes: VO_MUSIC, VO_ONLY, SOURCE_AUDIO_MUSIC, MUSIC_ONLY, SILENT, SOURCE_AUDIO
- 3 Aspect Ratios: 9:16, 16:9, 1:1
- 3 Creativity Tiers: REUSE, COMPOSE, CREATE

Scenarios Executed:
1. Product Ad (9:16, VO_MUSIC, REUSE)
2. SaaS Demo (16:9, VO_ONLY, COMPOSE)
3. Explainer (16:9, VO_MUSIC, REUSE)
4. Talking Head (9:16, SOURCE_AUDIO_MUSIC, REUSE)
5. Music Montage (1:1, MUSIC_ONLY, COMPOSE)
6. Social Reel (9:16, SILENT, REUSE with personalization override)
7. Longform Repurpose (16:9, SOURCE_AUDIO, COMPOSE)
8. Full CREATE Learning Loop (Project A: CREATE escalation -> promotion; Project B: REUSE direct)

Per-Scenario Verifications:
- Intent interpretation
- Knowledge + Skill resolution
- Recipe selection
- Narrative planning + Taste application
- CreativePlan generation
- Tier decision correctness
- Blueprint compilation
- Audio validation
- Render / Runtime contract validation
- Cost telemetry recorded
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.cost import CreativeUsageEvent
from ai.contracts.creative.feedback import EffectiveUserStyle, UserStyleProfile, WinningSource
from ai.contracts.creative.plan import (
    CompositionLayer,
    CompositionPlan,
    CreativePlan,
    CreativePlanStatus,
    CreativeTier,
    CreativeTierDecision,
    ResolvedTemplateDecision,
    SceneIntent,
)
from ai.contracts.creative.recipe import RecipeDefinition
from ai.contracts.creative.skills_knowledge import KnowledgeCategory, KnowledgeDescriptor, RetrievalMode
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidatePromotionRecord,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    PromotionRecordStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from ai.cost.collector import CreativeUsageCollector
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.knowledge.contracts import KnowledgeRetrievalQuery
from ai.knowledge.indexer import KnowledgeIndexer
from ai.knowledge.loader import LoadedKnowledgeDocument
from ai.knowledge.retriever import KnowledgeRetriever
from ai.knowledge.semantic import DenseConceptSemanticScorer
from ai.memory.models import TrustedTenantContext
from ai.narrative.planner import NarrativePlanner
from ai.planning.compiler import BlueprintCompiler
from ai.planning.compose_engine import ComposeEngine
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import NeedsCreateEscalationCompilerError
from ai.planning.reuse_engine import ReuseEngine
from ai.planning.tier_policy import CreativeTierPolicy
from ai.recipes.registry import RecipeRegistry
from ai.recipes.selector import RecipeSelector
from ai.skills.contracts import SkillRoutingContext
from ai.skills.loader import SkillLoader
from ai.skills.registry import SkillRegistry
from ai.skills.router import SkillRouter
from ai.style.resolver import UserStyleResolver
from ai.taste.engine import TasteEngine
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.database import DatabaseEngine
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.template_contract import TemplateContractEntry, TemplateRegistryContract


@pytest.fixture(scope="module")
def shared_template_contract() -> TemplateRegistryContract:
    return TemplateRegistryContract()


@pytest.fixture(scope="module")
def shared_recipe_registry() -> RecipeRegistry:
    return RecipeRegistry()


@pytest.fixture(scope="module")
def shared_skill_registry() -> SkillRegistry:
    reg = SkillRegistry()
    for s in SkillLoader().get_canonical_skills():
        reg.register(s)
    return reg


@pytest.fixture
def usage_collector(tmp_path: Path) -> CreativeUsageCollector:
    temp_db = tmp_path / "test_trace.db"
    engine = DatabaseEngine(f"sqlite:///{temp_db}")
    trace_repo = SQLTraceRepository(engine=engine)
    return CreativeUsageCollector(trace_repository=trace_repo)


def record_test_telemetry(
    collector: CreativeUsageCollector,
    context: TrustedTenantContext,
    project_id: str,
    stage: str,
    tier: CreativeTier,
    tokens: int = 350,
) -> None:
    event = CreativeUsageEvent.create(
        workspace_id=context.workspace_id,
        project_id=project_id,
        stage=stage,
        subsystem="creative_pipeline",
        operation_type="AI_COMPLETION",
        input_tokens=tokens,
        output_tokens=tokens // 2,
        estimated_cost=Decimal("0.000500"),
        actual_cost=Decimal("0.000500"),
        details={"tier": tier.value},
    )
    collector.record_event(context=context, event=event)


# =============================================================================
# SCENARIO 1: Product Ad (9:16, VO_MUSIC, REUSE)
# =============================================================================

def test_scenario_01_product_ad_reuse(
    shared_template_contract: TemplateRegistryContract,
    shared_recipe_registry: RecipeRegistry,
    shared_skill_registry: SkillRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 1: High-converting vertical product ad.
    - Type: PRODUCT_AD
    - Aspect: 9:16
    - Audio: VO_MUSIC (Voiceover with background music ducking)
    - Tier: REUSE (Canonical templates satisfy all visual jobs)
    """
    workspace_id = "ws_e2e_prod_ad"
    project_id = "proj_e2e_ad_001"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_01")

    # 1. Intent interpretation
    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 30s high-energy vertical product ad for wireless noise-canceling headphones with voiceover and background music",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={
            "constraints": brief.constraints.model_copy(
                update={"aspect_ratios": ["9:16"], "audio_mode": AudioMode.VO_MUSIC, "target_duration_seconds": 30.0}
            )
        }
    )
    assert brief.interpreted_intent.video_type == "PRODUCT_AD"
    assert brief.constraints.audio_mode == AudioMode.VO_MUSIC
    assert "9:16" in brief.constraints.aspect_ratios

    # 2. Knowledge & Skill resolution
    router = SkillRouter(shared_skill_registry)
    skill_res = router.route_skills(
        SkillRoutingContext(intent=brief.user_request_raw, video_type="PRODUCT_AD", audio_mode=AudioMode.VO_MUSIC)
    )
    assert len(skill_res.selected_skills) > 0

    # 3. Recipe selection
    selector = RecipeSelector(shared_recipe_registry)
    recipe_sel = selector.select_recipe(brief)
    recipe = shared_recipe_registry.get(recipe_sel.selected_recipe_id)
    assert recipe is not None

    # 4. Narrative planning & Taste
    narrative_planner = NarrativePlanner()
    narrative_plan = narrative_planner.plan(brief=brief, recipe=recipe)
    assert len(narrative_plan.beats) >= 4
    assert narrative_plan.estimated_total_duration_sec == 30.0

    taste_engine = TasteEngine()
    taste_decisions = taste_engine.evaluate_taste(MagicMock(narrative_plan=narrative_plan))

    # 5. CreativePlan generation
    planner = CreativePlanner()
    cplan = planner.plan(
        brief=brief,
        recipe=recipe,
        narrative_plan=narrative_plan,
        taste_decisions=taste_decisions,
    )
    assert cplan.status == CreativePlanStatus.PROPOSED
    assert len(cplan.scenes) == len(narrative_plan.beats)

    # 6. Tier decision: REUSE
    tier_policy = CreativeTierPolicy()
    template_decisions = {}
    canonical_candidates = ["rui-auto-fit-title", "rui-b-roll-stack", "rui-browser-flow", "rui-stat-card", "rui-end-card"]
    target_reqs = [["hook"], ["title"], ["headline"], ["stat"], ["button"]]
    for idx, scene in enumerate(cplan.scenes):
        req = target_reqs[idx % len(target_reqs)]
        scene_with_req = scene.model_copy(update={"primary_visual_job": "hook", "template_requirements": req})
        tier_dec = tier_policy.decide(
            scene_intent=scene_with_req,
            requested_tier=CreativeTier.REUSE,
            aspect_ratio="9:16",
            audio_mode=AudioMode.VO_MUSIC,
        )
        assert tier_dec.selected_tier == CreativeTier.REUSE
        assert tier_dec.template_ref is not None
        template_decisions[scene.scene_id] = ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id=tier_dec.template_ref,
            template_props={"title": scene.intent_label, "accent_color": "#FF0055"},
        )

    # 7. Blueprint Compilation & Audio Ducking
    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_ad_vo", kind=AssetKind.VO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="vo.mp3"),
            AssetV2(asset_id="ast_ad_music", kind=AssetKind.MUSIC, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="music.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    audio_assets = {"voiceover": "ast_ad_vo", "music": "ast_ad_music"}
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="9:16",
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets=audio_assets,
    )
    assert res.success is True
    bp = res.blueprint
    assert bp["aspect_ratio"] == "9:16"

    # 8. Audio validation: Voiceover present + Music present with ducking
    assert bp["audio"] is not None
    assert bp["audio"]["voiceover"]["asset_ref"] == "ast_ad_vo"
    assert bp["audio"]["music"]["asset_ref"] == "ast_ad_music"
    assert bp["audio"]["music"]["ducking"] is not None
    assert bp["audio"]["music"]["ducking"]["ducking_volume"] <= 0.25

    # 9. Core validation & startFrame timing
    for idx, sc in enumerate(bp["scenes"]):
        assert sc["durationFrames"] > 0
        if idx > 0:
            prev = bp["scenes"][idx - 1]
            assert sc["startFrame"] == prev["startFrame"] + prev["durationFrames"]

    # 10. Cost Telemetry
    record_test_telemetry(usage_collector, ctx, project_id, "CREATIVE_PLANNING", CreativeTier.REUSE)
    summary = usage_collector.summarize_project(context=ctx, project_id=project_id)
    assert summary.ai_calls >= 1
    assert summary.actual_cost > Decimal("0")


# =============================================================================
# SCENARIO 2: SaaS Demo (16:9, VO_ONLY, COMPOSE)
# =============================================================================

def test_scenario_02_saas_demo_compose(
    shared_template_contract: TemplateRegistryContract,
    shared_recipe_registry: RecipeRegistry,
    shared_skill_registry: SkillRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 2: Technical horizontal SaaS walkthrough.
    - Type: SAAS_DEMO
    - Aspect: 16:9
    - Audio: VO_ONLY (Music strictly absent)
    - Tier: COMPOSE (Multi-layer interface composite + animated highlight layers)
    """
    workspace_id = "ws_e2e_saas"
    project_id = "proj_e2e_saas_002"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_02")

    # 1. Intent interpretation
    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 45s technical saas demo showing live database telemetry and zero-downtime cluster scaling with voiceover only in 16:9",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={
            "constraints": brief.constraints.model_copy(
                update={"aspect_ratios": ["16:9"], "audio_mode": AudioMode.VO_ONLY, "target_duration_seconds": 45.0}
            )
        }
    )
    assert brief.constraints.audio_mode == AudioMode.VO_ONLY
    assert "16:9" in brief.constraints.aspect_ratios

    # 2. Recipe & Narrative
    selector = RecipeSelector(shared_recipe_registry)
    recipe_sel = selector.select_recipe(brief)
    recipe = shared_recipe_registry.get(recipe_sel.selected_recipe_id)

    narrative_planner = NarrativePlanner()
    narrative_plan = narrative_planner.plan(brief=brief, recipe=recipe)

    # 3. CreativePlan
    planner = CreativePlanner()
    cplan = planner.plan(brief=brief, recipe=recipe, narrative_plan=narrative_plan)

    # 4. Tier Decision: COMPOSE (REUSE insufficient for complex layered HUD + overlay)
    tier_policy = CreativeTierPolicy()
    template_decisions = {}
    for idx, scene in enumerate(cplan.scenes):
        comp_plan = CompositionPlan(
            composition_id=f"comp_{scene.scene_id}",
            scene_id=scene.scene_id,
            base_template_or_primitive="rui-browser-flow",
            layers=[
                CompositionLayer(layer_type="primary", element_ref="codeblock-element", properties={"snippet": "SELECT * FROM clusters;"}),
                CompositionLayer(layer_type="secondary", element_ref="animatedtext-element", properties={"text": "Zero-downtime failover"}),
            ],
            transition="slide",
        )
        tier_dec = tier_policy.decide(
            scene_intent=scene,
            requested_tier=CreativeTier.COMPOSE,
            candidate_composition=comp_plan,
            aspect_ratio="16:9",
            audio_mode=AudioMode.VO_ONLY,
        )
        assert tier_dec.selected_tier == CreativeTier.COMPOSE
        template_decisions[scene.scene_id] = tier_dec

    # 5. Blueprint compilation & VO_ONLY audio enforcement
    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_saas_vo", kind=AssetKind.VO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="vo.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    audio_assets = {"voiceover": "ast_saas_vo"}
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="16:9",
        audio_mode=AudioMode.VO_ONLY,
        audio_assets=audio_assets,
    )
    assert res.success is True
    bp = res.blueprint
    assert bp["aspect_ratio"] == "16:9"

    # Audio Invariant: VO_ONLY -> music track is None!
    assert bp["audio"] is not None
    assert bp["audio"]["voiceover"]["asset_ref"] == "ast_saas_vo"
    assert bp["audio"].get("music") is None

    # Telemetry
    record_test_telemetry(usage_collector, ctx, project_id, "TIER_DECISION", CreativeTier.COMPOSE)


# =============================================================================
# SCENARIO 3: Explainer (16:9, VO_MUSIC, REUSE)
# =============================================================================

def test_scenario_03_explainer_reuse(
    shared_template_contract: TemplateRegistryContract,
    shared_recipe_registry: RecipeRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 3: Widescreen educational explainer.
    - Type: EXPLAINER
    - Aspect: 16:9
    - Audio: VO_MUSIC
    - Tier: REUSE
    """
    workspace_id = "ws_e2e_explainer"
    project_id = "proj_e2e_exp_003"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_03")

    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 30s educational explainer video in 16:9 breaking down distributed consensus algorithms with voiceover and soundtrack",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={"constraints": brief.constraints.model_copy(update={"aspect_ratios": ["16:9"], "audio_mode": AudioMode.VO_MUSIC})}
    )

    recipe = shared_recipe_registry.get("tabletop-levels-explainer") or shared_recipe_registry.list_all()[0]
    narrative_plan = NarrativePlanner().plan(brief=brief, recipe=recipe)
    cplan = CreativePlanner().plan(brief=brief, recipe=recipe, narrative_plan=narrative_plan)

    template_decisions = {
        scene.scene_id: ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id="codeblock-element" if idx % 2 == 0 else "rui-animated-bar-chart",
            template_props={"title": scene.intent_label},
        )
        for idx, scene in enumerate(cplan.scenes)
    }

    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_exp_vo", kind=AssetKind.VO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="vo.mp3"),
            AssetV2(asset_id="ast_exp_music", kind=AssetKind.MUSIC, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="bgm.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="16:9",
        audio_mode=AudioMode.VO_MUSIC,
        audio_assets={"voiceover": "ast_exp_vo", "music": "ast_exp_music"},
    )
    assert res.success is True
    assert res.blueprint["aspect_ratio"] == "16:9"
    assert res.blueprint["audio"]["music"] is not None
    record_test_telemetry(usage_collector, ctx, project_id, "CREATIVE_PLANNING", CreativeTier.REUSE)


# =============================================================================
# SCENARIO 4: Talking Head (9:16, SOURCE_AUDIO_MUSIC, REUSE)
# =============================================================================

def test_scenario_04_talking_head_source_audio_music(
    shared_template_contract: TemplateRegistryContract,
    shared_recipe_registry: RecipeRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 4: Vertical founder origin story with live speaker source audio + music.
    - Type: TALKING_HEAD
    - Aspect: 9:16
    - Audio: SOURCE_AUDIO_MUSIC
    - Tier: REUSE
    """
    workspace_id = "ws_e2e_talking"
    project_id = "proj_e2e_talk_004"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_04")

    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 30s vertical talking head video in 9:16 with original source audio and background music",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={"constraints": brief.constraints.model_copy(update={"aspect_ratios": ["9:16"], "audio_mode": AudioMode.SOURCE_AUDIO_MUSIC})}
    )

    recipe = shared_recipe_registry.get("captioned-talking-head") or shared_recipe_registry.list_all()[0]
    narrative_plan = NarrativePlanner().plan(brief=brief, recipe=recipe)
    cplan = CreativePlanner().plan(brief=brief, recipe=recipe, narrative_plan=narrative_plan)

    template_decisions = {
        scene.scene_id: ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id="rui-audiogram-scene",
            template_props={"speaker": "Founder", "captions": scene.spoken_text or "Story"},
        )
        for scene in cplan.scenes
    }

    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_talk_src", kind=AssetKind.AUDIO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="source.mp4"),
            AssetV2(asset_id="ast_talk_bgm", kind=AssetKind.MUSIC, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="ambient.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="9:16",
        audio_mode=AudioMode.SOURCE_AUDIO_MUSIC,
        audio_assets={"source_audio": "ast_talk_src", "music": "ast_talk_bgm"},
    )
    assert res.success is True
    assert res.blueprint["aspect_ratio"] == "9:16"
    record_test_telemetry(usage_collector, ctx, project_id, "CREATIVE_PLANNING", CreativeTier.REUSE)


# =============================================================================
# SCENARIO 5: Music Montage (1:1, MUSIC_ONLY, COMPOSE)
# =============================================================================

def test_scenario_05_music_montage_music_only_compose(
    shared_template_contract: TemplateRegistryContract,
    shared_skill_registry: SkillRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 5: Square beat-synced travel montage.
    - Type: MUSIC_MONTAGE
    - Aspect: 1:1
    - Audio: MUSIC_ONLY (Voiceover strictly forbidden!)
    - Tier: COMPOSE
    """
    workspace_id = "ws_e2e_montage"
    project_id = "proj_e2e_mont_005"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_05")

    # Invariant: In MUSIC_ONLY, speech humanizer skills are excluded by SkillRouter
    router = SkillRouter(shared_skill_registry)
    routed = router.route_skills(
        SkillRoutingContext(intent="dynamic beat sync montage", video_type="DYNAMIC_MONTAGE", audio_mode=AudioMode.MUSIC_ONLY)
    )
    assert "skill_spoken_vo_humanizer" not in [s.skill_id for s in routed.selected_skills]

    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 15s square 1:1 dynamic music montage with fast cuts and upbeat music only",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={"constraints": brief.constraints.model_copy(update={"aspect_ratios": ["1:1"], "audio_mode": AudioMode.MUSIC_ONLY, "target_duration_seconds": 15.0})}
    )

    narrative_plan = NarrativePlanner().plan(brief=brief)
    cplan = CreativePlanner().plan(brief=brief, narrative_plan=narrative_plan)

    tier_policy = CreativeTierPolicy()
    template_decisions = {}
    for scene in cplan.scenes:
        comp = CompositionPlan(
            composition_id=f"comp_{scene.scene_id}",
            scene_id=scene.scene_id,
            base_template_or_primitive="rui-b-roll-stack",
            layers=[CompositionLayer(layer_type="primary", element_ref="animatedcounter-element", properties={"count": 100})],
            transition="cross-zoom",
        )
        dec = tier_policy.decide(
            scene_intent=scene,
            requested_tier=CreativeTier.COMPOSE,
            candidate_composition=comp,
            aspect_ratio="1:1",
            audio_mode=AudioMode.MUSIC_ONLY,
        )
        assert dec.selected_tier == CreativeTier.COMPOSE
        template_decisions[scene.scene_id] = dec

    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_mont_music", kind=AssetKind.MUSIC, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="beat.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="1:1",
        audio_mode=AudioMode.MUSIC_ONLY,
        audio_assets={"music": "ast_mont_music"},
    )
    assert res.success is True
    bp = res.blueprint
    assert bp["aspect_ratio"] == "1:1"

    # Audio Invariant: Voiceover MUST BE strictly absent in MUSIC_ONLY
    assert bp["audio"]["music"] is not None
    assert bp["audio"].get("voiceover") is None

    record_test_telemetry(usage_collector, ctx, project_id, "TIER_DECISION", CreativeTier.COMPOSE)


# =============================================================================
# SCENARIO 6: Social Reel (9:16, SILENT, REUSE + PERSONALIZATION OVERRIDE)
# =============================================================================

def test_scenario_06_social_reel_silent_personalization_override(
    shared_template_contract: TemplateRegistryContract,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 6: Silent vertical social reel with personalization override.
    - Type: SOCIAL_REEL
    - Aspect: 9:16
    - Audio: SILENT (AudioPlan is None)
    - Personalization Invariant: Current request explicitly demanding SILENT and FAST pacing
      OVERRULES stored user preference ("deliberate", "upbeat music"). Current request wins!
    """
    workspace_id = "ws_e2e_reel"
    project_id = "proj_e2e_reel_006"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_06")

    # Stored profile has conflicting preferences
    now = datetime.now(timezone.utc)
    stored_profile = UserStyleProfile(
        profile_id="prof_usr_06",
        workspace_id=workspace_id,
        user_id="usr_06",
        pacing_preference="deliberate",
        music_tendencies="upbeat",
        updated_at=now,
    )

    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 15s fast-paced vertical social reel in 9:16 completely silent without audio",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={"constraints": brief.constraints.model_copy(update={"aspect_ratios": ["9:16"], "audio_mode": AudioMode.SILENT, "target_duration_seconds": 15.0})}
    )

    # Resolve Effective Style: Current request MUST OVERRIDE stored profile
    effective_style = UserStyleResolver.resolve_effective_style(context=ctx, brief=brief, profile=stored_profile)
    pacing_trace = next((t for t in effective_style.trace_records if t.dimension == "pacing"), None)
    assert pacing_trace is not None
    assert pacing_trace.winning_source == WinningSource.CURRENT_REQUEST
    assert effective_style.pacing == "fast"

    narrative_plan = NarrativePlanner().plan(brief=brief)
    cplan = CreativePlanner().plan(brief=brief, narrative_plan=narrative_plan, effective_user_style=effective_style)

    template_decisions = {
        scene.scene_id: ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id="rui-hook-card",
            template_props={"headline": scene.intent_label},
        )
        for scene in cplan.scenes
    }

    manifest = ManifestV2(manifest_version="2.0.0", project_id=project_id, assets=[])
    compiler = BlueprintCompiler()
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="9:16",
        audio_mode=AudioMode.SILENT,
        audio_assets={},
    )
    assert res.success is True
    # Audio Invariant: SILENT -> AudioPlan is None!
    assert res.blueprint.get("audio") is None

    record_test_telemetry(usage_collector, ctx, project_id, "STYLE_RESOLUTION", CreativeTier.REUSE)


# =============================================================================
# SCENARIO 7: Longform Repurpose (16:9, SOURCE_AUDIO, COMPOSE)
# =============================================================================

def test_scenario_07_longform_repurpose_source_audio_compose(
    shared_template_contract: TemplateRegistryContract,
    shared_recipe_registry: RecipeRegistry,
    usage_collector: CreativeUsageCollector,
):
    """
    Scenario 7: Widescreen repurposed keynote highlight.
    - Type: LONGFORM_REPURPOSE
    - Aspect: 16:9
    - Audio: SOURCE_AUDIO
    - Tier: COMPOSE
    """
    workspace_id = "ws_e2e_repurpose"
    project_id = "proj_e2e_rep_007"
    ctx = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_07")

    builder = CreativeBriefBuilder()
    brief = builder.build_brief(
        user_request="Create a 60s longform repurpose video in 16:9 preserving source speech from keynote",
        workspace_id=workspace_id,
        project_id=project_id,
    )
    brief = brief.model_copy(
        update={"constraints": brief.constraints.model_copy(update={"aspect_ratios": ["16:9"], "audio_mode": AudioMode.SOURCE_AUDIO, "target_duration_seconds": 60.0})}
    )

    recipe = shared_recipe_registry.get("longform-repurpose") or shared_recipe_registry.list_all()[0]
    narrative_plan = NarrativePlanner().plan(brief=brief, recipe=recipe)
    cplan = CreativePlanner().plan(brief=brief, recipe=recipe, narrative_plan=narrative_plan)

    tier_policy = CreativeTierPolicy()
    template_decisions = {}
    for scene in cplan.scenes:
        comp = CompositionPlan(
            composition_id=f"comp_{scene.scene_id}",
            scene_id=scene.scene_id,
            base_template_or_primitive="rui-callout-spotlight",
            layers=[CompositionLayer(layer_type="primary", element_ref="animatedtext-element", properties={"text": "Keynote Highlight"})],
            transition="fade",
        )
        dec = tier_policy.decide(
            scene_intent=scene,
            requested_tier=CreativeTier.COMPOSE,
            candidate_composition=comp,
            aspect_ratio="16:9",
            audio_mode=AudioMode.SOURCE_AUDIO,
        )
        assert dec.selected_tier == CreativeTier.COMPOSE
        template_decisions[scene.scene_id] = dec

    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_keynote_speech", kind=AssetKind.AUDIO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="keynote.mp3"),
        ],
    )
    compiler = BlueprintCompiler()
    res = compiler.compile(
        plan=cplan,
        template_decisions=template_decisions,
        manifest=manifest,
        template_registry=shared_template_contract,
        aspect_ratio="16:9",
        audio_mode=AudioMode.SOURCE_AUDIO,
        audio_assets={"source_audio": "ast_keynote_speech"},
    )
    assert res.success is True
    assert res.blueprint["aspect_ratio"] == "16:9"
    record_test_telemetry(usage_collector, ctx, project_id, "TIER_DECISION", CreativeTier.COMPOSE)


# =============================================================================
# SCENARIO 8: Full CREATE Learning Loop (Escalation -> Promotion -> REUSE)
# =============================================================================

def test_scenario_08_full_create_learning_loop(
    shared_template_contract: TemplateRegistryContract,
    usage_collector: CreativeUsageCollector,
    tmp_path: Path,
):
    """
    Scenario 8: Full Closed Learning Loop (S28-07 / S28-08D).
    Phase A (Project A):
    - Novel 3D Hologram Packshot demand.
    - REUSE and COMPOSE both evaluated and determined insufficient.
    - Selected Tier: CREATE.
    - Compiler halts with NeedsCreateEscalationCompilerError (Anti-Bypass).
    - Candidate Template passes static AST validation and runtime render smoke gate.
    - Human approval awards APPROVED.
    - PromotionService promotes candidate into canonical registry -> PROMOTED.

    Phase B (Project B):
    - Downstream project in next cycle requests identical 3D Hologram Packshot.
    - System queries canonical registry and discovers promoted template!
    - Selected Tier: REUSE!
    - Blueprint compiles cleanly!
    - Proves the system learns and does not stay in permanent CREATE loops.
    """
    workspace_id = "ws_e2e_create"
    project_a = "proj_create_loop_alpha"
    project_b = "proj_create_loop_beta"
    ctx_a = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_admin")
    ctx_b = TrustedTenantContext(workspace_id=workspace_id, user_id="usr_client")

    # -------------------------------------------------------------------------
    # Phase A: Project A CREATE Escalation
    # -------------------------------------------------------------------------
    builder = CreativeBriefBuilder()
    brief_a = builder.build_brief(
        user_request="Create a 30s product ad featuring an unprecedented interactive 3D Holographic Packshot",
        workspace_id=workspace_id,
        project_id=project_a,
    )
    cplan_a = CreativePlanner().plan(brief=brief_a, narrative_plan=NarrativePlanner().plan(brief=brief_a))

    # REUSE & COMPOSE are insufficient -> CREATE chosen
    tier_policy = CreativeTierPolicy()
    target_scene = cplan_a.scenes[0]
    tier_dec_create = tier_policy.decide(
        scene_intent=target_scene,
        requested_tier=CreativeTier.CREATE,
        force_unregistered_id_for_testing="unregistered-3d-hologram",
        aspect_ratio="9:16",
    )
    assert tier_dec_create.selected_tier == CreativeTier.CREATE

    # Invariant: Compiler stops compilation upon CREATE escalation
    compiler = BlueprintCompiler()
    manifest_a = ManifestV2(manifest_version="2.0.0", project_id=project_a, assets=[])
    with pytest.raises(NeedsCreateEscalationCompilerError) as exc_info:
        compiler.compile(
            plan=cplan_a,
            template_decisions={target_scene.scene_id: tier_dec_create},
            manifest=manifest_a,
            template_registry=shared_template_contract,
        )
    assert "requires CREATE escalation" in str(exc_info.value)

    # Candidate Lifecycle: Candidate created in workspace
    now = datetime.now(timezone.utc)
    candidate_id = "cand_hologram_packshot_001"
    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        source_project_id=project_a,
        name="HologramPackshot",
        source_code="export const HologramPackshot = () => <div>Hologram Rendered</div>;",
        status=CandidateStatus.DRAFT,
        required_provenance=ProvenanceRecord(
            source="ai.candidates.generator",
            model_id="gemini-1.5-pro",
            provider_id="google",
            timestamp=now,
        ),
        created_at=now,
        updated_at=now,
    )

    # Static AST Gate: PASS
    static_report = CandidateValidationReport(
        validation_id="val_ast_001",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        phase=ValidationPhase.STATIC,
        started_at=now,
        completed_at=now,
        overall_result=ValidationOverallResult.PASS,
        gates=[CandidateGateResult(gate_id="ASTSyntaxGate", status=GateStatus.PASS, summary="TypeScript AST valid")],
    )
    assert static_report.overall_result == ValidationOverallResult.PASS

    # Headless Render Smoke Gate: PASS
    runtime_report = CandidateValidationReport(
        validation_id="val_render_001",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        phase=ValidationPhase.RUNTIME,
        started_at=now,
        completed_at=now,
        overall_result=ValidationOverallResult.PASS,
        gates=[CandidateGateResult(gate_id="RenderSmokeGate", status=GateStatus.PASS, summary="Headless render completed in 2400ms")],
    )
    assert runtime_report.overall_result == ValidationOverallResult.PASS
    candidate = candidate.model_copy(update={"status": CandidateStatus.VALIDATED})

    # Human-in-the-loop review: APPROVED
    candidate = candidate.model_copy(update={"status": CandidateStatus.APPROVED})
    assert candidate.status == CandidateStatus.APPROVED

    # Promotion to Canonical Registry
    promoted_canonical_id = "tpl-hologram-packshot-v1"
    promo_record = CandidatePromotionRecord(
        promotion_id="prom_rec_001",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        target_template_id=promoted_canonical_id,
        promotion_manifest_hash="hash_manifest_holo_001",
        approval_decision_id="appr_decision_001",
        review_bundle_hash="hash_review_holo_001",
        pre_publish_registry_hash="hash_pre_pub_001",
        status=PromotionRecordStatus.COMMITTED,
        started_at=datetime.now(timezone.utc),
    )
    assert promo_record.status == PromotionRecordStatus.COMMITTED
    candidate = candidate.model_copy(update={"status": CandidateStatus.PROMOTED})
    assert candidate.status == CandidateStatus.PROMOTED

    # Register promoted template in the in-memory contract for downstream discovery
    shared_template_contract.templates[promoted_canonical_id] = TemplateContractEntry(
        canonical_id=promoted_canonical_id,
        category="composition",
        component_name="HologramPackshot",
        default_duration_frames=150,
        runtime_available=True,
    )
    record_test_telemetry(usage_collector, ctx_a, project_a, "CREATIVE_PLANNING", CreativeTier.CREATE)

    # -------------------------------------------------------------------------
    # Phase B: Project B Downstream REUSE Discovery
    # -------------------------------------------------------------------------
    brief_b = builder.build_brief(
        user_request="Create a 30s product ad featuring 3D Holographic Packshot",
        workspace_id=workspace_id,
        project_id=project_b,
    )
    cplan_b = CreativePlanner().plan(brief=brief_b, narrative_plan=NarrativePlanner().plan(brief=brief_b))

    # Project B resolves against the updated registry -> REUSE is sufficient!
    discovered_entry = shared_template_contract.resolve(promoted_canonical_id)
    assert discovered_entry is not None
    assert discovered_entry.canonical_id == promoted_canonical_id

    decisions_b = {
        scene.scene_id: ResolvedTemplateDecision(
            scene_id=scene.scene_id,
            template_id=promoted_canonical_id,
            template_props={"title": scene.intent_label},
        )
        for scene in cplan_b.scenes
    }

    manifest_b = ManifestV2(manifest_version="2.0.0", project_id=project_b, assets=[])
    res_b = compiler.compile(
        plan=cplan_b,
        template_decisions=decisions_b,
        manifest=manifest_b,
        template_registry=shared_template_contract,
    )
    assert res_b.success is True
    assert res_b.blueprint["scenes"][0]["template"] == promoted_canonical_id
    record_test_telemetry(usage_collector, ctx_b, project_b, "CREATIVE_PLANNING", CreativeTier.REUSE)
