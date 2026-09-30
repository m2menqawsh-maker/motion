"""
tests/architecture/test_s19_architecture_guard.py — Architecture Guards for Package S19:
- Guard 1: scripts/gates/final_qc.py must load canonical Blueprint via scripts.core.blueprint_loader (LED-051).
- Guard 2: scripts/gates/final_qc.py must NOT contain runtime pip install (LED-056 / S19).
- Guard 3: scripts/gates/final_qc.py must invoke check_av_sync in execution path (LED-052).
- Guard 4: scripts/gates/final_qc.py must implement CHECK_FAILED_TO_EXECUTE semantics (LED-053).
- Guard 5: scripts/gates/final_qc.py must NOT contain SKIP_STRICT_QC bypass turning failure into exit 0 (LED-022).
- Guard 6: scripts/gates/final_qc.py must derive duration from scenes (max endFrame) (LED-051).
"""
import ast
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_final_qc_uses_canonical_blueprint_loader():
    """
    Guard 1 (LED-051):
    final_qc.py must import and use load_blueprint from scripts.core.blueprint_loader,
    never implementing parallel JSON parsing or reading raw meta.aspect_ratio/meta.duration_sec.
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(qc_script))

    imports_canonical_loader = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "scripts.core.blueprint_loader":
                for alias in node.names:
                    if alias.name == "load_blueprint":
                        imports_canonical_loader = True

    assert imports_canonical_loader, "Architecture Violation (LED-051): final_qc.py must import load_blueprint from scripts.core.blueprint_loader!"
    assert 'meta.get("aspect_ratio"' not in content, "final_qc.py must not read legacy meta.aspect_ratio"
    assert "meta.get('aspect_ratio'" not in content, "final_qc.py must not read legacy meta.aspect_ratio"
    assert 'meta.get("duration_sec"' not in content, "final_qc.py must not read legacy meta.duration_sec"
    assert "meta.get('duration_sec'" not in content, "final_qc.py must not read legacy meta.duration_sec"


def test_guard_final_qc_no_runtime_pip_install():
    """
    Guard 2:
    final_qc.py must not execute runtime pip install commands.
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    assert "pip" not in content or "pip install" not in content, (
        "Architecture Violation: final_qc.py must not run pip install at runtime!"
    )


def test_guard_final_qc_invokes_check_av_sync():
    """
    Guard 3 (LED-052):
    check_av_sync must be called within run_final_qc execution path.
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(qc_script))

    run_func = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "run_final_qc"), None)
    assert run_func is not None, "run_final_qc function must exist in final_qc.py"

    calls = [
        node.func.id for node in ast.walk(run_func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "check_av_sync" in calls, "Architecture Violation (LED-052): check_av_sync is not called in run_final_qc!"


def test_guard_final_qc_implements_check_failed_to_execute():
    """
    Guard 4 (LED-053):
    final_qc.py must implement CHECK_FAILED_TO_EXECUTE status semantics
    and treat critical execution failure as non-zero exit.
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    assert "CHECK_FAILED_TO_EXECUTE" in content, (
        "Architecture Violation (LED-053): CHECK_FAILED_TO_EXECUTE semantics missing from final_qc.py"
    )


def test_guard_final_qc_no_skip_strict_qc_bypass():
    """
    Guard 5 (LED-022 / S19):
    final_qc.py must not contain any bypass where hard failure or SKIP_STRICT_QC converts to sys.exit(0).
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    assert "SKIP_STRICT_QC" not in content, (
        "Architecture Violation: final_qc.py must not contain ambient SKIP_STRICT_QC bypass!"
    )


def test_guard_final_qc_derives_duration_from_scenes():
    """
    Guard 6 (LED-051):
    Expected duration must be derived from max(startFrame + durationFrames) / fps.
    """
    qc_script = ROOT / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    assert "max(s.startFrame + s.durationFrames" in content or "max(scene.startFrame + scene.durationFrames" in content, (
        "Architecture Violation (LED-051): final_qc.py must derive duration from max(startFrame + durationFrames)!"
    )
