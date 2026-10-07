"""
ai/speech/benchmark/__init__.py
===============================
Benchmark manifest and metrics harness package (S27.14).
"""

from ai.speech.benchmark.corpus_manifest import (
    BenchmarkReferenceSegment,
    BenchmarkSample,
    PROJECT_SPEECH_BENCHMARK_CORPUS,
    get_corpus_manifest,
    get_corpus_categories_summary,
)
from ai.speech.benchmark.metrics import (
    calculate_cer,
    calculate_diarization_error,
    calculate_language_accuracy,
    calculate_levenshtein_distance,
    calculate_timestamp_error,
    calculate_wer,
    normalize_text_for_wer,
)
from ai.speech.benchmark.runner import (
    CandidateBenchmarkResult,
    CandidateThresholds,
    SpeechBenchmarkReport,
    SpeechBenchmarkRunner,
)

__all__ = [
    "BenchmarkReferenceSegment",
    "BenchmarkSample",
    "PROJECT_SPEECH_BENCHMARK_CORPUS",
    "get_corpus_manifest",
    "get_corpus_categories_summary",
    "calculate_cer",
    "calculate_diarization_error",
    "calculate_language_accuracy",
    "calculate_levenshtein_distance",
    "calculate_timestamp_error",
    "calculate_wer",
    "normalize_text_for_wer",
    "CandidateBenchmarkResult",
    "CandidateThresholds",
    "SpeechBenchmarkReport",
    "SpeechBenchmarkRunner",
]
