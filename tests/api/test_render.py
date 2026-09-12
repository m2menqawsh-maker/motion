from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch
from fastapi.websockets import WebSocketDisconnect

client = TestClient(app)

def test_render_endpoint():
    res = client.post("/render/prj_123")
    assert res.status_code == 200
    assert res.json()["status"] == "rendering"

def test_websocket_connect():
    with client.websocket_connect("/render/prj_123/ws") as websocket:
        assert True

def test_websocket_receive():
    with client.websocket_connect("/render/prj_123/ws") as websocket:
        websocket.send_text("stop")
        assert True

@patch("api.services.render_service.asyncio.create_subprocess_exec")
def test_render_service_mock(mock_exec):
    mock_exec.return_value.returncode = 0
    res = client.post("/render/prj_mock")
    assert res.status_code == 200

def test_websocket_disconnect():
    try:
        with client.websocket_connect("/render/prj_456/ws") as websocket:
            websocket.close()
    except WebSocketDisconnect:
        pass
    assert True
