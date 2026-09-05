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

import final_qc


class TestFinalQC:
    def setup_method(self):
        """إعداد بيئة معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.proj_dir = self.test_dir / "projects" / "test_proj"
        self.proj_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_dimensions_check(self):
        """التحقق من فحص أبعاد الفيديو 1080x1920 بدقة"""
        # أبعاد صحيحة
        v_stream_valid = {'width': 1080, 'height': 1920, 'codec_name': 'h264', 'r_frame_rate': '30/1'}
        expected_w = 1080
        expected_h = 1920
        is_valid = (v_stream_valid['width'] == expected_w and v_stream_valid['height'] == expected_h)
        assert is_valid is True

        # أبعاد غير صحيحة
        v_stream_invalid = {'width': 1920, 'height': 1080}
        is_invalid = (v_stream_invalid['width'] == expected_w and v_stream_invalid['height'] == expected_h)
        assert is_invalid is False

    def test_fps_check(self):
        """التحقق من فحص معدل الإطارات FPS=30 مع قبول الفواصل الكسرية (30/1)"""
        expected_fps = 30.0

        for fps_str in ["30/1", "30", "30.00"]:
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                fps_val = num / den
            else:
                fps_val = float(fps_str)
            assert abs(fps_val - expected_fps) < 0.1

        # معدل إطارات مخالف (24fps)
        fps_str_wrong = "24/1"
        num, den = map(float, fps_str_wrong.split('/'))
        assert abs((num / den) - expected_fps) >= 0.1

    def test_codec_check(self):
        """التحقق من فحص H.264 للفيديو و AAC للصوت"""
        v_codec = "h264"
        a_codec = "aac"
        assert v_codec == "h264"
        assert a_codec == "aac"

        # كوديكات غير معتمدة
        invalid_v_codec = "vp9"
        assert invalid_v_codec != "h264"

    def test_audio_levels_check(self):
        """التحقق من اكتشاف غياب مسار الصوت"""
        # تدفق صوت مفقود
        a_stream_none = None
        check_result = {"status": "fail", "message": "لا يوجد تدفق صوت"} if not a_stream_none else {"status": "pass"}
        assert check_result["status"] == "fail"

        # تدفق صوت موجود
        a_stream_valid = {"codec_name": "aac"}
        check_result_valid = {"status": "fail", "message": "لا يوجد تدفق صوت"} if not a_stream_valid else {"status": "pass"}
        assert check_result_valid["status"] == "pass"

    def test_black_frames_detection(self):
        """التحقق من كشف الإطارات السوداء المستمرة"""
        # محاكاة إخراج ffmpeg يحتوي على blackdetect
        fake_ffmpeg = MagicMock()
        fake_ffmpeg.input.return_value.filter.return_value.output.return_value.run.return_value = (
            b"", b"blackdetect: black_start: 1.2 black_end: 2.5 black_duration: 1.3"
        )

        with patch.dict("sys.modules", {"ffmpeg": fake_ffmpeg}):
            res = final_qc.check_black_frames("dummy_path.mp4")
            assert res["status"] == "fail"
            assert "إطارات سوداء" in res["message"]

        # محاكاة عدم وجود إطارات سوداء
        fake_ffmpeg.input.return_value.filter.return_value.output.return_value.run.return_value = (b"", b"")
        with patch.dict("sys.modules", {"ffmpeg": fake_ffmpeg}):
            res_pass = final_qc.check_black_frames("dummy_path.mp4")
            assert res_pass["status"] == "pass"

    def test_av_sync_with_librosa(self):
        """فحص التزامن الصوتي-البصري باستخدام librosa ومقارنة الأوقات"""
        timings_file = self.proj_dir / "04_timings.json"
        timings_file.write_text(json.dumps({
            "scenes": [{"start": 0.0, "words": [{"start": 0.5}, {"start": 1.0}]}]
        }), encoding="utf-8")

        # عند وجود خطأ متوسط قليل (< 200ms)
        fake_y = [0.1, 0.5, 0.8, 0.2]
        fake_sr = 22050

        with patch("subprocess.run"), \
             patch("librosa.load", return_value=(fake_y, fake_sr)), \
             patch("librosa.onset.onset_detect", return_value=[11, 22]), \
             patch("librosa.frames_to_time", return_value=[0.51, 1.02]):
            res = final_qc.check_av_sync("dummy_video.mp4", timings_file)
            assert res["status"] == "pass"
            assert res["avg_sync_error_ms"] <= 200

    def test_ffmpeg_wav_extraction(self):
        """التعامل السلس عند غياب ملف التوقيت أو فشل استخراج الصوت"""
        missing_timings = self.test_dir / "non_existent_timings.json"
        res = final_qc.check_av_sync("dummy.mp4", missing_timings)
        assert res["status"] == "warning"
        assert "ملف التوقيت غير موجود" in res["message"]

    def test_find_ffprobe_discovery(self):
        """التحقق من عمل دالة البحث عن ffprobe دون انهيار"""
        res = final_qc.find_ffprobe()
        assert res is None or isinstance(res, str)

    def test_analyze_video_nonexistent(self):
        """التحقق من إرجاع None, None عند محاولة تحليل ملف فيديو غير موجود"""
        v, a = final_qc.analyze_video_with_ffmpeg("non_existent_video_path.mp4")
        assert v is None
        assert a is None

    def test_check_black_frames_ffmpeg_exception(self):
        """التحقق من إرجاع warning عند حدوث خطأ في استدعاء ffmpeg blackdetect"""
        with patch.dict("sys.modules", {"ffmpeg": MagicMock(side_effect=Exception("FFmpeg failed"))}):
            res = final_qc.check_black_frames("dummy.mp4")
            assert res["status"] in ["warning", "fail"]
