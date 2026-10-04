"""
tests/ai/planning/test_tier_policy.py
=====================================
Authoritative Unit Tests for S28-06 Creative Tier Policy:
- Machine-enforced deterministic tier sequence: REUSE -> COMPOSE -> CREATE-needed
- Anti-CREATE-bypass enforcement (Case 4: REUSE overrides CREATE; Case 5: COMPOSE overrides CREATE)
- Strict validation guard (Case 12: CREATE decision requires both REUSE and COMPOSE failure evidence)
- Heterogeneous multi-scene plan decisions
- Auditable CreativeTierDecision structure
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    ComposeEvaluationResult,
    CreativeTier,
    CreativeTierDecision,
    ReuseEvaluationResult,
    SceneIntent,
)
from ai.planning.tier_policy import CreativeTierPolicy


@pytest.fixture
def tier_policy() -> CreativeTierPolicy:
    return CreativeTierPolicy()


def test_tier_policy_selects_reuse_when_template_available(tier_policy: CreativeTierPolicy):
    """When a registered template is sufficient, policy deterministically selects REUSE."""
    si = SceneIntent(
        scene_id="sc_policy_reuse",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.5,
        spoken_text="Latency dropped by 80 percent across all nodes.",
    )
    decision = tier_policy.decide(scene_intent=si, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.REUSE
    assert decision.template_ref is not None
    assert decision.reuse_result is not None
    assert decision.reuse_result.sufficiency is True
    assert decision.composition_plan is None
    assert "REUSE sufficient: canonical registered template" in decision.rationale


def test_tier_policy_selects_compose_when_reuse_fails(tier_policy: CreativeTierPolicy):
    """When no single template satisfies need but Lego primitives can compose, selects COMPOSE."""
    si = SceneIntent(
        scene_id="sc_policy_compose",
        scene_index=1,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=5.0,
        spoken_text="Compare legacy monolithic architecture with microservices.",
        template_requirements=["split_screen_dual_view_custom_layout"],
    )
    decision = tier_policy.decide(scene_intent=si, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.COMPOSE
    assert decision.reuse_result is not None
    assert decision.reuse_result.sufficiency is False
    assert decision.compose_result is not None
    assert decision.compose_result.sufficiency is True
    assert decision.composition_plan is not None
    assert "COMPOSE sufficient using registered Lego anchor" in decision.rationale


def test_tier_policy_escalates_to_create_only_when_both_insufficient(tier_policy: CreativeTierPolicy):
    """When both REUSE and COMPOSE are insufficient, policy escalates to CREATE (evidence only)."""
    si = SceneIntent(
        scene_id="sc_policy_create",
        scene_index=2,
        intent_label="novel_3d_simulation_neural_avatar",
        mood="Experimental",
        motion_personality="Dynamic",
        primary_visual_job="action",
        estimated_duration_sec=6.0,
        spoken_text="Display interactive 3D WebGL neural network volumetric scan.",
    )
    decision = tier_policy.decide(scene_intent=si, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.CREATE
    assert decision.needs_create_evaluation is True
    assert decision.reuse_result is not None
    assert decision.reuse_result.sufficiency is False
    assert decision.compose_result is not None
    assert decision.compose_result.sufficiency is False
    assert "Escalation to CREATE justified" in decision.rationale


def test_anti_bypass_case_4_reuse_overrides_requested_create(tier_policy: CreativeTierPolicy):
    """Anti-Bypass Case 4: Caller requests CREATE when REUSE is sufficient; policy denies and enforces REUSE."""
    si = SceneIntent(
        scene_id="sc_bypass_reuse",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.0,
        spoken_text="Performance jumped 400 percent.",
    )
    decision = tier_policy.decide(
        scene_intent=si,
        requested_tier=CreativeTier.CREATE,
        aspect_ratio="9:16",
    )
    assert decision.selected_tier == CreativeTier.REUSE
    assert "Anti-Bypass Enforcement" in decision.rationale
    assert "Bypass request denied by policy" in decision.rationale
    assert "REUSE tier enforced" in decision.rationale


def test_anti_bypass_case_5_compose_overrides_requested_create(tier_policy: CreativeTierPolicy):
    """Anti-Bypass Case 5: Caller requests CREATE when COMPOSE is sufficient; policy denies and enforces COMPOSE."""
    si = SceneIntent(
        scene_id="sc_bypass_compose",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=5.0,
        spoken_text="Side by side code comparison.",
        template_requirements=["split_screen_dual_view_custom_layout"],
    )
    decision = tier_policy.decide(
        scene_intent=si,
        requested_tier=CreativeTier.CREATE,
        aspect_ratio="9:16",
    )
    assert decision.selected_tier == CreativeTier.COMPOSE
    assert "Anti-Bypass Enforcement" in decision.rationale
    assert "Escalation denied by policy" in decision.rationale
    assert "COMPOSE tier enforced" in decision.rationale


def test_anti_bypass_case_12_create_without_evidence_raises_validation_error():
    """Case 12: CreativeTierDecision cannot have selected_tier == CREATE without structured failure evidence."""
    with pytest.raises(ValidationError) as exc_info:
        CreativeTierDecision(
            decision_id="dec_invalid_create",
            scene_id="sc_invalid",
            selected_tier=CreativeTier.CREATE,
            needs_create_evaluation=True,
            rationale="Unsubstantiated tier choice without reuse/compose results.",
        )
    errors = str(exc_info.value)
    assert "REUSE evidence is missing or marked sufficient" in errors


def test_anti_bypass_case_12_create_with_sufficient_reuse_raises_validation_error():
    """Case 12: CreativeTierDecision cannot have selected_tier == CREATE if reuse_result.sufficiency is True."""
    dummy_reuse = ReuseEvaluationResult(
        need_description="metric callout",
        candidates_checked=["rui-stat-card"],
        eligible_candidates=["rui-stat-card"],
        ranked_candidates=[],
        selected_candidate="rui-stat-card",
        rejection_reasons={},
        sufficiency=True,  # SUFFICIENT!
        rationale="Template is available",
    )
    dummy_compose = ComposeEvaluationResult(
        need_description="metric callout",
        components_checked=[],
        eligible_components=[],
        composition_plan=None,
        rejection_reasons=["REUSE is sufficient"],
        sufficiency=False,
        rationale="Not needed",
    )
    with pytest.raises(ValidationError) as exc_info:
        CreativeTierDecision(
            decision_id="dec_contradictory_create",
            scene_id="sc_invalid",
            selected_tier=CreativeTier.CREATE,
            needs_create_evaluation=True,
            reuse_result=dummy_reuse,
            compose_result=dummy_compose,
            rationale="Contradiction",
        )
    errors = str(exc_info.value)
    assert "REUSE evidence is missing or marked sufficient" in errors


def test_tier_policy_heterogeneous_multi_scene_plan(tier_policy: CreativeTierPolicy):
    """A multi-scene plan correctly yields heterogeneous decisions across scenes."""
    scenes = [
        SceneIntent(
            scene_id="sc_01_hook",
            scene_index=0,
            intent_label="hook",
            mood="Energetic",
            motion_personality="Cinematic",
            primary_visual_job="action",
            estimated_duration_sec=3.0,
            spoken_text="Stop wasting hours on manual editing.",
        ),
        SceneIntent(
            scene_id="sc_02_split",
            scene_index=1,
            intent_label="comparison",
            mood="Technical",
            motion_personality="Cinematic",
            primary_visual_job="comparison",
            estimated_duration_sec=5.0,
            spoken_text="Compare traditional timelines with AI compilation.",
            template_requirements=["split_screen_dual_view_custom_layout"],
        ),
        SceneIntent(
            scene_id="sc_03_impossible",
            scene_index=2,
            intent_label="novel_3d_simulation_neural_avatar",
            mood="Experimental",
            motion_personality="Dynamic",
            primary_visual_job="action",
            estimated_duration_sec=6.0,
            spoken_text="Interact with 3D volumetric point cloud simulation.",
        ),
    ]

    decisions = [tier_policy.decide(scene_intent=si, aspect_ratio="9:16") for si in scenes]

    assert decisions[0].selected_tier == CreativeTier.REUSE
    assert decisions[0].template_ref is not None

    assert decisions[1].selected_tier == CreativeTier.COMPOSE
    assert decisions[1].composition_plan is not None

    assert decisions[2].selected_tier == CreativeTier.CREATE
    assert decisions[2].needs_create_evaluation is True


def test_cost_vs_fit_policy_quality_over_cheap_reuse(tier_policy: CreativeTierPolicy):
    """
    Cost / Fit Policy Evidence (S28-06A Requirement 7):
    Proves that policy does NOT use 'cheap = automatically better'.
    A single template REUSE would be structurally/computationally cheaper (0 additional layers),
    but fails the required fit threshold (<0.70) for an explicit custom split requirement.
    COMPOSE satisfies the explicit creative need using registered Lego components.
    Policy selects COMPOSE, proving quality and required fit take precedence over pure cheapness.
    """
    si = SceneIntent(
        scene_id="sc_cost_vs_fit",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.5,
        spoken_text="Compare legacy monolithic systems with modern event-driven architectures.",
        template_requirements=["split_screen_dual_view_custom_layout"],
    )
    decision = tier_policy.decide(scene_intent=si, aspect_ratio="9:16")

    # Policy must NOT blindly choose REUSE just because 1 template is cheaper
    assert decision.selected_tier == CreativeTier.COMPOSE
    assert decision.reuse_result is not None
    assert decision.reuse_result.sufficiency is False
    assert decision.compose_result is not None
    assert decision.compose_result.sufficiency is True
    assert decision.composition_plan is not None
    assert decision.needs_create_evaluation is False
    assert "COMPOSE sufficient" in decision.rationale

