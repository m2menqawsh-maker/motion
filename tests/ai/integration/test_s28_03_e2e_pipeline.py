"""
tests/ai/integration/test_s28_03_e2e_pipeline.py
================================================
End-to-End Pipeline Integration Test for S28-03:
Tests the entire path:
User Request + Constraints + MediaIntelligence
  -> Intent Understanding
  -> typed CreativeBrief with Provenance
  -> Audio Mode Policy Validation
  -> Recipe Hard Eligibility
  -> Recipe Ranking / Deterministic Selection
  -> S28-02 Knowledge and Skill Resolution
"""

from datetime import datetime, timezone
import pytest

from ai.audio.modes import AudioMode, AudioModeEngine
from ai.contracts.creative.brief import CreativeBrief, ProvenanceType
from ai.contracts.creative.recipe import RecipeSelection
from ai.contracts.media import MediaIntelligence, SpeechIntelligence, VisualIntelligence, AnalysisProvenance
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.recipes.registry import RecipeRegistry
from ai.recipes.selector import RecipeSelector


@pytest.fixture
def brief_builder() -> CreativeBriefBuilder:
    return CreativeBriefBuilder()


@pytest.fixture
def audio_engine() -> AudioModeEngine:
    return AudioModeEngine()


@pytest.fixture
def recipe_registry() -> RecipeRegistry:
    return RecipeRegistry()


@pytest.fixture
def recipe_selector(recipe_registry: RecipeRegistry, audio_engine: AudioModeEngine) -> RecipeSelector:
    return RecipeSelector(registry=recipe_registry, audio_engine=audio_engine)


def test_e2e_pipeline_saas_reels_music_only(
    brief_builder: CreativeBriefBuilder,
    recipe_selector: RecipeSelector,
    audio_engine: AudioModeEngine,
):
    """
    E2E Test 1: Fast SaaS Reel with Music Only.
    Verifies full lifecycle from user prompt to resolved skills and knowledge.
    """
    user_prompt = "بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى وستايل clean."
    workspace_constraints = {
        "target_platforms": ["instagram_reels"],
        "brand_color": "#0066FF",
    }

    # 1. Intent Understanding -> typed CreativeBrief
    brief: CreativeBrief = brief_builder.build_brief(
        user_request=user_prompt,
        workspace_constraints=workspace_constraints,
    )

    assert brief.interpreted_intent.video_type == "SAAS_DEMO"
    assert brief.constraints.audio_mode == AudioMode.MUSIC_ONLY
    assert brief.interpreted_intent.pace == "FAST"
    assert brief.interpreted_intent.style == "CLEAN"
    assert brief.field_provenance["audio_mode"].source_type == ProvenanceType.EXPLICIT
    assert brief.field_provenance["video_type"].source_type == ProvenanceType.EXPLICIT

    # 2. Audio Mode Policy verification
    policy = audio_engine.get_policy(brief.constraints.audio_mode)
    assert policy.speech_policy.value == "FORBIDDEN"
    assert "TEXT_TO_SPEECH" in [c.value for c in policy.forbidden_capabilities]

    # 3. Recipe Selection (Eligibility + Ranking + S28-02 Resolution)
    selection: RecipeSelection = recipe_selector.select_recipe(brief=brief)

    assert selection.selected_recipe_id in ("dynamic-montage-ad", "faceless-broll-ad", "motion-collage-explainer")
    assert selection.confidence_score >= 0.50
    assert len(selection.selection_reasons) > 0

    # 4. S28-02 Integration verification: skills and knowledge bounded and populated
    # Selected recipe must have resolved skills and knowledge without dumping entire registries
    assert selection.required_skills == ["skill_dynamic_montage", "skill_motion_typography"]
    assert selection.required_knowledge == ["know_taste_sfx_matrix", "know_eng_audio_sync"]



def test_e2e_pipeline_talking_head_with_media_intelligence(
    brief_builder: CreativeBriefBuilder,
    recipe_selector: RecipeSelector,
):
    """
    E2E Test 2: Interview Talking Head with MediaIntelligence probe.
    Verifies that real speech asset satisfies the talking head prerequisite.
    """
    user_prompt = "ريلز لحديث الكاميرا مع مؤسس الشركة مع الحفاظ على الصوت المسجل الأصلي"
    now_iso = datetime.now(timezone.utc).isoformat()

    media_intel = MediaIntelligence(
        workspace_id="ws_launch",
        asset_id="asset_interview_01",
        content_hash="hash_speech_probe_123",
        created_at=now_iso,
        speech=SpeechIntelligence(
            transcript="We are thrilled to announce our brand new release today.",
            language="en",
            provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
        ),
        visual=VisualIntelligence(
            has_visual_analysis=True,
            provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
        ),
        provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
    )

    # 1. Intent Understanding
    brief = brief_builder.build_brief(
        user_request=user_prompt,
        media_intelligence=media_intel,
        workspace_constraints={"target_platforms": ["instagram_reels"]},
    )
    assert brief.interpreted_intent.video_type == "TALKING_HEAD"
    assert brief.constraints.audio_mode in (AudioMode.SOURCE_AUDIO, AudioMode.SOURCE_AUDIO_MUSIC)

    # 2. Recipe Selection
    selection = recipe_selector.select_recipe(
        brief=brief,
        available_media=["interview_recording.mp4"],
        media_intelligence=media_intel,
    )
    assert selection.selected_recipe_id in ("captioned-talking-head", "longform-repurpose")
    assert len(selection.selection_reasons) > 0
    assert selection.required_skills == ["skill_motion_typography"]
