# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import context_compactor


class TestContextCompactor:
    def setup_method(self):
        """إعداد بيئة معزولة للمشروع"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.projects_dir = self.test_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.orig_projects_dir = context_compactor.PROJECTS_DIR
        context_compactor.PROJECTS_DIR = str(self.projects_dir)
        self.project_id = "test_compactor_proj"

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        context_compactor.PROJECTS_DIR = self.orig_projects_dir
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_compact_generation(self):
        """توليد ملف session_digest.md بنجاح"""
        context_compactor.compact(self.project_id)
        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        assert digest_file.exists()
        content = digest_file.read_text(encoding="utf-8")
        assert "# 📋 ملخص الجلسة (Session Digest)" in content
        assert self.project_id in content

    def test_100_line_limit(self):
        """التأكد من عدم تجاوز session_digest.md لـ 100 سطر مهما بلغ عدد المشاكل والقرارات"""
        state = context_compactor.load_state(self.project_id)
        state["issues_resolved"] = [{"issue": f"Issue {i}", "solution": f"Sol {i}"} for i in range(120)]
        state["warnings"] = [f"Warning {i}" for i in range(50)]
        context_compactor.generate_digest(self.project_id, state)

        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        assert digest_file.exists()
        lines = digest_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 100

    def test_add_approved_decision(self):
        """إضافة قرار معتمد وتوثيقه في الحالة والملخص"""
        context_compactor.add_decision(self.project_id, "اعتماد خط Cairo للعناوين", "approved")
        state = context_compactor.load_state(self.project_id)
        assert len(state["approved_decisions"]) == 1
        assert state["approved_decisions"][0]["text"] == "اعتماد خط Cairo للعناوين"

        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        content = digest_file.read_text(encoding="utf-8")
        assert "اعتماد خط Cairo للعناوين" in content

    def test_add_rejected_decision(self):
        """إضافة قرار مرفوض وتوثيقه لمنع تكراره"""
        context_compactor.add_decision(self.project_id, "استخدام أصوات النظام الافتراضية", "rejected")
        state = context_compactor.load_state(self.project_id)
        assert len(state["rejected_decisions"]) == 1
        assert state["rejected_decisions"][0]["text"] == "استخدام أصوات النظام الافتراضية"

        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        content = digest_file.read_text(encoding="utf-8")
        assert "استخدام أصوات النظام الافتراضية" in content

    def test_set_phase(self):
        """تحديث المرحلة الحالية وتوثيقها"""
        context_compactor.set_phase(self.project_id, "المرحلة 3: بناء المشاهد")
        state = context_compactor.load_state(self.project_id)
        assert state["current_phase"] == "المرحلة 3: بناء المشاهد"

        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        content = digest_file.read_text(encoding="utf-8")
        assert "المرحلة 3: بناء المشاهد" in content

    def test_add_note(self):
        """إضافة ملاحظات (مشاكل محلولة، تحذيرات)"""
        context_compactor.add_note(self.project_id, "issue_resolved", "Font size mismatch: Fixed in scene 2")
        context_compactor.add_note(self.project_id, "warning", "High render latency detected")

        state = context_compactor.load_state(self.project_id)
        assert len(state["issues_resolved"]) == 1
        assert state["issues_resolved"][0]["issue"] == "Font size mismatch"
        assert state["issues_resolved"][0]["solution"] == "Fixed in scene 2"
        assert "High render latency detected" in state["warnings"]

    def test_transcript_cleaner_integration(self):
        """التحقق من التكامل مع transcript_cleaner عند تجاوز 50 دورة في المحادثة"""
        with patch.object(context_compactor, "get_current_session_id", return_value="sess_123"), \
             patch.object(context_compactor, "count_turns", return_value=60), \
             patch("subprocess.run") as mock_sub:
            context_compactor.compact(self.project_id)
            assert mock_sub.called
            call_args = mock_sub.call_args[0][0]
            assert "transcript_cleaner.py" in str(call_args)
            assert "sess_123" in call_args

            state = context_compactor.load_state(self.project_id)
            assert any("تنظيف السجل التلقائي" in str(i) for i in state["issues_resolved"])

    def test_utf8_encoding(self):
        """التحقق من ترميز UTF-8 الصحيح دون أي تشويه للأحرف العربية والإيموجي"""
        arabic_text = "✨ تجربة النصوص العربية الفصحى مع التشكيل والرموز 🚀"
        context_compactor.add_decision(self.project_id, arabic_text, "approved")
        state = context_compactor.load_state(self.project_id)
        assert state["approved_decisions"][0]["text"] == arabic_text

        digest_file = self.projects_dir / self.project_id / "session_digest.md"
        content = digest_file.read_text(encoding="utf-8")
        assert arabic_text in content

    def test_show_digest(self, capsys):
        """التحقق من طباعة محتوى session_digest.md عبر دالة show"""
        context_compactor.compact(self.project_id)
        context_compactor.show(self.project_id)
        captured = capsys.readouterr()
        assert "ملخص الجلسة" in captured.out

    def test_load_state_default_values(self):
        """التحقق من إرجاع البنية الافتراضية عند عدم وجود ملف حالة مسبق"""
        fresh_state = context_compactor.load_state("completely_fresh_id")
        assert fresh_state["project_id"] == "completely_fresh_id"
        assert fresh_state["approved_decisions"] == []
        assert fresh_state["rejected_decisions"] == []
        assert "current_phase" in fresh_state

    def test_save_state_updates_timestamp(self):
        """التحقق من تحديث حقل last_updated عند حفظ الحالة"""
        state = context_compactor.load_state(self.project_id)
        old_time = "2020-01-01T00:00:00Z"
        state["last_updated"] = old_time
        context_compactor.save_state(self.project_id, state)
        reloaded = context_compactor.load_state(self.project_id)
        assert reloaded["last_updated"] != old_time
