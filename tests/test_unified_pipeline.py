import pytest
from fastapi.testclient import TestClient
from api.main import app
import os
from pathlib import Path

client = TestClient(app)

def test_unified_pipeline_full_flow():
    # 1. Scaffold Project
    create_payload = {
        "name": "Integration Test Project",
        "aspect": "16:9",
        "fps": 30,
        "language": "ar"
    }
    create_res = client.post("/projects/", json=create_payload)
    assert create_res.status_code == 200
    project_id = create_res.json()["project_id"]
    
    # 2. Check Initial Status (Backward compatibility)
    status_res = client.get(f"/gates/{project_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["current_stage"] == "asset_gate"
    assert status_data["status"] == "started"
    
    # 3. Simulate GUI progression
    # GUI finishes asset gate
    res = client.post(f"/gates/{project_id}/finish/0")
    assert res.status_code == 200
    assert res.json()["output"]["status"] == "finished"
    
    # GUI approves plan gate
    res = client.post(f"/gates/{project_id}/approve/1?by=gui_test")
    assert res.status_code == 200
    assert res.json()["output"]["current_stage"] == "plan_gate"
    assert res.json()["output"]["status"] == "locked"
    
    # 4. Trigger Pipeline (we don't want to actually run heavy AI, but we can verify the orchestrator runs and gracefully fails if no plan)
    # The pipeline.py will immediately fail if it doesn't find .agents/rules etc or if it fails the hash checks.
    # We'll just verify the subprocess wrapper executes it.
