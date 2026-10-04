"""
ai/speech/stt_provider.py
=========================
Authoritative Speech-to-Text abstraction and contracts for S28-M04.

Invariants:
- Dedicated STT abstraction; strictly decoupled from generic LLM chat interfaces.
- Deterministic canonical configuration hashing (config_hash).
- Standardized typed requests, responses, health, capabilities, and metadata.
- Comprehensive structured error taxonomy mapping directly to canonical AIError.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel, TzAwareDatetime
from ai.contracts.common import CapabilityType, QualityTarget, QualityTargetEnum
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.media import (
    AnalysisProvenance,
    SpeechIntelligence,
    SpeechSegment,
    SpeechSpeaker,
    SpeechWord,
    TranscriptArtifact,
)
from ai.cache.key import normalize_canonical_json


# =============================================================================
# Structured Error Taxonomy for Speech-to-Text
# =============================================================================

class STTError(Exception):
    """Base exception for all speech-to-text runtime failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.INTERNAL_ERROR,
            message=self.message,
            retryable=False,
            details=self.details,
        )


class InvalidAudioError(STTError):
    """Raised when audio payload is corrupt, zero-byte, or not a valid audio format."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "INVALID_AUDIO", **self.details},
        )


class AudioDecodeError(STTError):
    """Raised when audio decoding fails (e.g. missing audio stream or invalid codecs)."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.CONTENT_REJECTED,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "AUDIO_DECODE_FAILED", **self.details},
        )


class ModelNotAvailableError(STTError):
    """Raised when the requested STT model weights or engine cannot be found."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.CAPABILITY_UNAVAILABLE,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "MODEL_NOT_AVAILABLE", **self.details},
        )


class ModelLoadError(STTError):
    """Raised when initializing the STT model fails."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.PROVIDER_UNAVAILABLE,
            message=self.message,
            retryable=True,
            details={"stt_error_category": "MODEL_LOAD_FAILED", **self.details},
        )


class ModelInferenceError(STTError):
    """Raised when inference crashes during transcription."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.DEPENDENCY_FAILED,
            message=self.message,
            retryable=True,
            details={"stt_error_category": "MODEL_INFERENCE_FAILED", **self.details},
        )


class DeviceUnavailableError(STTError):
    """Raised when requested acceleration device (e.g. CUDA) is unavailable and fallback disallowed."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.PROVIDER_UNAVAILABLE,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "DEVICE_UNAVAILABLE", **self.details},
        )


class ResourceExhaustedError(STTError):
    """Raised when concurrency or queue backpressure limits are exceeded."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.RATE_LIMITED,
            message=self.message,
            retryable=True,
            details={"stt_error_category": "RESOURCE_EXHAUSTED", **self.details},
        )


class STTTimeoutError(STTError):
    """Raised when transcription execution exceeds configured timeout."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.TIMEOUT,
            message=self.message,
            retryable=True,
            details={"stt_error_category": "TIMEOUT", **self.details},
        )


class STTCancelledError(STTError):
    """Raised when transcription execution is cancelled by caller."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.CANCELLED,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "CANCELLED", **self.details},
        )


class OutputValidationError(STTError):
    """Raised when provider output violates SpeechIntelligence invariants."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.INVALID_MODEL_OUTPUT,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "OUTPUT_VALIDATION_FAILED", **self.details},
        )


class StorageReadError(STTError):
    """Raised when storage retrieval of input audio fails."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.DEPENDENCY_FAILED,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "STORAGE_READ_FAILED", **self.details},
        )


class TenantAccessDeniedError(STTError):
    """Raised when cross-tenant or cross-project asset access is attempted."""
    def to_ai_error(self) -> AIError:
        return AIError.create(
            code=AIErrorCode.TENANT_ACCESS_DENIED,
            message=self.message,
            retryable=False,
            details={"stt_error_category": "TENANT_ACCESS_DENIED", **self.details},
        )


# =============================================================================
# Canonical STT Configuration & Hashing
# =============================================================================

class STTConfig(AIContractModel):
    """
    Deterministic configuration parameters governing speech recognition.
    Every parameter affecting model execution is included to prevent cache collisions.
    """
    model_size: str = Field(default="base", description="Whisper model tier: 'tiny', 'base', 'small', 'medium', 'large-v3'")
    language: Optional[str] = Field(default=None, description="Optional ISO 639-1 language code; None for auto-detect")
    beam_size: int = Field(default=5, ge=1, le=10, description="Beam search width")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature")
    word_timestamps: bool = Field(default=True, description="Whether to extract word-level timestamps")
    vad_filter: bool = Field(default=True, description="Whether to apply Silero VAD pre-filtering")
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Silero VAD speech probability threshold")
    min_speech_duration_ms: int = Field(default=250, ge=50, description="Minimum active speech duration")
    min_silence_duration_ms: int = Field(default=2000, ge=100, description="Minimum silence duration for sentence splitting")
    condition_on_previous_text: bool = Field(default=False, description="Whether Whisper conditions on previous window")
    initial_prompt: Optional[str] = Field(default=None, description="Optional initial prompt context")

    def compute_config_hash(self) -> str:
        """
        Derives an authoritative, stable SHA-256 hash of this configuration.
        Keys are sorted recursively and floats normalized to ensure cross-platform stability.
        """
        raw_dict = self.model_dump()
        canonical_str = normalize_canonical_json(raw_dict)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


# =============================================================================
# STT Request & Response Contracts
# =============================================================================

class STTRequest(AIContractModel):
    """
    Typed input request dispatched to an STTProvider.
    Uses abstract media payload or resolved local materialization path.
    """
    request_id: str = Field(min_length=1, description="Unique correlation identifier")
    audio_path: str = Field(min_length=1, description="Validated path to temporary materialized audio file")
    audio_content_hash: str = Field(min_length=8, description="Cryptographic SHA-256 hash of audio bytes")
    config: STTConfig = Field(default_factory=STTConfig, description="Transcription hyperparameters")
    source_asset_id: Optional[str] = Field(default=None, description="Canonical asset identifier if known")
    timeout_seconds: float = Field(default=60.0, gt=0.0, description="Execution timeout deadline in seconds")


class STTResponse(AIContractModel):
    """
    Typed analytical result returned by an STTProvider.
    """
    request_id: str = Field(min_length=1, description="Correlation identifier matching request")
    transcript: str = Field(description="Full consolidated transcript")
    language: Optional[str] = Field(default=None, description="Detected or requested language code")
    language_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence of detected language")
    duration_seconds: float = Field(ge=0.0, description="Total media duration in seconds")
    segments: List[SpeechSegment] = Field(default_factory=list, description="Chronological speech segments")
    words: List[SpeechWord] = Field(default_factory=list, description="Chronological aligned word tokens")
    speakers: List[SpeechSpeaker] = Field(default_factory=list, description="Speaker diarization records")
    model_device: str = Field(description="Actual hardware device used: 'cpu' or 'cuda'")
    compute_type: str = Field(description="Actual CTranslate2 compute type: 'int8', 'float16', etc.")
    model_id: str = Field(description="Specific model identifier used (e.g. 'faster-whisper-base')")
    model_version: str = Field(description="Version of model or engine")
    engine: str = Field(description="Inference engine: 'faster-whisper / CTranslate2'")
    fallback_occurred: bool = Field(default=False, description="Whether device fallback to CPU occurred")
    fallback_reason: Optional[str] = Field(default=None, description="Diagnostic reason if fallback occurred")
    queue_wait_ms: float = Field(default=0.0, ge=0.0, description="Time spent waiting in queue in ms")
    model_load_ms: float = Field(default=0.0, ge=0.0, description="Time spent loading model in ms")
    inference_ms: float = Field(default=0.0, ge=0.0, description="Inference wall time in ms")
    real_time_factor: float = Field(default=0.0, ge=0.0, description="RTF = inference_time / audio_duration")
    speech_periods: List[Dict[str, float]] = Field(default_factory=list, description="VAD speech intervals")
    silence_periods: List[Dict[str, float]] = Field(default_factory=list, description="VAD silence intervals")
    config_hash: str = Field(description="Configuration hash used")

    def to_speech_intelligence(self, producer: str = "LocalSTTProvider") -> SpeechIntelligence:
        """Converts response into the canonical SpeechIntelligence product contract."""
        now = datetime.now(timezone.utc)
        provenance = AnalysisProvenance(
            producer=producer,
            provider="local",
            model=self.model_id,
            version=self.model_version,
            confidence=self.language_confidence or 0.95,
            timestamp=now,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )
        return SpeechIntelligence(
            language=self.language,
            language_confidence=self.language_confidence,
            transcript=self.transcript,
            segments=self.segments,
            words=self.words,
            speakers=self.speakers,
            duration_seconds=self.duration_seconds,
            overall_confidence=self.language_confidence or 0.95,
            provenance=provenance,
        )

    def to_transcript_artifact(
        self,
        source_asset_id: str,
        source_content_hash: str,
        producer: str = "LocalSTTProvider",
    ) -> TranscriptArtifact:
        """Constructs canonical TranscriptArtifact representation."""
        speech_intel = self.to_speech_intelligence(producer=producer)
        return TranscriptArtifact.from_speech_intelligence(
            speech_intel=speech_intel,
            source_asset_id=source_asset_id,
            source_content_hash=source_content_hash,
            model_id=self.model_id,
            model_version=self.model_version,
            config_hash=self.config_hash,
        )


# =============================================================================
# Health & Capability Metadata Contracts
# =============================================================================

class STTHealth(AIContractModel):
    """Health and runtime operational status of an STTProvider."""
    provider_id: str = Field(description="Provider identifier (e.g. 'local-stt-provider')")
    model_id: str = Field(description="Current or default model identifier")
    model_version: str = Field(description="Model version")
    registered: bool = Field(description="Whether provider is registered in system")
    weights_available: bool = Field(description="Whether model weights exist locally")
    loaded: bool = Field(description="Whether model is currently loaded in memory")
    device: str = Field(description="Target or detected hardware device ('cpu', 'cuda')")
    compute_type: str = Field(description="Active compute precision type ('int8', 'float16')")
    ready: bool = Field(description="Whether provider is ready to accept requests")
    queue_depth: int = Field(ge=0, description="Current number of requests waiting in queue")
    active_requests: int = Field(ge=0, description="Current number of requests executing inference")
    load_count: int = Field(ge=0, description="Total number of times model was initialized")


class STTCapabilities(AIContractModel):
    """Declarative capability metadata for an STTProvider."""
    provider_id: str = Field(description="Provider identifier")
    model_family: str = Field(default="whisper", description="Model family name")
    engine: str = Field(default="faster-whisper / CTranslate2", description="Execution engine")
    supported_model_sizes: List[str] = Field(default_factory=lambda: ["tiny", "base", "small", "medium", "large-v3"])
    supported_devices: List[str] = Field(default_factory=lambda: ["cpu", "cuda"])
    supported_compute_types: List[str] = Field(default_factory=lambda: ["int8", "float16", "float32"])
    word_timestamps_supported: bool = Field(default=True)
    language_detection_supported: bool = Field(default=True)
    vad_supported: bool = Field(default=True)
    batch_supported: bool = Field(default=True)
    streaming_supported: bool = Field(default=False)
    languages: List[str] = Field(default_factory=lambda: ["*"])


class STTModelMetadata(AIContractModel):
    """
    Authoritative model registry metadata for faster-whisper local implementations (Section 9).
    """
    model_id: str = Field(description="Canonical model identifier (e.g. 'faster-whisper-base')")
    model_family: str = Field(default="whisper")
    model_version: str = Field(default="1.2.1")
    provider_id: str = Field(default="local")
    capabilities: List[str] = Field(default_factory=lambda: ["SPEECH_TO_TEXT"])
    execution: str = Field(default="LOCAL")
    engine: str = Field(default="faster-whisper / CTranslate2")
    languages: List[str] = Field(default_factory=lambda: ["*"])
    device_support: List[str] = Field(default_factory=lambda: ["cpu", "cuda"])
    compute_types: List[str] = Field(default_factory=lambda: ["int8", "float16", "float32"])
    batch_support: bool = Field(default=True)
    streaming_support: bool = Field(default=False)
    word_timestamps_support: bool = Field(default=True)
    language_detection_support: bool = Field(default=True)
    vad_support: bool = Field(default=True)
    quality_profile: QualityTargetEnum = Field(default=QualityTarget.STANDARD)
    latency_profile: str = Field(default="FAST")
    status: str = Field(default="ACTIVE")
    # Measured / Estimated hardware requirements (Section 9)
    ram_requirement_mode: str = Field(default="MEASURED", description="'MEASURED', 'ESTIMATED', or 'UNKNOWN'")
    ram_requirement_mb: int = Field(default=500, description="Approximate RAM footprint in MB")
    vram_requirement_mode: str = Field(default="ESTIMATED", description="'MEASURED', 'ESTIMATED', or 'UNKNOWN'")
    vram_requirement_mb: Optional[int] = Field(default=1000, description="Optional VRAM footprint if CUDA active")
    disk_requirement_mb: int = Field(default=150, description="Model weight footprint on disk")


# =============================================================================
# Abstract STTProvider Interface
# =============================================================================

class STTProvider(ABC):
    """
    Abstract interface for Speech-to-Text intelligence providers.
    Decoupled from generic text/chat models (STT != ChatCompletion).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Returns unique provider identifier (e.g. 'local')."""
        pass

    @abstractmethod
    async def transcribe(self, request: STTRequest) -> STTResponse:
        """Executes speech-to-text transcription."""
        pass

    @abstractmethod
    def get_health(self) -> STTHealth:
        """Returns current operational and health status without triggering model load."""
        pass

    @abstractmethod
    def get_capabilities(self) -> STTCapabilities:
        """Returns declarative capabilities supported by provider."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully closes provider and releases any resident resources."""
        pass
