"""
tests/ai/recipes/test_recipe_selector.py
========================================
Unit and Negative Invariant tests for S28-03 RecipeSelector:
- Deterministic Stage 1 eligibility gating (disqualifying incompatible audio modes or platforms).
- Talking head prerequisite enforcement (Section 34).
- Weighted candidate scoring and deterministic tie-breaking.
- Error handling when no recipes match brief constraints.
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.recipe import RecipeSelection
from ai.contracts.media import MediaIntelligence, SpeechIntelligence, AnalysisProvenance
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.recipes.contracts import NoEligibleRecipeError
from ai.recipes.selector import RecipeSelector


@pytest.fixture
def selector() -> RecipeSelector:
    return RecipeSelector()


@pytest.fixture
def builder() -> CreativeBriefBuilder:
    return CreativeBriefBuilder()


def test_selector_picks_dynamic_montage_for_music_only(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """Verifies that for an explicit music-only reel, an eligible montage recipe is selected."""
    brief = builder.build_brief(
        user_request="بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى",
        workspace_constraints={"target_platforms": ["instagram_reels"]},
    )

    selection: RecipeSelection = selector.select_recipe(brief=brief)
    assert selection.selected_recipe_id in ("dynamic-montage-ad", "faceless-broll-ad", "motion-collage-explainer")
    assert selection.confidence_score > 0.50
    assert len(selection.selection_reasons) > 0


def test_selector_disqualifies_talking_head_without_speech(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """
    Section 34 enforcement:
    If captioned-talking-head is considered, but audio_mode is MUSIC_ONLY or SILENT,
    or no speech audio is in media assets, it must be disqualified in Stage 1.
    """
    brief = builder.build_brief(
        user_request="حديث الكاميرا متحدث ولكن بدون أي صوت نهائيا صامت",
        workspace_constraints={"target_platforms": ["instagram_reels"]},
    )

    # captioned-talking-head must NOT be selected under SILENT
    try:
        selection = selector.select_recipe(brief=brief)
        assert selection.selected_recipe_id != "captioned-talking-head"
    except NoEligibleRecipeError:
        # Expected if all reels recipes are disqualified under SILENT
        pass


def test_selector_selects_talking_head_when_speech_provided(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """Verifies captioned-talking-head is selected when SOURCE_AUDIO is requested and speech is detected."""
    now_iso = datetime.now(timezone.utc).isoformat()
    brief = builder.build_brief(
        user_request="ريلز لحديث الكاميرا مع مؤسس الشركة مع الصوت الأصلي",
        workspace_constraints={"target_platforms": ["instagram_reels"]},
    )

    media_intel = MediaIntelligence(
        workspace_id="ws_01",
        asset_id="asset_founder_01",
        content_hash="hash_speech_founder",
        created_at=now_iso,
        speech=SpeechIntelligence(
            transcript="Welcome to our launch event.",
            language="en",
            provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
        ),
        provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
    )

    selection = selector.select_recipe(
        brief=brief,
        available_media=["founder_video.mp4"],
        media_intelligence=media_intel,
    )

    assert selection.selected_recipe_id in ("captioned-talking-head", "longform-repurpose")


def test_selector_raises_when_no_recipe_eligible(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """Verifies NoEligibleRecipeError is raised when brief constraints eliminate all recipes."""
    brief = builder.build_brief(
        user_request="Silent video without any sound",
        workspace_constraints={
            "target_platforms": ["non_existent_platform_999"],
            "excluded_templates": [r.recipe_id for r in selector.registry.list_all()],
        },
    )

    with pytest.raises(NoEligibleRecipeError):
        selector.select_recipe(brief=brief)


def test_selector_deterministic_tie_breaking(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """Verifies that running selection multiple times on the same input produces identical primary selection."""
    brief = builder.build_brief(
        user_request="فيديو توضيحي",
        workspace_constraints={"target_platforms": ["youtube"]},
    )

    sel1 = selector.select_recipe(brief=brief)
    sel2 = selector.select_recipe(brief=brief)
    assert sel1.selected_recipe_id == sel2.selected_recipe_id
    assert sel1.confidence_score == sel2.confidence_score
