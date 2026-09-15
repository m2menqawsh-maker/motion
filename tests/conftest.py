import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ['TESTING'] = '1'
    yield
    os.environ.pop('TESTING', None)
import pytest
import shutil
import asyncio
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_tmpdir(monkeypatch, tmp_path):
    """Patch the current working directory or paths to avoid touching real projects"""
    
    # We monkeypatch PipelineService._get_state_path to use tmp_path
    from api.services.pipeline_service import PipelineService
    
    original_get_state_path = PipelineService._get_state_path
    
    def mock_get_state_path(cls, project_id: str) -> Path:
        # Instead of real 'projects/', we use the tmp_path
        # But wait, validate_project_id might still be called.
        return tmp_path / "projects" / project_id / ".pipeline_state.json"
        
    monkeypatch.setattr(PipelineService, "_get_state_path", classmethod(mock_get_state_path))
    
    # Also patch run_pipeline to not try to run a real subprocess by default
    # Or we can just let mock_subprocess do it.

@pytest.fixture
def test_project(tmp_path):
    """E41H9 *,1J(J DD'.*('1"""
    project_id = "test-golden-001"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # %F4'! 'DEDA'* 'D#3'3J) 'DE7DH()
    (project_dir / "master_plan.md").write_text("# Test Plan", encoding="utf-8")
    (project_dir / "blueprint.json").write_text('{"scenes": []}', encoding="utf-8")
    
    yield project_id
    
    # 'D*F8JA (9/ 'D'.*('1
    if project_dir.exists():
        shutil.rmtree(project_dir)

@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock D@ safe_subprocess D*,F( 'D*4:JD 'DA9DJ"""
    async def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '{"master_plan_hash": "abc", "blueprint_hash": "def"}'
            stderr = ""
        return Result()
        
    # We mock it via the synchronous function though, safe_subprocess is sync in pipeline_service.py
    def fake_sync_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '__PIPELINE_STATE__{"master_plan_hash": "abc", "blueprint_hash": "def"}__PIPELINE_STATE__'
            stderr = ""
        return Result()
    
    import api.services.pipeline_service as ps
    monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run)
