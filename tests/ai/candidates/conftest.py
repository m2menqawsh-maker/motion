"""
tests/ai/candidates/conftest.py
===============================
Shared fixtures for Candidate test suite (S28-07A).
"""

from __future__ import annotations

import pytest

from ai.contracts.creative.plan import (
    CreativeTier,
    CreativeTierDecision,
    ComposeEvaluationResult,
    ReuseEvaluationResult,
)


@pytest.fixture
def valid_create_decision():
    return CreativeTierDecision(
        decision_id="tier_dec_create_001",
        scene_id="scene_hero",
        selected_tier=CreativeTier.CREATE,
        rationale="Specialized kinetic counter component required.",
        needs_create_evaluation=True,
        requested_need="Kinetic counter with spring physics",
        reuse_candidates_checked=["tmpl-counter-static"],
        reuse_result=ReuseEvaluationResult(
            need_description="Kinetic counter with spring physics",
            candidates_checked=["tmpl-counter-static"],
            eligible_candidates=[],
            ranked_candidates=[],
            selected_candidate=None,
            rejection_reasons={"tmpl-counter-static": ["Static display only, no kinetic easing"]},
            sufficiency=False,
            rationale="REUSE insufficient: no registered template meets spring physics requirements.",
        ),
        compose_candidates_checked=["elem-text"],
        compose_result=ComposeEvaluationResult(
            need_description="Kinetic counter with spring physics",
            components_checked=["elem-text"],
            eligible_components=[],
            composition_plan=None,
            rejection_reasons=["elem-text cannot animate dynamic counter physics"],
            sufficiency=False,
            rationale="COMPOSE insufficient: primitive Lego elements cannot meet performance target.",
        ),
    )


@pytest.fixture
def valid_creative_plan():
    return "cplan_launch_001"
