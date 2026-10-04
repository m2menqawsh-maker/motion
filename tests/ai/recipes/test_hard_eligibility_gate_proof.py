"""
tests/ai/recipes/test_hard_eligibility_gate_proof.py
====================================================
Hard Eligibility Gate Proof for S28-03A:
Proves deterministically that:
1. Stage 1 Hard Eligibility gating executes strictly BEFORE candidate scoring/ranking.
2. Ineligible recipes CANNOT be resurrected by keyword matching, ranking, or AI reasoning.
3. Incompatible AudioMode combinations (e.g. MUSIC_ONLY + TTS) are eliminated before ranking.
4. Unsupported platforms (e.g. horizontal YouTube vs vertical Reels) are eliminated before ranking.
5. Missing required media assets (Section 34) disqualify recipes deterministically.
"""

import pytest

from ai.audio.modes import AudioMode
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


def test_ineligible_recipe_with_top_keyword_relevance_excluded_before_ranking(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """
    Proof 1:
    Even when an ineligible recipe has 100% keyword match ('avatar', 'explainer', 'avatar explainer'),
    if the brief specifies MUSIC_ONLY, Stage 1 hard eligibility eliminates it BEFORE ranking.
    It cannot appear as primary recipe or as an alternative.
    """
    user_prompt = "أريد فيديو أفاتار توضيحي avatar explainer يشرح ميزات المنصة بدون أي صوت متحدث بس موسيقى فقط"
    brief = builder.build_brief(
        user_request=user_prompt,
        workspace_constraints={"target_platforms": ["youtube"]},
    )
    assert brief.constraints.audio_mode == AudioMode.MUSIC_ONLY

    selection: RecipeSelection = selector.select_recipe(brief=brief)

    # Primary selection must NOT be avatar-explainer
    assert selection.selected_recipe_id != "avatar-explainer"
    assert selection.selected_recipe_id != "avatar-product-walkthrough"

    # avatar-explainer must NOT be in alternatives
    assert "avatar-explainer" not in selection.alternative_recipe_ids

    # avatar-explainer must be explicitly recorded in excluded_recipe_ids
    assert "avatar-explainer" in selection.excluded_recipe_ids
    exclusion_reason = selection.excluded_recipe_ids["avatar-explainer"]
    assert (
        "requires capability 'TEXT_TO_SPEECH' which is forbidden" in exclusion_reason
        or "does not support audio mode 'MUSIC_ONLY'" in exclusion_reason
    )


def test_unsupported_platform_recipe_excluded_before_ranking(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """
    Proof 2:
    Even when 'dynamic-montage-ad' matches all keywords ('dynamic', 'montage', 'ad', 'clean'),
    if the brief specifies platform='website' or platform='youtube' (landscape 16:9),
    Stage 1 hard eligibility eliminates it BEFORE ranking.
    """
    user_prompt = "عمل dynamic montage ad سريع ونظيف مع موسيقى حماسية"
    brief = builder.build_brief(
        user_request=user_prompt,
        workspace_constraints={"target_platforms": ["website"]},
    )

    selection: RecipeSelection = selector.select_recipe(brief=brief)

    assert selection.selected_recipe_id != "dynamic-montage-ad"
    assert "dynamic-montage-ad" not in selection.alternative_recipe_ids
    assert "dynamic-montage-ad" in selection.excluded_recipe_ids
    assert "does not support requested platforms" in selection.excluded_recipe_ids["dynamic-montage-ad"]


def test_required_media_unavailable_excluded_before_ranking(
    selector: RecipeSelector,
    builder: CreativeBriefBuilder,
):
    """
    Proof 3:
    Talking head recipes strictly require source speech assets (Section 34).
    When available_media is empty ([]), Stage 1 eliminates captioned-talking-head
    and longform-repurpose before ranking, raising NoEligibleRecipeError.
    """
    user_prompt = "ريلز لحديث الكاميرا مع مؤسس الشركة مع الحفاظ على الصوت المسجل الأصلي"
    brief = builder.build_brief(
        user_request=user_prompt,
        workspace_constraints={"target_platforms": ["instagram_reels"]},
    )
    assert brief.constraints.audio_mode in (AudioMode.SOURCE_AUDIO, AudioMode.SOURCE_AUDIO_MUSIC)

    with pytest.raises(NoEligibleRecipeError) as exc_info:
        selector.select_recipe(brief=brief, available_media=[])

    err_msg = str(exc_info.value)
    assert "captioned-talking-head" in err_msg
    assert "requires source speech media, but no speech detected" in err_msg
