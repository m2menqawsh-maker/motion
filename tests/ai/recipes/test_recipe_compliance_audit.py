"""
tests/ai/recipes/test_recipe_compliance_audit.py
================================================
Comprehensive compliance audit for all 18 migrated legacy recipes (S28-03A).

Audits every recipe item-by-item across 17 mandatory dimensions:
1. schema_valid
2. version_present
3. owner_present
4. supported_intents_present
5. supported_platforms_present
6. supported_audio_modes_present
7. required_capabilities_present
8. optional_capabilities_valid
9. forbidden_capabilities_valid
10. required_skills_valid
11. required_knowledge_valid
12. phases_valid
13. dependencies_valid
14. quality_profile_valid
15. budget_profile_valid
16. fallback_valid_or_not_applicable
17. provider_neutral

Outputs machine-readable report to documentation/audits/s28_03a_recipe_compliance_report.json.
"""

import json
from pathlib import Path
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.creative.recipe import RecipeDefinition
from ai.recipes.registry import RecipeRegistry, assert_provider_neutral


def test_audit_all_18_legacy_recipes():
    registry = RecipeRegistry()
    all_recipes = registry.list_all()
    assert len(all_recipes) == 18, f"Expected exactly 18 active recipes, found {len(all_recipes)}"

    audit_records = []
    registered_ids = set(r.recipe_id for r in all_recipes)

    for recipe in all_recipes:
        record = {
            "recipe_id": recipe.recipe_id,
            "schema_valid": isinstance(recipe, RecipeDefinition),
            "version_present": bool(recipe.version and len(recipe.version) > 0),
            "owner_present": bool(recipe.owner and len(recipe.owner) > 0),
            "supported_intents_present": len(recipe.supported_intents) > 0,
            "supported_platforms_present": len(recipe.supported_platforms) > 0,
            "supported_audio_modes_present": len(recipe.supported_audio_modes) > 0,
            "required_capabilities_present": isinstance(recipe.required_capabilities, list),
            "optional_capabilities_valid": (
                isinstance(recipe.optional_capabilities, list)
                and all(isinstance(c, CapabilityType) for c in recipe.optional_capabilities)
            ),
            "forbidden_capabilities_valid": (
                isinstance(recipe.forbidden_capabilities, list)
                and all(isinstance(c, CapabilityType) for c in recipe.forbidden_capabilities)
            ),
            "required_skills_valid": (
                isinstance(recipe.required_skills, list)
                and all(isinstance(s, str) and len(s) > 0 for s in recipe.required_skills)
            ),
            "required_knowledge_valid": (
                isinstance(recipe.required_knowledge, list)
                and all(isinstance(k, str) and len(k) > 0 for k in recipe.required_knowledge)
            ),
            "phases_valid": isinstance(recipe.phases, list) and len(recipe.phases) > 0,
            "dependencies_valid": isinstance(recipe.dependencies, list),
            "quality_profile_valid": recipe.quality_profile in ("DRAFT", "STANDARD", "PREMIUM"),
            "budget_profile_valid": recipe.budget_profile in ("LOW", "STANDARD", "HIGH"),
            "fallback_valid_or_not_applicable": (
                recipe.fallback_strategy is None or recipe.fallback_strategy in registered_ids
            ),
            "provider_neutral": True,
        }

        # Check provider neutrality
        try:
            assert_provider_neutral(recipe)
        except Exception:
            record["provider_neutral"] = False

        audit_records.append(record)

        # Assert every single dimension is True for this recipe
        for key, val in record.items():
            assert val is True or (key == "recipe_id" and isinstance(val, str)), (
                f"Recipe '{recipe.recipe_id}' failed compliance audit on '{key}': {val}"
            )

    report = {
        "report_version": "1.0.0",
        "domain": "S28-03A Legacy Recipe Compliance Audit",
        "total_recipes_audited": len(audit_records),
        "compliant_recipes_count": sum(
            1 for r in audit_records if all(v is True for k, v in r.items() if k != "recipe_id")
        ),
        "non_compliant_recipes_count": sum(
            1 for r in audit_records if any(v is not True for k, v in r.items() if k != "recipe_id")
        ),
        "compliance_rate": round(
            sum(1 for r in audit_records if all(v is True for k, v in r.items() if k != "recipe_id"))
            / len(audit_records),
            4,
        ),
        "recipes": audit_records,
    }

    out_file = Path("documentation/audits/s28_03a_recipe_compliance_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert out_file.exists()
    assert report["compliant_recipes_count"] == 18
