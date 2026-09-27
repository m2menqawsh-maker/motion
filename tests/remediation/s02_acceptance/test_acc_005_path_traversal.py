"""S02 Acceptance Contract 005: Path Traversal Confinement.

Vulnerability: ASSET-009 / Boundary E
Contract:
Asset manifest processing and materialization must reject asset_ids containing
path traversal sequences ('..') or leading slashes. Processing must fail with a validation
error and NEVER copy or write files outside the project's designated media directory.
"""

import pytest
import json
import subprocess
import sys
import shutil
from pathlib import Path


@pytest.mark.acceptance
def test_materializer_must_reject_path_traversal_asset_ids(tmp_path):
    """materialize_project.py must reject '../escape' asset_id before writing files."""
    project_id = "test_acc_005_proj"
    proj_dir = Path.cwd() / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir(parents=True, exist_ok=True)
    secret_file = outside_dir / "secret.txt"
    secret_file.write_text("CONFIDENTIAL", encoding="utf-8")
    
    pub_projects = Path.cwd() / "remotion-app" / "public" / "projects" / project_id
    escaped_file = pub_projects / "traversal_escape.txt"
    
    try:
        manifest = {
            "project_id": project_id,
            "assets": [
                {
                    "asset_id": "../traversal_escape",
                    "type": "image",
                    "path": str(secret_file.resolve())
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
        
        # Expected S02 behavior:
        # 1. Escaped file must not exist
        # 2. Materializer must fail with a non-zero exit code due to invalid path traversal
        assert proc.returncode != 0, (
            "Security Failure: materialize_project succeeded despite path traversal sequence in asset_id."
        )
        assert not escaped_file.exists(), (
            f"Security Failure: File was materialized outside confined media boundary at {escaped_file}."
        )
    finally:
        if escaped_file.exists():
            escaped_file.unlink()
        if pub_projects.exists():
            shutil.rmtree(pub_projects)
        if proj_dir.exists():
            shutil.rmtree(proj_dir)
