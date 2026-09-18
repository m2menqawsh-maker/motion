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

