import pytest
from api.services.pipeline_service import PipelineService
from api.core.errors import InvalidGateError
import json

class TestFailureRecovery:
    """التعافي من الفشل"""
    
    @pytest.mark.asyncio
    async def test_pipeline_failure_preserves_state(self, test_project, monkeypatch):
        """فشل الـ pipeline يجب أن يحفظ الحالة ولن يتسبب في تدميرها"""
        # Scaffold and approve
        await PipelineService.scaffold_project(test_project)
        await PipelineService.approve_gate(test_project, "gate_4", "user")
        
        # Read the state before failure
        from scripts.core.state_store import StateStore
        state_before = StateStore.load(PipelineService._get_project_dir(test_project))
        
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
        state_after = StateStore.load(PipelineService._get_project_dir(test_project))
        legacy_state = PipelineService._format_legacy_state(state_after)
        assert legacy_state["current_stage"] == "qc_gate"
        assert legacy_state["status"] == "locked"
