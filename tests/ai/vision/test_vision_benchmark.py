"""
tests/ai/vision/test_vision_benchmark.py
========================================
Tests for Vision Intelligence Benchmark Manifest and Quality Gate Promotion (S27.15 Rules 27, 28, 34).
"""

from ai.vision.benchmark.manifest import (
    PROJECT_VISION_BENCHMARK_CORPUS,
    get_vision_benchmark_manifest,
    get_vision_categories_summary,
)
from ai.vision.benchmark.metrics import (
    calculate_ocr_word_accuracy,
    calculate_shot_recall_and_precision,
)
from ai.vision.benchmark.runner import VisionBenchmarkRunner


def test_vision_benchmark_manifest_mandatory_categories():
    """
    Mandatory Test (Rule 27):
    Verifies coverage of all 11 mandatory visual domains:
    talking head, product video, screen recording, B-roll, UI demo, motion graphics,
    vertical video, horizontal video, Arabic text, English text, low light.
    """
    summary = get_vision_categories_summary()
    assert summary.get("talking_head", 0) >= 1
    assert summary.get("product_video", 0) >= 1
    assert summary.get("screen_recording", 0) >= 1
    assert summary.get("b_roll", 0) >= 1
    assert summary.get("ui_demo", 0) >= 1
    assert summary.get("motion_graphics", 0) >= 1
    assert summary.get("vertical_video", 0) >= 1
    assert summary.get("horizontal_video", 0) >= 1
    assert summary.get("arabic_text", 0) >= 1
    assert summary.get("english_text", 0) >= 1
    assert summary.get("low_light", 0) >= 1


def test_vision_benchmark_metrics():
    # Shot recall and precision
    pred_cuts = [2.0, 4.0, 6.0]
    gt_cuts = [2.0, 4.1, 8.0]
    recall, precision, f1 = calculate_shot_recall_and_precision(pred_cuts, gt_cuts, tolerance_seconds=0.2)
    assert recall == 0.667
    assert precision == 0.667

    # OCR accuracy
    pred_words = ["مرحبا", "بكم", "في", "المنصة"]
    gt_words = ["مرحبا", "بكم", "في", "منصة", "الفيديو"]
    acc = calculate_ocr_word_accuracy(pred_words, gt_words)
    assert acc == 0.60


def test_vision_quality_certification_deferred_to_final_validation():
    """
    Mandatory Test (Rule 34):
    Verifies that the architecture/functionality gate is PASS,
    while real visual quality certification is strictly DEFERRED TO FINAL VALIDATION.
    """
    runner = VisionBenchmarkRunner()
    report = runner.evaluate_architecture_gate()

    assert report.gate_s27_15_architecture_status == "PASS"
    assert report.real_vision_quality_benchmark_status == "DEFERRED TO FINAL VALIDATION"
    assert "DEFERRED TO FINAL VALIDATION" in report.notes
    assert report.total_categories_covered == 11
