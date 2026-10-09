import sys
from scripts.security.path_security import validate_project_id
from scripts.security.security import safe_subprocess
from pathlib import Path


import shutil
from typing import Optional


def create_project(
    name: str,
    language: str,
    workspace_id: Optional[str] = None,
    created_by: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    # Use sys.executable to prevent Python interpreter drift (DISC-004)
    cmd = [
        sys.executable, "scripts/scaffold_project.py",
        "--name", name,
        "--language", language
    ]
    if workspace_id:
        cmd.extend(["--workspace-id", workspace_id])
    if created_by:
        cmd.extend(["--created-by", created_by])
    if project_id:
        validate_project_id(project_id)
        cmd.extend(["--project-id", project_id])

    result = safe_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        if project_id:
            proj_dir = Path(f"projects/{project_id}")
            if proj_dir.exists() and proj_dir.name == project_id and project_id.startswith("prj_"):
                shutil.rmtree(proj_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to create project: {result.stderr}")
    return result.stdout.strip()
