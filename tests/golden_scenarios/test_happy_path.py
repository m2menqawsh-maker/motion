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
    async def test_approve_gates_fail_closed_under_s04(self, test_project):
        """محاولة الموافقة على البوابات عبر API القديم تُرفض (S04) لحين توفر ReviewService (S09)"""
        await PipelineService.scaffold_project(test_project)
        from api.core.errors import UnsupportedGateOperationError
        
        with pytest.raises(UnsupportedGateOperationError):
            await PipelineService.approve_gate(test_project, "asset_gate", "user")
        
        # التحقق من الحالة: صفر أعراض جانبية، الحالة لم تتغير
        status = await PipelineService.get_status(test_project)
        assert status["current_stage"] == "asset_gate"
        assert status["status"] == "started"
        assert "approved_by" not in status
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, test_project, mock_subprocess):
        """دورة الحياة الكاملة"""
        # 1. Scaffold
        await PipelineService.scaffold_project(test_project)
        
        # 2. تشغيل Pipeline (مع mock)
        result = await PipelineService.run_pipeline(test_project)
        
        # 4. التحقق من النجاح
        assert result["status"] == "success"
        assert result["state"]["master_plan_hash"] == "abc"
        assert result["state"]["blueprint_hash"] == "def"
