"""
tests/architecture/test_s18_architecture_guard.py — Architecture Guards for Package S18:
- Guard 1: scripts/gates/probe_qc.py must NOT access legacy 'timeline' (AST check) (LED-047).
- Guard 2: scripts/gates/probe_qc.py must NOT contain silent fallback .get('fps', 30) (AST check) (LED-048).
- Guard 3: scripts/gates/probe_qc.py must use build_render_input() from scripts.core.render_input (S17 parity).
- Guard 4: scripts/gates/probe_qc.py must use derive_probe_frame_plan() as the single frame selection authority.
- Guard 5: scripts/gates/probe_qc.py must enforce ReviewService.create_review_bundle() integration (LED-050).
"""
import ast
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_probe_qc_no_legacy_timeline_access():
    """
    Guard 1 (LED-047):
    scripts/gates/probe_qc.py must not query or inspect 'timeline' from blueprint dictionary.
    AST analysis guarantees no subscripts, lookups, or .get('timeline') calls exist.
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(probe_script))

    for node in ast.walk(tree):
        # Check node.attr or Call like .get('timeline')
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "timeline":
                    pytest.fail("Architecture Violation (LED-047): probe_qc.py contains .get('timeline') call!")
        # Check subscript like bp['timeline']
        elif isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and node.slice.value == "timeline":
                pytest.fail("Architecture Violation (LED-047): probe_qc.py accesses subscript ['timeline']!")

    # Check textual presence
    assert 'get("timeline"' not in content
    assert "['timeline']" not in content
    assert '["timeline"]' not in content


def test_guard_probe_qc_no_silent_fps_default():
    """
    Guard 2 (LED-048):
    scripts/gates/probe_qc.py must not silently default FPS to 30.
    Must fail closed if FPS is missing or mismatched.
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(probe_script))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "fps":
                    if isinstance(node.args[1], ast.Constant) and node.args[1].value == 30:
                        pytest.fail("Architecture Violation (LED-048): probe_qc.py contains silent fallback .get('fps', 30)!")

    assert 'get("fps", 30)' not in content
    assert "get('fps', 30)" not in content


def test_guard_probe_qc_uses_build_render_input_authority():
    """
    Guard 3 (S17 Invariant):
    probe_qc.py imports and invokes build_render_input() directly.
    Does not assemble blueprint/brand/media_map manually.
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")

    assert "from scripts.core.render_input import" in content
    assert "build_render_input" in content
    assert "build_render_input(" in content


def test_guard_probe_qc_uses_derive_probe_frame_plan_authority():
    """
    Guard 4 (LED-047):
    scripts/core/probe_planner.py is the single authority for probe frame derivation.
    probe_qc.py delegates timing selection entirely to derive_probe_frame_plan().
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")

    assert "from scripts.core.probe_planner import" in content
    assert "derive_probe_frame_plan" in content
    assert "derive_probe_frame_plan(" in content


def test_guard_probe_qc_integrates_review_service():
    """
    Guard 5 (LED-050):
    probe_qc.py imports and invokes ReviewService.create_review_bundle to bind evidence.
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")

    assert "ReviewService.create_review_bundle" in content
    assert "require_contact_sheet=True" in content
