"""
tests/architecture/test_s17_architecture_guard.py — Architecture & Structural Guards for Package S17:
- Guard 1: scripts/core/render_input.py is the single authority exporting build_render_input.
- Guard 2: No script under scripts/ manually assembles render envelope props outside render_input.py.
- Guard 3: All four consumers (Local render, Docker render, Studio, Probe QC) use build_render_input.
- Guard 4: Docker render and Docker studio NEVER pass raw 05_blueprint.json as --props.
- Guard 5: ContractAuthorityMatrix records GovernedDomain.RENDER_INPUT with single canonical authority.
"""
import ast
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "scripts"
RENDER_INPUT_PY = SCRIPTS_DIR / "core" / "render_input.py"
RENDER_PROJECT_PY = SCRIPTS_DIR / "render_project.py"
OPEN_STUDIO_PY = SCRIPTS_DIR / "open_studio.py"
PROBE_QC_PY = SCRIPTS_DIR / "gates" / "probe_qc.py"


def test_guard_render_input_module_exists_and_exports_authority():
    """Guard 1: scripts/core/render_input.py must exist and export build_render_input."""
    assert RENDER_INPUT_PY.is_file(), "scripts/core/render_input.py does not exist!"
    from scripts.core.render_input import build_render_input, get_render_props_path
    assert callable(build_render_input)
    assert callable(get_render_props_path)


def test_guard_no_manual_render_props_assembly_outside_authority():
    """
    Guard 2: No python script under scripts/ (except scripts/core/render_input.py)
    may manually construct a dictionary combining 'blueprint', 'brand', and 'media_map'.
    """
    py_files = [
        f for f in SCRIPTS_DIR.rglob("*.py")
        if f.resolve() != RENDER_INPUT_PY.resolve()
        and "archive" not in f.parts
        and "tests" not in f.parts
    ]

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = set()
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.add(k.value)
                # Check for manual assembly of render props components
                combined_keys = {"blueprint", "brand", "media_map"}
                if combined_keys.issubset(keys):
                    pytest.fail(
                        f"Architecture Guard Violation in {py_file.relative_to(ROOT)}: "
                        f"Manual assembly of render payload dict with keys {keys}. "
                        f"MUST use scripts.core.render_input.build_render_input()!"
                    )


def test_guard_all_consumers_use_build_render_input():
    """
    Guard 3: scripts/render_project.py, scripts/open_studio.py, and scripts/gates/probe_qc.py
    MUST import and call build_render_input.
    """
    consumers = [RENDER_PROJECT_PY, OPEN_STUDIO_PY, PROBE_QC_PY]
    for script_path in consumers:
        assert script_path.is_file(), f"{script_path} does not exist"
        content = script_path.read_text(encoding="utf-8")
        assert "build_render_input" in content, (
            f"Architecture Guard Violation: {script_path.name} does not reference build_render_input!"
        )
        assert "from scripts.core.render_input import" in content or "import scripts.core.render_input" in content, (
            f"Architecture Guard Violation: {script_path.name} does not import scripts.core.render_input!"
        )


def test_guard_no_docker_raw_blueprint_props():
    """
    Guard 4: Docker execution paths in render_project.py and open_studio.py
    must never pass raw 05_blueprint.json as --props.
    """
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")
        assert not re.search(r'--props\s+[^"\']*05_blueprint\.json', content), (
            f"Architecture Guard Violation: {script_path.name} passes raw 05_blueprint.json to Remotion!"
        )
        assert re.search(r'--props.*render_props\.json', content), (
            f"Architecture Guard Violation: {script_path.name} must pass render_props.json in Docker command!"
        )


def test_guard_authority_matrix_declares_render_input():
    """Guard 5: ContractAuthorityMatrix GovernedDomain.RENDER_INPUT reflects build_render_input."""
    from scripts.core.authority_matrix import ContractAuthorityMatrix, GovernedDomain, RepresentationRole
    entry = ContractAuthorityMatrix.get_entry(GovernedDomain.RENDER_INPUT)
    assert entry is not None
    assert entry.canonical_authority == "scripts.core.render_input.build_render_input"
    assert entry.canonical_path == "scripts/core/render_input.py"
    canonical_reps = [r for r in entry.representations if r.role == RepresentationRole.CANONICAL]
    assert len(canonical_reps) == 1
    assert canonical_reps[0].path == "scripts/core/render_input.py"
