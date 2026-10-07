"""
ai/contracts/specialized.py
===========================
Canonical typed contracts for Specialized Media AI Operations (S27.17 / AI-13).

Covers provider-neutral interfaces for:
- TEXT_TO_SPEECH
- IMAGE_GENERATION
- VIDEO_GENERATION
- PERSON_SEGMENTATION
- BACKGROUND_REMOVAL
- LIP_SYNC
- UPSCALE
- AUDIO_DENOISE
- AUDIO_ENHANCE
- VOCAL_ISOLATION

Invariants:
- Absolute host filesystem paths are NEVER exposed (ADR-004 DEC-06.5).
- Storage artifacts referenced exclusively via canonical abstract storage_key.
- Strict Pydantic models (no Dict[str, Any] at boundary contracts).
- Every analytical/generative result carries full provenance audit records.
"""

from __future__ import annotations

from typing import Optional
from pydantic import Field

from ai.contracts.base import AIContractModel
from ai.contracts.media import AnalysisProvenance


# =============================================================================
# 1. Text to Speech (TTS)
# =============================================================================

class TTSRequest(AIContractModel):
    """Canonical request payload for neural text-to-speech synthesis."""
    text: str = Field(min_length=1, description="Verbatim text to synthesize")
    voice_id: str = Field(min_length=1, description="Target voice profile identifier")
    language: Optional[str] = Field(default=None, description="Spoken language code (e.g. 'ar', 'en')")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Pacing multiplier")
    pitch: Optional[float] = Field(default=0.0, ge=-20.0, le=20.0, description="Semitone pitch offset")
    format: str = Field(default="wav", description="Target audio format ('wav', 'mp3')")


class TTSResult(AIContractModel):
    """Canonical result for text-to-speech synthesis."""
    audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for synthesized audio")
    audio_hash: str = Field(min_length=8, description="SHA-256 hash of synthesized audio payload")
    duration_seconds: float = Field(ge=0.0, description="Duration of synthesized audio")
    sample_rate: int = Field(ge=8000, description="Sample rate in Hz")
    format: str = Field(default="wav", description="Audio format")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 2. Image Generation
# =============================================================================

class ImageGenerationRequest(AIContractModel):
    """Canonical request payload for image generation."""
    prompt: str = Field(min_length=1, description="Text prompt describing desired visual")
    negative_prompt: Optional[str] = Field(default=None, description="Elements to exclude")
    width: int = Field(default=1024, ge=256, le=4096, description="Output image width")
    height: int = Field(default=1024, ge=256, le=4096, description="Output image height")
    style: Optional[str] = Field(default=None, description="Artistic or aesthetic style tag")
    seed: Optional[int] = Field(default=None, ge=0, description="Deterministic seed for reproducibility")


class ImageGenerationResult(AIContractModel):
    """Canonical result for image generation."""
    image_storage_key: str = Field(min_length=1, description="Abstract StorageService key for generated image")
    image_hash: str = Field(min_length=8, description="SHA-256 hash of generated image payload")
    width: int = Field(ge=1, description="Rendered width")
    height: int = Field(ge=1, description="Rendered height")
    format: str = Field(default="png", description="Image format")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 3. Video Generation
# =============================================================================

class VideoGenerationRequest(AIContractModel):
    """Canonical request payload for video generation."""
    prompt: str = Field(min_length=1, description="Text prompt describing video motion and narrative")
    duration_seconds: float = Field(default=4.0, ge=0.5, le=60.0, description="Target clip duration")
    fps: int = Field(default=24, ge=12, le=60, description="Target frame rate")
    width: int = Field(default=1280, ge=256, le=3840, description="Target width")
    height: int = Field(default=720, ge=256, le=2160, description="Target height")
    input_frame_storage_key: Optional[str] = Field(default=None, description="Key for image-to-video conditioning")
    seed: Optional[int] = Field(default=None, ge=0, description="Deterministic seed")


class VideoGenerationResult(AIContractModel):
    """Canonical result for video generation."""
    video_storage_key: str = Field(min_length=1, description="Abstract StorageService key for generated video")
    video_hash: str = Field(min_length=8, description="SHA-256 hash of generated video payload")
    duration_seconds: float = Field(ge=0.0, description="Actual rendered duration")
    fps: float = Field(ge=1.0, description="Rendered frame rate")
    width: int = Field(ge=1, description="Rendered width")
    height: int = Field(ge=1, description="Rendered height")
    format: str = Field(default="mp4", description="Container format")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 4. Person Segmentation
# =============================================================================

class PersonSegmentationRequest(AIContractModel):
    """Canonical request payload for human segmentation mask extraction."""
    image_storage_key: str = Field(min_length=1, description="Abstract StorageService key for input image/frame")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of input image")
    return_mask: bool = Field(default=True, description="Whether to produce alpha matte binary mask")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Probability cutoff threshold")


class PersonSegmentationResult(AIContractModel):
    """Canonical result for person segmentation."""
    mask_storage_key: str = Field(min_length=1, description="Abstract StorageService key for segmentation mask")
    mask_hash: str = Field(min_length=8, description="SHA-256 hash of mask payload")
    person_count: int = Field(default=1, ge=0, description="Detected human figure count")
    confidence: float = Field(ge=0.0, le=1.0, description="Average segmentation confidence")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 5. Background Removal
# =============================================================================

class BackgroundRemovalRequest(AIContractModel):
    """Canonical request payload for visual background removal."""
    image_storage_key: str = Field(min_length=1, description="Abstract StorageService key for input image")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of input image")
    output_format: str = Field(default="png", description="Output format preserving alpha (e.g. 'png', 'webp')")


class BackgroundRemovalResult(AIContractModel):
    """Canonical result for background removal."""
    output_storage_key: str = Field(min_length=1, description="Abstract StorageService key for transparent image")
    output_hash: str = Field(min_length=8, description="SHA-256 hash of transparent image payload")
    format: str = Field(default="png", description="Format of output image")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 6. Lip Sync
# =============================================================================

class LipSyncRequest(AIContractModel):
    """Canonical request payload for audio-driven facial lip synchronization."""
    video_storage_key: str = Field(min_length=1, description="Abstract StorageService key for talking-head video")
    audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for speech audio")
    content_hash: str = Field(min_length=8, description="Combined hash of inputs")


class LipSyncResult(AIContractModel):
    """Canonical result for lip synchronization."""
    output_video_storage_key: str = Field(min_length=1, description="Abstract StorageService key for lip-synced video")
    output_video_hash: str = Field(min_length=8, description="SHA-256 hash of output video")
    duration_seconds: float = Field(ge=0.0, description="Output video duration")
    sync_confidence: float = Field(ge=0.0, le=1.0, description="Estimated audio-visual alignment confidence")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 7. Upscale
# =============================================================================

class UpscaleRequest(AIContractModel):
    """Canonical request payload for visual super-resolution / upscaling."""
    media_storage_key: str = Field(min_length=1, description="Abstract StorageService key for input media")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of input media")
    scale_factor: float = Field(default=2.0, ge=1.0, le=8.0, description="Spatial scaling factor")
    target_width: Optional[int] = Field(default=None, ge=1, description="Optional target width constraint")
    target_height: Optional[int] = Field(default=None, ge=1, description="Optional target height constraint")


class UpscaleResult(AIContractModel):
    """Canonical result for super-resolution / upscaling."""
    output_storage_key: str = Field(min_length=1, description="Abstract StorageService key for upscaled media")
    output_hash: str = Field(min_length=8, description="SHA-256 hash of upscaled media payload")
    width: int = Field(ge=1, description="Output pixel width")
    height: int = Field(ge=1, description="Output pixel height")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 8. Audio Denoise
# =============================================================================

class AudioDenoiseRequest(AIContractModel):
    """Canonical request payload for acoustic background noise suppression."""
    audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for noisy audio")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of noisy audio")
    aggressiveness: float = Field(default=0.5, ge=0.0, le=1.0, description="Denoise suppression strength")


class AudioDenoiseResult(AIContractModel):
    """Canonical result for audio denoising."""
    output_audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for denoised audio")
    output_audio_hash: str = Field(min_length=8, description="SHA-256 hash of cleaned audio")
    noise_reduction_db: float = Field(default=12.0, description="Estimated noise reduction in dB")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 9. Audio Enhance
# =============================================================================

class AudioEnhanceRequest(AIContractModel):
    """Canonical request payload for audio voice presence and mastering enhancement."""
    audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for input audio")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of input audio")
    target_lufs: float = Field(default=-16.0, le=0.0, description="Target integrated loudness")


class AudioEnhanceResult(AIContractModel):
    """Canonical result for audio enhancement."""
    output_audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for enhanced audio")
    output_audio_hash: str = Field(min_length=8, description="SHA-256 hash of mastered audio")
    applied_lufs: float = Field(description="Achieved integrated loudness in LUFS")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")


# =============================================================================
# 10. Vocal Isolation
# =============================================================================

class VocalIsolationRequest(AIContractModel):
    """Canonical request payload for stem separation / vocal isolation."""
    audio_storage_key: str = Field(min_length=1, description="Abstract StorageService key for composite audio")
    content_hash: str = Field(min_length=8, description="SHA-256 hash of composite audio")
    extract_instrumental: bool = Field(default=True, description="Whether to also produce backing track stem")


class VocalIsolationResult(AIContractModel):
    """Canonical result for vocal stem separation."""
    vocals_storage_key: str = Field(min_length=1, description="Abstract StorageService key for isolated vocal stem")
    vocals_hash: str = Field(min_length=8, description="SHA-256 hash of vocal stem")
    instrumental_storage_key: Optional[str] = Field(default=None, description="Key for backing track stem")
    instrumental_hash: Optional[str] = Field(default=None, description="SHA-256 hash of backing stem")
    provenance: AnalysisProvenance = Field(description="Provenance audit record")
