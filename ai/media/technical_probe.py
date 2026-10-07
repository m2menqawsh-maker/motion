"""
ai/media/technical_probe.py
===========================
Deterministic technical media inspection and audio/speech presence probe (S27.13 / S27.14).

Invariants:
- Extracts structural container and stream metadata without expensive AI model invocations.
- Evaluates acoustic presence (energy / silence threshold) before triggering speech recognition.
- Strictly provider-neutral and isolated from external vendor SDKs.
- No direct project filesystem references (accepts bytes or safe abstract buffers).
"""

from __future__ import annotations

import io
import math
import struct
import wave
from datetime import datetime, timezone
from typing import Optional, Tuple

from ai.contracts.media import AnalysisProvenance, TechnicalMetadata


def inspect_wave_bytes(data: bytes) -> Optional[TechnicalMetadata]:
    """Inspects a standard RIFF/WAVE byte buffer using the standard library wave module."""
    if len(data) < 44 or not data.startswith(b"RIFF"):
        return None
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            sampwidth = wf.getsampwidth()
            duration = float(n_frames) / float(sample_rate) if sample_rate > 0 else 0.0
            bitrate = sample_rate * channels * sampwidth * 8

            provenance = AnalysisProvenance(
                producer="technical_probe_wave",
                timestamp=datetime.now(timezone.utc),
                analysis_version="1.0.0",
                contract_version="1.0.0",
            )

            return TechnicalMetadata(
                format="wav",
                duration_seconds=round(duration, 3),
                file_size_bytes=len(data),
                has_audio=True,
                has_video=False,
                audio_channels=channels,
                audio_sample_rate=sample_rate,
                audio_bitrate=bitrate,
                audio_codec=f"pcm_s{sampwidth * 8}le",
                provenance=provenance,
            )
    except Exception:
        return None


def calculate_pcm_rms_energy(pcm_bytes: bytes, sampwidth: int = 2) -> float:
    """Calculates root-mean-square (RMS) normalized energy of 16-bit PCM audio samples."""
    if not pcm_bytes or sampwidth != 2:
        return 0.0

    num_samples = len(pcm_bytes) // 2
    if num_samples == 0:
        return 0.0

    # Unpack 16-bit signed integers
    sum_squares = 0.0
    for i in range(0, len(pcm_bytes) - 1, 2):
        sample = struct.unpack_from("<h", pcm_bytes, i)[0]
        # Normalize to [-1.0, 1.0]
        norm = sample / 32768.0
        sum_squares += norm * norm

    mean_square = sum_squares / num_samples
    return math.sqrt(mean_square)


def detect_speech_presence(audio_bytes: bytes, min_rms_threshold: float = 0.005) -> Tuple[bool, float]:
    """
    Evaluates whether speech/audio signal is likely present in wave audio bytes.
    Returns (is_speech_likely_present: bool, rms_energy: float).
    If audio is pure digital silence or below threshold, returns False.
    """
    if len(audio_bytes) < 44 or not audio_bytes.startswith(b"RIFF"):
        # For non-wave, check non-zero payload heuristic
        non_zero = any(b != 0 for b in audio_bytes[:4096])
        return non_zero, 0.05 if non_zero else 0.0

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.readframes(min(wf.getnframes(), 44100 * 5))  # inspect up to 5 seconds
            rms = calculate_pcm_rms_energy(frames, sampwidth=wf.getsampwidth())
            is_present = rms >= min_rms_threshold
            return is_present, rms
    except Exception:
        return True, 0.05


class TechnicalMediaProbe:
    """
    Deterministic technical inspection engine for media assets.
    """

    def probe_media_bytes(self, media_bytes: bytes, hint_format: Optional[str] = None) -> TechnicalMetadata:
        """Inspects media bytes and extracts technical container metadata."""
        # 1. Try wave inspection
        wave_meta = inspect_wave_bytes(media_bytes)
        if wave_meta is not None:
            return wave_meta

        # 2. General fallback for other formats
        file_size = len(media_bytes)
        provenance = AnalysisProvenance(
            producer="technical_probe_generic",
            timestamp=datetime.now(timezone.utc),
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        fmt = hint_format or "unknown"
        if media_bytes.startswith(b"\x00\x00\x00") and b"ftyp" in media_bytes[:16]:
            fmt = "mp4"

        return TechnicalMetadata(
            format=fmt,
            file_size_bytes=file_size,
            has_audio=True,
            has_video=(fmt == "mp4"),
            provenance=provenance,
        )

    def is_speech_likely_present(self, media_bytes: bytes) -> bool:
        """Determines if the media contains detectable audio signal suitable for speech processing."""
        present, _ = detect_speech_presence(media_bytes)
        return present
