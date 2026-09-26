from fastapi.testclient import TestClient
from api.main import app
import pytest
from pathlib import Path

client = TestClient(app)

def test_project_creation_endpoint():
    response = client.post("/projects/", json={
        "name": "E2E Test Creation",
        "language": "en"
    })
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert "project_id" in data
    
    project_id = data["project_id"]
    project_dir = Path(f"projects/{project_id}")
    
    # Assert physical directories and files were created
    assert project_dir.exists()
    assert (project_dir / "project.json").exists()
    assert (project_dir / "02_asset_manifest.json").exists()
    assert not (project_dir / "manifest.json").exists()
    assert (project_dir / ".pipeline_state.json").exists()
    
    # Cleanup (optional but good for test hygiene)
    import shutil
    shutil.rmtree(project_dir)
