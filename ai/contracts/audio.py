"""
ai/contracts/audio.py
=====================
Canonical typed contracts for Audio Intelligence & Acoustic Analysis (S27.16 / AI-13).

Invariants:
- Absolute host filesystem paths are NEVER exposed (ADR-004 DEC-06.5).
- Storage artifacts referenced exclusively via abstract storage_key.
- Strict distinction between analytical observations and generated/transformed media files.
- Deterministic Native DSP first: silence, loudness, clipping, and basic energy detection
  must never require external AI provider calls.
- Every analytical observation carries provenance, version, and confidence metrics.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel
from ai.contracts.media import AnalysisProvenance


class TimeRange(AIContractModel):
    """Canonical chronological interval in seconds."""
    start: float = Field(ge=0.0, description="Start timestamp in seconds")
    end: float = Field(ge=0.0, description="End timestamp in seconds")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence score")
    label: Optional[str] = Field(default=None, description="Optional classification label (e.g. 'silence', 'speech')")

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"TimeRange end ({self.end}) must be >= start ({self.start})")
        return self


class AudioLoudnessMetrics(AIContractModel):
    """
    Deterministic loudness and dynamic range metrics extracted via DSP.
    """
    integrated_lufs: Optional[float] = Field(default=None, description="Integrated loudness in LUFS (EBU R128)")
    momentary_max_lufs: Optional[float] = Field(default=None, description="Maximum momentary loudness in LUFS")
    rms_db: Optional[float] = Field(default=None, description="Root-mean-square level in dBFS")
    peak_db: Optional[float] = Field(default=None, description="True peak sample level in dBFS")
    clipping_detected: bool = Field(default=False, description="Whether digital audio clipping was detected")
    clipping_events_count: int = Field(default=0, ge=0, description="Total number of clipped sample runs")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance audit")


class AudioNoiseEstimate(AIContractModel):
    """
    Acoustic noise floor and signal-to-noise ratio estimation.
    """
    snr_db: Optional[float] = Field(default=None, description="Estimated Signal-to-Noise Ratio in dB")
    noise_floor_db: Optional[float] = Field(default=None, description="Estimated ambient noise floor in dBFS")
    noise_profile_label: Optional[str] = Field(default=None, description="Noise categorization ('clean', 'hum', 'hiss', 'broadband')")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Estimation confidence")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance audit")


class AudioBeatTrack(AIContractModel):
    """
    Musical tempo and rhythmic beat timestamps extracted for timeline synchronization.
    """
    tempo_bpm: Optional[float] = Field(default=None, ge=0.0, description="Detected tempo in Beats Per Minute")
    beat_timestamps: List[float] = Field(default_factory=list, description="Chronological beat timestamps in seconds")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Beat grid tracking confidence")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance audit")


class AudioQualityObservation(AIContractModel):
    """
    Individual audio quality evaluation metric.
    """
    metric_name: str = Field(min_length=1, description="Quality attribute name (e.g. 'clarity', 'echo_detected')")
    score: float = Field(ge=0.0, le=1.0, description="Normalized quality score [0.0, 1.0]")
    details: Optional[str] = Field(default=None, description="Explanatory notes or diagnostic indicators")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance audit")


class AudioIntelligence(AIContractModel):
    """
    Canonical Audio Intelligence contract unifying DSP metrics and acoustic observations.
    """
    status: str = Field(default="TYPED_FOUNDATION_AI13", description="Subsystem readiness state")
    has_audio_analysis: bool = Field(default=False, description="Whether audio analysis has been executed")
    speech_ranges: List[TimeRange] = Field(default_factory=list, description="Detected speech intervals")
    silence_ranges: List[TimeRange] = Field(default_factory=list, description="Detected silence intervals")
    loudness: Optional[AudioLoudnessMetrics] = Field(default=None, description="DSP loudness and peak metrics")
    noise_estimate: Optional[AudioNoiseEstimate] = Field(default=None, description="SNR and noise floor estimates")
    beats: Optional[AudioBeatTrack] = Field(default=None, description="Musical tempo and beat grid")
    music_ranges: List[TimeRange] = Field(default_factory=list, description="Detected background music intervals")
    quality_observations: List[AudioQualityObservation] = Field(default_factory=list, description="Audio quality scores")

    # Retained foundation fields for backward compatibility
    noise_profile: Optional[str] = Field(default=None, description="Acoustic noise classification")
    tempo_bpm: Optional[float] = Field(default=None, ge=0.0, description="Detected musical tempo in BPM")
    beat_timestamps: List[float] = Field(default_factory=list, description="Extracted musical beat timestamps")
    vocal_isolation_ref: Optional[str] = Field(default=None, description="Storage key to separated vocal stem")

    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Overall audio analysis provenance")
