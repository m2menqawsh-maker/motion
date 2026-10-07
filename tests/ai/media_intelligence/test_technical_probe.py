"""
tests/ai/media_intelligence/test_technical_probe.py
===================================================
Tests for TechnicalMediaProbe and audio presence checks (S27.13 / S27.14).
"""

import io
import math
import struct
import wave
import pytest

from ai.media.technical_probe import TechnicalMediaProbe, calculate_pcm_rms_energy, detect_speech_presence


def generate_synthetic_wave(duration_sec: float = 1.0, sample_rate: int = 44100, is_silent: bool = False) -> bytes:
    """Generates synthetic 16-bit mono WAVE bytes with sine wave or digital silence."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        num_samples = int(duration_sec * sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            if is_silent:
                val = 0
            else:
                # 440 Hz sine wave
                val = int(16000 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


def test_probe_wave_metadata():
    probe = TechnicalMediaProbe()
    wave_bytes = generate_synthetic_wave(duration_sec=2.5, sample_rate=48000, is_silent=False)

    metadata = probe.probe_media_bytes(wave_bytes)

    assert metadata.format == "wav"
    assert metadata.has_audio is True
    assert metadata.has_video is False
    assert metadata.audio_channels == 1
    assert metadata.audio_sample_rate == 48000
    assert abs((metadata.duration_seconds or 0.0) - 2.5) < 0.05
    assert metadata.audio_codec == "pcm_s16le"
    assert metadata.provenance is not None
    assert metadata.provenance.producer == "technical_probe_wave"


def test_speech_presence_detection():
    # 1. Digital silence
    silent_wave = generate_synthetic_wave(duration_sec=1.0, is_silent=True)
    is_present, rms = detect_speech_presence(silent_wave)
    assert is_present is False
    assert rms == 0.0

    probe = TechnicalMediaProbe()
    assert probe.is_speech_likely_present(silent_wave) is False

    # 2. Audible sine wave signal
    active_wave = generate_synthetic_wave(duration_sec=1.0, is_silent=False)
    is_active, active_rms = detect_speech_presence(active_wave)
    assert is_active is True
    assert active_rms > 0.1
    assert probe.is_speech_likely_present(active_wave) is True


def test_calculate_pcm_rms_energy():
    # Empty bytes
    assert calculate_pcm_rms_energy(b"") == 0.0

    # Max amplitude DC
    full_scale = struct.pack("<h", 32767) * 100
    rms = calculate_pcm_rms_energy(full_scale)
    assert abs(rms - 1.0) < 0.01
