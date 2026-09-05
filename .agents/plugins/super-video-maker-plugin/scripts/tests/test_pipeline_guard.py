# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
import time
import hashlib
from pathlib import Path
import tempfile
import shutil

# Ensure scripts can be imported
scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from pipeline_guard import PipelineGuard, GuardViolation


class TestPipelineGuard:
    def setup_method(self):
        """إعداد بيئة اختبار معزولة في مجلد مؤقت"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.orig_cwd = os.getcwd()
        os.chdir(str(self.test_dir))
        (self.test_dir / "projects").mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        os.chdir(self.orig_cwd)
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def _create_project(self, project_id: str) -> Path:
        proj_dir = self.test_dir / "projects" / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir

    def test_audio_free_bypass(self):
        """تجاوز فحص الصوت للمشاريع الصامتة"""
        proj_dir = self._create_project("proj_silent")
        state_file = proj_dir / ".session_state.json"
        state_file.write_text(json.dumps({"audio_free": True}), encoding="utf-8")

        guard = PipelineGuard("proj_silent")
        # لا يرمي استثناء عند طلب فحص الصوت للمشروع الصامت
        guard.require_vo_quality_check()
        guard.require_stage_complete("audio_analysis")
        guard.require_all_sentences_covered()

    def test_experimental_bypass(self):
        """تجاوز المشاريع التجريبية"""
        proj_dir = self._create_project("proj_exp")
        state_file = proj_dir / ".session_state.json"
        state_file.write_text(json.dumps({"experimental": True}), encoding="utf-8")

        guard = PipelineGuard("proj_exp")
        # لا يرمي استثناء في فحص جودة الصوت
        guard.require_vo_quality_check()

    def test_skip_backup_bypass(self):
        """تجاوز النسخة الاحتياطية"""
        proj_dir = self._create_project("proj_backup_skip")
        state_file = proj_dir / ".session_state.json"
        state_file.write_text(json.dumps({"skip_backup": True}), encoding="utf-8")

        guard = PipelineGuard("proj_backup_skip")
        # لا يرمي استثناء عند طلب النسخة الاحتياطية
        guard.require_auto_backup()

    def test_missing_vo_check_raises(self):
        """رفض بدون فحص صوت"""
        proj_dir = self._create_project("proj_no_vo")
        guard = PipelineGuard("proj_no_vo")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_vo_quality_check()
        assert "VO_QUALITY_CHECK_MISSING" in str(excinfo.value)

    def test_missing_backup_raises(self):
        """رفض بدون نسخة احتياطية"""
        proj_dir = self._create_project("proj_no_backup")
        guard = PipelineGuard("proj_no_backup")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_auto_backup()
        assert "AUTO_BACKUP_MISSING" in str(excinfo.value)

    def test_missing_plan_raises(self):
        """رفض بدون خطة"""
        proj_dir = self._create_project("proj_no_plan")
        guard = PipelineGuard("proj_no_plan")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_stage_complete("plan")
        assert "STAGE_INCOMPLETE" in str(excinfo.value)

    def test_seal_verification(self):
        """التحقق من الختم الرقمي SHA-256"""
        proj_dir = self._create_project("proj_seal")
        report_file = proj_dir / "probe_qc_report.json"
        report_file.write_text(json.dumps({"status": "pass", "score": 98}), encoding="utf-8")

        # قبل الختم: التحقق يفشل
        assert not PipelineGuard.verify_report_seal(report_file)

        # ختم الملف
        PipelineGuard.seal_report(report_file)
        assert PipelineGuard.verify_report_seal(report_file)

        # تعديل الملف يدوياً: التحقق يفشل
        report_file.write_text(json.dumps({"status": "pass", "score": 100}), encoding="utf-8")
        assert not PipelineGuard.verify_report_seal(report_file)

    def test_studio_unlock_required(self):
        """اشتراط .studio_unlocked"""
        proj_dir = self._create_project("proj_studio_lock")
        guard = PipelineGuard("proj_studio_lock")

        # مقفل: يرمي استثناء
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_studio_unlocked()
        assert "STUDIO_LOCKED" in str(excinfo.value)

        # إنشاء ملف الفتح
        unlock_file = proj_dir / ".studio_unlocked"
        unlock_file.write_text("unlocked", encoding="utf-8")
        guard.require_studio_unlocked()  # يمر بنجاح

    def test_studio_approved_required(self):
        """اشتراط .studio_approved وكشف التزوير الزمني"""
        proj_dir = self._create_project("proj_approval")
        guard = PipelineGuard("proj_approval")

        # بدون ملف موافقة
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_user_approval()
        assert "NO_USER_APPROVAL" in str(excinfo.value)

        unlock_file = proj_dir / ".studio_unlocked"
        approval_file = proj_dir / ".studio_approved"

        # سيناريو 1: الموافقة أقدم من فتح الاستوديو (موافقة قديمة STALE)
        unlock_file.write_text("unlocked", encoding="utf-8")
        approval_file.write_text("approved", encoding="utf-8")
        base_time = 1700000000.0
        os.utime(str(unlock_file), (base_time + 100, base_time + 100))
        os.utime(str(approval_file), (base_time + 50, base_time + 50))
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_user_approval()
        assert "STALE_APPROVAL" in str(excinfo.value)

        # سيناريو 2: الموافقة سريعة جداً أقل من 10 ثوانٍ (تزوير FORGED)
        os.utime(str(unlock_file), (base_time, base_time))
        os.utime(str(approval_file), (base_time + 3, base_time + 3))
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_user_approval()
        assert "FORGED_APPROVAL" in str(excinfo.value)

        # سيناريو 3: موافقة سليمة بعد فترة كافية (15 ثانية)
        os.utime(str(approval_file), (base_time + 15, base_time + 15))
        guard.require_user_approval()  # يمر بنجاح

    def test_render_requires_final_qc(self):
        """اشتراط final_qc بعد الرندر والتحقق من نجاحه"""
        proj_dir = self._create_project("proj_final_qc")
        guard = PipelineGuard("proj_final_qc")

        # بدون تقرير final_qc
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_final_qc_passed()
        assert "NO_FINAL_QC" in str(excinfo.value)

        qc_file = proj_dir / "final_qc_report.json"
        # تقرير فاشل
        qc_file.write_text(json.dumps({"status": "fail"}), encoding="utf-8")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_final_qc_passed()
        assert "FINAL_QC_FAILED" in str(excinfo.value)

        # تقرير ناجح
        qc_file.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
        guard.require_final_qc_passed()  # يمر بنجاح

    def test_unknown_stage_raises(self):
        """رفض الاستعلام عن مرحلة غير معروفة"""
        proj_dir = self._create_project("proj_unknown_stage")
        guard = PipelineGuard("proj_unknown_stage")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_stage_complete("non_existent_stage_name")
        assert "UNKNOWN_STAGE" in str(excinfo.value)

    def test_empty_stage_file_raises(self):
        """رفض ملف المرحلة إذا كان فارغاً (0 بايت)"""
        proj_dir = self._create_project("proj_empty_file")
        plan_file = proj_dir / "01_plan.md"
        plan_file.write_text("", encoding="utf-8")
        guard = PipelineGuard("proj_empty_file")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_stage_complete("plan")
        assert "EMPTY_STAGE_FILE" in str(excinfo.value)

    def test_media_in_build_manual_copy_raises(self):
        """كشف النسخ اليدوي للميديا في مجلد 06_build بدون media_map.json"""
        proj_dir = self._create_project("proj_manual_media")
        media_dir = proj_dir / "06_build" / "public" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "sample.mp4").write_bytes(b"dummy")

        guard = PipelineGuard("proj_manual_media")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_media_in_build()
        assert "MANUAL_MEDIA_COPY" in str(excinfo.value)

        # عند إضافة media_map.json
        (proj_dir / "06_build" / "media_map.json").write_text("{}", encoding="utf-8")
        guard.require_media_in_build()  # يمر بنجاح

    def test_missing_scenes_raises(self):
        """كشف نقص المشاهد (Creative Amnesia) مقارنة بالجمل الصوتية"""
        proj_dir = self._create_project("proj_missing_scenes")
        timings_file = proj_dir / "04_timings.json"
        timings_file.write_text(json.dumps({
            "sentences": [{"idx": 1}, {"idx": 2}, {"idx": 3}]
        }), encoding="utf-8")

        comps_dir = proj_dir / "06_build" / "src" / "compositions"
        comps_dir.mkdir(parents=True, exist_ok=True)
        (comps_dir / "Scene1.tsx").write_text("export const Scene1 = () => null;", encoding="utf-8")

        guard = PipelineGuard("proj_missing_scenes")
        with pytest.raises(GuardViolation) as excinfo:
            guard.require_all_sentences_covered()
        assert "MISSING_SCENES" in str(excinfo.value)
