from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_project():
    response = client.post("/projects/", json={
        "name": "Test API Project",
        "aspect": "16:9",
        "fps": 30,
        "language": "en"
    })
    assert response.status_code == 200
    assert "project_id" in response.json()
    assert response.json()["project_id"].startswith("prj_")

def test_list_projects():
    res = client.post("/projects/", json={
        "name": "Test", "aspect": "1:1", "fps": 30, "language": "ar"
    })
    project_id = res.json()["project_id"]
    
    res = client.get("/projects/")
    assert res.status_code == 200
    assert project_id in res.json()["projects"]

def test_get_project():
    res = client.post("/projects/", json={
        "name": "Test", "aspect": "1:1", "fps": 30, "language": "ar"
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
        "name": "Missing aspect"
    })
    assert response.status_code == 422

def test_get_brand():
    res = client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.get(f"/brand/{project_id}")
    assert res.status_code == 200
    assert res.json()["brandName"] == "Default Brand"

def test_update_brand():
    res = client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"})
    project_id = res.json()["project_id"]
    payload = {"brandName": "New Brand", "fonts": {"display": "X", "body": "Y"}, "colors": {}}
    res = client.post(f"/brand/{project_id}", json=payload)
    assert res.status_code == 200
    res = client.get(f"/brand/{project_id}")
    assert res.json()["brandName"] == "New Brand"

def test_get_blueprint_not_found():
    res = client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.get(f"/blueprint/{project_id}")
    assert res.status_code == 200
    assert "overrides" in res.json()
    assert "blueprint" not in res.json()

def test_update_blueprint():
    res = client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.post(f"/blueprint/{project_id}/blueprint", json={"test": "data"})
    assert res.status_code == 200
    res = client.get(f"/blueprint/{project_id}")
    assert "blueprint" in res.json()
    assert res.json()["blueprint"]["test"] == "data"

def test_update_overrides():
    res = client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"})
    project_id = res.json()["project_id"]
    res = client.post(f"/blueprint/{project_id}/overrides", json={"new": "overrides"})
    assert res.status_code == 200
    res = client.get(f"/blueprint/{project_id}")
    assert res.json()["overrides"]["new"] == "overrides"
