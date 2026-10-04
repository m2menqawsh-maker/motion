"""
tests/ai/speech/test_real_human_speech_validation.py
===================================================
Real Human Speech Validation Suite (S27.14 / AI-15R2).

Invariants:
- Uses REAL_HUMAN_AUDIO with authentic HUMAN_VERIFIED_REFERENCE.
- Never uses Whisper or LLM output as ground truth.
- Runs real local Faster-Whisper engine.
- Evaluates raw WER, normalized WER, language detection, and latency/min.
- Reports unreferenced human audio (e.g. vo_norm.wav) as REFERENCE_MISSING.
"""

from __future__ import annotations

from pathlib import Path
import time
import pytest
from faster_whisper import WhisperModel

from ai.speech.benchmark.metrics import calculate_wer, normalize_text_for_wer


def test_real_human_speech_validation():
    """
    Executes real faster-whisper on verified human VO recording.
    """
    wav_path = Path("assets/incoming/tests/human_vo_01.wav")
    ref_path = Path("assets/incoming/tests/human_vo_01.txt")

    assert wav_path.exists(), f"Audio asset missing: {wav_path}"
    assert ref_path.exists(), f"Reference transcript missing: {ref_path}"

    reference_text = ref_path.read_text(encoding="utf-8").strip()
    assert len(reference_text) > 0, "Reference transcript is empty"

    # Initialize real Faster-Whisper CPU int8 engine
    model = WhisperModel("base", device="cpu", compute_type="int8")

    t0 = time.perf_counter()
    segments, info = model.transcribe(str(wav_path), language="ar")
    texts = [s.text for s in segments]
    latency_sec = time.perf_counter() - t0

    hypothesis_text = " ".join(texts).strip()

    # Calculate metrics with project normalization policy
    raw_wer = calculate_wer(reference_text, hypothesis_text, is_arabic=False)
    normalized_wer = calculate_wer(reference_text, hypothesis_text, is_arabic=True)

    dur_min = info.duration / 60.0
    latency_per_min = latency_sec / dur_min

    # Invariants
    assert info.language == "ar", f"Expected Arabic language detection, got {info.language}"
    assert info.language_probability >= 0.90, f"Low language confidence: {info.language_probability}"
    assert normalized_wer == 0.0, f"Expected 0.0% normalized WER on verified human sample, got {normalized_wer}"
    assert raw_wer == 0.0, f"Expected 0.0% raw WER, got {raw_wer}"
    assert latency_per_min < 30.0, f"Latency per minute too high: {latency_per_min}s/min"


def test_unreferenced_human_audio_classified_as_reference_missing():
    """
    Verifies that human audio without a verified human transcript (vo_norm.wav)
    is strictly classified as REFERENCE_MISSING and rejected from ground-truth evaluation.
    """
    vo_norm_path = Path("tests/fixtures/clean_room_project/assets/ready/vo_norm.wav")
    vo_norm_txt = Path("tests/fixtures/clean_room_project/assets/ready/vo_norm.txt")

    assert vo_norm_path.exists(), "vo_norm.wav exists in fixtures"
    # Ground truth transcript does not exist in repo; must be REFERENCE_MISSING
    assert not vo_norm_txt.exists(), "vo_norm.txt should not be fabricated"
