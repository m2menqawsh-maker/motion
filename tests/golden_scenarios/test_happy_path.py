import pytest
from api.services.pipeline_service import PipelineService

class TestHappyPath:
    """المسار السعيد: من إنشاء المشروع إلى الموافقة"""
    
    @pytest.mark.asyncio
    async def test_scaffold_creates_project(self, test_project):
        """scaffold يجب أن ينشئ المشروع بنجاح"""
        result = await PipelineService.scaffold_project(test_project)
        assert result["status"] == "success"
        
        status = await PipelineService.get_status(test_project)
        assert status["current_stage"] == "asset_gate"
        assert status["status"] == "started"
    
    @pytest.mark.asyncio
    async def test_approve_gates_in_order(self, test_project):
        """الموافقة على البوابات بالترتيب"""
        await PipelineService.scaffold_project(test_project)
        
        # الموافقة على البوابات بالترتيب
        await PipelineService.approve_gate(test_project, "gate_1", "user")
        await PipelineService.approve_gate(test_project, "gate_2", "user")
        await PipelineService.approve_gate(test_project, "gate_4", "user")
        
        # التحقق من الحالة
        status = await PipelineService.get_status(test_project)
        assert status["current_stage"] == "qc_gate"
        assert status["status"] == "locked"
        assert status["approved_by"] == "user"
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, test_project, mock_subprocess):
        """دورة الحياة الكاملة"""
        # 1. Scaffold
        await PipelineService.scaffold_project(test_project)
        
        # 2. الموافقة على البوابات
        for gate in ["gate_1", "gate_2", "gate_3", "gate_4"]:
            await PipelineService.approve_gate(test_project, gate, "user")
        
        # 3. تشغيل Pipeline (مع mock)
        result = await PipelineService.run_pipeline(test_project)
        
        # 4. التحقق من النجاح
        assert result["status"] == "success"
        assert result["state"]["master_plan_hash"] == "abc"
        assert result["state"]["blueprint_hash"] == "def"
