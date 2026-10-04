"""
ai/contracts/common.py
======================
Common domain vocabularies, enums, and provenance structures for AI contracts.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import Field

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum


class ExecutionClass(str, Enum):
    """Execution latency and scheduling tier for an AI workload."""
    INTERACTIVE = "INTERACTIVE"  # Low-latency, synchronous or interactive stream
    BATCH = "BATCH"              # Asynchronous queue-based batch execution
    BACKGROUND = "BACKGROUND"    # Speculative or offline maintenance workload


class PrivacyRequirement(str, Enum):
    """Data privacy and retention requirements for external AI processing."""
    ZERO_DATA_RETENTION = "ZERO_DATA_RETENTION"  # Provider must not log or retain input/output
    INTERNAL_ONLY = "INTERNAL_ONLY"              # Must execute on local or private enterprise models
    PUBLIC_ALLOWED = "PUBLIC_ALLOWED"            # Standard public cloud provider terms acceptable


class QualityTarget(str, Enum):
    """Quality and resource allocation tier for model generation."""
    DRAFT = "DRAFT"          # Fastest, cheapest output for prototyping
    STANDARD = "STANDARD"    # Production balanced quality
    HIGH = "HIGH"            # High fidelity generation
    ULTRA = "ULTRA"          # Maximum quality / exhaustive search


class CapabilityType(str, Enum):
    """
    Authoritative, provider-neutral capability identifiers (ADR-004 DEC-06.3).
    Vendor names (e.g. openai_*, elevenlabs_*, fal_*) are strictly forbidden.
    """
    # Core Language & Reasoning
    TEXT_GENERATION = "TEXT_GENERATION"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    SUMMARIZATION = "SUMMARIZATION"
    TRANSLATION = "TRANSLATION"

    # Representation & Retrieval
    EMBEDDING = "EMBEDDING"
    MULTIMODAL_EMBEDDING = "MULTIMODAL_EMBEDDING"

    # Audio & Speech
    SPEECH_TO_TEXT = "SPEECH_TO_TEXT"
    LANGUAGE_DETECTION = "LANGUAGE_DETECTION"
    DIARIZATION = "DIARIZATION"
    SPEECH_ALIGNMENT = "SPEECH_ALIGNMENT"
    TEXT_TO_SPEECH = "TEXT_TO_SPEECH"
    AUDIO_DENOISE = "AUDIO_DENOISE"
    AUDIO_ENHANCE = "AUDIO_ENHANCE"
    VOCAL_ISOLATION = "VOCAL_ISOLATION"
    BEAT_DETECTION = "BEAT_DETECTION"
    MUSIC_GENERATION = "MUSIC_GENERATION"
    VOICE_ANALYSIS = "VOICE_ANALYSIS"

    # Vision & Visual Understanding
    VISION = "VISION"
    VIDEO_UNDERSTANDING = "VIDEO_UNDERSTANDING"
    OCR = "OCR"
    SHOT_DETECTION = "SHOT_DETECTION"
    OBJECT_DETECTION = "OBJECT_DETECTION"
    PERSON_DETECTION = "PERSON_DETECTION"
    SCENE_CLASSIFICATION = "SCENE_CLASSIFICATION"
    CAPTIONING = "CAPTIONING"

    # Visual Synthesis & Manipulation
    IMAGE_GENERATION = "IMAGE_GENERATION"
    VIDEO_GENERATION = "VIDEO_GENERATION"
    PERSON_SEGMENTATION = "PERSON_SEGMENTATION"
    BACKGROUND_REMOVAL = "BACKGROUND_REMOVAL"
    LIP_SYNC = "LIP_SYNC"
    UPSCALE = "UPSCALE"

    # S28-M02 Audio Processing Capabilities
    TRIM_AUDIO = "TRIM_AUDIO"
    EXTEND_AUDIO = "EXTEND_AUDIO"
    NORMALIZE_AUDIO_LOUDNESS = "NORMALIZE_AUDIO_LOUDNESS"
    TRIM_AUDIO_SILENCE = "TRIM_AUDIO_SILENCE"

    # S28-M02 Speech Intelligence Extensions
    SEGMENT_SPEECH_AUDIO = "SEGMENT_SPEECH_AUDIO"
    GENERATE_SPEECH_MANIFEST = "GENERATE_SPEECH_MANIFEST"
    BUILD_SPEECH_TIMELINE = "BUILD_SPEECH_TIMELINE"

    # S28-M02 Video Processing Capabilities
    TRIM_VIDEO = "TRIM_VIDEO"
    EXTEND_VIDEO = "EXTEND_VIDEO"
    RESIZE_VIDEO = "RESIZE_VIDEO"
    TRIM_BLACK_FRAMES = "TRIM_BLACK_FRAMES"
    CHANGE_VIDEO_SPEED = "CHANGE_VIDEO_SPEED"
    ENFORCE_KEYFRAME_INTERVAL = "ENFORCE_KEYFRAME_INTERVAL"
    CONCATENATE_VIDEOS = "CONCATENATE_VIDEOS"

    # S28-M02 Image Processing Capabilities
    RESIZE_IMAGE = "RESIZE_IMAGE"
    CROP_IMAGE_TO_RATIO = "CROP_IMAGE_TO_RATIO"
    AUTO_CROP_IMAGE = "AUTO_CROP_IMAGE"

    # S28-M02 Media Acquisition & Search Capabilities
    DOWNLOAD_REMOTE_MEDIA = "DOWNLOAD_REMOTE_MEDIA"
    EXTRACT_MEDIA_PAGE = "EXTRACT_MEDIA_PAGE"
    SEARCH_ICONS = "SEARCH_ICONS"
    DOWNLOAD_ICON = "DOWNLOAD_ICON"
    SEARCH_STOCK_IMAGES = "SEARCH_STOCK_IMAGES"
    SEARCH_STOCK_VIDEOS = "SEARCH_STOCK_VIDEOS"
    SEARCH_STOCK_AUDIO = "SEARCH_STOCK_AUDIO"
    SEARCH_SOUND_EFFECTS = "SEARCH_SOUND_EFFECTS"

    # S28-M02 Media Inspection Capabilities
    INSPECT_MEDIA = "INSPECT_MEDIA"

    # S28-M02 Asset Domain Operations
    MUTATE_ASSET_STATUS = "MUTATE_ASSET_STATUS"

    # S28-M02 Cache Management Operations
    CHECK_MEDIA_CACHE = "CHECK_MEDIA_CACHE"
    STORE_MEDIA_CACHE = "STORE_MEDIA_CACHE"

    # S28-M02 Processing Job Lifecycle Management
    GET_JOB_STATUS = "GET_JOB_STATUS"
    CANCEL_PROCESSING_JOB = "CANCEL_PROCESSING_JOB"


# Strict annotated types for field declarations
ExecutionClassEnum = strict_enum(ExecutionClass)
PrivacyRequirementEnum = strict_enum(PrivacyRequirement)
QualityTargetEnum = strict_enum(QualityTarget)
CapabilityTypeEnum = strict_enum(CapabilityType)


class ProvenanceRecord(AIContractModel):
    """Cryptographic and operational audit record tracking origin and execution latency."""
    source: str = Field(min_length=1, description="Origin subsystem or source adapter")
    model_id: Optional[str] = Field(default=None, description="Identifier of the model invoked")
    provider_id: Optional[str] = Field(default=None, description="Identifier of the provider adapter")
    timestamp: TzAwareDatetime = Field(description="Timezone-aware timestamp of event occurrence")
    latency_ms: Optional[int] = Field(default=None, ge=0, description="Execution duration in milliseconds")
