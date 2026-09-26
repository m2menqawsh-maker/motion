import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from api.services.pipeline_service import PipelineService

@pytest.mark.asyncio
async def test_pipeline_start_does_not_block_event_loop(tmp_path, monkeypatch):
    """
    اختبار أن بدء الـ Pipeline لا يجمد الـ Event Loop.
    """
    def mock_get_project_dir(project_id):
        path = tmp_path / f"projects_{project_id}"
        path.mkdir(exist_ok=True)
        return path
    
    monkeypatch.setattr("api.services.pipeline_service.PipelineService._get_project_dir", mock_get_project_dir)
    
    # Mock subprocess to simulate a slow running process
    def mock_safe_subprocess(cmd, *args, **kwargs):
        time.sleep(2)  # Simulate slow process blocking thread
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Simulation"
        mock_result.stderr = ""
        return mock_result
        
    monkeypatch.setattr("api.services.pipeline_service.safe_subprocess", mock_safe_subprocess)

    # To test if the event loop is blocked, we run it concurrently with a simple task
    # that measures time.
    async def measure_event_loop_lag():
        start = time.perf_counter()
        await asyncio.sleep(0.5)
        end = time.perf_counter()
        return end - start

    start_time = time.perf_counter()
    
    # Run both concurrently
    lag_task = asyncio.create_task(measure_event_loop_lag())
    pipeline_task = asyncio.create_task(PipelineService.run_pipeline("perf_test_1"))
    
    result = await pipeline_task
    lag_duration = await lag_task
    
    end_time = time.perf_counter()
    total_duration = end_time - start_time
    
    assert result["status"] == "success"
    # Total time will be at least 2 seconds because we await the pipeline
    assert total_duration >= 2.0
    # But the lag task should finish in ~0.5 seconds, proving the event loop wasn't blocked!
    assert lag_duration < 1.0, f"Event loop was blocked! Lag task took {lag_duration} seconds instead of 0.5"
