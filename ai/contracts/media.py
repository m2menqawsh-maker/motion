"""
ai/contracts/media.py
=====================
Canonical contracts for Media Intelligence and Speech Intelligence (S27.13 / S27.14).

Invariants:
- Absolute host filesystem paths are NEVER exposed (ADR-004 DEC-06.5).
- Storage is referenced via canonical storage_key handled by StorageService.
- All analytical result sections are strictly typed (no Dict[str, Any] at boundaries).
- Comprehensive provenance tracking across all intelligence layers.
- Full support for multilingual transcripts (Arabic MSA, Palestinian Arabic, English, Code-Switching).
- Audio, visual, and semantic sections represent typed foundation schemas for AI-13+.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel, TzAwareDatetime


# =============================================================================
# 1. Provenance
# =============================================================================

class AnalysisProvenance(AIContractModel):
    """
    Authoritative audit record tracking the generator, model, version,
    confidence, and execution timestamp of an intelligence result.
    """
    producer: str = Field(min_length=1, description="Originating subsystem, service, or tool")
    provider: Optional[str] = Field(default=None, description="Provider adapter identifier (e.g. 'local', 'whisper')")
    model: Optional[str] = Field(default=None, description="Specific model invoked (e.g. 'whisper-large-v3')")
    version: Optional[str] = Field(default=None, description="Provider or model engine version")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence score bounded [0.0, 1.0]")
    timestamp: TzAwareDatetime = Field(description="Timezone-aware timestamp of analysis execution")
    analysis_version: str = Field(default="1.0.0", description="Analysis schema and logic version")
    contract_version: str = Field(default="1.0.0", description="SemVer of canonical contract")


# =============================================================================
# 2. Technical Metadata Section
# =============================================================================

class TechnicalMetadata(AIContractModel):
    """
    Deterministic technical audio/video inspection metadata.
    Extracted from file headers / local probes without expensive model calls.
    """
    format: Optional[str] = Field(default=None, description="Container format (e.g. 'wav', 'mp4')")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Total media duration in seconds")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="Size of file payload in bytes")
    has_audio: bool = Field(default=False, description="Whether an audio stream is detected")
    has_video: bool = Field(default=False, description="Whether a video stream is detected")
    audio_channels: Optional[int] = Field(default=None, ge=1, description="Number of audio channels")
    audio_sample_rate: Optional[int] = Field(default=None, ge=1, description="Audio sample rate in Hz")
    audio_bitrate: Optional[int] = Field(default=None, ge=1, description="Audio bitrate in bps")
    audio_codec: Optional[str] = Field(default=None, description="Audio codec identifier (e.g. 'pcm_s16le', 'aac')")
    width: Optional[int] = Field(default=None, ge=1, description="Video frame width in pixels")
    height: Optional[int] = Field(default=None, ge=1, description="Video frame height in pixels")
    fps: Optional[float] = Field(default=None, ge=0.0, description="Video frames per second")
    video_codec: Optional[str] = Field(default=None, description="Video codec identifier (e.g. 'h264')")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance of technical inspection")


# =============================================================================
# 3. Speech Intelligence Sub-Contracts
# =============================================================================

class SpeechWord(AIContractModel):
    """
    Canonical word-level timestamp and confidence alignment token.
    """
    text: str = Field(min_length=1, description="Word verbatim text")
    start: float = Field(ge=0.0, description="Start timestamp in seconds relative to original asset start")
    end: float = Field(ge=0.0, description="End timestamp in seconds relative to original asset start")
    speaker_id: Optional[str] = Field(default=None, description="Associated speaker identifier (e.g. 'SPEAKER_00')")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Word-level recognition confidence")
    language: Optional[str] = Field(default=None, description="Token language if distinct from primary")

    @model_validator(mode="after")
    def validate_word_boundaries(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"SpeechWord end timestamp ({self.end}) must be >= start timestamp ({self.start})")
        return self


class SpeechSegment(AIContractModel):
    """
    Canonical speech utterance / sentence / subtitle segment.
    """
    id: Optional[str] = Field(default=None, description="Unique segment identifier")
    start: float = Field(ge=0.0, description="Segment start timestamp in seconds relative to original asset start")
    end: float = Field(ge=0.0, description="Segment end timestamp in seconds relative to original asset start")
    text: str = Field(description="Segment verbatim transcript text")
    speaker_id: Optional[str] = Field(default=None, description="Associated speaker identifier")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Segment average confidence")
    language: Optional[str] = Field(default=None, description="Segment language if distinct/code-switched")
    words: List[SpeechWord] = Field(default_factory=list, description="Constituent aligned words if available")

    @model_validator(mode="after")
    def validate_segment_boundaries(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"SpeechSegment end timestamp ({self.end}) must be >= start timestamp ({self.start})")
        return self


class SpeechSpeaker(AIContractModel):
    """
    Canonical speaker diarization identity turn record.
    Uses neutral identifiers (e.g. SPEAKER_00) to avoid false human attribution.
    """
    speaker_id: str = Field(min_length=1, description="Neutral speaker identifier (e.g. 'SPEAKER_00')")
    label: Optional[str] = Field(default=None, description="Descriptive or role-based label if known")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Speaker cluster confidence")
    total_speaking_time_seconds: Optional[float] = Field(default=None, ge=0.0, description="Total active duration")


class SpeechQuality(AIContractModel):
    """
    Acoustic and speech intelligibility quality metrics.
    """
    speech_snr_db: Optional[float] = Field(default=None, description="Estimated Signal-to-Noise Ratio in dB")
    audio_clarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Subjective clarity [0.0, 1.0]")
    clipping_detected: Optional[bool] = Field(default=None, description="Whether digital audio clipping was detected")
    silence_percentage: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Proportion of silent audio")


class SpeechIntelligence(AIContractModel):
    """
    Canonical Speech Intelligence contract.
    All speech providers (regardless of vendor API shape) normalize into this structure.
    """
    language: Optional[str] = Field(default=None, description="Primary detected language code (e.g. 'ar', 'en')")
    language_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Language detection confidence")
    transcript: str = Field(description="Full consolidated verbatim transcript")
    segments: List[SpeechSegment] = Field(default_factory=list, description="Chronological speech segments")
    words: List[SpeechWord] = Field(default_factory=list, description="Chronological aligned word tokens")
    speakers: List[SpeechSpeaker] = Field(default_factory=list, description="Identified speaker diarization clusters")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Duration of speech activity")
    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Aggregate confidence")
    provenance: AnalysisProvenance = Field(description="Audit record tracking speech generation source")

    @model_validator(mode="after")
    def validate_speech_coherence(self) -> Self:
        # Validate monotonicity of segments
        for i in range(len(self.segments) - 1):
            if self.segments[i + 1].start < self.segments[i].start:
                raise ValueError(
                    f"Segments must be chronologically ordered by start time. "
                    f"Segment {i} starts at {self.segments[i].start}, but segment {i+1} starts at {self.segments[i+1].start}"
                )

        # Validate monotonicity of words
        for i in range(len(self.words) - 1):
            if self.words[i + 1].start < self.words[i].start:
                raise ValueError(
                    f"Words must be chronologically ordered by start time. "
                    f"Word {i} ('{self.words[i].text}') starts at {self.words[i].start}, "
                    f"but word {i+1} ('{self.words[i+1].text}') starts at {self.words[i+1].start}"
                )

        # Validate speaker references if speakers catalog is populated
        if self.speakers:
            valid_speaker_ids = {s.speaker_id for s in self.speakers}
            for seg in self.segments:
                if seg.speaker_id is not None and seg.speaker_id not in valid_speaker_ids:
                    raise ValueError(
                        f"Segment references unknown speaker_id '{seg.speaker_id}'. "
                        f"Known speakers: {sorted(valid_speaker_ids)}"
                    )
            for w in self.words:
                if w.speaker_id is not None and w.speaker_id not in valid_speaker_ids:
                    raise ValueError(
                        f"Word '{w.text}' references unknown speaker_id '{w.speaker_id}'. "
                        f"Known speakers: {sorted(valid_speaker_ids)}"
                    )

        return self


class TranscriptArtifact(AIContractModel):
    """
    Authoritative canonical speech transcription artifact (S28-M04).
    Guarantees deterministic identity, provenance, and structured representation
    for video composition and kinetic captioning.
    """
    transcript_id: str = Field(min_length=1, description="Canonical transcript identifier")
    source_asset_id: str = Field(min_length=1, description="Source audio asset identifier")
    source_content_hash: str = Field(min_length=8, description="Cryptographic SHA-256 hash of source audio bytes")
    model_id: str = Field(min_length=1, description="Model identifier used for transcription")
    model_version: str = Field(min_length=1, description="Version of the model used")
    config_hash: str = Field(min_length=8, description="Deterministic canonical hash of transcription hyperparameters")
    language: Optional[str] = Field(default=None, description="Detected or specified spoken language")
    language_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Language confidence score")
    transcript: str = Field(description="Full consolidated transcript text")
    segments: List[SpeechSegment] = Field(default_factory=list, description="Chronological speech segments")
    words: List[SpeechWord] = Field(default_factory=list, description="Chronological word-level alignment tokens")
    speakers: List[SpeechSpeaker] = Field(default_factory=list, description="Identified speaker diarization clusters")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Total speech duration in seconds")
    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Overall aggregate confidence")
    created_at: TzAwareDatetime = Field(description="Timezone-aware creation timestamp")
    provenance: AnalysisProvenance = Field(description="Audit provenance record")

    def to_speech_intelligence(self) -> SpeechIntelligence:
        return SpeechIntelligence(
            language=self.language,
            language_confidence=self.language_confidence,
            transcript=self.transcript,
            segments=self.segments,
            words=self.words,
            speakers=self.speakers,
            duration_seconds=self.duration_seconds,
            overall_confidence=self.overall_confidence,
            provenance=self.provenance,
        )

    @classmethod
    def from_speech_intelligence(
        cls,
        speech_intel: SpeechIntelligence,
        source_asset_id: str,
        source_content_hash: str,
        model_id: str,
        model_version: str,
        config_hash: str,
        transcript_id: Optional[str] = None,
    ) -> TranscriptArtifact:
        tid = transcript_id or f"tr_{source_content_hash[:8]}_{model_id}_{config_hash[:8]}"
        return cls(
            transcript_id=tid,
            source_asset_id=source_asset_id,
            source_content_hash=source_content_hash,
            model_id=model_id,
            model_version=model_version,
            config_hash=config_hash,
            language=speech_intel.language,
            language_confidence=speech_intel.language_confidence,
            transcript=speech_intel.transcript,
            segments=speech_intel.segments,
            words=speech_intel.words,
            speakers=speech_intel.speakers,
            duration_seconds=speech_intel.duration_seconds,
            overall_confidence=speech_intel.overall_confidence,
            created_at=speech_intel.provenance.timestamp,
            provenance=speech_intel.provenance,
        )


# =============================================================================
from ai.contracts.audio import AudioIntelligence
from ai.contracts.vision import VisualIntelligence

# Backward compatibility aliases
AudioIntelligenceFoundation = AudioIntelligence
VisualIntelligenceFoundation = VisualIntelligence


class SemanticIntelligenceFoundation(AIContractModel):
    """
    Typed foundation for semantic classification and summarization (AI-13).
    Unimplemented in AI-12/AI-13; provides strict structural boundary.
    """
    status: str = Field(default="TYPED_FOUNDATION_AI13", description="Subsystem readiness state")
    topics: List[str] = Field(default_factory=list, description="Extracted semantic topic labels")
    summary: Optional[str] = Field(default=None, description="Concise multi-modal narrative summary")


class MediaQualityIntelligence(AIContractModel):
    """
    Unified media quality evaluation section.
    Houses speech quality in AI-12; audio/visual quality in AI-13+.
    """
    speech: Optional[SpeechQuality] = Field(default=None, description="Speech-specific acoustic quality metrics")
    audio_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Overall audio quality")
    visual_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Overall visual quality")
    overall_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Composite media quality score")


# =============================================================================
# 5. Canonical MediaIntelligence Root Contract
# =============================================================================

class MediaIntelligence(AIContractModel):
    """
    Authoritative canonical contract unifying all media understanding dimensions.
    Mediates between raw assets, provider models, and downstream domain services.
    """
    workspace_id: str = Field(min_length=1, description="Tenant workspace ownership scope")
    asset_id: str = Field(min_length=1, description="Associated domain asset identifier")
    content_hash: str = Field(min_length=8, description="Cryptographic SHA-256 hash of media bytes")
    analysis_version: str = Field(default="1.0.0", description="Analysis semantics and pipeline version")
    contract_version: str = Field(default="1.0.0", description="SemVer of canonical contract")
    created_at: TzAwareDatetime = Field(description="Timezone-aware timestamp of analysis record")

    technical: TechnicalMetadata = Field(default_factory=TechnicalMetadata, description="Technical container inspection")
    speech: Optional[SpeechIntelligence] = Field(default=None, description="Speech recognition, alignment, diarization")
    audio: AudioIntelligence = Field(default_factory=AudioIntelligence, description="Acoustic intelligence (AI-13)")
    visual: VisualIntelligence = Field(default_factory=VisualIntelligence, description="Visual intelligence (AI-13)")
    semantic: SemanticIntelligenceFoundation = Field(default_factory=SemanticIntelligenceFoundation, description="Semantic foundation (AI-13)")
    quality: MediaQualityIntelligence = Field(default_factory=MediaQualityIntelligence, description="Quality evaluation")

    provenance: AnalysisProvenance = Field(description="Top-level analysis provenance audit record")


# =============================================================================
# 6. Media Intelligence Storage Reference
# =============================================================================

class MediaIntelligenceRef(AIContractModel):
    """
    Contract reference allowing the rest of the workspace to address a media analysis
    or intelligence artifact without coupling to underlying storage backends.
    """
    artifact_id: str = Field(min_length=1, description="Unique artifact record identifier")
    asset_id: str = Field(min_length=1, description="Associated domain asset identifier")
    analysis_version: str = Field(default="1.0.0", description="Schema version of the analysis payload")
    content_hash: str = Field(min_length=8, description="Cryptographic SHA-256 hash of analyzed content")
    storage_key: str = Field(min_length=1, description="Abstract StorageService object key")
    created_at: TzAwareDatetime = Field(description="Timezone-aware timestamp of artifact registration")

    @field_validator("storage_key")
    @classmethod
    def validate_storage_key_abstraction(cls, key: str) -> str:
        if key.startswith("/") or key.startswith("\\") or ":" in key[:2]:
            raise ValueError(f"storage_key must be an abstract storage key, not a host absolute path: '{key}'")
        if ".." in key:
            raise ValueError(f"storage_key cannot contain path traversal components ('..'): '{key}'")
        key_segments = [seg.lower() for seg in key.replace("\\", "/").split("/")]
        if "projects" in key_segments:
            raise ValueError(f"storage_key cannot point to raw project workspace directories: '{key}'")
        return key
