"""S02 Acceptance Contract 009: SKIP_STRICT_QC Must Not Bypass Failures in Production.

Vulnerability: LED-022 / Environment Variables Policy
Contract:
In production, the presence of SKIP_STRICT_QC=1 must NEVER convert a quality gate
failure into a success. Hard QC failures must block the pipeline regardless of environment flags.
"""

import pytest
import os
import subprocess
import sys
import shutil
import json
from pathlib import Path


@pytest.mark.acceptance
def test_skip_strict_qc_must_not_bypass_failure_in_production(tmp_path):
    """In production, Final QC failure must exit non-zero even if SKIP_STRICT_QC=1 is set."""
    project_id = "test_acc_009_proj"
    proj_dir = Path.cwd() / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create minimal failing project setup
        (proj_dir / ".studio_approved").touch()
        # Create an empty or corrupt out.mp4 so probe fails
        (proj_dir / "out.mp4").write_bytes(b"INVALID_MP4_HEADER")
        (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
        (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")

        # Set environment to PRODUCTION with SKIP_STRICT_QC=1
        env = os.environ.copy()
        env["MOTION_ENV"] = "production"
        env["SKIP_STRICT_QC"] = "1"

        script_path = Path.cwd() / "scripts" / "gates" / "final_qc.py"
        proc = subprocess.run(
            [sys.executable, str(script_path), project_id],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )

        # Expected in S02:
        # Must fail with non-zero exit code because out.mp4 is invalid
        # In current main, SKIP_STRICT_QC=1 prints warning and returns 0!
        assert proc.returncode != 0, (
            "Security / QC Violation: Final QC exited with 0 (success) despite hard failure, "
            "because SKIP_STRICT_QC=1 bypassed the gate in production."
        )
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
