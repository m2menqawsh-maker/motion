"""
ai/vision/benchmark/__init__.py
===============================
"""

from ai.vision.benchmark.manifest import (
    PROJECT_VISION_BENCHMARK_CORPUS,
    VisionBenchmarkCategory,
    VisionBenchmarkSample,
    get_vision_benchmark_manifest,
    get_vision_categories_summary,
)
from ai.vision.benchmark.metrics import (
    calculate_ocr_word_accuracy,
    calculate_shot_recall_and_precision,
)
from ai.vision.benchmark.runner import (
    VisionBenchmarkReport,
    VisionBenchmarkRunner,
)

__all__ = [
    "PROJECT_VISION_BENCHMARK_CORPUS",
    "VisionBenchmarkCategory",
    "VisionBenchmarkSample",
    "get_vision_benchmark_manifest",
    "get_vision_categories_summary",
    "calculate_shot_recall_and_precision",
    "calculate_ocr_word_accuracy",
    "VisionBenchmarkReport",
    "VisionBenchmarkRunner",
]
