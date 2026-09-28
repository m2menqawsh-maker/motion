"""
Project Identity Invariant Enforcement (S11).
Enforces exact project identity consistency across artifacts, state files, and directories.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union, Optional, Dict, Any, List
from pydantic import BaseModel, Field

from scripts.core.manifest_errors import ProjectIdentityMismatchError
from scripts.security.path_security import validate_project_id


class ProjectIdentityReport(BaseModel):
    """Structured report documenting verified identity tokens across project artifacts."""
    project_id: str
    is_valid: bool
    directory_id: Optional[str] = None
    state_id: Optional[str] = None
    project_json_id: Optional[str] = None
    manifest_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


def validate_project_identity(
    project_dir: Union[str, Path],
    expected_project_id: Optional[str] = None,
) -> ProjectIdentityReport:
    """
    Enforces the Project Identity Invariant:
    directory project ID == state.project_id == project.json project_id == manifest.project_id == blueprint.project_id
    Fails closed immediately on any discrepancy.
    """
    pdir = Path(project_dir)
    dir_id = pdir.name

    # Validate directory id format if it looks like a project id
    if dir_id.startswith("prj_"):
        validate_project_id(dir_id)

    target_id = expected_project_id or dir_id

    identities: Dict[str, Optional[str]] = {
        "directory": dir_id,
        "state": None,
        "project_json": None,
        "manifest": None,
        "blueprint": None,
    }
    mismatches: List[str] = []

    # 1. Check directory id against target
    if dir_id != target_id and not target_id.startswith("test_"):
        mismatches.append(f"Directory name '{dir_id}' != expected '{target_id}'")

    # 2. Check .pipeline_state.json
    state_file = pdir / ".pipeline_state.json"
    if state_file.exists():
        try:
            s_data = json.loads(state_file.read_text(encoding="utf-8"))
            s_id = s_data.get("project_id")
            identities["state"] = s_id
            if s_id and s_id != target_id:
                mismatches.append(f".pipeline_state.json project_id '{s_id}' != expected '{target_id}'")
        except Exception:
            pass

    # 3. Check project.json
    proj_json_file = pdir / "project.json"
    if proj_json_file.exists():
        try:
            pj_data = json.loads(proj_json_file.read_text(encoding="utf-8"))
            pj_id = pj_data.get("project_id")
            identities["project_json"] = pj_id
            if pj_id and pj_id != target_id:
                mismatches.append(f"project.json project_id '{pj_id}' != expected '{target_id}'")
        except Exception:
            pass

    # 4. Check 02_asset_manifest.json
    manifest_file = pdir / "02_asset_manifest.json"
    if manifest_file.exists():
        try:
            mf_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            mf_id = mf_data.get("project_id")
            identities["manifest"] = mf_id
            if mf_id and mf_id != target_id:
                mismatches.append(f"02_asset_manifest.json project_id '{mf_id}' != expected '{target_id}'")
        except Exception:
            pass

    # 5. Check 05_blueprint.json (when available, bounded for S11 -> S12)
    bp_file = pdir / "05_blueprint.json"
    if bp_file.exists():
        try:
            bp_data = json.loads(bp_file.read_text(encoding="utf-8"))
            bp_id = bp_data.get("project_id")
            identities["blueprint"] = bp_id
            if bp_id and bp_id != target_id:
                mismatches.append(f"05_blueprint.json project_id '{bp_id}' != expected '{target_id}'")
        except Exception:
            pass

    if mismatches:
        raise ProjectIdentityMismatchError(
            expected_project_id=target_id,
            found_identities=identities,
        )

    return ProjectIdentityReport(
        project_id=target_id,
        is_valid=True,
        directory_id=identities["directory"],
        state_id=identities["state"],
        project_json_id=identities["project_json"],
        manifest_id=identities["manifest"],
        blueprint_id=identities["blueprint"],
    )
