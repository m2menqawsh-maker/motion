import pytest
import asyncio
import time
from unittest.mock import patch
from api.services.pipeline_service import PipelineService
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_state_read_performance(tmp_path, monkeypatch):
    """
    اختبار أن قراءة حالة الـ Pipeline سريعة جداً.
    """
    def mock_get_project_dir(project_id):
        path = tmp_path / f"projects_{project_id}"
        path.mkdir(exist_ok=True)
        state_path = path / ".pipeline_state.json"
        if not state_path.exists():
            state_path.write_text('{"legacy_gui_state": {"status": "pending"}}', encoding="utf-8")
        return path
    
    monkeypatch.setattr("api.services.pipeline_service.PipelineService._get_project_dir", mock_get_project_dir)
    
    start_time = time.perf_counter()
    
    state = await PipelineService.get_status("perf_test_2")
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    assert state.get("status") == "pending"
    # Reading a local JSON file should be almost instantaneous
    assert duration < 0.05, f"State read took too long: {duration} seconds"

def test_api_health_performance():
    """
    اختبار سرعة استجابة الـ API للأوامر الأساسية.
    """
    start_time = time.perf_counter()
    
    response = client.get("/health")
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    assert response.status_code == 200
    assert duration < 0.1, f"API health check blocked for {duration} seconds"
