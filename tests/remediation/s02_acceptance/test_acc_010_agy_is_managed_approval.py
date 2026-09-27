"""S02 Acceptance Contract 010: AGY_IS_MANAGED Must Not Bypass Studio Approval in Production.

Vulnerability: LED-019 / Environment Variables Policy
Contract:
In production, having AGY_IS_MANAGED=1 must NEVER allow rendering a project that
lacks explicit .studio_approved review sign-off. The approval requirement must be strictly enforced.
"""

import pytest
import os
import subprocess
import sys
import shutil
import json
from pathlib import Path


@pytest.mark.acceptance
def test_agy_is_managed_must_not_bypass_studio_approved_in_production(tmp_path):
    """Rendering without .studio_approved must be blocked immediately even if AGY_IS_MANAGED=1 is set."""
    project_id = "test_acc_010_proj"
    proj_dir = Path.cwd() / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create minimal project WITHOUT .studio_approved
        (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
        (proj_dir / "project.json").write_text(json.dumps({"fps": 30, "title": "Test"}), encoding="utf-8")
        (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
        
        # Ensure .studio_approved does NOT exist
        studio_approved_file = proj_dir / ".studio_approved"
        if studio_approved_file.exists():
            studio_approved_file.unlink()

        # Set environment to PRODUCTION with AGY_IS_MANAGED=1
        env = os.environ.copy()
        env["MOTION_ENV"] = "production"
        env["AGY_IS_MANAGED"] = "1"
        env["AGY_RUN_ID"] = "test-run-123"

        script_path = Path.cwd() / "scripts" / "render_project.py"
        proc = subprocess.run(
            [sys.executable, str(script_path), project_id],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )

        # In current main (render_project.py line 81):
        # 'if not is_approved and not is_managed:' skips checking approval and jumps directly
        # to rendering: "🎥 جاري الرندر (محلي)...".
        # Expected in S02:
        # 1. Must NOT proceed to render
        # 2. Must report project not approved
        assert "🎥 جاري الرندر" not in proc.stdout, (
            "Security Defect (LED-019): render_project bypassed the .studio_approved requirement "
            "and attempted video render because AGY_IS_MANAGED=1 was present in production."
        )
        assert "Project is not approved (gate_3) for rendering" in proc.stdout or proc.returncode != 0
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
