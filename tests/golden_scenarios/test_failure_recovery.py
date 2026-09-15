import pytest
from api.services.pipeline_service import PipelineService, InvalidGateException
import json

class TestFailureRecovery:
    """التعافي من الفشل"""
    
    @pytest.mark.asyncio
    async def test_invalid_gate_raises_error(self, test_project):
        """بوابة غير صالحة يجب أن ترفع خطأ ولن تتأثر الحالة"""
        await PipelineService.scaffold_project(test_project)
        
        status_before = await PipelineService.get_status(test_project)
        
        with pytest.raises(InvalidGateException):
            await PipelineService.approve_gate(test_project, "invalid_gate", "user")
            
        status_after = await PipelineService.get_status(test_project)
        assert status_before == status_after
    
    @pytest.mark.asyncio
    async def test_pipeline_failure_preserves_state(self, test_project, monkeypatch):
        """فشل الـ pipeline يجب أن يحفظ الحالة ولن يتسبب في تدميرها"""
        # Scaffold and approve
        await PipelineService.scaffold_project(test_project)
        await PipelineService.approve_gate(test_project, "asset_gate", "user")
        
        # Read the state before failure
        state_before = PipelineService._load_state(test_project)
        
        # Mock subprocess to simulate failure
        def fake_sync_run_fail(*args, **kwargs):
            class Result:
                returncode = 1
                stdout = "Something went horribly wrong"
                stderr = "Traceback..."
            return Result()
            
        import api.services.pipeline_service as ps
        monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run_fail)
        
        result = await PipelineService.run_pipeline(test_project)
        
        # Assert failure
        assert result["status"] == "failed"
        assert result["return_code"] == 1
        
        # State must remain intact
        state_after = PipelineService._load_state(test_project)
        assert state_after["legacy_gui_state"]["current_stage"] == "asset_gate"
        assert state_after["legacy_gui_state"]["status"] == "locked"
