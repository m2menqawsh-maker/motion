"""
tests/ai/audio/test_dsp_analysis.py
===================================
Acoustic DSP tests for NativeAudioDSP (S27.16 / AI-13).

Invariants verified:
- Native DSP first: silence, loudness, clipping, and basic speech-energy
  NEVER invoke external or cloud AI providers (Rule 10, 13: provider_calls == 0).
- Pure computational acoustics over raw PCM / WAVE buffers.
- Correct segmentation of silence and speech without impossible timestamps.
- Accurate clipping detection on saturated signals.
- Clean noise estimation and beat/tempo detection.
"""

from unittest.mock import MagicMock
import pytest

from ai.audio.benchmark.fixtures import (
    generate_clean_speech_fixture,
    generate_clipping_fixture,
    generate_low_volume_fixture,
    generate_music_fixture,
    generate_noise_fixture,
)
from ai.audio.dsp import NativeAudioDSP


def test_loudness_and_clipping_detection():
    dsp = NativeAudioDSP()
    clip_wav = generate_clipping_fixture(duration_sec=1.5)
    metrics = dsp.measure_loudness_and_clipping(clip_wav)

    assert metrics.clipping_detected is True
    assert metrics.clipping_events_count > 0
    assert metrics.peak_db >= -0.1
    assert -25.0 <= metrics.integrated_lufs <= 0.0
    assert metrics.provenance.provider == "local"
    assert metrics.provenance.model == "native_dsp_v1"


def test_low_volume_loudness_detection():
    dsp = NativeAudioDSP()
    quiet_wav = generate_low_volume_fixture(duration_sec=2.0)
    metrics = dsp.measure_loudness_and_clipping(quiet_wav)

    assert metrics.clipping_detected is False
    assert metrics.clipping_events_count == 0
    assert metrics.integrated_lufs < -40.0


def test_speech_and_silence_segmentation():
    dsp = NativeAudioDSP(silence_threshold_db=-40.0, min_silence_duration_sec=0.2)
    speech_wav = generate_clean_speech_fixture(duration_sec=3.0)
    speech_ranges, silence_ranges = dsp.detect_speech_and_silence_ranges(speech_wav)

    # Invariants on ranges
    for r in speech_ranges + silence_ranges:
        assert r.start >= 0.0
        assert r.end >= r.start
        assert r.end <= 3.1
        assert 0.0 <= r.confidence <= 1.0

    assert len(speech_ranges) > 0


def test_noise_profile_estimation():
    dsp = NativeAudioDSP()
    noise_wav = generate_noise_fixture(duration_sec=2.0)
    noise_estimate = dsp.estimate_noise_profile(noise_wav)

    assert noise_estimate.noise_profile_label in ["noisy", "low_hiss", "clean"]
    assert isinstance(noise_estimate.snr_db, float)
    assert isinstance(noise_estimate.noise_floor_db, float)
    assert noise_estimate.provenance.provider == "local"


def test_beat_and_tempo_detection():
    dsp = NativeAudioDSP()
    music_wav = generate_music_fixture(duration_sec=3.0, bpm=120.0)
    beat_track = dsp.detect_beats_and_tempo(music_wav)

    assert 70.0 <= beat_track.tempo_bpm <= 160.0
    assert len(beat_track.beat_timestamps) > 0
    for t in beat_track.beat_timestamps:
        assert 0.0 <= t <= 3.0


def test_zero_ai_provider_calls_for_deterministic_analysis():
    """
    Mandatory Test (Rule 13, 31):
    silence, loudness, clipping, basic speech-energy detection
    MUST NOT call external AI providers.
    Expected: provider_calls == 0
    """
    ai_provider_mock = MagicMock()
    dsp = NativeAudioDSP()

    # Process all procedural audio tests
    wav1 = generate_clean_speech_fixture(duration_sec=1.0)
    wav2 = generate_clipping_fixture(duration_sec=1.0)
    wav3 = generate_noise_fixture(duration_sec=1.0)
    wav4 = generate_music_fixture(duration_sec=1.0, bpm=120.0)

    dsp.measure_loudness_and_clipping(wav1)
    dsp.detect_speech_and_silence_ranges(wav1)
    dsp.measure_loudness_and_clipping(wav2)
    dsp.estimate_noise_profile(wav3)
    dsp.detect_beats_and_tempo(wav4)

    # Assert ZERO provider invocations
    assert ai_provider_mock.call_count == 0
    assert ai_provider_mock.invoke.call_count == 0
