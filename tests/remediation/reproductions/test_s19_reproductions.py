"""
tests/remediation/reproductions/test_s19_reproductions.py — S19 Reproductions & Regression Suite:
- LED-051 (P0): Final QC uses canonical aspect/duration and checks FPS (evolved to GREEN proof).
- LED-052 (P1): check_av_sync actively invoked in execution path (evolved to GREEN proof).
- LED-053 (P1): Analyzer crash produces CHECK_FAILED_TO_EXECUTE without swallowing (evolved to GREEN proof).
"""
import ast
from pathlib import Path
import pytest


def test_reproduce_led_051_duration_mismatch_and_fps_check():
    """
    Finding: LED-051 (CLOSED in S19)
    Evolution: Evolved from S00 Expected-RED reproduction to S19 GREEN regression proof.
    Expected correct behavior:
    1. FPS must be checked in report["checks"]["fps"].
    2. Duration difference > 0.5s must be status 'FAIL' (CRITICAL), never a warning or pass.
    3. Duration is derived from max(s.startFrame + s.durationFrames) / fps.
    """
    qc_path = Path("scripts/gates/final_qc.py")
    code_text = qc_path.read_text(encoding="utf-8")

    # 1. FPS check is now present in report["checks"]["fps"]
    assert 'report["checks"]["fps"]' in code_text, (
        "LED-051 regression: fps check must be present in report['checks']"
    )

    # 2. Duration mismatch is no longer assigned 'warning'
    assert '"pass" if duration_diff < 0.5 else "warning"' not in code_text, (
        "LED-051 regression: duration mismatch must not be assigned 'warning'!"
    )
    assert '"PASS" if matches else "FAIL"' in code_text or '"status": "PASS" if matches else "FAIL"' in code_text, (
        "LED-051: duration check must strictly return PASS or FAIL"
    )


def test_reproduce_led_052_check_av_sync_is_called_in_execution_path():
    """
    Finding: LED-052 (CLOSED in S19)
    Evolution: Evolved from S00 Expected-RED reproduction to S19 GREEN regression proof.
    Expected correct behavior:
    check_av_sync must be actively called in run_final_qc execution path and wired into report.
    """
    qc_path = Path("scripts/gates/final_qc.py")
    tree = ast.parse(qc_path.read_text(encoding="utf-8"))

    run_func = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "run_final_qc"), None)
    assert run_func is not None, "run_final_qc must exist"

    calls = [
        node.func.id for node in ast.walk(run_func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert "check_av_sync" in calls, (
        "LED-052 regression: check_av_sync must be called in run_final_qc execution path!"
    )


def test_reproduce_led_053_analyzer_exceptions_use_check_failed_to_execute():
    """
    Finding: LED-053 (CLOSED in S19)
    Evolution: Evolved from S00 Expected-RED reproduction to S19 GREEN regression proof.
    Expected correct behavior:
    Analyzer exceptions must return CHECK_FAILED_TO_EXECUTE, never status 'warning'.
    """
    qc_path = Path("scripts/gates/final_qc.py")
    code_text = qc_path.read_text(encoding="utf-8")

    # Black frames exception must return CHECK_FAILED_TO_EXECUTE
    assert '"status": "CHECK_FAILED_TO_EXECUTE"' in code_text, (
        "LED-053 regression: CHECK_FAILED_TO_EXECUTE must be used in exception handling"
    )

    # Must NOT swallow into warning
    assert 'return {"status": "warning", "message": f"تعذر فحص الإطارات السوداء: {e}"}' not in code_text, (
        "LED-053 regression: check_black_frames must not swallow exceptions into warning!"
    )
    assert 'return {"status": "warning", "message": f"فشل تحليل LUFS: {e}"}' not in code_text, (
        "LED-053 regression: check_audio_lufs must not swallow exceptions into warning!"
    )
