"""S02 Acceptance Contract 006: Symlink Directory Escape Prevention.

Vulnerability: SEC-001 / Filesystem Confinement
Contract:
Asset processing and materialization must reject files that resolve through symlinks
to targets outside the allowed workspace/project boundary. Symlink dereferencing
must not exfiltrate external files into the public media directory.
"""

import pytest
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path


@pytest.mark.acceptance
def test_materializer_must_reject_symlink_escaping_workspace(tmp_path):
    """materialize_project.py must reject symlink pointing outside the workspace."""
    project_id = "test_acc_006_proj"
    proj_dir = Path.cwd() / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    outside_dir = tmp_path / "outside_host"
    outside_dir.mkdir(parents=True, exist_ok=True)
    sensitive_file = outside_dir / "host_secret.txt"
    sensitive_file.write_text("SUPER_SECRET_HOST_DATA", encoding="utf-8")

    symlink_asset = proj_dir / "assets" / "symlink_leak.txt"
    symlink_asset.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(sensitive_file, symlink_asset)
    except OSError:
        pytest.skip("Symlinks not supported in this test environment.")

    pub_media = Path.cwd() / "remotion-app" / "public" / "projects" / project_id / "media"
    copied_leak = pub_media / "symlink_leak.txt"

    try:
        manifest = {
            "project_id": project_id,
            "assets": [
                {
                    "asset_id": "symlink_leak",
                    "type": "text",
                    "path": str(symlink_asset.resolve())
                }
            ]
        }
        (proj_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
        (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")

        script_path = Path.cwd() / "scripts" / "generators" / "materialize_project.py"
        proc = subprocess.run(
            [sys.executable, str(script_path), str(proj_dir)],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        # In current main, materialize_project follows symlinks and copies sensitive_file to pub_media!
        # Expected in S02:
        # 1. materialize_project must fail (returncode != 0)
        # 2. copied_leak must NOT exist in pub_media
        assert proc.returncode != 0, (
            "Security Failure: materialize_project succeeded and processed a symlink pointing outside the workspace."
        )
        assert not copied_leak.exists(), (
            f"Security Failure: Sensitive external file was copied to public media directory via symlink escape: {copied_leak}"
        )
    finally:
        if copied_leak.exists():
            copied_leak.unlink()
        if pub_media.exists():
            shutil.rmtree(pub_media)
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
