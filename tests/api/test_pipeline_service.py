import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from api.services.pipeline_service import PipelineService, InvalidGateException, PipelineAlreadyRunningException

@pytest.fixture
def project_id(tmp_path, monkeypatch):
    pid = "test_unified_123"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    
    # Mock safe_resolve via validate_project_id to use tmp_path
    def mock_validate(pid):
        return pid
    monkeypatch.setattr("api.services.pipeline_service.validate_project_id", mock_validate)
    
    # Mock Path to point to tmp_path for the service
    original_get_state_path = PipelineService._get_state_path
    @classmethod
    def mock_get_state_path(cls, p_id):
        return tmp_path / "projects" / p_id / ".pipeline_state.json"
    monkeypatch.setattr(PipelineService, "_get_state_path", mock_get_state_path)
    
    # Reset locks
    PipelineService._active_pipelines = {}
    
    return pid

def test_scaffold_project(project_id, tmp_path):
    async def run():
        result = await PipelineService.scaffold_project(project_id)
        assert result["status"] == "success"
        
        state_file = tmp_path / "projects" / project_id / ".pipeline_state.json"
        assert state_file.exists()
        
        state = json.loads(state_file.read_text())
        assert "legacy_gui_state" in state
        assert state["legacy_gui_state"]["current_stage"] == "asset_gate"
        assert state["legacy_gui_state"]["status"] == "started"
    asyncio.run(run())

def test_legacy_gate_mapping(project_id):
    async def run():
        await PipelineService.scaffold_project(project_id)
        
        result = await PipelineService.start_stage(project_id, "0")
        assert result["current_stage"] == "asset_gate"
        assert result["status"] == "started"

        result = await PipelineService.finish_stage(project_id, "1")
        assert result["current_stage"] == "plan_gate"
        assert result["status"] == "finished"

        result = await PipelineService.approve_gate(project_id, "2", "test_user")
        assert result["current_stage"] == "taste_gate"
        assert result["status"] == "locked"
        assert result["approved_by"] == "test_user"
    asyncio.run(run())

def test_invalid_gate_exception(project_id):
    async def run():
        await PipelineService.scaffold_project(project_id)
        
        with pytest.raises(InvalidGateException):
            await PipelineService.start_stage(project_id, "invalid_gate")
    asyncio.run(run())

def test_get_status(project_id):
    async def run():
        await PipelineService.scaffold_project(project_id)
        await PipelineService.start_stage(project_id, "plan_gate")
        
        status = await PipelineService.get_status(project_id)
        assert status["current_stage"] == "plan_gate"
        assert status["status"] == "started"
        assert "timestamp" in status
    asyncio.run(run())

def test_run_pipeline_extracts_hashes_and_merges(project_id, monkeypatch):
    async def run():
        await PipelineService.scaffold_project(project_id)
        await PipelineService.start_stage(project_id, "plan_gate")
        
        class MockResult:
            returncode = 0
            stdout = 'some log\n__PIPELINE_STATE__{"master_plan_hash": "abc"}__PIPELINE_STATE__\nother log'
            stderr = ''
            
        def mock_subprocess(*args, **kwargs):
            return MockResult()
            
        monkeypatch.setattr("api.services.pipeline_service.safe_subprocess", mock_subprocess)
        
        result = await PipelineService.run_pipeline(project_id)
        assert result["status"] == "success"
        
        state = result["state"]
        assert state["master_plan_hash"] == "abc"
        assert "legacy_gui_state" in state
        assert state["legacy_gui_state"]["current_stage"] == "plan_gate"
    asyncio.run(run())

def test_pipeline_lock_prevents_concurrent_runs(project_id, monkeypatch):
    async def slow_pipeline():
        await asyncio.sleep(0.1)
        
    async def mock_run_pipeline(p_id):
        if p_id not in PipelineService._active_pipelines:
            PipelineService._active_pipelines[p_id] = asyncio.Lock()
        lock = PipelineService._active_pipelines[p_id]
        if lock.locked():
            raise PipelineAlreadyRunningException()
        async with lock:
            await slow_pipeline()
            return {"status": "success"}

    async def run_both():
        t1 = asyncio.create_task(mock_run_pipeline(project_id))
        await asyncio.sleep(0.01)
        
        t2 = asyncio.create_task(mock_run_pipeline(project_id))
        
        with pytest.raises(PipelineAlreadyRunningException):
            await t2
            
        await t1

    asyncio.run(run_both())
