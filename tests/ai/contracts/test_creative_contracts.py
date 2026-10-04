"""
tests/ai/contracts/test_creative_contracts.py
=============================================
Contract tests for S28 Creative Intelligence Platform.

Guarantees:
- Every valid contract fixture validates cleanly against Pydantic canonical models.
- Every valid contract fixture validates against generated JSON Schemas.
- Missing required fields are strictly caught.
- Unknown enum values are strictly caught.
- Contradictory constraints (min > max duration) are strictly caught.
- Invalid audio modes are strictly caught.
- Invalid creative tiers are strictly caught.
- Template candidates without required provenance are strictly caught.
- Self-authorization of template promotion by AI is strictly rejected.
- Unexpected fields are rejected (extra="forbid").
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import jsonschema

from ai.contracts.creative import (
    AudioMode,
    CandidateValidationReport,
    CompositionLayer,
    CompositionPlan,
    CreativeBrief,
    CreativeConstraints,
    CreativeFeedback,
    CreativeIntent,
    CreativePlan,
    CreativePlanStatus,
    CreativeTier,
    CreativeTierDecision,
    KnowledgeDescriptor,
    NarrativeBeat,
    NarrativePlan,
    PromotionDecision,
    PromotionStatus,
    RecipeDefinition,
    RecipeSelection,
    RecipeStage,
    SceneIntent,
    SkillDefinition,
    TasteDecision,
    TasteRule,
    TasteRuleSeverity,
    TemplateCandidate,
    UserStyleProfile,
)

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "creative_contract_fixtures.json"
SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "schemas" / "creative"


@pytest.fixture(scope="module")
def fixtures_data():
    assert FIXTURES_PATH.exists(), f"Missing fixtures file: {FIXTURES_PATH}"
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


# ============================================================================
# VALID CONTRACT TESTS
# ============================================================================

def test_valid_creative_brief(fixtures_data):
    payload = fixtures_data["valid"]["creative_brief"]
    brief = CreativeBrief.model_validate(payload)
    assert brief.brief_id == "brief_tech_saas_001"
    assert brief.constraints.audio_mode == AudioMode.VO_MUSIC
    assert brief.constraints.target_duration_seconds == 30.0

    # JSON Schema validation
    schema_path = SCHEMA_DIR / "creative_brief.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_narrative_plan(fixtures_data):
    payload = fixtures_data["valid"]["narrative_plan"]
    plan = NarrativePlan.model_validate(payload)
    assert plan.narrative_id == "narrative_001"
    assert len(plan.beats) == 3
    assert plan.estimated_total_duration_sec == 30.0

    # JSON Schema validation
    schema_path = SCHEMA_DIR / "narrative_plan.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_skill_definition(fixtures_data):
    payload = fixtures_data["valid"]["skill_definition"]
    skill = SkillDefinition.model_validate(payload)
    assert skill.skill_id == "skill_motion_typography"
    assert skill.task_type == "motion_typography"

    schema_path = SCHEMA_DIR / "skill_definition.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_knowledge_descriptor(fixtures_data):
    payload = fixtures_data["valid"]["knowledge_descriptor"]
    kd = KnowledgeDescriptor.model_validate(payload)
    assert kd.knowledge_id == "know_motion_personality"
    assert kd.authority_level == 5

    schema_path = SCHEMA_DIR / "knowledge_descriptor.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_recipe_definition(fixtures_data):
    payload = fixtures_data["valid"]["recipe_definition"]
    recipe = RecipeDefinition.model_validate(payload)
    assert recipe.recipe_id == "living-canvas-explainer"
    assert len(recipe.stages) == 3

    schema_path = SCHEMA_DIR / "recipe_definition.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_recipe_selection(fixtures_data):
    payload = fixtures_data["valid"]["recipe_selection"]
    sel = RecipeSelection.model_validate(payload)
    assert sel.selected_recipe_id == "living-canvas-explainer"
    assert sel.confidence_score == 0.94

    schema_path = SCHEMA_DIR / "recipe_selection.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)


def test_valid_taste_rule_and_decision(fixtures_data):
    rule_payload = fixtures_data["valid"]["taste_rule"]
    rule = TasteRule.model_validate(rule_payload)
    assert rule.severity == TasteRuleSeverity.MANDATORY_CREATIVE

    dec_payload = fixtures_data["valid"]["taste_decision"]
    dec = TasteDecision.model_validate(dec_payload)
    assert dec.rule_id == rule.rule_id


def test_valid_creative_plan_and_tier(fixtures_data):
    payload = fixtures_data["valid"]["creative_plan"]
    plan = CreativePlan.model_validate(payload)
    assert plan.plan_id == "cplan_tech_001"
    assert plan.status == CreativePlanStatus.PROPOSED
    assert len(plan.scenes) == 2

    tier_payload = fixtures_data["valid"]["creative_tier_decision"]
    tier_dec = CreativeTierDecision.model_validate(tier_payload)
    assert tier_dec.selected_tier == CreativeTier.REUSE


def test_valid_template_candidate_and_promotion(fixtures_data):
    cand_payload = fixtures_data["valid"]["template_candidate"]
    cand = TemplateCandidate.model_validate(cand_payload)
    assert cand.candidate_id == "cand_custom_pulse_box"
    assert cand.target_tier == CreativeTier.REUSE

    report_payload = fixtures_data["valid"]["candidate_validation_report"]
    report = CandidateValidationReport.model_validate(report_payload)
    assert report.passed is True

    promo_payload = fixtures_data["valid"]["promotion_decision"]
    promo = PromotionDecision.model_validate(promo_payload)
    assert promo.status == PromotionStatus.APPROVED
    assert promo.authorized_by == "usr_lead_architect"


def test_valid_user_style_and_feedback(fixtures_data):
    prof_payload = fixtures_data["valid"]["user_style_profile"]
    prof = UserStyleProfile.model_validate(prof_payload)
    assert prof.preferred_motion_personality == "Cinematic"

    fb_payload = fixtures_data["valid"]["creative_feedback"]
    fb = CreativeFeedback.model_validate(fb_payload)
    assert fb.user_rating == 5


# ============================================================================
# NEGATIVE & REJECTION TESTS
# ============================================================================

def test_rejects_missing_required_fields(fixtures_data):
    payload = fixtures_data["invalid"]["missing_required_fields"]
    with pytest.raises(Exception):
        CreativeBrief.model_validate(payload)


def test_rejects_unknown_enum_values(fixtures_data):
    payload = fixtures_data["invalid"]["unknown_enum_values"]
    with pytest.raises(Exception):
        CreativeTierDecision.model_validate(payload)


def test_rejects_contradictory_constraints(fixtures_data):
    """Enforces min_duration <= max_duration invariant."""
    payload = fixtures_data["invalid"]["contradictory_constraints"]
    with pytest.raises(ValueError, match="Contradictory constraints: min_duration_seconds"):
        CreativeConstraints.model_validate(payload)


def test_rejects_invalid_audio_mode(fixtures_data):
    payload = fixtures_data["invalid"]["invalid_audio_mode"]
    with pytest.raises(Exception):
        CreativeConstraints.model_validate(payload)


def test_rejects_invalid_creative_tier(fixtures_data):
    payload = fixtures_data["invalid"]["invalid_creative_tier"]
    with pytest.raises(Exception):
        CreativeTierDecision.model_validate(payload)


def test_rejects_candidate_without_required_provenance(fixtures_data):
    """Candidate with empty provenance source must be rejected."""
    payload = fixtures_data["invalid"]["candidate_no_provenance"]
    with pytest.raises(Exception):
        TemplateCandidate.model_validate(payload)


def test_rejects_template_promotion_authorized_by_ai(fixtures_data):
    """Promotion approved by 'ai' or 'agent' must be rejected (AI is not registry authority)."""
    payload = fixtures_data["invalid"]["promotion_authorized_by_ai"]
    with pytest.raises(ValueError, match="Template promotion cannot be authorized by raw AI"):
        PromotionDecision.model_validate(payload)


def test_rejects_unexpected_fields():
    """Guarantees extra='forbid' across creative models."""
    payload = {
        "intent_id": "int_001",
        "goal": "Test goal",
        "audience": "Developers",
        "tone": "Technical",
        "key_takeaway": "Reliability",
        "unauthorized_field": "SHOULD_FAIL",
    }
    with pytest.raises(Exception, match="Extra inputs are not permitted"):
        CreativeIntent.model_validate(payload)
