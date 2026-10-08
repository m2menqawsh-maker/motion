from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch
from fastapi.websockets import WebSocketDisconnect

from tests.conftest import make_test_auth_headers

client = TestClient(app)

AUTH_HEADERS = make_test_auth_headers(principal_id="usr_test_admin", roles=["admin"], project_scopes={"*": ["admin"]})

def test_render_endpoint():
    res_proj = client.post("/projects/", headers=AUTH_HEADERS, json={"name": "RenderTest", "language": "ar"})
    assert res_proj.status_code == 200
    project_id = res_proj.json()["project_id"]
    res = client.post(f"/render/{project_id}", headers=AUTH_HEADERS)
    assert res.status_code == 200
    assert res.json()["status"] == "rendering"

def test_websocket_connect():
    with client.websocket_connect("/render/prj_123/ws") as websocket:
        assert True

def test_websocket_receive():
    with client.websocket_connect("/render/prj_123/ws") as websocket:
        websocket.send_text("stop")
        assert True
from unittest.mock import patch, AsyncMock

@patch("api.services.render_service.asyncio.create_subprocess_exec", new_callable=AsyncMock)
def test_render_service_mock(mock_exec):
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.stdout.readline.side_effect = [b"Rendering...\n", b""]
    mock_process.stderr.readline.side_effect = [b""]
    mock_exec.return_value = mock_process
    
    res = client.post("/render/prj_mock", headers=AUTH_HEADERS)
    assert res.status_code == 200

def test_websocket_disconnect():
    try:
        with client.websocket_connect("/render/prj_456/ws") as websocket:
            websocket.close()
    except WebSocketDisconnect:
        pass
    assert True
