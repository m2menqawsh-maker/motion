"""
Project Identity Matrix Verification Suite (S11 Closure).
Verifies each individual identity boundary:
1. directory project_id != manifest.project_id -> hard failure.
2. project.json.project_id != manifest.project_id -> hard failure.
3. state.project_id != manifest.project_id -> hard failure.
4. blueprint.project_id != manifest.project_id -> hard failure.
5. All matching -> passes.
6. Failure occurs before any side effects.
"""

import json
import pytest
from pathlib import Path
from scripts.core.project_identity import validate_project_identity
from scripts.core.manifest_errors import ProjectIdentityMismatchError


def create_baseline_project(tmp_path: Path, project_id: str) -> Path:
    pdir = tmp_path / "projects" / project_id
    pdir.mkdir(parents=True)
    
    (pdir / "project.json").write_text(
        json.dumps({"project_id": project_id, "name": "TestProj"}),
        encoding="utf-8"
    )
    (pdir / ".pipeline_state.json").write_text(
        json.dumps({"project_id": project_id, "lifecycle_state": "DRAFT"}),
        encoding="utf-8"
    )
    (pdir / "02_asset_manifest.json").write_text(
        json.dumps({
            "manifest_version": "2.0.0",
            "project_id": project_id,
            "created_at": "2026-09-28T12:00:00Z",
            "assets": []
        }),
        encoding="utf-8"
    )
    (pdir / "05_blueprint.json").write_text(
        json.dumps({"project_id": project_id, "scenes": []}),
        encoding="utf-8"
    )
    return pdir


def test_identity_all_match_passes(tmp_path):
    """Happy path: All artifacts and directory share the identical project_id."""
    pid = "prj_canonical_match"
    pdir = create_baseline_project(tmp_path, pid)
    
    report = validate_project_identity(pdir)
    assert report.is_valid is True
    assert report.project_id == pid
    assert report.directory_id == pid
    assert report.state_id == pid
    assert report.project_json_id == pid
    assert report.manifest_id == pid
    assert report.blueprint_id == pid


def test_identity_directory_mismatch_fails(tmp_path):
    """Boundary 1: directory project_id != manifest.project_id -> hard failure."""
    real_pid = "prj_real_dir"
    pdir = create_baseline_project(tmp_path, real_pid)
    
    # Corrupt manifest to a different project_id
    manifest_file = pdir / "02_asset_manifest.json"
    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    m_data["project_id"] = "prj_mismatch_manifest"
    manifest_file.write_text(json.dumps(m_data), encoding="utf-8")
    
    with pytest.raises(ProjectIdentityMismatchError) as exc_info:
        validate_project_identity(pdir)
    
    err = exc_info.value
    assert "prj_mismatch_manifest" in str(err)
    assert real_pid in str(err)


def test_identity_project_json_mismatch_fails(tmp_path):
    """Boundary 2: project.json.project_id != manifest.project_id -> hard failure."""
    pid = "prj_pjson_test"
    pdir = create_baseline_project(tmp_path, pid)
    
    # Corrupt project.json
    (pdir / "project.json").write_text(
        json.dumps({"project_id": "prj_impostor_pjson"}),
        encoding="utf-8"
    )
    
    with pytest.raises(ProjectIdentityMismatchError) as exc_info:
        validate_project_identity(pdir)
    
    err = exc_info.value
    assert "prj_impostor_pjson" in str(err)


def test_identity_state_mismatch_fails(tmp_path):
    """Boundary 3: state.project_id != manifest.project_id -> hard failure."""
    pid = "prj_state_test"
    pdir = create_baseline_project(tmp_path, pid)
    
    # Corrupt .pipeline_state.json
    (pdir / ".pipeline_state.json").write_text(
        json.dumps({"project_id": "prj_impostor_state"}),
        encoding="utf-8"
    )
    
    with pytest.raises(ProjectIdentityMismatchError) as exc_info:
        validate_project_identity(pdir)
    
    err = exc_info.value
    assert "prj_impostor_state" in str(err)


def test_identity_blueprint_mismatch_fails(tmp_path):
    """Boundary 4: blueprint.project_id != manifest.project_id -> hard failure."""
    pid = "prj_bp_test"
    pdir = create_baseline_project(tmp_path, pid)
    
    # Corrupt 05_blueprint.json
    (pdir / "05_blueprint.json").write_text(
        json.dumps({"project_id": "prj_impostor_bp", "scenes": []}),
        encoding="utf-8"
    )
    
    with pytest.raises(ProjectIdentityMismatchError) as exc_info:
        validate_project_identity(pdir)
    
    err = exc_info.value
    assert "prj_impostor_bp" in str(err)


def test_identity_failure_occurs_before_side_effects(tmp_path):
    """Boundary 5: Project identity mismatch causes ZERO file modifications or creations."""
    pid = "prj_side_effect_check"
    pdir = create_baseline_project(tmp_path, pid)
    
    # Corrupt manifest
    manifest_file = pdir / "02_asset_manifest.json"
    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    m_data["project_id"] = "prj_different_id"
    manifest_file.write_text(json.dumps(m_data), encoding="utf-8")
    
    files_before = {f.name: f.stat().st_mtime for f in pdir.iterdir()}
    
    with pytest.raises(ProjectIdentityMismatchError):
        validate_project_identity(pdir)
        
    files_after = {f.name: f.stat().st_mtime for f in pdir.iterdir()}
    assert files_before == files_after, "Files were modified or created upon identity check failure!"
