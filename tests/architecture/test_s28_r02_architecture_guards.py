"""
tests/architecture/test_s28_r02_architecture_guards.py
Pytest Architecture Enforcement for S28-R02 Canonical Video Contract Purity.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_directory_has_zero_react_and_remotion_imports():
    """Verifies that all TypeScript files in contracts/ have ZERO imports from react or remotion."""
    contracts_dir = REPO_ROOT / "contracts"
    assert contracts_dir.is_dir(), "contracts directory must exist"

    ts_files = list(contracts_dir.glob("*.ts"))
    assert len(ts_files) > 0, "contracts directory must contain TypeScript contract files"

    import_pattern = re.compile(
        r"""(?:import\s+(?:[\w*\s{},]*\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))"""
    )

    violations = []
    for f in ts_files:
        content = f.read_text(encoding="utf-8")
        for match in import_pattern.finditer(content):
            specifier = match.group(1) or match.group(2)
            if not specifier:
                continue
            if (
                specifier == "react"
                or specifier == "react-dom"
                or specifier == "remotion"
                or specifier.startswith("@remotion/")
            ):
                violations.append(f"{f.name} imports '{specifier}'")
            if specifier.endswith(".tsx") or "engine-bridge" in specifier:
                violations.append(f"{f.name} imports runtime component '{specifier}'")

    assert not violations, f"Architecture violations detected in contracts/:\n" + "\n".join(violations)


def test_ai_planning_layer_has_zero_remotion_imports():
    """Verifies that ai/planning/ modules are 100% engine-neutral and import zero Remotion."""
    ai_planning_dir = REPO_ROOT / "ai" / "planning"
    if not ai_planning_dir.is_dir():
        pytest.skip("ai/planning directory not found")

    py_files = list(ai_planning_dir.glob("**/*.py"))
    assert len(py_files) > 0

    violations = []
    for f in py_files:
        content = f.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if "remotion" in stripped:
                    violations.append(f"{f.name}:{line_no} -> {stripped}")

    assert not violations, f"Remotion imports found in ai/planning/:\n" + "\n".join(violations)


def test_core_normalizer_exists_and_is_engine_neutral():
    """Verifies contracts/normalization.ts exists and has zero renderer imports."""
    norm_file = REPO_ROOT / "contracts" / "normalization.ts"
    assert norm_file.is_file(), "contracts/normalization.ts must exist"

    content = norm_file.read_text(encoding="utf-8")
    assert "from \"remotion\"" not in content
    assert "from '@remotion" not in content
    assert "from \"@remotion" not in content
    assert "from \"react\"" not in content
    assert "from 'react'" not in content


def test_canonical_video_entrypoint_exists():
    """Verifies contracts/canonical-video.ts exists and provides parse and normalize APIs."""
    cv_file = REPO_ROOT / "contracts" / "canonical-video.ts"
    assert cv_file.is_file(), "contracts/canonical-video.ts must exist"

    content = cv_file.read_text(encoding="utf-8")
    assert "export function parseCanonicalVideo" in content
    assert "export function validateCanonicalVideo" in content
    assert "normalizeCanonicalVideo" in content


def test_r03_canonical_modules_exist_and_are_engine_neutral():
    """Verifies R03 timeline, layers, keyframes, evaluator exist with zero renderer imports."""
    contracts_dir = REPO_ROOT / "contracts"
    r03_modules = ["timeline.ts", "layers.ts", "keyframes.ts", "evaluator.ts"]

    for mod in r03_modules:
        mod_path = contracts_dir / mod
        assert mod_path.is_file(), f"{mod} must exist in contracts/"
        content = mod_path.read_text(encoding="utf-8")
        assert "from \"remotion\"" not in content
        assert "from '@remotion" not in content
        assert "from \"react\"" not in content
        assert "from 'react'" not in content


def test_r03_evaluator_has_zero_dom_and_wall_clock_dependencies():
    """Verifies evaluator has zero wall-clock and zero browser DOM dependencies."""
    eval_file = REPO_ROOT / "contracts" / "evaluator.ts"
    content = eval_file.read_text(encoding="utf-8")
    assert "Date.now()" not in content
    assert "performance.now()" not in content
    assert "window" not in content
    assert "document" not in content

