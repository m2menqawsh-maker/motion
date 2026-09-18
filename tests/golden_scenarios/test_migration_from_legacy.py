import pytest
import json
from pathlib import Path
from scripts.migrate_state import migrate_project
from api.services.pipeline_service import PipelineService

class TestMigrationFromLegacy:
    """الترحيل من النظام القديم"""
    
    @pytest.mark.asyncio
    async def test_state_json_migration(self, test_project, tmp_path, monkeypatch):
        """state.json القديم يجب أن يرحل إلى .pipeline_state.json"""
        
        # We need to mock Path in migrate_state so it uses tmp_path
        import scripts.migrate_state as ms
        original_path = ms.Path
        
        class MockPath:
            def __new__(cls, *args, **kwargs):
                path_str = str(args[0])
                if path_str.startswith("projects/"):
                    # Redirect to tmp_path
                    return tmp_path / path_str
                return original_path(*args, **kwargs)
                
        monkeypatch.setattr(ms, "Path", MockPath)
        
        # إنشاء state.json قديم
        project_dir = tmp_path / "projects" / test_project
        old_state_path = project_dir / "state.json"
        
        legacy_state = {
            "current_stage": "2",
            "status": "started",
            "approved_by": "legacy_user"
        }
        old_state_path.write_text(json.dumps(legacy_state), encoding="utf-8")
        
        # تشغيل الترحيل
        migrate_project(test_project)
        
        # التحقق من الترحيل
        new_state_path = PipelineService._get_project_dir(test_project) / ".pipeline_state.json"
        new_state = json.loads(new_state_path.read_text(encoding="utf-8"))
        assert "legacy_gui_state" in new_state
        assert new_state["legacy_gui_state"]["approved_by"] == "legacy_user"
        assert new_state["legacy_gui_state"]["current_stage"] == "plan_gate"
        
        # Ensure old state is renamed
        assert not old_state_path.exists()
        assert (project_dir / "state.json.deprecated").exists()
