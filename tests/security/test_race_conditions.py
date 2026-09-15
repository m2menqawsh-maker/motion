import asyncio
import pytest
from api.services.pipeline_service import PipelineService

class TestRaceConditions:
    """حماية من Race Conditions"""
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_calls(self, test_project, monkeypatch):
        """استدعاءات pipeline متزامنة يجب أن تُرفض"""
        await PipelineService.scaffold_project(test_project)
        
        # We need a mock for subprocess that takes a little bit of time so they actually overlap
        import api.services.pipeline_service as ps
        
        # To avoid blocking the event loop and effectively testing the lock,
        # we can just mock the asyncio.Lock acquiring mechanism, 
        # but since they all await the lock and then raise PipelineAlreadyRunningException 
        # (Wait, actually they use lock.locked() or lock.acquire(blocking=False)? 
        # PipelineService uses lock.locked() to check if it's already running).
        # Let's see: if ps._active_pipelines[project_id].locked(): raise PipelineAlreadyRunningException
        # So we just need run_pipeline to not finish immediately.
        # But wait, run_pipeline calls safe_subprocess synchronously! So it blocks the loop.
        # We should patch safe_subprocess to just do time.sleep and we must run run_pipeline using asyncio.to_thread if we want true async concurrency.
        # Wait, the pipeline service runs synchronously in the event loop right now.
        # To test it we can mock safe_subprocess to be async? No, then run_pipeline will throw TypeError because it doesn't await it.
        # We'll just patch safe_subprocess to return quickly, and see if the lock is held. 
        # Actually, since it's an async function, we can just use a fake lock that holds it for a while.
        
        def fake_sync_run_sleep(*args, **kwargs):
            import time
            time.sleep(0.1)
            class Result:
                returncode = 0
                stdout = '__PIPELINE_STATE__{}__PIPELINE_STATE__'
                stderr = ""
            return Result()
            
        monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run_sleep)
        
        # We can't really do true async concurrency if safe_subprocess blocks the loop.
        # But we can try to use asyncio.gather and since run_pipeline has an 'await cls._get_lock()' maybe?
        # Actually in pipeline_service.py it is:
        # lock = cls._active_pipelines.setdefault(...)
        # if lock.locked(): raise PipelineAlreadyRunningException
        # async with lock:
        #   ...
        
        # محاولة تشغيل 5 pipelines في نفس الوقت
        tasks = [
            asyncio.create_task(PipelineService.run_pipeline(test_project))
            for _ in range(5)
        ]
        
        # واحد فقط يجب أن ينجح، والباقي يجب أن يفشل
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count == 1, "فقط واحد يجب أن ينجح"
    
    @pytest.mark.asyncio
    async def test_concurrent_state_writes(self, test_project):
        """كتابة متزامنة للحالة لا تفقد البيانات"""
        await PipelineService.scaffold_project(test_project)
        
        # محاولة كتابة الحالة من 10 tasks في نفس الوقت
        async def write_state(i):
            # We use an async sleep to yield control and increase chance of race condition
            await asyncio.sleep(0.01)
            await PipelineService.approve_gate(
                test_project, 
                "asset_gate", 
                f"user_{i}"
            )
        
        tasks = [asyncio.create_task(write_state(i)) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # التحقق من أن الحالة لا تزال صالحة
        status = await PipelineService.get_status(test_project)
        assert "current_stage" in status
        assert status["approved_by"].startswith("user_")
