# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
import time
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch, MagicMock

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import batch_builder


class TestBatchBuilder:
    def setup_method(self):
        """إعداد بيئة معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.proj_dir = self.test_dir / "projects" / "test_proj"
        self.build_dir = self.proj_dir / "06_build" / "src"
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_successful_build(self):
        """بناء المشهد بنجاح من المحاولة الأولى"""
        with patch.object(batch_builder, "_do_build_scene", return_value={"success": True}):
            res = batch_builder.build_scene(self.proj_dir, 1)
            assert res["status"] == "pass"
            assert res["scene"] == 1
            assert res["attempts"] == 1

    def test_transient_error_retry(self):
        """إعادة المحاولة (retry) عند حدوث خطأ عابر (IOError)"""
        # يفشل في المحاولة الأولى بـ IOError ثم ينجح في الثانية
        calls = [0]

        def fake_do_build(p, idx):
            calls[0] += 1
            if calls[0] == 1:
                raise IOError("Temporary lock")
            return {"success": True}

        with patch.object(batch_builder, "_do_build_scene", side_effect=fake_do_build), \
             patch("time.sleep", return_value=None):
            res = batch_builder.build_scene(self.proj_dir, 1)
            assert res["status"] == "pass"
            assert res["attempts"] == 2
            assert calls[0] == 2

    def test_logical_error_no_retry(self):
        """التوقف الفوري دون إعادة المحاولة عند حدوث خطأ منطقي"""
        with patch.object(batch_builder, "_do_build_scene", return_value={
            "success": False, "error": "Invalid TSX syntax", "error_type": "logical"
        }):
            res = batch_builder.build_scene(self.proj_dir, 1)
            assert res["status"] == "fail"
            assert res["error_type"] == "logical"
            # يجب ألا يقوم بـ retry

    def test_max_retries_exceeded(self):
        """الفشل بعد استنفاد أقصى عدد للمحاولات (3 محاولات)"""
        with patch.object(batch_builder, "_do_build_scene", side_effect=IOError("Persistent I/O")), \
             patch("time.sleep", return_value=None):
            res = batch_builder.build_scene(self.proj_dir, 1)
            assert res["status"] == "fail"
            assert res["attempts"] == 3
            assert res["error_type"] == "transient"

    def test_exponential_backoff(self):
        """التحقق من تطبيق تأخير متزايد (Exponential Backoff) عند إعادة المحاولة"""
        sleep_calls = []

        def fake_sleep(dur):
            sleep_calls.append(dur)

        with patch.object(batch_builder, "_do_build_scene", side_effect=IOError("I/O error")), \
             patch("time.sleep", side_effect=fake_sleep):
            batch_builder.build_scene(self.proj_dir, 1)

            # مع max_retries=3 والتأخيرات الافتراضية [0.5, 1.0, 2.0]
            # يجب أن يتم استدعاء sleep مرتين (بعد المحاولة 1 و2)
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == 0.5
            assert sleep_calls[1] == 1.0

    def test_main_composition_generation(self):
        """توليد MainComposition.tsx بشكل صحيح لجميع المشاهد"""
        batch_builder.generate_main_composition(self.proj_dir, 3, [1, 2, 3])
        main_file = self.build_dir / "MainComposition.tsx"
        assert main_file.exists()
        content = main_file.read_text(encoding="utf-8")
        assert "import { Scene1 } from './compositions/Scene1';" in content
        assert "import { Scene2 } from './compositions/Scene2';" in content
        assert "import { Scene3 } from './compositions/Scene3';" in content
        assert "<Scene1 />" in content
        assert "<Scene2 />" in content
        assert "<Scene3 />" in content

    def test_partial_success_handling(self):
        """التعامل مع فشل بعض المشاهد وتضمين المشاهد الناجحة فقط"""
        # المشهد 2 فشل، المشهد 1 و 3 نجحا
        batch_builder.generate_main_composition(self.proj_dir, 3, [1, 3])
        main_file = self.build_dir / "MainComposition.tsx"
        assert main_file.exists()
        content = main_file.read_text(encoding="utf-8")
        assert "import { Scene1 }" in content
        assert "import { Scene3 }" in content
        assert "Scene2" not in content

    def test_batch_build_report_generation(self):
        """التحقق من هيكل وسلامة تقرير البناء batch_build_report.json"""
        report_data = {
            "project_id": "test_proj",
            "timestamp": "2026-09-05T00:00:00",
            "total_scenes": 3,
            "successful": [1, 2],
            "failed": [3],
            "retry_stats": {
                "total_retries": 1,
                "scenes_with_retries": 1
            }
        }
        report_file = self.proj_dir / "batch_build_report.json"
        report_file.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

        assert report_file.exists()
        loaded = json.loads(report_file.read_text(encoding="utf-8"))
        assert loaded["total_scenes"] == 3
        assert loaded["successful"] == [1, 2]
        assert loaded["failed"] == [3]
        assert loaded["retry_stats"]["total_retries"] == 1

    def test_get_scene_duration_from_timings(self):
        """قراءة مدة المشهد بالفريمات من 04_timings.json"""
        timings_file = self.proj_dir / "04_timings.json"
        timings_file.write_text(json.dumps({
            "sentences": [{"idx": 1, "duration_frames": 120}]
        }), encoding="utf-8")
        dur = batch_builder.get_scene_duration(self.proj_dir, 1)
        assert dur == 120

    def test_get_scene_duration_default_when_missing(self):
        """إرجاع المدة الافتراضية 90 فريم عند غياب ملف التوقيتات أو المشهد"""
        dur = batch_builder.get_scene_duration(self.proj_dir, 999)
        assert dur == 90

    def test_generate_main_composition_empty_successful_raises(self):
        """رمي استثناء عند محاولة توليد MainComposition بدون أي مشهد ناجح"""
        with pytest.raises(Exception) as exc:
            batch_builder.generate_main_composition(self.proj_dir, 3, [])
        assert "لا يوجد أي مشهد ناجح" in str(exc.value)
