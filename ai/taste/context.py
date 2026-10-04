"""
ai/taste/context.py
===================
TasteContext builder constructing the contextual snapshot for Taste Engine and Directors (S28-04).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from ai.contracts.creative.brief import CreativeBrief
from ai.contracts.creative.feedback import UserStyleProfile
from ai.contracts.creative.narrative import NarrativePlan
from ai.contracts.creative.recipe import RecipeDefinition, RecipeSelection
from ai.contracts.creative.taste import TasteContext


class TasteContextBuilder:
    """
    Constructs a validated, bounded TasteContext object without leaking raw file handles.
    """

    @classmethod
    def build(
        cls,
        brief: CreativeBrief,
        narrative_plan: NarrativePlan,
        recipe: Optional[Union[RecipeDefinition, RecipeSelection]] = None,
        media_intelligence: Optional[Dict[str, Any]] = None,
        available_assets: Optional[List[str]] = None,
        user_style_profile: Optional[UserStyleProfile] = None,
        active_knowledge_ids: Optional[List[str]] = None,
        active_skill_ids: Optional[List[str]] = None,
    ) -> TasteContext:
        """Assembles a TasteContext instance."""
        recipe_id = "default-recipe"
        recipe_name = "Default Production Recipe"

        if recipe is not None:
            if isinstance(recipe, RecipeDefinition):
                recipe_id = recipe.recipe_id
                recipe_name = recipe.name
            elif isinstance(recipe, RecipeSelection):
                recipe_id = recipe.selected_recipe_id
                recipe_name = recipe.selected_recipe_id

        return TasteContext(
            brief=brief,
            narrative_plan=narrative_plan,
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            media_intelligence=media_intelligence or {},
            available_assets=available_assets or [],
            user_style_profile=user_style_profile,
            active_knowledge_ids=active_knowledge_ids or [],
            active_skill_ids=active_skill_ids or [],
        )
