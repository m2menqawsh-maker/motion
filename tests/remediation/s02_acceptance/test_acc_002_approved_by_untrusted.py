"""S02 Acceptance Contract 002: User-Supplied approved_by Must Not Be Trusted.

Vulnerability: AUTH-001 / DEC-04
Contract:
Request parameters such as ?by=..., approved_by, or actor in query or body
must NEVER be accepted as trusted identity. The actor identity recorded in state
must be drawn exclusively from the server-authenticated Principal.
"""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from scripts.core.state_store import StateStore


@pytest.mark.acceptance
def test_user_supplied_by_parameter_must_not_become_trusted_actor(tmp_path, monkeypatch):
    """Passing ?by=spoofed_admin must not record 'spoofed_admin' as verified actor."""
    project_id = "test_acc_002_proj"
    project_dir = Path("projects") / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        # Create a test project via StateStore
        project_dir.mkdir(parents=True, exist_ok=True)
        StateStore.create(project_dir, project_id)

        client = TestClient(app)
        
        # Untrusted client passes arbitrary identity in query
        spoofed_actor = "untrusted_spoofed_ceo"
        response = client.post(f"/gates/{project_id}/approve/gate_1?by={spoofed_actor}")

        # If endpoint is called without verified principal matching spoofed_actor,
        # either the request must be rejected (401/403/422) OR the state must NOT record spoofed_actor
        if response.status_code == 200:
            state = StateStore.load(project_dir)
            gate_1_state = state.gates.get("gate_1", {})
            recorded_actor = gate_1_state.get("approved_by") if isinstance(gate_1_state, dict) else getattr(gate_1_state, "approved_by", None)
            
            assert recorded_actor != spoofed_actor, (
                f"Security Failure: Gate recorded unverified caller '{recorded_actor}' directly from query string. "
                "Identity must be extracted solely from authenticated Principal."
            )
        else:
            assert response.status_code in (401, 403, 422)

    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir)
