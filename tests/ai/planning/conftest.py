"""
tests/ai/planning/conftest.py
=============================
Shared fixtures and factory helpers for S28-05 Creative Planning and Blueprint Compiler tests.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    ResolvedTemplateDecision,
    SceneIntent,
)
from ai.contracts.creative.recipe import RecipeDefinition, RecipeStage
from ai.contracts.creative.taste import TasteDecision
from ai.narrative.planner import NarrativePlanner
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.template_contract import TemplateRegistryContract


@pytest.fixture
def narrative_planner() -> NarrativePlanner:
    return NarrativePlanner()


@pytest.fixture
def template_registry() -> TemplateRegistryContract:
    return TemplateRegistryContract()


def create_test_brief(
    brief_id: str = "brief_saas_001",
    video_type: str = "SAAS_DEMO",
    audio_mode: AudioMode = AudioMode.VO_MUSIC,
    target_duration: float = 30.0,
    goal: str = "Showcase database performance and zero downtime deployments",
    key_takeaway: str = "Sub-millisecond queries scale effortlessly",
) -> CreativeBrief:
    now = datetime.now(timezone.utc)
    return CreativeBrief(
        brief_id=brief_id,
        project_id="proj_s28_test",
        workspace_id="ws_s28_test",
        user_request_raw=f"Create a {video_type} about {goal}.",
        interpreted_intent=CreativeIntent(
            intent_id="intent_001",
            goal=goal,
            audience="Software Engineers & Tech Leads",
            tone="confident",
            key_takeaway=key_takeaway,
            call_to_action="Start your free cluster today",
            video_type=video_type,
            language="en",
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=target_duration,
            aspect_ratios=["9:16"],
            audio_mode=audio_mode,
        ),
        provenance=ProvenanceRecord(
            source="test_fixture",
            model_id="test_model",
            provider_id="test_provider",
            timestamp=now,
            latency_ms=1,
        ),
        created_at=now,
    )


def create_test_recipe(
    recipe_id: str = "saas-launch-recipe",
    audio_mode: AudioMode = AudioMode.VO_MUSIC,
) -> RecipeDefinition:
    caps = ["TEXT_TO_SPEECH", "SPEECH_ALIGNMENT"] if audio_mode in (AudioMode.VO_MUSIC, AudioMode.VO_ONLY) else []
    return RecipeDefinition(
        recipe_id=recipe_id,
        name="SaaS Launch Recipe",
        version="1.0.0",
        description="Structured SaaS video walkthrough",
        best_for=["SaaS", "DevTools"],
        not_for=["Gaming memes"],
        platforms=["youtube", "linkedin"],
        aspect_ratios=["9:16", "16:9"],
        duration_seconds_min=15.0,
        duration_seconds_max=60.0,
        duration_seconds_target=30.0,
        stages=[
            RecipeStage(
                stage_id="s1",
                title="Narrative Planning",
                actions=["plan_beats"],
                required_capabilities=[],
                artifacts=["narrative_plan.json"],
            )
        ],
        required_skills=["skill_motion_typography"],
        required_capabilities=caps,
        routing_keywords=["saas", "database"],
        routing_negative_keywords=[],
        deliverables=["out.mp4"],
    )


def create_test_manifest(
    project_id: str = "proj_s28_test",
    asset_ids: Optional[List[str]] = None,
) -> ManifestV2:
    default_ids = ["ast_vo_01", "ast_bgm_01", "ast_logo_01", "ast_demo_screen"]
    ids = asset_ids or default_ids

    assets = []
    for aid in ids:
        kind = AssetKind.AUDIO
        if "vo" in aid:
            kind = AssetKind.VO
        elif "bgm" in aid or "music" in aid:
            kind = AssetKind.MUSIC
        elif "logo" in aid:
            kind = AssetKind.LOGO
        elif "demo" in aid or "screen" in aid:
            kind = AssetKind.IMAGE

        assets.append(
            AssetV2(
                asset_id=aid,
                kind=kind,
                provenance=Provenance.USER_UPLOAD,
                status=AssetStatus.READY,
                source_path=f"assets/{aid}.png",
            )
        )

    return ManifestV2(
        manifest_version="2.0.0",
        project_id=project_id,
        assets=assets,
    )
