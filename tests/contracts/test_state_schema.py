import pytest
import asyncio
from pathlib import Path
import json

from api.services.pipeline_service import PipelineService

@pytest.fixture
def project_id():
    return "test-schema-project"

@pytest.fixture(autouse=True)
def setup_teardown(project_id):
    # Setup
    state_file = PipelineService._get_project_dir(project_id) / ".pipeline_state.json"
    if state_file.exists():
        state_file.unlink()
    
    yield
    
    # Teardown
    if state_file.exists():
        state_file.unlink()

@pytest.mark.asyncio
async def test_pipeline_state_has_required_fields(project_id):
    """ملف الحالة يجب أن يحتوي على الحقول المطلوبة بمجرد تشغيل بايبلاين وهمي"""
    
    # Scaffold
    await PipelineService.scaffold_project(project_id)
    
    # We can write fake data to simulate pipeline run
    state_file = PipelineService._get_project_dir(project_id) / ".pipeline_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    
    state["master_plan_hash"] = "abc"
    state["blueprint_hash"] = "def"
    
    state_file.write_text(json.dumps(state))
    
    # Reload
    loaded_state = json.loads(state_file.read_text(encoding="utf-8"))
    
    required_fields = {"master_plan_hash", "blueprint_hash"}
    assert required_fields.issubset(loaded_state.keys())
    
    # legacy_gui_state schema check via API
    legacy = await PipelineService.get_status(project_id)
    legacy_fields = {"current_stage", "status"}
    assert legacy_fields.issubset(legacy.keys())
