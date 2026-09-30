from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app, headers={"X-Principal-ID": "test_admin", "X-Principal-Roles": "admin"})

def test_create_project():
    response = client.post("/projects/", json={
        "name": "Test API Project",
                        "language": "en"
    })
    assert response.status_code == 200
    assert "project_id" in response.json()
    assert response.json()["project_id"].startswith("prj_")

def test_list_projects():
    res = client.post("/projects/", json={
        "name": "Test", "language": "ar"
    })
    project_id = res.json()["project_id"]
    
    res = client.get("/projects/")
    assert res.status_code == 200
    assert project_id in res.json()["projects"]

def test_get_project():
    res = client.post("/projects/", json={
        "name": "Test", "language": "ar"
    })
    project_id = res.json()["project_id"]
    
    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 200
    data = res.json()
    assert "project" in data
    assert "state" in data
    assert "manifest" in data
    assert data["project"]["name"] == "Test"

def test_get_nonexistent_project():
    res = client.get("/projects/prj_invalid999")
    assert res.status_code == 404

def test_create_project_invalid_payload():
    response = client.post("/projects/", json={
        "invalid_payload": "Missing name"
    })
    assert response.status_code == 422

def test_get_brand():
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.get(f"/brand/{project_id}")
    assert res.status_code == 200
    assert res.json()["brandName"] == "Default Brand"

def test_update_brand():
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    payload = {
        "brandName": "New Brand",
        "fonts": {"display": "Cairo", "body": "Inter"},
        "colors": {
            "primary": "#FF0000",
            "accent": "#00FF00",
            "background": "#000000",
            "text": "#FFFFFF",
        },
    }
    res = client.post(f"/brand/{project_id}", json=payload)
    assert res.status_code == 200
    res = client.get(f"/brand/{project_id}")
    assert res.json()["brandName"] == "New Brand"

def test_get_blueprint_not_found():
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.get(f"/blueprint/{project_id}")
    assert res.status_code == 200
    assert "overrides" in res.json()
    assert res.json()["blueprint"] is None

def test_update_blueprint():
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    payload = {
        "project_id": project_id,
        "version": "1.0",
        "fps": 30,
        "aspect_ratio": "16:9",
        "meta": {"motion_personality": "Cinematic"},
        "scenes": []
    }
    res = client.post(f"/blueprint/{project_id}/blueprint", json=payload)
    assert res.status_code == 200
    res = client.get(f"/blueprint/{project_id}")
    assert "blueprint" in res.json()
    assert res.json()["blueprint"]["scenes"] == []

def test_update_overrides():
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    payload = {
        "project_id": project_id,
        "scenes": [
            {
                "scene_id": "scene_1",
                "timing": {"startFrame": 0, "durationFrames": 90},
            }
        ],
    }
    res = client.post(f"/blueprint/{project_id}/overrides", json=payload)
    assert res.status_code == 200
    res = client.get(f"/blueprint/{project_id}")
    assert len(res.json()["overrides"]["scenes"]) == 1


def test_api_blueprint_update_invalidates_downstream_evidence():
    """Verify LED-090 fix: updating blueprint via API invalidates downstream evidence."""
    from scripts.core.state_store import StateStore
    from scripts.core.state_model import ArtifactRecord, ValidationLevel, EvidenceStatus
    from pathlib import Path

    from api.services.pipeline_service import PipelineService
    res = client.post("/projects/", json={"name": "T", "language": "ar"})
    project_id = res.json()["project_id"]
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        project_dir = PipelineService._get_project_dir(project_id)

    # Add dummy probe evidence as VALID
    state = StateStore.load(project_dir)
    state.record_evidence(ArtifactRecord(
        path="probe_qc_report.json",
        validation=ValidationLevel.EXISTS,
        status=EvidenceStatus.VALID,
    ))
    StateStore.save(project_dir, state)

    # Call API to update blueprint
    payload = {
        "project_id": project_id,
        "version": "1.0",
        "fps": 30,
        "aspect_ratio": "16:9",
        "meta": {"motion_personality": "Cinematic"},
        "scenes": []
    }
    res = client.post(f"/blueprint/{project_id}/blueprint", json=payload)
    assert res.status_code == 200, res.text

    # Verify probe evidence became INVALIDATED
    updated_state = StateStore.load(project_dir)
    probe_rec = updated_state.get_artifact_record("probe_qc_report.json")
    assert probe_rec is not None
    assert probe_rec.status == EvidenceStatus.INVALIDATED
    assert "Blueprint updated via API" in probe_rec.invalidated_reason
