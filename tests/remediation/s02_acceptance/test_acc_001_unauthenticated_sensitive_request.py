"""S02 Acceptance Contract 001: Unauthenticated Sensitive Request Rejection.

Vulnerability: AUTH-001 / AUTH-002
Contract:
All sensitive mutating endpoints must require authenticated Principal credentials
(e.g., Authorization: Bearer <token> or valid session). Unauthenticated requests
must be rejected with HTTP 401 Unauthorized or HTTP 403 Forbidden.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.mark.acceptance
def test_unauthenticated_project_creation_must_be_rejected():
    """Unauthenticated POST /projects must be rejected with 401 or 403."""
    client = TestClient(app)
    
    # Send request without any Authorization header
    response = client.post("/projects", json={"name": "unauthorized_test", "language": "en"})
    
    # Contract: Must be rejected with 401 or 403 before any project is created
    assert response.status_code in (401, 403), (
        f"Expected HTTP 401/403 for unauthenticated request, but received {response.status_code}. "
        "Sensitive endpoints currently allow anonymous, unauthenticated execution."
    )
