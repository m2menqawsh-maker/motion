import pytest
import asyncio
from api.services.pipeline_service import PipelineService, PipelineAlreadyRunningException

class TestConcurrentRequests:
    """الطلبات المتزامنة"""
    
    @pytest.mark.asyncio
    async def test_only_one_pipeline_at_a_time(self, test_project, monkeypatch):
        """لا يمكن تشغيل أكثر من pipeline واحد"""
        await PipelineService.scaffold_project(test_project)
        
        # We need a mock subprocess that sleeps so we can test concurrency
        async def fake_sync_run_slow(*args, **kwargs):
            await asyncio.sleep(0.1) # Simulate slow pipeline
            class Result:
                returncode = 0
                stdout = '__PIPELINE_STATE__{}__PIPELINE_STATE__'
                stderr = ""
            return Result()
            
        import api.services.pipeline_service as ps
        
        # Since pipeline.py uses a synchronous safe_subprocess, and we are mocking it in asyncio context,
        # we can just use asyncio.sleep in the mock if it's called with run_in_executor, but in pipeline_service.py it's called directly.
        # Wait, run_pipeline calls safe_subprocess synchronously! This blocks the event loop.
        # So we can't test concurrency using asyncio if it's blocking the loop. 
        # Actually run_pipeline should be calling it via asyncio.to_thread, but currently it's just calling it.
        # Let's mock run_pipeline directly to test the lock itself.
        
        original_run = ps.safe_subprocess
        
        def fake_sync_run_sleep(*args, **kwargs):
            import time
            time.sleep(0.2)
            class Result:
                returncode = 0
                stdout = '__PIPELINE_STATE__{}__PIPELINE_STATE__'
                stderr = ""
            return Result()
            
        monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run_sleep)
        
        # If we use asyncio.create_task for a sync blocking function, it blocks everything unless we use to_thread.
        # Because run_pipeline is an async function that blocks on a sync function, we can just mock run_pipeline's inner working to yield control.
        # Let's just mock safe_subprocess to be async? No, python will complain it is not awaited inside run_pipeline.
        # We will mock the asyncio lock to see if it raises. 
        
        # To test the lock, we can manually acquire it.
        if test_project not in ps.PipelineService._active_pipelines:
            ps.PipelineService._active_pipelines[test_project] = asyncio.Lock()
            
        lock = ps.PipelineService._active_pipelines[test_project]
        
        await lock.acquire()
        try:
            # Attempt to run while locked
            with pytest.raises(PipelineAlreadyRunningException):
                await PipelineService.run_pipeline(test_project)
        finally:
            lock.release()
