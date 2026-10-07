"""
tests/ai/speech/test_benchmark_harness.py
=========================================
Tests for Speech Benchmark Manifest and Quality Gate Promotion (S27.14 Rules 23, 24, 27, 30, 41, 43).
"""

from decimal import Decimal
import pytest

from ai.speech.benchmark.corpus_manifest import (
    CorpusRequirementLevel,
    PROJECT_SPEECH_BENCHMARK_CORPUS,
    get_corpus_categories_summary,
    get_corpus_manifest,
    get_optional_corpus,
    get_required_gate_corpus,
)
from ai.speech.benchmark.runner import (
    CandidateBenchmarkResult,
    CandidateThresholds,
    SpeechBenchmarkReport,
    SpeechBenchmarkRunner,
)


def test_corpus_manifest_mandatory_categories_coverage():
    """
    Mandatory Test (Rule 23):
    Corpus covers: Arabic MSA, Palestinian Arabic, Arabic-English code switching,
    fast speech, noisy speech, music under speech, male voice, female voice, multiple speakers.
    """
    summary = get_corpus_categories_summary()

    # Category checks
    assert summary.get("ar_msa", 0) >= 1
    assert summary.get("ar_palestinian", 0) >= 1
    assert summary.get("code_switch_ar_en", 0) >= 1
    assert summary.get("fast_speech", 0) >= 1
    assert summary.get("noisy", 0) >= 1
    assert summary.get("music_under_speech", 0) >= 1
    assert summary.get("male", 0) >= 1
    assert summary.get("female", 0) >= 1
    assert summary.get("multi_speaker", 0) >= 1


def test_palestinian_arabic_is_optional_coverage():
    """
    Mandatory Test:
    Verifies that Palestinian Arabic is classified as OPTIONAL_COVERAGE
    rather than a blocking product gate requirement unless explicitly mandated by an ADR.
    """
    corpus = get_corpus_manifest()
    pal_sample = next((s for s in corpus if s.language_category == "ar_palestinian"), None)

    assert pal_sample is not None
    assert pal_sample.requirement_level == CorpusRequirementLevel.OPTIONAL_COVERAGE.value
    assert pal_sample.has_real_audio_file is False
    assert "dialect" in pal_sample.audio_characteristics


def test_required_gate_corpus_contains_mandatory_production_categories():
    """
    Mandatory Test:
    Verifies that the required gate corpus specifically contains the core voiceover
    scenarios (MSA, Male, Female, Fast Speech, Music Bed, Multi-Speaker for Diarization).
    """
    required_samples = get_required_gate_corpus()
    sample_ids = {s.sample_id for s in required_samples}

    assert "corpus_ar_msa_001" in sample_ids
    assert "corpus_female_voice_001" in sample_ids
    assert "corpus_fast_speech_001" in sample_ids
    assert "corpus_music_under_speech_001" in sample_ids
    assert "corpus_multi_speaker_001" in sample_ids

    # Optional samples must not block the core gate
    assert "corpus_ar_palestinian_001" not in sample_ids
    assert "corpus_noisy_speech_001" not in sample_ids
    assert "corpus_code_switch_001" not in sample_ids

    optional_samples = get_optional_corpus()
    optional_ids = {s.sample_id for s in optional_samples}
    assert "corpus_ar_palestinian_001" in optional_ids
    assert "corpus_noisy_speech_001" in optional_ids
    assert "corpus_code_switch_001" in optional_ids


def test_default_model_gate_rejects_substandard_candidate():
    """
    Mandatory Test (Rule 30):
    Model with WER exceeding quality floor is rejected from promotion.
    """
    runner = SpeechBenchmarkRunner(CandidateThresholds(max_wer=0.15))
    corpus = get_corpus_manifest()

    # Synthetic run where model has 30% WER
    sample_results = [
        {
            "sample_id": s.sample_id,
            "transcript": "نص خاطئ جدا مليء بالاخطاء والكلمات الزائدة",
            "language": "ar",
            "intervals": [],
            "speaker_turns": [],
        }
        for s in corpus
    ]

    candidate = runner.evaluate_candidate(
        model_id="bad-stt-v1",
        provider_id="bad-provider",
        sample_results=sample_results,
        cost_per_minute=Decimal("0.02"),
        latency_per_minute_sec=5.0,
        is_synthetic_simulation=False,
    )

    assert candidate.status == "NOT APPROVED"
    assert any("exceeds quality floor" in r for r in candidate.rejection_reasons)


def test_quality_gate_blocks_promotion_on_insufficient_data():
    """
    Mandatory Test (Rule 43):
    In offline environment with synthetic/incomplete data, gate reports:
    S27.13 = PASS
    S27.14 = BLOCKED ON REAL BENCHMARK
    AI-12 = INCOMPLETE
    Default Promoted = NO
    """
    runner = SpeechBenchmarkRunner()

    candidate = runner.evaluate_candidate(
        model_id="whisper-large-v3",
        provider_id="local",
        sample_results=[],  # No live production runs
        cost_per_minute=Decimal("0.00"),
        latency_per_minute_sec=4.0,
        is_synthetic_simulation=True,
    )

    assert candidate.status == "INSUFFICIENT DATA"

    report = runner.generate_benchmark_report([candidate])

    assert report.gate_s27_13_status == "PASS"
    assert report.gate_s27_14_status == "BLOCKED ON REAL BENCHMARK"
    assert report.overall_ai12_status == "INCOMPLETE"
    assert report.promoted_default_model is None
    assert "Representative real human speech" in report.notes
