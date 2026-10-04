"""
ai/recipes/contracts.py
=======================
Runtime contracts and domain exceptions for Recipe Engine (S28-03).
"""

from __future__ import annotations


class RecipeError(Exception):
    """Base exception for recipe engine errors."""
    pass


class RecipeNotFoundError(RecipeError):
    """Raised when a requested recipe ID is not found in the registry."""
    pass


class NoEligibleRecipeError(RecipeError):
    """Raised when no recipe satisfies hard eligibility constraints for a brief."""
    pass


class RecipeValidationError(RecipeError):
    """Raised when a recipe definition fails contract validation."""
    pass


class ProviderNeutralityViolationError(RecipeError):
    """Raised when a recipe definition or selector leaks third-party vendor or provider names."""
    pass
