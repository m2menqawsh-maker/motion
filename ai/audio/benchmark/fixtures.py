"""
ai/audio/benchmark/fixtures.py
==============================
Deterministic procedural audio fixture generators for Audio Benchmark (S27.16 / AI-13).

Generates in-memory 16-bit PCM RIFF/WAVE byte buffers for:
1. Clean speech
2. Noise
3. Music
4. Music + speech composite
5. Clipping
6. Echo
7. Low volume
"""

from __future__ import annotations

import io
import math
import struct
import wave


def _pack_wave_bytes(samples: list[float], sample_rate: int = 44100) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            # Clamped to 16-bit signed
            val = int(max(-1.0, min(1.0, s)) * 32767.0)
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


def generate_clean_speech_fixture(duration_sec: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Simulates speech-like harmonic energy modulated with syllabic pauses."""
    n = int(duration_sec * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        # Syllabic envelope modulation (approx 3 syllables per sec)
        envelope = 0.5 * (1.0 + math.sin(2.0 * math.pi * 3.0 * t))
        # Fundamental voice formant (150 Hz + harmonics)
        v = (
            0.6 * math.sin(2.0 * math.pi * 150.0 * t)
            + 0.3 * math.sin(2.0 * math.pi * 300.0 * t)
            + 0.1 * math.sin(2.0 * math.pi * 600.0 * t)
        )
        samples.append(v * envelope * 0.7)
    return _pack_wave_bytes(samples, sample_rate)


def generate_noise_fixture(duration_sec: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Generates continuous deterministic pseudo-random broadband hiss."""
    n = int(duration_sec * sample_rate)
    samples = []
    state = 42
    for i in range(n):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        noise_val = ((state / 0x7FFFFFFF) * 2.0 - 1.0) * 0.2
        samples.append(noise_val)
    return _pack_wave_bytes(samples, sample_rate)


def generate_music_fixture(duration_sec: float = 3.0, bpm: float = 120.0, sample_rate: int = 44100) -> bytes:
    """Generates melodic tone with steady rhythmic kick drum onsets."""
    n = int(duration_sec * sample_rate)
    beat_period = 60.0 / bpm
    samples = []
    for i in range(n):
        t = i / sample_rate
        # Rhythm kick at beat onsets
        t_in_beat = t % beat_period
        kick = math.exp(-t_in_beat * 25.0) * math.sin(2.0 * math.pi * 60.0 * t_in_beat) if t_in_beat < 0.2 else 0.0
        # Harmonic chord (A4 = 440 Hz, E5 = 660 Hz)
        chord = 0.25 * math.sin(2.0 * math.pi * 440.0 * t) + 0.15 * math.sin(2.0 * math.pi * 660.0 * t)
        samples.append(0.6 * kick + 0.4 * chord)
    return _pack_wave_bytes(samples, sample_rate)


def generate_music_and_speech_fixture(duration_sec: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Composite of speech on top of background music."""
    speech = generate_clean_speech_fixture(duration_sec, sample_rate)
    music = generate_music_fixture(duration_sec, sample_rate=sample_rate)

    # Decode and mix
    n = int(duration_sec * sample_rate)
    s_raw = struct.unpack(f"<{n}h", speech[44 : 44 + n * 2])
    m_raw = struct.unpack(f"<{n}h", music[44 : 44 + n * 2])

    mixed = []
    for s, m in zip(s_raw, m_raw):
        val = (s / 32768.0) * 0.7 + (m / 32768.0) * 0.3
        mixed.append(val)
    return _pack_wave_bytes(mixed, sample_rate)


def generate_clipping_fixture(duration_sec: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Generates heavily saturated signal with multiple consecutive samples at 1.0 (clipping)."""
    n = int(duration_sec * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        # Multiply by 4.0 to drive into heavy saturation
        val = 4.0 * math.sin(2.0 * math.pi * 440.0 * t)
        samples.append(max(-1.0, min(1.0, val)))
    return _pack_wave_bytes(samples, sample_rate)


def generate_echo_fixture(duration_sec: float = 3.0, delay_sec: float = 0.25, sample_rate: int = 44100) -> bytes:
    """Generates impulse followed by delayed decayed multi-tap reflections."""
    n = int(duration_sec * sample_rate)
    samples = [0.0] * n
    delay_samples = int(delay_sec * sample_rate)

    # Primary impulse
    impulse_len = int(0.1 * sample_rate)
    for i in range(impulse_len):
        t = i / sample_rate
        samples[i] = math.sin(2.0 * math.pi * 1000.0 * t) * 0.8

    # Add 3 echo taps
    decay = 0.5
    for tap in range(1, 4):
        offset = tap * delay_samples
        for i in range(impulse_len):
            if offset + i < n:
                samples[offset + i] += samples[i] * (decay**tap)

    return _pack_wave_bytes(samples, sample_rate)


def generate_low_volume_fixture(duration_sec: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Generates audio scaled down to -40 dBFS."""
    clean = generate_clean_speech_fixture(duration_sec, sample_rate)
    n = int(duration_sec * sample_rate)
    raw = struct.unpack(f"<{n}h", clean[44 : 44 + n * 2])
    # Attenuate by factor of 0.01 (-40 dB)
    samples = [(s / 32768.0) * 0.01 for s in raw]
    return _pack_wave_bytes(samples, sample_rate)
