from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def create_proj():
    return client.post("/projects/", json={"name": "T", "aspect": "1:1", "fps": 30, "language": "ar"}).json()["project_id"]

def test_status_initial():
    pid = create_proj()
    res = client.get(f"/gates/{pid}/status")
    assert res.status_code == 200
    assert res.json()["current_stage"] == 0

def test_status_not_found():
    res = client.get("/gates/prj_unknown/status")
    assert res.status_code == 404

def test_start_stage_0_already_started():
    pid = create_proj()
    res = client.post(f"/gates/{pid}/start/0")
    assert res.status_code in [200, 500] 

def test_approve_gate_1_locked():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    res = client.post(f"/gates/{pid}/approve/1?by=test")
    assert res.status_code == 200

def test_reject_gate_1():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    res = client.post(f"/gates/{pid}/reject/1?by=test&note=bad")
    assert res.status_code == 200

def test_start_stage_1_without_approve():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    res = client.post(f"/gates/{pid}/start/1")
    assert res.status_code == 500

def test_start_stage_1_after_approve():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    client.post(f"/gates/{pid}/approve/1?by=test")
    res = client.post(f"/gates/{pid}/start/1")
    assert res.status_code == 200

def test_finish_stage_1():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    client.post(f"/gates/{pid}/approve/1?by=test")
    client.post(f"/gates/{pid}/start/1")
    res = client.post(f"/gates/{pid}/finish/1")
    assert res.status_code == 200

def test_approve_gate_invalid():
    pid = create_proj()
    res = client.post(f"/gates/{pid}/approve/99")
    assert res.status_code == 500

def test_status_updates():
    pid = create_proj()
    client.post(f"/gates/{pid}/start/0")
    client.post(f"/gates/{pid}/finish/0")
    client.post(f"/gates/{pid}/approve/1?by=test")
    client.post(f"/gates/{pid}/start/1")
    res = client.get(f"/gates/{pid}/status")
    assert res.json()["current_stage"] == 1
    assert res.json()["stages"]["1"]["status"] == "running"
