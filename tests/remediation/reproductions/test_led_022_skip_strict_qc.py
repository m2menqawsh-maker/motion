import pytest
from pathlib import Path

def test_led_022_skip_strict_qc_bypass():
    """
    Finding: LED-022 / LED-074
    Expected correct behavior: In production gates, QC failures must be definitive (non-zero exit).
    Ambient environment variables like SKIP_STRICT_QC must not turn hard validation failures
    into success (exit code 0).
    Actual behavior on current main: scripts/gates/final_qc.py checks:
        if has_fail and not os.environ.get("SKIP_STRICT_QC"):
            sys.exit(1)
        elif has_fail:
            print("⚠️ Final QC فشل ولكن تم تخطيه بسبب SKIP_STRICT_QC.")
            sys.exit(0)
    """
    qc_script = Path.cwd() / "scripts" / "gates" / "final_qc.py"
    content = qc_script.read_text(encoding="utf-8")
    
    has_skip_bypass = 'elif has_fail:' in content and 'SKIP_STRICT_QC' in content and 'sys.exit(0)' in content
    
    # Assertion proving the defect:
    # Correct behavior: Hard QC failures must never exit with code 0 based on ambient env vars.
    # Current behavior on main: has_skip_bypass is True.
    assert not has_skip_bypass, (
        "DEFECT PROVEN (LED-022): scripts/gates/final_qc.py converts hard failures to exit(0) "
        "when SKIP_STRICT_QC is set, completely defeating the Quality Control gate."
    )
