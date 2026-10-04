"""
tests/ai/recipes/test_recipe_registry.py
========================================
Unit tests for S28-03 RecipeRegistry:
- Verifies all 18 legacy recipes are loaded and migrated into typed RecipeDefinition models.
- Verifies provider neutrality enforcement (assert_provider_neutral).
- Verifies no legacy recipes are deleted from disk.
- Verifies validation errors on missing/malformed recipes.
"""

from pathlib import Path
import pytest

from ai.contracts.creative.recipe import RecipeDefinition
from ai.recipes.contracts import (
    ProviderNeutralityViolationError,
    RecipeNotFoundError,
)
from ai.recipes.registry import RecipeRegistry, assert_provider_neutral


@pytest.fixture
def registry() -> RecipeRegistry:
    return RecipeRegistry()


def test_registry_loads_all_18_legacy_recipes(registry: RecipeRegistry):
    """Verifies that all 18 legacy recipes in recipes/ are successfully loaded and typed."""
    all_recipes = registry.list_all()
    assert len(all_recipes) == 18

    recipe_ids = [r.recipe_id for r in all_recipes]
    assert len(recipe_ids) == 18

    # Check key expected legacy recipes are present
    expected_ids = [
        "agent-browser-proof",
        "avatar-explainer",
        "avatar-hook-broll",
        "avatar-insta-split",
        "avatar-product-walkthrough",
        "avatar-vo-broll",
        "captioned-talking-head",
        "dynamic-montage-ad",
        "faceless-broll-ad",
        "living-canvas-explainer",
        "longform-repurpose",
        "misotts-article-sprint",
        "motion-collage-explainer",
        "motion-graphics",
        "review-conquest-compilation",
        "screencast-demo",
        "tabletop-levels-explainer",
        "ugc-ai-ad",
    ]
    for expected_id in expected_ids:
        assert expected_id in recipe_ids
        recipe = registry.get(expected_id)
        assert isinstance(recipe, RecipeDefinition)
        assert recipe.recipe_id == expected_id
        assert recipe.version != ""
        assert len(recipe.supported_intents) > 0
        assert len(recipe.supported_platforms) > 0
        assert len(recipe.supported_audio_modes) > 0


def test_legacy_files_not_deleted():
    """Verifies that none of the original 18 recipe JSON files were deleted from disk."""
    recipe_dir = Path("recipes")
    assert recipe_dir.is_dir()
    recipe_files = [f for f in recipe_dir.glob("*.json") if f.name != "schema.json"]
    assert len(recipe_files) == 18


def test_provider_neutrality_in_all_registered_recipes(registry: RecipeRegistry):
    """
    Verifies the S28 architectural invariant: Recipe != Provider.
    None of the migrated RecipeDefinition objects may contain provider names in capability/phase keys.
    """
    for recipe in registry.list_all():
        assert_provider_neutral(recipe)


def test_provider_neutrality_guard_detects_violations():
    """Negative test: assert_provider_neutral raises ProviderNeutralityViolationError on vendor lock-in."""
    bad_payload = {
        "recipe_id": "bad_recipe_vendor_lock",
        "phases": [{"id": "tts", "action": "call elevenlabs tts"}],
    }

    with pytest.raises(ProviderNeutralityViolationError) as exc_info:
        assert_provider_neutral(bad_payload)
    assert "Provider neutrality violation" in str(exc_info.value)
    assert "elevenlabs" in str(exc_info.value).lower()


def test_registry_get_nonexistent_recipe_raises(registry: RecipeRegistry):
    """Verifies RecipeNotFoundError is raised when using get_or_raise with a non-existent recipe."""
    with pytest.raises(RecipeNotFoundError):
        registry.get_or_raise("non_existent_recipe_id_12345")
