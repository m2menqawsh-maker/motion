import pytest
import asyncio
from pathlib import Path
import json

from api.services.pipeline_service import PipelineService, InvalidGateException

@pytest.fixture
def project_id():
    return "test-contract-project"

@pytest.fixture(autouse=True)
def setup_teardown(project_id):
    # Setup
    state_file = Path(f"projects/{project_id}/.pipeline_state.json")
    if state_file.exists():
        state_file.unlink()
    
    yield
    
    # Teardown
    if state_file.exists():
        state_file.unlink()

@pytest.mark.asyncio
async def test_always_returns_legacy_gui_state(project_id):
    """get_status يجب أن يعيد legacy_gui_state دائمًا"""
    # Test for uninitialized project
    status = await PipelineService.get_status(project_id)
    assert isinstance(status, dict)
    assert "current_stage" in status
    assert "status" in status
    assert status["status"] == "pending"
    
    # Test for initialized project
    await PipelineService.scaffold_project(project_id)
    status2 = await PipelineService.get_status(project_id)
    assert status2["status"] == "started"
    assert status2["current_stage"] == "asset_gate"

def test_gate_mapping_complete():
    """خريطة البوابات يجب أن تكون مكتملة وصحيحة"""
    expected_gates = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}
    assert PipelineService.VALID_GATES == expected_gates

@pytest.mark.asyncio
async def test_validation_rejects_invalid_gates(project_id):
    """يجب رفض البوابات غير الصالحة"""
    await PipelineService.scaffold_project(project_id)
    
    with pytest.raises(InvalidGateException):
        await PipelineService.approve_gate(project_id, "invalid_gate")
        
    with pytest.raises(InvalidGateException):
        await PipelineService.start_stage(project_id, "4")
        
    with pytest.raises(InvalidGateException):
        await PipelineService.finish_stage(project_id, "foo")

@pytest.mark.asyncio
async def test_gate_mapping_adapter(project_id):
    """يجب أن يقبل الأرقام القديمة (0, 1, 2, 3) ويحولها للبوابات الجديدة"""
    await PipelineService.scaffold_project(project_id)
    
    state1 = await PipelineService.start_stage(project_id, "0")
    assert state1["current_stage"] == "asset_gate"
    
    state2 = await PipelineService.finish_stage(project_id, "1")
    assert state2["current_stage"] == "plan_gate"
    
    state3 = await PipelineService.approve_gate(project_id, "3", "tester")
    assert state3["current_stage"] == "qc_gate"
    assert state3["status"] == "locked"
    assert state3["approved_by"] == "tester"
