import pytest
import asyncio
from pathlib import Path
import json

from api.services.pipeline_service import PipelineService
from api.core.errors import InvalidGateError

@pytest.fixture
def project_id():
    return "test-contract-project"

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
    """Validation must reject invalid gates and leave zero side effects."""
    await PipelineService.scaffold_project(project_id)
    pdir = PipelineService._get_project_dir(project_id)
    state_file = pdir / ".pipeline_state.json"
    content_before = state_file.read_bytes()

    with pytest.raises(InvalidGateError):
        await PipelineService.approve_gate(project_id, "invalid_gate_name", "tester")

    assert state_file.read_bytes() == content_before

@pytest.mark.asyncio
async def test_gate_mapping_adapter(project_id):
    """التحقق من سلوك البوابات وتطبيق قاعدة منع تجاوز الحالة دون دليل (S03) والتحقق النمطي للبوابات (S04)"""
    await PipelineService.scaffold_project(project_id)
    
    from api.core.errors import InvalidStageError, InvalidGateError
    from scripts.core.lifecycle_service import LifecyclePreconditionFailedError

    # Invalid stage identifier is rejected
    with pytest.raises(InvalidStageError):
        await PipelineService.start_stage(project_id, "0")

    # Direct finish_stage without evidence must be rejected
    with pytest.raises(LifecyclePreconditionFailedError):
        await PipelineService.finish_stage(project_id, "asset_gate")
    
    # Invalid gate identifier is rejected
    with pytest.raises(InvalidGateError):
        await PipelineService.approve_gate(project_id, "gate_4", "tester")

    # Valid gate records approved_by
    state3 = await PipelineService.approve_gate(project_id, "asset_gate", "tester")
    assert state3["approved_by"] == "tester"
