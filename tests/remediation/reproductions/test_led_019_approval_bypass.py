import pytest
import os
from pathlib import Path

def test_led_019_approval_bypass_via_agy_is_managed(tmp_path):
    """
    Finding: LED-019 (PARTIALLY CLOSED in S02 - AGY_IS_MANAGED bypass removed; Hash binding in S09)
    Evolution: Evolved from S00 Expected-RED reproduction to S02 GREEN regression proof.
    Expected correct behavior: scripts/render_project.py must enforce human approval (gate_3)
    strictly. Environment variables like AGY_IS_MANAGED=1 MUST NOT bypass human approval.
    Post-S02 behavior: Bypass condition removed; approval check is unconditional.
    """
    render_script = Path.cwd() / "scripts" / "render_project.py"
    content = render_script.read_text(encoding="utf-8")
    
    # Inspecting the exact gate check in render_project.py
    # Lines 81: "if not is_approved and not is_managed:"
    has_bypass_condition = "if not is_approved and not is_managed:" in content
    
    # Assertion proving the defect:
    # Correct behavior: is_managed MUST NOT be used to bypass the is_approved requirement
    # Current behavior on main: has_bypass_condition is True
    assert not has_bypass_condition, (
        "DEFECT PROVEN (LED-019): scripts/render_project.py contains bypass condition "
        "'if not is_approved and not is_managed:', allowing any caller setting AGY_IS_MANAGED=1 "
        "to render without human approval (.studio_approved)!"
    )
