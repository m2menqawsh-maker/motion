from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app, headers={"X-Principal-ID": "test_admin", "X-Principal-Roles": "admin,reviewer,editor"})

from scripts.core.state_store import StateStore
from api.services.pipeline_service import PipelineService

def create_proj():
    pid = client.post("/projects/", json={"name": "T", "language": "ar"}).json()["project_id"]
    pdir = PipelineService._get_project_dir(pid)
    if not (pdir / ".pipeline_state.json").exists():
        StateStore.create(pdir, pid)
    return pid

def test_status_initial():
    pid = create_proj()
    res = client.get(f"/gates/{pid}/status")
    assert res.status_code == 200
    assert res.json()["state"]["current_stage"] == "asset_gate"

def test_status_not_found():
    res = client.get("/gates/prj_unknown/status")
    assert res.status_code == 200
    assert res.json()["state"]["current_stage"] == "asset_gate"

def test_start_stage_invalid_identifier_rejected():
    """Finding B: Stringly-typed or unknown stages like '0' must be rejected with 422."""
    pid = create_proj()
    res = client.post(f"/gates/{pid}/start/0")
    assert res.status_code == 422

def test_start_stage_valid_stage_is_unsupported():
    """Finding A: Direct stage start is unsupported via legacy endpoint (must fail closed)."""
    pid = create_proj()
    res = client.post(f"/gates/{pid}/start/asset_gate")
    assert res.status_code == 422
    assert res.json()["error"] == "UnsupportedGateOperationError"

def test_approve_gate_valid():
    """Valid gate approval with authorized principal succeeds and records approved_by."""
    pid = create_proj()
    res = client.post(f"/gates/{pid}/approve/asset_gate")
    assert res.status_code == 200
    assert res.json()["output"]["approved_by"] == "test_admin"

def test_approve_gate_invalid_rejected():
    """Finding A & B: Invalid or unknown gates must be rejected with 422."""
    pid = create_proj()
    res = client.post(f"/gates/{pid}/approve/99")
    assert res.status_code == 422

    res2 = client.post(f"/gates/{pid}/approve/unknown_gate")
    assert res2.status_code == 422

def test_reject_gate_is_unsupported():
    """Finding C: reject_gate must NOT return fake success. Fails closed with 422."""
    pid = create_proj()
    # Invalid identifier fails validation
    res = client.post(f"/gates/{pid}/reject/1?note=bad")
    assert res.status_code == 422

    # Valid identifier is unsupported pending ReviewService (S09)
    res2 = client.post(f"/gates/{pid}/reject/asset_gate?note=bad")
    assert res2.status_code == 422
    assert res2.json()["error"] == "UnsupportedGateOperationError"

def test_finish_stage_requires_verified_evidence():
    """Finding A & S03: Direct finish without proof is rejected with 422."""
    pid = create_proj()
    # Invalid stage identifier rejected
    res_inv = client.post(f"/gates/{pid}/finish/1")
    assert res_inv.status_code == 422

    # Valid stage identifier rejected because direct finish without evidence is forbidden
    res = client.post(f"/gates/{pid}/finish/asset_gate")
    assert res.status_code == 422
    assert res.json()["error"] == "LifecyclePreconditionFailedError"

def test_status_updates():
    pid = create_proj()
    client.post(f"/gates/{pid}/approve/asset_gate")
    res = client.get(f"/gates/{pid}/status")
    assert res.json()["state"]["current_stage"] == "asset_gate"
    assert res.json()["state"]["status"] == "started"
    assert res.json()["state"]["approved_by"] == "test_admin"
