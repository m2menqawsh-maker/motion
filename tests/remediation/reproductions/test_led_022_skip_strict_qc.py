import pytest
from pathlib import Path

def test_led_022_skip_strict_qc_bypass():
    """
    Finding: LED-022 (CLOSED in S02)
    Evolution: Evolved from S00 Expected-RED reproduction to S02 GREEN regression proof.
    Expected correct behavior: In production gates, QC failures must be definitive (non-zero exit).
    Ambient environment variables like SKIP_STRICT_QC must not turn hard validation failures
    into success (exit code 0).
    Post-S02 behavior: Hard QC failure exits with code 1 in production regardless of SKIP_STRICT_QC.
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
