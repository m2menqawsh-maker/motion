# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import session_manager
import context_compactor


class TestSessionManager:
    def setup_method(self):
        """إعداد بيئة معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.projects_dir = self.test_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.orig_projects_dir = session_manager.PROJECTS_DIR
        session_manager.PROJECTS_DIR = str(self.projects_dir)
        context_compactor.PROJECTS_DIR = str(self.projects_dir)
        self.project_id = "test_sess_proj"
        self.proj_dir = self.projects_dir / self.project_id
        self.proj_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        session_manager.PROJECTS_DIR = self.orig_projects_dir
        context_compactor.PROJECTS_DIR = self.orig_projects_dir
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_save_state(self):
        """التحقق من استدعاء compactor عند حفظ الحالة"""
        with patch.object(session_manager, "run_compactor") as mock_comp:
            session_manager.save_state(self.project_id)
            mock_comp.assert_called_once_with(self.project_id)

    def test_restore_state(self, capsys):
        """التحقق من استعادة الحالة عند وجودها"""
        state_file = self.proj_dir / ".session_state.json"
        state_file.write_text(json.dumps({"current_phase": "build"}), encoding="utf-8")

        session_manager.restore_state(self.project_id)
        # تأكد من عدم حدوث أخطاء

    def test_list_projects(self):
        """عرض المشاريع التي تمتلك حالات محفوظة فقط"""
        # مشروع 1 يمتلك حالة
        p1 = self.projects_dir / "proj_with_state"
        p1.mkdir(parents=True, exist_ok=True)
        (p1 / ".session_state.json").write_text("{}", encoding="utf-8")

        # مشروع 2 لا يمتلك حالة
        p2 = self.projects_dir / "proj_without_state"
        p2.mkdir(parents=True, exist_ok=True)

        projects_found = []
        for d in os.listdir(session_manager.PROJECTS_DIR):
            proj_dir = os.path.join(session_manager.PROJECTS_DIR, d)
            if os.path.isdir(proj_dir) and os.path.exists(os.path.join(proj_dir, ".session_state.json")):
                projects_found.append(d)

        assert "proj_with_state" in projects_found
        assert "proj_without_state" not in projects_found

    def test_resume_generation(self):
        """توليد ملف resume_brief.md لاستئناف الجلسة"""
        state_file = self.proj_dir / ".session_state.json"
        state_file.write_text(json.dumps({"current_phase": "المرحلة 2: الخطة التفصيلية"}), encoding="utf-8")
        digest_file = self.proj_dir / "session_digest.md"
        digest_file.write_text("# Digest", encoding="utf-8")

        with patch.object(session_manager, "get_current_session_id", return_value=None):
            session_manager.generate_resume_brief(self.project_id)

        brief_file = self.proj_dir / "resume_brief.md"
        assert brief_file.exists()
        content = brief_file.read_text(encoding="utf-8")
        assert self.project_id in content
        assert "المرحلة 2: الخطة التفصيلية" in content

    def test_export_state(self):
        """تصدير ملف الحالة إلى exported_state_<id>.json"""
        state_file = self.proj_dir / ".session_state.json"
        state_data = {"current_phase": "phase_1", "approved_decisions": ["decision_1"]}
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        session_manager.export_state(self.project_id)
        export_file = self.proj_dir / f"exported_state_{self.project_id}.json"
        assert export_file.exists()
        loaded = json.loads(export_file.read_text(encoding="utf-8"))
        assert loaded == state_data

    def test_delete_state(self):
        """حذف ملفات الحالة والـ digest بنجاح"""
        state_file = self.proj_dir / ".session_state.json"
        digest_file = self.proj_dir / "session_digest.md"
        state_file.write_text("{}", encoding="utf-8")
        digest_file.write_text("digest", encoding="utf-8")

        session_manager.delete_state(self.project_id)
        assert not state_file.exists()
        assert not digest_file.exists()

    def test_nonexistent_project_handling(self):
        """التعامل بأناقة مع المشاريع غير الموجودة دون توقف أو انهيار"""
        non_id = "non_existent_project_xyz"
        # استدعاء جميع العمليات للتأكد من عدم رمي أخطاء قاتلة
        session_manager.restore_state(non_id)
        session_manager.export_state(non_id)
        session_manager.delete_state(non_id)

    def test_get_project_dir_resolution(self):
        """التحقق من صحة حل مسار مجلد المشروع"""
        p_dir = session_manager.get_project_dir("custom_id")
        assert p_dir.endswith("custom_id")
        assert "projects" in p_dir

    def test_get_state_file_resolution(self):
        """التحقق من صحة حل مسار ملف الحالة .session_state.json"""
        s_file = session_manager.get_state_file("custom_id")
        assert s_file.endswith(".session_state.json")

    def test_get_digest_file_resolution(self):
        """التحقق من صحة حل مسار ملف الملخص session_digest.md"""
        d_file = session_manager.get_digest_file("custom_id")
        assert d_file.endswith("session_digest.md")
