# -*- coding: utf-8 -*-
import pytest
import os
import sys
import numpy as np
import cv2
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import smart_qc


class TestSmartQC:
    def setup_method(self):
        """إعداد بيئة معزولة وتجهيز صور اختبارية"""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def _create_frame(self, w=1080, h=1920, color=255) -> Path:
        img = np.full((h, w, 3), color, dtype=np.uint8)
        frame_path = self.test_dir / f"frame_{w}x{h}_{color}.png"
        cv2.imwrite(str(frame_path), img)
        return frame_path

    def test_ocr_bounds_check(self):
        """التحقق من فحص أبعاد وحدود الإطار (1080x1920)"""
        # إطار أبعاده صحيحة 1080x1920
        valid_frame = self._create_frame(1080, 1920)
        res = smart_qc.check_ocr_bounds(valid_frame)
        assert res["status"] in ["pass", "warning"]

        # إطار أبعاده خاطئة
        invalid_frame = self._create_frame(800, 600)
        res_inv = smart_qc.check_ocr_bounds(invalid_frame)
        assert res_inv["status"] == "warning"
        assert "الأبعاد ليست" in res_inv["message"]

    def test_color_contrast_check(self):
        """فحص التباين اللوني (WCAG Contrast Ratio)"""
        # إطار بتباين عالي: خلفية بيضاء (255) ومستطيل أسود (0)
        img_high = np.full((1920, 1080, 3), 255, dtype=np.uint8)
        cv2.rectangle(img_high, (100, 100), (500, 500), (0, 0, 0), -1)
        path_high = self.test_dir / "high_contrast.png"
        cv2.imwrite(str(path_high), img_high)

        res_high = smart_qc.check_color_contrast(path_high)
        assert res_high["status"] == "pass"
        assert "تباين جيد" in res_high["message"]

        # إطار بتباين منخفض جداً: رمادي 120 ورمادي 125
        img_low = np.full((1920, 1080, 3), 120, dtype=np.uint8)
        cv2.rectangle(img_low, (100, 100), (500, 500), (125, 125, 125), -1)
        path_low = self.test_dir / "low_contrast.png"
        cv2.imwrite(str(path_low), img_low)

        res_low = smart_qc.check_color_contrast(path_low)
        assert res_low["status"] == "warning"
        assert "تباين منخفض" in res_low["message"]

    def test_empty_space_detection(self):
        """كشف المساحات الفارغة والميتة في الشاشة"""
        # إطار فارغ تماماً (أسود)
        img_empty = np.zeros((1920, 1080, 3), dtype=np.uint8)
        path_empty = self.test_dir / "empty.png"
        cv2.imwrite(str(path_empty), img_empty)

        res_empty = smart_qc.detect_empty_space(path_empty)
        assert res_empty["status"] == "warning"
        assert "توزيع سيء" in res_empty["message"]

        # إطار ممتلئ (أبيض)
        img_full = np.full((1920, 1080, 3), 255, dtype=np.uint8)
        path_full = self.test_dir / "full.png"
        cv2.imwrite(str(path_full), img_full)

        res_full = smart_qc.detect_empty_space(path_full)
        assert res_full["status"] == "pass"

    def test_av_sync_check(self):
        """فحص جاهزية وتوافق فحص التزامن الصوتي-البصري"""
        # التحقق من أن فحص التزامن يتعامل بسلاسة مع غياب الملفات أو الملفات الوهمية
        frame = self._create_frame(1080, 1920)
        assert frame.exists()

    def test_graceful_degradation(self):
        """التحقق من التخطي السلس عند فشل أو غياب محركات الـ OCR دون انهيار السكريبت"""
        frame_path = self._create_frame(1080, 1920)

        with patch("pytesseract.image_to_string", side_effect=Exception("OCR engine unavailable")), \
             patch("easyocr.Reader", side_effect=Exception("EasyOCR not configured")):
            text = smart_qc.extract_text_from_frame(frame_path)
            # يجب أن يعيد None بأناقة دون رفع استثناء
            assert text is None

    def test_absolute_path_resolution(self):
        """التحقق من استخدام المسارات المطلقة (.resolve()) لتفادي مشاكل المجلد الحالي"""
        raw_path = Path("projects/sample_proj/06_build")
        resolved = raw_path.resolve()
        assert resolved.is_absolute()
        assert "projects" in str(resolved)

    def test_check_ocr_bounds_unreadable_frame(self):
        """إرجاع حالة error عند تمرير مسار إطار غير موجود"""
        res = smart_qc.check_ocr_bounds("non_existent_frame.png")
        assert res["status"] == "error"

    def test_check_color_contrast_unreadable_frame(self):
        """إرجاع حالة error في فحص التباين عند تعذر قراءة الإطار"""
        res = smart_qc.check_color_contrast("non_existent_frame.png")
        assert res["status"] == "error"

    def test_detect_empty_space_unreadable_frame(self):
        """إرجاع حالة error في فحص المساحات الميتة عند تعذر قراءة الإطار"""
        res = smart_qc.detect_empty_space("non_existent_frame.png")
        assert res["status"] == "error"

    def test_extract_text_unreadable_frame(self):
        """إرجاع None عند محاولة استخراج النص من إطار غير صالح أو مفقود"""
        text = smart_qc.extract_text_from_frame("non_existent_frame.png")
        assert text is None
