import pytest
import json
from pathlib import Path
from scripts.core.pipeline import UnifiedPipeline
from scripts.core.gates import GateViolation

def setup_mock_project(tmp_path: Path, project_id: str = "test_proj"):
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)
    
    # Create valid plan
    (project_dir / "master_plan.md").write_text("# Plan")
    
    # Create valid blueprint
    valid_bp = {
        "project_id": project_id,
        "version": "1.0",
        "fps": 30,
        "meta": {
            "title": "Test",
            "motion_personality": "Cinematic"
        },
        "scenes": [
            {
                "scene_id": "scene_1",
                "template": "TestTemplate",
                "startFrame": 0,
                "durationFrames": 400,
                "layout": {
                    "layer": 1,
                    "coverage_pct": 50
                },
                "content": {}
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(valid_bp))
    
    return project_dir, project_id

def test_pipeline_approval_invalidation(tmp_path: Path, monkeypatch):
    # Setup mock workspace
    monkeypatch.chdir(tmp_path)
    # Copy real schema to avoid bypass
    Path("schemas").mkdir()
    real_schema = Path(__file__).parent.parent / "schemas" / "blueprint.schema.json"
    Path("schemas/blueprint.schema.json").write_text(real_schema.read_text(encoding="utf-8"), encoding="utf-8")
    
    project_dir, project_id = setup_mock_project(tmp_path)
    
    pipeline = UnifiedPipeline(project_id)
    
    # 1. Prep and Materialize
    prep_info = pipeline.prep_and_materialize()
    assert "hash" in prep_info
    
    # 2. Approve
    pipeline.approve()
    assert (project_dir / ".studio_approved").exists()
    
    # 3. Modify Project (Simulate changing a file after approval)
    bp = json.loads((project_dir / "05_blueprint.json").read_text())
    bp["scenes"][0]["layout"]["coverage_pct"] = 99
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp))
    
    # 4. Render should fail due to hash mismatch
    with pytest.raises(GateViolation) as excinfo:
        pipeline.render()
    
    assert excinfo.value.rule == "APPROVAL_INVALIDATED"
    assert not (project_dir / ".studio_approved").exists() # File is deleted upon invalidation

def test_api_blueprint_reject_invalid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_dir, project_id = setup_mock_project(tmp_path)
    
    # Write invalid JSON
    (project_dir / "05_blueprint.json").write_text("{invalid")
    
    pipeline = UnifiedPipeline(project_id)
    with pytest.raises(GateViolation) as excinfo:
        pipeline.prep_and_materialize()
        
    assert excinfo.value.rule == "BLUEPRINT_INVALID_JSON"

def test_v2_features_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Copy real schema to avoid bypass
    Path("schemas").mkdir()
    real_schema = Path(__file__).parent.parent / "schemas" / "blueprint.schema.json"
    Path("schemas/blueprint.schema.json").write_text(real_schema.read_text(encoding="utf-8"), encoding="utf-8")
    
    project_dir, project_id = setup_mock_project(tmp_path)
    
    # Modify BP to violate Layer bounds
    bp = json.loads((project_dir / "05_blueprint.json").read_text())
    bp["scenes"][0]["layout"]["layer"] = 10
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp))
    
    pipeline = UnifiedPipeline(project_id)
    with pytest.raises(GateViolation) as excinfo:
        pipeline.prep_and_materialize()
        
    assert excinfo.value.rule == "LAYER_VIOLATION"
