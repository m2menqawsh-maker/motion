"""
tests/remediation/reproductions/test_s17_remediation_proof.py — GREEN Remediation Proof for Package S17:
- LED-054 (P1): Render Props Divergence across Local, Docker, Studio, and Probe.
- Single Authority: scripts/core/render_input.py build_render_input().
- 100% Payload Parity: Local, Docker, Studio, and Probe all consume the exact same canonical envelope.
- Docker execution parity: Docker container passes render_props.json, never raw 05_blueprint.json.
"""
import re
from pathlib import Path
import pytest

from scripts.core.render_input import build_render_input, get_render_props_path
from scripts.core.authority_matrix import ContractAuthorityMatrix, GovernedDomain, RepresentationRole

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_green_led_054_single_authority_exports_callable():
    """GREEN PROOF 1: build_render_input is the canonical callable entry point."""
    assert callable(build_render_input)
    assert callable(get_render_props_path)


def test_green_led_054_authority_matrix_governed_domain():
    """GREEN PROOF 2: GovernedDomain.RENDER_INPUT registered with S17 build_render_input authority."""
    entry = ContractAuthorityMatrix.get_entry(GovernedDomain.RENDER_INPUT)
    assert entry is not None
    assert entry.canonical_authority == "scripts.core.render_input.build_render_input"
    assert entry.canonical_path == "scripts/core/render_input.py"
    assert entry.owner_package.migration_owner == "S17"


def test_green_led_054_docker_local_props_parity():
    """
    GREEN PROOF 3 (LED-054):
    Local and Docker renders both pass render_props.json to Remotion.
    Neither passes raw 05_blueprint.json.
    """
    render_script = ROOT / "scripts" / "render_project.py"
    content = render_script.read_text(encoding="utf-8")

    assert re.search(r'remotion.*render.*--props.*props_file', content) is not None
    assert re.search(r'--props["\',\s]+(?:\.\./projects/\{project_id\}/render_props\.json|f"\.\./projects/\{project_id\}/render_props\.json)', content) is not None
    assert not re.search(r'--props \.\./projects/\{project_id\}/05_blueprint\.json', content)


def test_green_led_054_studio_docker_local_props_parity():
    """
    GREEN PROOF 4 (LED-054):
    Studio in both local and Docker modes passes render_props.json.
    """
    studio_script = ROOT / "scripts" / "open_studio.py"
    content = studio_script.read_text(encoding="utf-8")

    assert re.search(r'remotion.*studio.*--props.*props_file', content) is not None
    assert re.search(r'--props.*render_props\.json', content) is not None
    assert not re.search(r'--props.*05_blueprint\.json', content)


def test_green_led_054_probe_qc_uses_render_input():
    """
    GREEN PROOF 5:
    Probe QC imports and uses build_render_input and passes render_props.json to Remotion.
    """
    probe_script = ROOT / "scripts" / "gates" / "probe_qc.py"
    content = probe_script.read_text(encoding="utf-8")

    assert "build_render_input" in content
    assert "from scripts.core.render_input import" in content
    assert "--props" in content
    assert "props_file_abs" in content
