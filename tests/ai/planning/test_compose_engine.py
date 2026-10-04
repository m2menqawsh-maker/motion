"""
tests/ai/planning/test_compose_engine.py
========================================
Authoritative Unit Tests for S28-06 COMPOSE Engine:
- Lego primitive authority: registered templates, elements, bridged effects, transitions
- Fail-closed validation against unknown components (anchor, element, effect, transition)
- Synthesis of structured CompositionPlan with layers, spatial layouts, timing
- Invariant: Zero code generation (no .tsx, no TemplateCandidate, no file writes)
- AudioMode constraints enforcement across composite layers
"""

from __future__ import annotations

import pytest
from typing import Dict, List

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    CompositionLayer,
    CompositionPlan,
    SceneIntent,
)
from ai.planning.compose_engine import (
    BRIDGED_EFFECTS,
    SUPPORTED_TRANSITIONS,
    ComposeEngine,
)


@pytest.fixture
def compose_engine() -> ComposeEngine:
    return ComposeEngine()


def test_compose_engine_registered_lego_authority(compose_engine: ComposeEngine):
    """COMPOSE engine only composes from registered templates, elements, effects, and transitions."""
    assert compose_engine.is_component_registered("animatedcounter-element")
    assert compose_engine.is_component_registered("codeblock-element")
    assert "fade" in SUPPORTED_TRANSITIONS
    assert "slide" in SUPPORTED_TRANSITIONS
    assert "Highlight" in BRIDGED_EFFECTS or "CameraRig" in BRIDGED_EFFECTS


def test_compose_engine_synthesizes_valid_composition_plan(compose_engine: ComposeEngine):
    """Synthesizes valid multi-layer CompositionPlan when composite need is satisfiable."""
    si = SceneIntent(
        scene_id="sc_comp_valid",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=5.0,
        spoken_text="Compare legacy architecture with real-time streaming.",
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        aspect_ratio="9:16",
    )
    assert res.sufficiency is True
    assert res.composition_plan is not None
    plan = res.composition_plan
    assert isinstance(plan, CompositionPlan)
    assert plan.base_template_or_primitive == "rui-split-screen"
    assert len(plan.layers) >= 2
    assert plan.transition in SUPPORTED_TRANSITIONS
    assert all(compose_engine.is_component_registered(l.element_ref) for l in plan.layers)


def test_compose_engine_rejects_unknown_base_anchor(compose_engine: ComposeEngine):
    """Unknown base anchor component must fail closed and invalidate composition."""
    si = SceneIntent(
        scene_id="sc_unknown_anchor",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.0,
    )
    invalid_plan = CompositionPlan(
        composition_id="comp_invalid_anchor",
        scene_id="sc_unknown_anchor",
        base_template_or_primitive="fake-nonexistent-base-template",
        layers=[
            CompositionLayer(
                layer_type="primary",
                element_ref="animatedtext-element",
                properties={"text": "Test"},
            )
        ],
        layout_zone="full",
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        candidate_plan=invalid_plan,
    )
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert any("Unknown or unregistered base component" in r for r in res.rejection_reasons)


def test_compose_engine_rejects_unknown_element_layer(compose_engine: ComposeEngine):
    """Unknown element layer component must fail closed and invalidate composition."""
    si = SceneIntent(
        scene_id="sc_unknown_layer",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.0,
    )
    invalid_plan = CompositionPlan(
        composition_id="comp_invalid_layer",
        scene_id="sc_unknown_layer",
        base_template_or_primitive="rui-split-screen",
        layers=[
            CompositionLayer(
                layer_type="primary",
                element_ref="fake-unregistered-overlay-widget",
                properties={"text": "Test"},
            )
        ],
        layout_zone="full",
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        candidate_plan=invalid_plan,
    )
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert any("unknown or unregistered component" in r for r in res.rejection_reasons)


def test_compose_engine_rejects_unknown_effect(compose_engine: ComposeEngine):
    """Unknown effect must fail closed and invalidate composition."""
    si = SceneIntent(
        scene_id="sc_unknown_effect",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.0,
    )
    invalid_plan = CompositionPlan(
        composition_id="comp_invalid_effect",
        scene_id="sc_unknown_effect",
        base_template_or_primitive="rui-split-screen",
        layers=[
            CompositionLayer(
                layer_type="primary",
                element_ref="animatedtext-element",
                properties={"text": "Test"},
            )
        ],
        layout_zone="full",
        effects=["unsupported_hologram_warp_v99"],
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        candidate_plan=invalid_plan,
    )
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert any("Unknown or unbridged effect" in r for r in res.rejection_reasons)


def test_compose_engine_rejects_unknown_transition(compose_engine: ComposeEngine):
    """Unknown transition must fail closed and invalidate composition."""
    si = SceneIntent(
        scene_id="sc_unknown_trans",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.0,
    )
    invalid_plan = CompositionPlan(
        composition_id="comp_invalid_trans",
        scene_id="sc_unknown_trans",
        base_template_or_primitive="rui-split-screen",
        layers=[
            CompositionLayer(
                layer_type="primary",
                element_ref="animatedtext-element",
                properties={"text": "Test"},
            )
        ],
        layout_zone="full",
        transition="hyperdrive_quantum_jump",
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        candidate_plan=invalid_plan,
    )
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert any("Unsupported transition" in r for r in res.rejection_reasons)


def test_compose_engine_forced_unknown_component_rejection(compose_engine: ComposeEngine):
    """Testing hook force_unknown_component_for_testing triggers fail-closed rejection."""
    si = SceneIntent(
        scene_id="sc_forced_unknown",
        scene_index=0,
        intent_label="comparison",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="comparison",
        estimated_duration_sec=4.0,
    )
    res = compose_engine.evaluate(
        scene_intent=si,
        force_unknown_component_for_testing="rogue_gl_canvas",
    )
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert "rogue_gl_canvas" in res.rejection_reasons[0]


def test_compose_engine_zero_code_generation_invariant(compose_engine: ComposeEngine):
    """COMPOSE engine must never generate .tsx code or instantiate TemplateCandidate."""
    for forbidden_attr in ("generate_tsx", "create_candidate", "compile_component"):
        assert not hasattr(compose_engine, forbidden_attr)


def test_compose_engine_impossible_need_fails_closed(compose_engine: ComposeEngine):
    """Completely unsatisfiable need with no matching Lego primitives fails closed without crashing."""
    si = SceneIntent(
        scene_id="sc_impossible",
        scene_index=0,
        intent_label="novel_3d_simulation_neural_avatar",
        mood="Experimental",
        motion_personality="Dynamic",
        primary_visual_job="action",
        estimated_duration_sec=5.0,
        spoken_text="Render an interactive WebGL 3D molecular simulation.",
    )
    res = compose_engine.evaluate(scene_intent=si)
    assert res.sufficiency is False
    assert res.composition_plan is None
    assert "COMPOSE insufficient" in res.rationale
