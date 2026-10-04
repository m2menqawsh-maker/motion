"""
tests/ai/audio/test_audio_benchmark.py
======================================
Benchmark foundation tests for Audio Intelligence (S27.16 / AI-13).

Invariants verified:
- Covers all 7 required audio categories (Rule 14):
  clean speech, noise, music, music + speech, clipping, echo, low volume.
- Zero external provider calls for native DSP.
- Real Audio AI Quality Benchmark is recorded explicitly as:
  DEFERRED TO FINAL VALIDATION (Rule 14, 29).
"""

from ai.audio.benchmark.manifest import (
    AudioBenchmarkCategory,
    get_audio_benchmark_manifest,
    get_audio_categories_summary,
)
from ai.audio.benchmark.runner import AudioBenchmarkRunner


def test_audio_benchmark_manifest_mandatory_categories():
    """Verifies that all 7 required audio categories exist in the benchmark manifest."""
    manifest = get_audio_benchmark_manifest()
    assert len(manifest) == 7

    cat_names = {sample.category.value for sample in manifest}
    expected = {
        "clean_speech",
        "noise",
        "music",
        "music_plus_speech",
        "clipping",
        "echo",
        "low_volume",
    }
    assert cat_names == expected
    for sample in manifest:
        assert sample.duration_sec >= 1.0


def test_audio_benchmark_execution_and_metrics():
    """Executes the benchmark runner across procedural fixtures."""
    runner = AudioBenchmarkRunner()
    report = runner.evaluate_architecture_and_dsp_gate()

    assert report.total_categories_tested == 7
    assert report.dsp_provider_calls_count == 0
    assert report.gate_s27_16_architecture_status == "PASS"
    assert report.fixtures_verified["clean_speech_valid"] is True
    assert report.fixtures_verified["clipping_detected"] is True
    assert report.fixtures_verified["noise_profile_detected"] is True
    assert report.fixtures_verified["low_volume_detected"] is True


def test_audio_ai_quality_certification_deferred_to_final_validation():
    """
    Mandatory Gate (Rule 14, 29):
    Real Audio AI Quality Benchmark must NOT falsely claim production quality PASS.
    Status must be explicitly DEFERRED TO FINAL VALIDATION.
    """
    runner = AudioBenchmarkRunner()
    report = runner.evaluate_architecture_and_dsp_gate()

    assert report.audio_ai_quality_benchmark_status == "DEFERRED TO FINAL VALIDATION"
    assert "DEFERRED TO FINAL VALIDATION" in report.notes
