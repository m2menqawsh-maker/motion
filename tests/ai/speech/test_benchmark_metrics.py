"""
tests/ai/speech/test_benchmark_metrics.py
=========================================
Tests for Speech Intelligence Benchmark Metrics (S27.14 Rules 25, 26, 28).

Verifies:
- Arabic Unicode and diacritics normalization
- Word Error Rate (WER) precision
- Timestamp Mean Absolute Error (MAE)
- Permutation-invariant Diarization Error Rate (DER)
"""

import pytest

from ai.speech.benchmark.metrics import (
    calculate_cer,
    calculate_diarization_error,
    calculate_language_accuracy,
    calculate_levenshtein_distance,
    calculate_timestamp_error,
    calculate_wer,
    normalize_text_for_wer,
)


def test_arabic_unicode_normalization_policy():
    """
    Mandatory Test (Rule 26):
    Normalizes tashkeel (fathah, dammah, etc.), alef variants (أ, إ, آ),
    ta marbuta (ة -> ه), and alef maksura (ى -> ي).
    """
    raw_arabic = "المُوبَايِلْ الَّذِي تَحْمِلُهُ فِي يَدِكَ، أَقْوَى مِنْ حَوَاسِيبِ نَاسَا!"
    normalized = normalize_text_for_wer(raw_arabic, is_arabic=True)

    # Invariant: Tashkeel stripped, Alef unified, punctuation stripped
    assert "ُ" not in normalized
    assert "َ" not in normalized
    assert "ْ" not in normalized
    assert "!" not in normalized
    assert "،" not in normalized
    assert normalized == "الموبايل الذي تحمله في يدك اقوي من حواسيب ناسا"


def test_wer_with_tashkeel_invariance():
    # Identical semantic words with different diacritics must yield 0.0 WER
    ref = "الموبايل الذي تحمله في يدك"
    hyp = "المُوبَايِلْ الَّذِي تَحْمِلُهُ فِي يَدِكَ"

    wer = calculate_wer(ref, hyp, is_arabic=True)
    assert wer == 0.0


def test_wer_calculation_substitutions_and_deletions():
    # 4 reference words: "الموبايل الي بايدك اقوى"
    # Hyp has 1 substitution: "الموبايل هادا بايدك اقوى" (الي -> هادا)
    ref = "الموبايل الي بايدك اقوى"
    hyp = "الموبايل هادا بايدك اقوى"
    wer = calculate_wer(ref, hyp)
    assert wer == 0.25  # 1 error / 4 words = 0.25

    # Hyp has 1 deletion: "الموبايل بايدك اقوى" (dropped 'الي')
    hyp_del = "الموبايل بايدك اقوى"
    wer_del = calculate_wer(ref, hyp_del)
    assert wer_del == 0.25


def test_timestamp_error_mae():
    ref_intervals = [(0.0, 1.0), (1.5, 2.5), (3.0, 4.0)]
    # Hypothesis shifted by exactly +0.1s
    hyp_intervals = [(0.1, 1.1), (1.6, 2.6), (3.1, 4.1)]

    mae = calculate_timestamp_error(ref_intervals, hyp_intervals)
    assert abs(mae - 0.1) < 1e-4


def test_diarization_permutation_invariance():
    """
    Mandatory Test (Rule 28):
    Diarization metric must not depend on arbitrary speaker label names (e.g. SPEAKER_00 vs SPEAKER_01 swapping).
    """
    # Reference: Speaker A from 0-5s, Speaker B from 5-10s
    ref_turns = [
        (0.0, 5.0, "SPEAKER_00"),
        (5.0, 10.0, "SPEAKER_01"),
    ]

    # Hypothesis: Swapped label assignments!
    # Speaker 'SPEAKER_99' from 0-5s, Speaker 'SPEAKER_88' from 5-10s
    hyp_turns = [
        (0.0, 5.0, "SPEAKER_99"),
        (5.0, 10.0, "SPEAKER_88"),
    ]

    # Permutation-invariant matching must find the optimal 1-to-1 bijection (99->00, 88->01)
    # resulting in 0.0 Diarization Error Rate!
    der = calculate_diarization_error(ref_turns, hyp_turns)
    assert der == 0.0


def test_language_accuracy_metric():
    assert calculate_language_accuracy("ar", "ar") == 1.0
    assert calculate_language_accuracy("ar", "ar-EG") == 1.0
    assert calculate_language_accuracy("ar", "en") == 0.0
    assert calculate_language_accuracy("en", None) == 0.0


def test_cer_calculation_basic():
    ref = "كتاب"
    hyp = "كتيب"
    # 1 substitution out of 4 characters = 0.25
    assert calculate_cer(ref, hyp) == 0.25


def test_mixed_arabic_english_metrics_distinction():
    """
    S28-M04.1 Regression Guard:
    Strictly asserts that phonetic/transliteration equivalence CANNOT be reported
    as textual WER = 0.0 or textual CER = 0.0 when orthographic scripts differ.
    """
    ref = "السلام عليكم using the video rendering pipeline"
    hyp = "Assalamualaikum Using the video rendering pipeline"

    # 1. Textual WER on normalized surface strings
    wer = calculate_wer(ref, hyp, is_arabic=True)
    assert wer == 0.2857  # 2 errors (1 sub, 1 del) / 7 words
    assert wer > 0.20  # Guards against false claims of 0% WER

    # 2. Textual CER on normalized surface strings (with whitespace)
    cer = calculate_cer(ref, hyp, is_arabic=True, ignore_whitespace=False)
    assert cer == 0.3191  # 15 character errors / 47 chars
    assert cer > 0.25

    # 3. Clean Arabic ground truth vs identical hypothesis must be 0.0
    ar_ref = "السلام عليكم, هذا اختبار للمشروع"
    ar_hyp = "السلام عليكم, هذا اختبار للمشروع"
    assert calculate_wer(ar_ref, ar_hyp, is_arabic=True) == 0.0
    assert calculate_cer(ar_ref, ar_hyp, is_arabic=True) == 0.0
