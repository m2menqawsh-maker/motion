import os
import pytest
import shutil
import asyncio
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ['TESTING'] = '1'
    yield
    os.environ.pop('TESTING', None)

@pytest.fixture(autouse=True)
def setup_tmpdir(monkeypatch, tmp_path):
    """Patch the current working directory or paths to avoid touching real projects"""
    from api.services.pipeline_service import PipelineService
    
    def mock_get_project_dir(cls, project_id: str) -> Path:
        p = tmp_path / "projects" / project_id
        p.mkdir(parents=True, exist_ok=True)
        return p
        
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(mock_get_project_dir))

@pytest.fixture
def test_project(tmp_path):
    """Test Project"""
    project_id = "test-golden-001"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    (project_dir / "master_plan.md").write_text("# Test Plan", encoding="utf-8")
    (project_dir / "blueprint.json").write_text('{"scenes": []}', encoding="utf-8")
    
    yield project_id
    
    if project_dir.exists():
        shutil.rmtree(project_dir)

@pytest.fixture
def mock_subprocess(monkeypatch):
    async def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '{"master_plan_hash": "abc", "blueprint_hash": "def"}'
            stderr = ""
        return Result()
        
    def fake_sync_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '__PIPELINE_STATE__{"master_plan_hash": "abc", "blueprint_hash": "def"}__PIPELINE_STATE__'
            stderr = ""
        return Result()
    
    import api.services.pipeline_service as ps
    monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run)
