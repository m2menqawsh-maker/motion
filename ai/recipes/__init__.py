"""
ai/recipes/__init__.py
======================
Recipe Engine package for S28-03.
"""

from ai.recipes.contracts import (
    NoEligibleRecipeError,
    ProviderNeutralityViolationError,
    RecipeError,
    RecipeNotFoundError,
    RecipeValidationError,
)
from ai.recipes.registry import (
    RecipeRegistry,
    assert_provider_neutral,
)
from ai.recipes.selector import (
    RecipeSelector,
)

__all__ = [
    "NoEligibleRecipeError",
    "ProviderNeutralityViolationError",
    "RecipeError",
    "RecipeNotFoundError",
    "RecipeRegistry",
    "RecipeSelector",
    "RecipeValidationError",
    "assert_provider_neutral",
]
