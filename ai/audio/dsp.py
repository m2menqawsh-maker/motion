"""
ai/audio/dsp.py
===============
Deterministic Native Digital Signal Processing (DSP) Engine (S27.16 / AI-13).

Invariants:
- Native DSP First: Silence, loudness, peak, clipping, and basic speech-energy
  detection NEVER call external or cloud AI providers (AI provider calls == 0).
- Pure computational acoustics over raw PCM / WAVE buffers.
- Bounded, predictable execution time.
- All returned metrics normalize into canonical AudioIntelligence sub-contracts.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ai.contracts.audio import (
    AudioBeatTrack,
    AudioLoudnessMetrics,
    AudioNoiseEstimate,
    AudioQualityObservation,
    TimeRange,
)
from ai.contracts.media import AnalysisProvenance


class NativeAudioDSP:
    """
    Pure deterministic DSP engine.
    """

    def __init__(self, silence_threshold_db: float = -42.0, min_silence_duration_sec: float = 0.3):
        self.silence_threshold_db = silence_threshold_db
        self.min_silence_duration_sec = min_silence_duration_sec

    @staticmethod
    def _read_pcm_samples(audio_bytes: bytes) -> Tuple[List[float], int, int]:
        """
        Unpacks 16-bit PCM audio samples normalized to [-1.0, 1.0].
        Returns (samples, sample_rate, channels).
        """
        if len(audio_bytes) >= 44 and audio_bytes.startswith(b"RIFF"):
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                    sr = wf.getframerate()
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    raw = wf.readframes(wf.getnframes())

                    if sampwidth == 2:
                        count = len(raw) // 2
                        unpacked = struct.unpack(f"<{count}h", raw)
                        # Average channels if stereo
                        if channels == 1:
                            samples = [s / 32768.0 for s in unpacked]
                        else:
                            samples = [
                                ((unpacked[i] + unpacked[i + 1]) / 2.0) / 32768.0
                                for i in range(0, count - 1, channels)
                            ]
                        return samples, sr, channels
            except Exception:
                pass

        # Fallback raw byte interpretation
        count = len(audio_bytes) // 2
        if count == 0:
            return [], 44100, 1
        unpacked = struct.unpack(f"<{count}h", audio_bytes[: count * 2])
        return [s / 32768.0 for s in unpacked], 44100, 1

    def measure_loudness_and_clipping(
        self,
        audio_bytes: bytes,
        provenance_producer: str = "native_dsp_engine",
    ) -> AudioLoudnessMetrics:
        """
        Calculates RMS level, true sample peak, clipping occurrences, and approximated LUFS.
        """
        samples, sr, _ = self._read_pcm_samples(audio_bytes)
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer=provenance_producer,
            provider="local",
            model="native_dsp_v1",
            version="1.0.0",
            confidence=0.99,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        if not samples:
            return AudioLoudnessMetrics(
                integrated_lufs=-70.0,
                momentary_max_lufs=-70.0,
                rms_db=-70.0,
                peak_db=-70.0,
                clipping_detected=False,
                clipping_events_count=0,
                provenance=prov,
            )

        sum_sq = 0.0
        peak_val = 0.0
        consecutive_clips = 0
        clipping_events = 0

        for s in samples:
            abs_s = abs(s)
            sum_sq += s * s
            if abs_s > peak_val:
                peak_val = abs_s

            # Detect clipping (sample >= 0.999 / 32760 in 16-bit)
            if abs_s >= 0.999:
                consecutive_clips += 1
                if consecutive_clips == 2:
                    clipping_events += 1
            else:
                consecutive_clips = 0

        mean_sq = sum_sq / len(samples)
        rms = math.sqrt(mean_sq) if mean_sq > 0 else 1e-7

        rms_db = round(20.0 * math.log10(max(rms, 1e-5)), 2)
        peak_db = round(20.0 * math.log10(max(peak_val, 1e-5)), 2)

        # Integrated LUFS approximation (gated K-weighting offset: approx RMS - 0.69 dB on broad audio)
        integrated_lufs = round(rms_db - 0.7, 2)
        momentary_max_lufs = round(min(peak_db - 0.2, 0.0), 2)

        return AudioLoudnessMetrics(
            integrated_lufs=max(integrated_lufs, -70.0),
            momentary_max_lufs=max(momentary_max_lufs, -70.0),
            rms_db=max(rms_db, -70.0),
            peak_db=min(peak_db, 0.0),
            clipping_detected=clipping_events > 0,
            clipping_events_count=clipping_events,
            provenance=prov,
        )

    def detect_speech_and_silence_ranges(
        self,
        audio_bytes: bytes,
        window_ms: float = 100.0,
    ) -> Tuple[List[TimeRange], List[TimeRange]]:
        """
        Segments audio into chronological speech and silence intervals via RMS windowing.
        """
        samples, sr, _ = self._read_pcm_samples(audio_bytes)
        if not samples:
            return [], []

        window_size = int(sr * (window_ms / 1000.0))
        if window_size == 0:
            window_size = 1

        silence_threshold = 10.0 ** (self.silence_threshold_db / 20.0)

        # Compute window energies
        window_energies: List[Tuple[float, bool]] = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i : i + window_size]
            sum_sq = sum(s * s for s in chunk)
            rms = math.sqrt(sum_sq / len(chunk))
            t_sec = i / float(sr)
            is_silent = rms < silence_threshold
            window_energies.append((t_sec, is_silent))

        total_duration = len(samples) / float(sr)

        # Group into intervals
        silence_ranges: List[TimeRange] = []
        speech_ranges: List[TimeRange] = []

        if not window_energies:
            return [], []

        current_is_silent = window_energies[0][1]
        start_t = 0.0

        for idx in range(1, len(window_energies)):
            t_sec, is_silent = window_energies[idx]
            if is_silent != current_is_silent:
                interval_dur = t_sec - start_t
                if current_is_silent:
                    if interval_dur >= self.min_silence_duration_sec:
                        silence_ranges.append(
                            TimeRange(start=round(start_t, 3), end=round(t_sec, 3), confidence=0.98, label="silence")
                        )
                else:
                    if interval_dur >= 0.1:
                        speech_ranges.append(
                            TimeRange(start=round(start_t, 3), end=round(t_sec, 3), confidence=0.96, label="speech")
                        )
                start_t = t_sec
                current_is_silent = is_silent

        # Append final interval
        final_dur = total_duration - start_t
        if current_is_silent:
            if final_dur >= self.min_silence_duration_sec:
                silence_ranges.append(
                    TimeRange(start=round(start_t, 3), end=round(total_duration, 3), confidence=0.98, label="silence")
                )
        else:
            if final_dur >= 0.1:
                speech_ranges.append(
                    TimeRange(start=round(start_t, 3), end=round(total_duration, 3), confidence=0.96, label="speech")
                )

        return speech_ranges, silence_ranges

    def estimate_noise_profile(
        self,
        audio_bytes: bytes,
        provenance_producer: str = "native_dsp_noise",
    ) -> AudioNoiseEstimate:
        """
        Estimates signal-to-noise ratio (SNR) and ambient noise floor from quietest intervals.
        """
        samples, sr, _ = self._read_pcm_samples(audio_bytes)
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer=provenance_producer,
            provider="local",
            model="native_dsp_v1",
            version="1.0.0",
            confidence=0.95,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        if not samples:
            return AudioNoiseEstimate(
                snr_db=30.0,
                noise_floor_db=-70.0,
                noise_profile_label="clean",
                confidence=0.95,
                provenance=prov,
            )

        window_size = int(sr * 0.1)  # 100ms
        rmses: List[float] = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i : i + window_size]
            mean_sq = sum(s * s for s in chunk) / len(chunk)
            rmses.append(math.sqrt(mean_sq))

        rmses.sort()
        # Noise floor estimated from bottom 10th percentile
        p10_idx = max(0, int(len(rmses) * 0.10))
        noise_rms = max(rmses[p10_idx], 1e-6)
        noise_floor_db = round(20.0 * math.log10(noise_rms), 2)

        # Signal peak estimated from 90th percentile
        p90_idx = min(len(rmses) - 1, int(len(rmses) * 0.90))
        signal_rms = max(rmses[p90_idx], 1e-5)
        signal_db = round(20.0 * math.log10(signal_rms), 2)

        snr_db = round(signal_db - noise_floor_db, 2)

        label = "clean"
        if snr_db < 15.0:
            label = "noisy"
        elif snr_db < 25.0:
            label = "low_hiss"

        return AudioNoiseEstimate(
            snr_db=snr_db,
            noise_floor_db=noise_floor_db,
            noise_profile_label=label,
            confidence=0.95,
            provenance=prov,
        )

    def detect_beats_and_tempo(
        self,
        audio_bytes: bytes,
        provenance_producer: str = "native_dsp_beats",
    ) -> AudioBeatTrack:
        """
        Extracts musical tempo (BPM) and beat onsets via energy flux.
        """
        samples, sr, _ = self._read_pcm_samples(audio_bytes)
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer=provenance_producer,
            provider="local",
            model="native_dsp_v1",
            version="1.0.0",
            confidence=0.92,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        if not samples:
            return AudioBeatTrack(
                tempo_bpm=120.0,
                beat_timestamps=[],
                confidence=0.90,
                provenance=prov,
            )

        # Energy flux per 50ms block
        block_size = int(sr * 0.05)
        energies: List[Tuple[float, float]] = []
        for i in range(0, len(samples), block_size):
            chunk = samples[i : i + block_size]
            e = sum(s * s for s in chunk) / len(chunk)
            t = i / float(sr)
            energies.append((t, e))

        # Detect local energy peaks
        peaks: List[float] = []
        if len(energies) >= 3:
            avg_e = sum(e for _, e in energies) / len(energies)
            for idx in range(1, len(energies) - 1):
                t_prev, e_prev = energies[idx - 1]
                t_curr, e_curr = energies[idx]
                t_next, e_next = energies[idx + 1]
                if e_curr > e_prev and e_curr > e_next and e_curr > (avg_e * 1.3):
                    # Minimum 250ms interval between beats (max 240 BPM)
                    if not peaks or (t_curr - peaks[-1]) >= 0.25:
                        peaks.append(round(t_curr, 3))

        # Estimate tempo from inter-beat intervals
        tempo_bpm = 120.0
        if len(peaks) >= 2:
            intervals = [peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1)]
            median_interval = sorted(intervals)[len(intervals) // 2]
            if median_interval > 0:
                raw_bpm = 60.0 / median_interval
                # Normalize to standard 70-160 BPM musical window
                while raw_bpm < 70.0:
                    raw_bpm *= 2.0
                while raw_bpm > 160.0:
                    raw_bpm /= 2.0
                tempo_bpm = round(raw_bpm, 1)

        return AudioBeatTrack(
            tempo_bpm=tempo_bpm,
            beat_timestamps=peaks,
            confidence=0.92,
            provenance=prov,
        )
