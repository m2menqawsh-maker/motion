import os
import json
from pathlib import Path
from scripts.migrate_legacy_projects import migrate_project

def test_migrate_manifest_to_asset_manifest(tmp_path):
    project_dir = tmp_path / "prj_test123"
    project_dir.mkdir()
    
    old_manifest = project_dir / "manifest.json"
    old_manifest.write_text(json.dumps({"project_id": "prj_test123", "assets": []}))
    
    migrated = migrate_project(project_dir)
    
    assert migrated is True
    assert not old_manifest.exists()
    assert (project_dir / "02_asset_manifest.json").exists()

def test_migrate_blueprint(tmp_path):
    project_dir = tmp_path / "prj_test123"
    project_dir.mkdir()
    
    old_bp = project_dir / "blueprint.json"
    old_bp.write_text(json.dumps({"project_id": "prj_test123", "scenes": []}))
    
    migrated = migrate_project(project_dir)
    
    assert migrated is True
    assert not old_bp.exists()
    assert (project_dir / "05_blueprint.json").exists()

def test_migrate_state_conflict_and_idempotency(tmp_path):
    project_dir = tmp_path / "prj_test123"
    project_dir.mkdir()
    
    # Setup legacy files
    old_state = project_dir / "state.json"
    old_state.write_text(json.dumps({"status": "failed", "last_error": "Timeout"}))
    
    old_manifest = project_dir / "manifest.json"
    old_manifest.write_text(json.dumps({}))
    
    new_manifest = project_dir / "02_asset_manifest.json"
    new_manifest.write_text(json.dumps({"canonical": True}))
    
    # Run migration
    migrated = migrate_project(project_dir)
    assert migrated is True
    
    # Check conflict handling (manifest.json -> manifest.json.conflict)
    assert not old_manifest.exists()
    assert (project_dir / "manifest.json.conflict").exists()
    
    # Check state migration
    assert not old_state.exists()
    assert (project_dir / "state.json.deprecated").exists()
    
    state_path = project_dir / ".pipeline_state.json"
    assert state_path.exists()
    
    state_data = json.loads(state_path.read_text())
    assert state_data["lifecycle_state"] == "FAILED"
    assert state_data["schema_version"] == 1
    assert len(state_data["structured_errors"]) == 1
    assert state_data["structured_errors"][0]["message"] == "Timeout"

    # Idempotency check: run again
    migrated_again = migrate_project(project_dir)
    # Should be False if no new legacy files were found to migrate (except pipeline_state which is canonical)
    # Actually wait, migrate_project writes pipeline_state if state_migrated OR not new_state_path.exists().
    # Since it exists and no state_migrated, it will return False.
    assert migrated_again is False
