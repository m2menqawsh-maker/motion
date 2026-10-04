"""
ai/speech/__init__.py
=====================
Speech Intelligence subsystem (S27.14 / S28-M04).
"""

from ai.speech.adapter import (
    FakeSpeechProviderA,
    FakeSpeechProviderB,
    GoogleStyleAdapter,
    SpeechProviderAdapter,
    WhisperStyleAdapter,
)
from ai.speech.reconciliation import (
    AudioChunkPlan,
    deduplicate_boundary_words,
    plan_media_chunks,
    reconcile_chunk_transcripts,
    reconcile_speaker_catalog,
    shift_segment_timestamps,
    shift_word_timestamps,
)
from ai.speech.stt_provider import (
    AudioDecodeError,
    DeviceUnavailableError,
    InvalidAudioError,
    ModelInferenceError,
    ModelLoadError,
    ModelNotAvailableError,
    OutputValidationError,
    ResourceExhaustedError,
    STTCapabilities,
    STTConfig,
    STTError,
    STTHealth,
    STTModelMetadata,
    STTProvider,
    STTRequest,
    STTResponse,
    STTTimeoutError,
    StorageReadError,
    TenantAccessDeniedError,
)
from ai.speech.lifecycle import WhisperLifecycleManager
from ai.speech.local_provider import LocalSTTProvider
from ai.speech.storage_resolver import resolve_and_materialize_audio
from ai.speech.cache import STTCacheManager, get_stt_cache_manager

__all__ = [
    # S27
    "AudioChunkPlan",
    "deduplicate_boundary_words",
    "plan_media_chunks",
    "reconcile_chunk_transcripts",
    "reconcile_speaker_catalog",
    "shift_segment_timestamps",
    "shift_word_timestamps",
    "FakeSpeechProviderA",
    "FakeSpeechProviderB",
    "GoogleStyleAdapter",
    "SpeechProviderAdapter",
    "WhisperStyleAdapter",
    # S28-M04
    "STTProvider",
    "LocalSTTProvider",
    "WhisperLifecycleManager",
    "STTRequest",
    "STTResponse",
    "STTConfig",
    "STTHealth",
    "STTCapabilities",
    "STTModelMetadata",
    "STTError",
    "InvalidAudioError",
    "AudioDecodeError",
    "ModelNotAvailableError",
    "ModelLoadError",
    "ModelInferenceError",
    "DeviceUnavailableError",
    "ResourceExhaustedError",
    "STTTimeoutError",
    "OutputValidationError",
    "StorageReadError",
    "TenantAccessDeniedError",
    "resolve_and_materialize_audio",
    "STTCacheManager",
    "get_stt_cache_manager",
]
