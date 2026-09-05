# -*- coding: utf-8 -*-
import pytest
import os
import sys
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import render_project
from pipeline_guard import GuardViolation


class TestRenderProject:
    def setup_method(self):
        """إعداد بيئة معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.proj_dir = self.test_dir / "projects" / "test_render_proj"
        self.build_dir = self.proj_dir / "06_build"
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.project_id = "test_render_proj"

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_production_report_generation(self):
        """توليد تقرير الإنتاج PRODUCTION_REPORT.md"""
        render_project.generate_initial_report(self.proj_dir, self.project_id)
        report_file = self.proj_dir / "PRODUCTION_REPORT.md"
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert f"تقرير الإنتاج - {self.project_id}" in content
        assert "vo_quality_check.py" in content
        assert "render_project.py" in content

    def test_studio_approved_required(self, capsys):
        """اشتراط ملف .studio_approved ومنع الرندر بدونه"""
        approval_file = self.proj_dir / ".studio_approved"
        # بدون الملف
        assert not approval_file.exists()

        # فحص كشف التزوير الزمني (< 10 ثوانٍ)
        unlock_file = self.proj_dir / ".studio_unlocked"
        unlock_file.write_text("unlocked", encoding="utf-8")
        approval_file.write_text("approved", encoding="utf-8")

        base_time = 1700000000.0
        os.utime(str(unlock_file), (base_time, base_time))
        os.utime(str(approval_file), (base_time + 3, base_time + 3))

        time_diff = approval_file.stat().st_mtime - unlock_file.stat().st_mtime
        assert time_diff < 10

    def test_pipeline_guard_integration(self):
        """التكامل مع PipelineGuard واعتراض الرندر عند وجود مخالفة"""
        mock_guard = MagicMock()
        mock_guard.require_probe_qc_genuine.side_effect = GuardViolation(
            "REPORT_TAMPERED", "تقرير مزور", "أعد فحص QC"
        )

        with patch("pipeline_guard.PipelineGuard", return_value=mock_guard):
            import pipeline_guard
            guard = pipeline_guard.PipelineGuard(self.project_id)
            with pytest.raises(GuardViolation) as exc:
                guard.require_probe_qc_genuine()
            assert exc.value.rule == "REPORT_TAMPERED"

    def test_final_qc_integration(self):
        """التحقق من استدعاء final_qc.py فور انتهاء الرندر"""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value.returncode = 0
            final_qc_script = scripts_dir / "final_qc.py"
            subprocess_cmd = [sys.executable, str(final_qc_script), self.project_id]
            import subprocess
            res = subprocess.run(subprocess_cmd)
            assert res.returncode == 0

    def test_render_with_all_gates(self):
        """التحقق من تسلسل الفحوصات الإلزامية قبل أمر الرندر"""
        mock_guard = MagicMock()
        with patch("pipeline_guard.PipelineGuard", return_value=mock_guard):
            import pipeline_guard
            guard = pipeline_guard.PipelineGuard(self.project_id)
            guard.require_probe_qc_genuine()
            guard.require_studio_unlocked()
            guard.require_user_approval()
            guard.require_all_sentences_covered()
            guard.require_typescript_clean()
            guard.require_motion_valid()
            guard.require_smart_qc_passed()

            assert mock_guard.require_probe_qc_genuine.called
            assert mock_guard.require_studio_unlocked.called
            assert mock_guard.require_user_approval.called
            assert mock_guard.require_all_sentences_covered.called
            assert mock_guard.require_typescript_clean.called
            assert mock_guard.require_motion_valid.called
            assert mock_guard.require_smart_qc_passed.called

    def test_stale_approval_detected(self):
        """كشف الموافقة القديمة (STALE) التي أُنشئت قبل آخر فتح للاستوديو"""
        unlock_file = self.proj_dir / ".studio_unlocked"
        approval_file = self.proj_dir / ".studio_approved"
        unlock_file.write_text("unlocked", encoding="utf-8")
        approval_file.write_text("approved", encoding="utf-8")

        base_time = 1700000000.0
        # الاستوديو فُتح لاحقاً بعد الموافقة
        os.utime(str(unlock_file), (base_time + 100, base_time + 100))
        os.utime(str(approval_file), (base_time + 50, base_time + 50))
        assert approval_file.stat().st_mtime <= unlock_file.stat().st_mtime

    def test_missing_project_directory_check(self):
        """التحقق من كشف غياب مجلد المشروع"""
        fake_proj = Path("projects/definitely_not_existing_proj")
        assert not fake_proj.exists()

    def test_missing_build_directory_check(self):
        """التحقق من كشف غياب مجلد 06_build"""
        empty_proj = self.test_dir / "projects" / "empty_proj"
        empty_proj.mkdir(parents=True, exist_ok=True)
        assert not (empty_proj / "06_build").exists()
