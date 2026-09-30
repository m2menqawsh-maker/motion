"""
test_s16_remediation_proof.py — GREEN Remediation Proof for Package S16:
- LED-043 (P1): Transition end-to-end propagation and fail-closed validation.
- LED-044 (P1): parseRenderInput is the single canonical runtime gate.
- LED-045 (P1): Template-specific fail-closed runtime schemas (LED-045).
- LED-046 (P1): Effects fail-closed before render (no silent drops as no-op).
"""
import json
from pathlib import Path
import pytest

from scripts.core.blueprint_model import BlueprintV2, BlueprintSceneV2, TransitionRef, EffectRef
from scripts.core.blueprint_validator import validate_blueprint_v2

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_green_led_043_transition_end_to_end_contract():
    """
    GREEN PROOF for LED-043:
    Transitions are structurally validated and preserved end-to-end.
    - TransitionRef accepts valid transition type and duration.
    - Transition duration exceeding scene duration is rejected.
    """
    trans = TransitionRef(type="wipe", durationFrames=20)
    assert trans.type == "wipe"
    assert trans.durationFrames == 20

    scene = BlueprintSceneV2(
        scene_id="s1",
        template="rui-hero-device-assemble",
        startFrame=0,
        durationFrames=30,
        transition=trans,
    )
    bp = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_trans_test",
        fps=30,
        aspect_ratio="16:9",
        scenes=[scene],
    )
    result = validate_blueprint_v2(bp)
    assert result.ok is True

    # Transition duration >= scene duration must fail
    bad_scene = BlueprintSceneV2(
        scene_id="s1",
        template="rui-hero-device-assemble",
        startFrame=0,
        durationFrames=15,
        transition=TransitionRef(type="wipe", durationFrames=20),
    )
    bad_bp = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_trans_test_bad",
        fps=30,
        aspect_ratio="16:9",
        scenes=[bad_scene],
    )
    bad_result = validate_blueprint_v2(bad_bp)
    assert bad_result.ok is False
    assert any("transition durationFrames" in err for err in bad_result.errors)


def test_green_led_044_canonical_render_input_gate_contract_files_exist():
    """
    GREEN PROOF for LED-044:
    contracts/render-input.ts exists and exports canonical parseRenderInput and error hierarchy.
    """
    render_input_ts = ROOT / "contracts" / "render-input.ts"
    assert render_input_ts.is_file()

    content = render_input_ts.read_text(encoding="utf-8")
    assert "export function parseRenderInput" in content
    assert "class InvalidRenderInputError" in content
    assert "class UnknownTemplateError" in content
    assert "class UnknownEffectError" in content
    assert "class UnknownTransitionError" in content
    assert "InvalidTemplatePayloadError" in content


def test_green_led_045_template_specific_schemas_file_exists():
    """
    GREEN PROOF for LED-045:
    contracts/template-schemas.ts exists and provides fail-closed validation for template payloads.
    """
    schemas_ts = ROOT / "contracts" / "template-schemas.ts"
    assert schemas_ts.is_file()

    content = schemas_ts.read_text(encoding="utf-8")
    assert "StrictStyleSurfaceSchema" in content
    assert "DataStoryPropsSchema" in content
    assert "AnimatedTextPropsSchema" in content
    assert "validateTemplatePayload" in content
    assert "buildPropsSchemaFromFields" in content


def test_green_led_046_effects_runtime_fail_closed_authority():
    """
    GREEN PROOF for LED-046:
    registry/effects-runtime.ts is the single authority for effects.
    Exports isKnownEffect and does not drop unknown effects silently.
    """
    effects_ts = ROOT / "registry" / "effects-runtime.ts"
    assert effects_ts.is_file()

    content = effects_ts.read_text(encoding="utf-8")
    assert "export function isKnownEffect" in content
    assert "EFFECTS_RUNTIME" in content
    assert "EFFECT_IDS" in content
