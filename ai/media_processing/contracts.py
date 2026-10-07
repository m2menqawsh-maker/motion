"""
ai/media_processing/contracts.py
================================
Canonical typed operation contracts for Unified Media Processing (S28-M06).

Invariants:
- Absolute host filesystem paths are NEVER exposed to callers / AI.
- Storage objects are referenced exclusively via project_id and canonical storage_key.
- Fully typed Pydantic models (no arbitrary flags pass-through, no raw command strings).
- Strict validation, bounding, and allowlisting for all operations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel
from ai.contracts.media import TechnicalMetadata


class MediaOperationType(str, Enum):
    """Canonical media operations supported by MediaProcessingService."""
    PROBE_MEDIA = "PROBE_MEDIA"
    TRANSCODE_VIDEO = "TRANSCODE_VIDEO"
    TRIM_VIDEO = "TRIM_VIDEO"
    EXTRACT_AUDIO = "EXTRACT_AUDIO"
    EXTRACT_FRAMES = "EXTRACT_FRAMES"
    CONCAT_MEDIA = "CONCAT_MEDIA"
    CHANGE_CONTAINER = "CHANGE_CONTAINER"
    NORMALIZE_MEDIA = "NORMALIZE_MEDIA"

    # Preserved specialized operations
    RESIZE_VIDEO = "RESIZE_VIDEO"
    EXTEND_VIDEO = "EXTEND_VIDEO"
    TRIM_BLACK_FRAMES = "TRIM_BLACK_FRAMES"
    CHANGE_VIDEO_SPEED = "CHANGE_VIDEO_SPEED"
    ENFORCE_KEYFRAME_INTERVAL = "ENFORCE_KEYFRAME_INTERVAL"
    TRIM_AUDIO = "TRIM_AUDIO"
    EXTEND_AUDIO = "EXTEND_AUDIO"
    TRIM_AUDIO_SILENCE = "TRIM_AUDIO_SILENCE"
    ANALYZE_LOUDNESS = "ANALYZE_LOUDNESS"
    DETECT_SILENCE = "DETECT_SILENCE"
    NORMALIZE_AUDIO = "NORMALIZE_AUDIO"
    INSPECT_MEDIA = "INSPECT_MEDIA"


# =============================================================================
# Stream & Technical Inspection Models
# =============================================================================

class MediaStreamInfo(AIContractModel):
    """Detailed stream metadata extracted via ffprobe."""
    index: int = Field(ge=0, description="Stream index")
    codec_type: str = Field(description="Stream type ('video', 'audio', 'subtitle')")
    codec_name: str = Field(description="Codec name (e.g. 'h264', 'aac')")
    codec_long_name: Optional[str] = Field(default=None, description="Descriptive codec name")
    profile: Optional[str] = Field(default=None, description="Codec profile")
    width: Optional[int] = Field(default=None, ge=1, description="Video width in pixels")
    height: Optional[int] = Field(default=None, ge=1, description="Video height in pixels")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Video frame rate")
    pixel_format: Optional[str] = Field(default=None, description="Pixel color format (e.g. 'yuv420p')")
    sample_rate: Optional[int] = Field(default=None, ge=1, description="Audio sample rate in Hz")
    channels: Optional[int] = Field(default=None, ge=1, description="Audio channel count")
    channel_layout: Optional[str] = Field(default=None, description="Audio channel layout (e.g. 'stereo', 'mono')")
    bit_rate: Optional[int] = Field(default=None, ge=0, description="Stream bitrate in bps")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Stream duration in seconds")


class ProbeMediaRequest(AIContractModel):
    """Request to probe media metadata via ffprobe."""
    project_id: str = Field(min_length=1, description="Target project identifier")
    storage_key: str = Field(min_length=1, description="StorageService key for source media")
    deep_probe: bool = Field(default=True, description="Whether to probe stream packets and technical details")


class ProbeMediaResult(AIContractModel):
    """Result of media probing."""
    project_id: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)
    container: str = Field(description="Container format (e.g. 'mov,mp4,m4a,3gp,3g2,mj2')")
    duration_seconds: float = Field(ge=0.0, description="Media duration in seconds")
    bit_rate: Optional[int] = Field(default=None, ge=0, description="Overall bitrate in bps")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")
    has_video: bool = Field(description="Whether video stream is present")
    has_audio: bool = Field(description="Whether audio stream is present")
    video_streams: List[MediaStreamInfo] = Field(default_factory=list)
    audio_streams: List[MediaStreamInfo] = Field(default_factory=list)
    streams: List[MediaStreamInfo] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)
    technical_metadata: Optional[TechnicalMetadata] = None


# =============================================================================
# Video Transcoding & Manipulation Models
# =============================================================================

ALLOWED_VIDEO_CONTAINERS = {"mp4", "mkv", "webm", "mov"}
ALLOWED_VIDEO_CODECS = {"libx264", "libx265", "vp9", "mpeg4", "copy"}
ALLOWED_AUDIO_CODECS = {"aac", "mp3", "opus", "pcm_s16le", "copy", "flac"}
ALLOWED_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}


class TranscodeVideoRequest(AIContractModel):
    """Request to transcode a video into target container and codec specifications."""
    project_id: str = Field(min_length=1, description="Target project identifier")
    source_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    target_container: str = Field(default="mp4", description="Target container format")
    video_codec: str = Field(default="libx264", description="Video codec")
    audio_codec: Optional[str] = Field(default="aac", description="Audio codec")
    crf: Optional[int] = Field(default=23, ge=0, le=51, description="Constant rate factor (0-51)")
    preset: Optional[str] = Field(default="medium", description="Encoding speed preset")
    target_width: Optional[int] = Field(default=None, gt=0, description="Target width in pixels")
    target_height: Optional[int] = Field(default=None, gt=0, description="Target height in pixels")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Target frame rate")
    destination_storage_key: Optional[str] = Field(default=None, description="Optional destination storage key")

    @field_validator("target_container")
    @classmethod
    def validate_container(cls, v: str) -> str:
        clean = v.lower().strip().lstrip(".")
        if clean not in ALLOWED_VIDEO_CONTAINERS:
            raise ValueError(f"Container '{clean}' not in allowed containers: {ALLOWED_VIDEO_CONTAINERS}")
        return clean

    @field_validator("video_codec")
    @classmethod
    def validate_vcodec(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ALLOWED_VIDEO_CODECS:
            raise ValueError(f"Video codec '{clean}' not in allowed codecs: {ALLOWED_VIDEO_CODECS}")
        return clean

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.lower().strip()
        if clean not in ALLOWED_PRESETS:
            raise ValueError(f"Preset '{clean}' not in allowed presets: {ALLOWED_PRESETS}")
        return clean


class TranscodeVideoResult(AIContractModel):
    """Result of video transcoding."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    container: str = Field(description="Output container format")
    video_codec: str = Field(description="Applied video codec")
    audio_codec: Optional[str] = Field(default=None, description="Applied audio codec")
    width: int = Field(ge=1, description="Rendered width")
    height: int = Field(ge=1, description="Rendered height")
    duration_seconds: float = Field(ge=0.0, description="Duration in seconds")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")


class TrimVideoRequest(AIContractModel):
    """Request to trim video duration."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    start_time_seconds: float = Field(default=0.0, ge=0.0, description="Start timestamp")
    duration_seconds: Optional[float] = Field(default=None, gt=0.0, description="Duration in seconds")
    end_time_seconds: Optional[float] = Field(default=None, gt=0.0, description="End timestamp")
    accurate_seek: bool = Field(default=True, description="Whether to re-encode for sample accuracy")
    destination_storage_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.duration_seconds is None and self.end_time_seconds is None:
            raise ValueError("Either duration_seconds or end_time_seconds must be provided.")
        if self.end_time_seconds is not None and self.end_time_seconds <= self.start_time_seconds:
            raise ValueError(f"end_time_seconds ({self.end_time_seconds}) must be greater than start_time_seconds ({self.start_time_seconds}).")
        return self


class TrimVideoResult(AIContractModel):
    """Result of video trimming."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    start_time_seconds: float = Field(ge=0.0)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class ResizeVideoRequest(AIContractModel):
    """Request to resize video dimensions."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_width: int = Field(gt=0, description="Target width in pixels")
    target_height: int = Field(gt=0, description="Target height in pixels")
    maintain_aspect_ratio: bool = Field(default=True, description="Pad/pillarbox to preserve aspect ratio")
    mode: str = Field(default="contain", description="Fit mode ('contain', 'cover', 'stretch')")
    destination_storage_key: Optional[str] = None


class ResizeVideoResult(AIContractModel):
    """Result of video resizing."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class ExtendVideoRequest(AIContractModel):
    """Request to extend video duration via looping or freezing."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_duration_seconds: float = Field(gt=0.0, description="Desired total duration in seconds")
    method: str = Field(default="loop", description="Extension method: 'loop' or 'freeze_last_frame'")
    short_duration_threshold: float = Field(default=2.0, ge=0.1, description="Threshold for short video warning")
    destination_storage_key: Optional[str] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ("loop", "freeze_last_frame"):
            raise ValueError(f"Unknown extend method: '{v}'. Must be 'loop' or 'freeze_last_frame'.")
        return clean


class ExtendVideoResult(AIContractModel):
    """Result of extending video duration."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    duration_seconds: float = Field(ge=0.0)
    warning_message: str = Field(default="")
    file_size_bytes: int = Field(ge=0)


class DetectBlackFramesRequest(AIContractModel):
    """Request to detect and trim black frames at boundaries."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    threshold: float = Field(default=0.98, ge=0.0, le=1.0, description="pic_th: ratio of pixels that must be black")
    min_duration: float = Field(default=0.1, ge=0.01, description="Minimum duration to detect black block")
    trim_start: bool = Field(default=True, description="Whether to trim black frames at the beginning")
    trim_end: bool = Field(default=True, description="Whether to trim black frames at the end")
    destination_storage_key: Optional[str] = None


class DetectBlackFramesResult(AIContractModel):
    """Result of black frames detection and trimming."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    trimmed: bool = Field(description="Whether trimming was applied")
    message: str = Field(description="Operational diagnostic message")
    original_duration_seconds: float = Field(ge=0.0)
    new_duration_seconds: float = Field(ge=0.0)
    black_intervals: List[List[float]] = Field(default_factory=list, description="[[start, end], ...]")
    file_size_bytes: int = Field(ge=0)


class ChangeVideoSpeedRequest(AIContractModel):
    """Request to adjust video playback speed."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    speed_factor: float = Field(gt=0.0, le=100.0, description="Speed multiplier (e.g. 2.0 = 2x faster)")
    destination_storage_key: Optional[str] = None


class ChangeVideoSpeedResult(AIContractModel):
    """Result of video speed adjustment."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    speed_factor: float = Field(gt=0.0)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class EnforceKeyframesRequest(AIContractModel):
    """Request to re-encode video enforcing GOP keyframe spacing."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    gop_value: int = Field(default=1, ge=1, le=300, description="GOP interval (1 = all-intra)")
    destination_storage_key: Optional[str] = None


class EnforceKeyframesResult(AIContractModel):
    """Result of GOP keyframe enforcement."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    gop_value: int = Field(ge=1)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


# =============================================================================
# Audio Processing Models
# =============================================================================

ALLOWED_AUDIO_FORMATS = {"wav", "mp3", "aac", "m4a", "flac", "ogg"}


class ExtractAudioRequest(AIContractModel):
    """Request to extract audio track from video."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    audio_format: str = Field(default="wav", description="Target audio format ('wav', 'mp3', 'aac')")
    sample_rate: int = Field(default=44100, ge=8000, le=192000)
    channels: int = Field(default=2, ge=1, le=8)
    destination_storage_key: Optional[str] = None

    @field_validator("audio_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        clean = v.lower().strip().lstrip(".")
        if clean not in ALLOWED_AUDIO_FORMATS:
            raise ValueError(f"Audio format '{clean}' not in allowed formats: {ALLOWED_AUDIO_FORMATS}")
        return clean


class ExtractAudioResult(AIContractModel):
    """Result of audio extraction."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    audio_format: str = Field(description="Container/format of output")
    sample_rate: int = Field(ge=8000)
    channels: int = Field(ge=1)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class TrimAudioRequest(AIContractModel):
    """Request to trim audio duration."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_duration_seconds: float = Field(gt=0.0, description="Target duration in seconds")
    destination_storage_key: Optional[str] = None


class TrimAudioResult(AIContractModel):
    """Result of audio trimming."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class NormalizeMediaRequest(AIContractModel):
    """Request to normalize media audio loudness (EBU R128)."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_lufs: float = Field(default=-16.0, ge=-70.0, le=0.0, description="Target integrated loudness")
    true_peak_db: float = Field(default=-1.5, le=0.0, description="True peak limit in dBFS")
    loudness_range: float = Field(default=11.0, gt=0.0, description="Target loudness range (LRA)")
    sample_rate: int = Field(default=44100, ge=8000, le=192000, description="Target sample rate")
    destination_storage_key: Optional[str] = None


class NormalizeMediaResult(AIContractModel):
    """Result of media loudness normalization."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    target_lufs: float = Field(description="Target LUFS requested")
    measured_lufs: float = Field(description="Measured LUFS after normalization")
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class TrimSilenceRequest(AIContractModel):
    """Request to detect and trim silence in audio."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    threshold_db: float = Field(default=-40.0, le=0.0, description="Noise threshold in dB")
    min_silence_duration: float = Field(default=0.1, ge=0.01, description="Minimum silence duration in seconds")
    trim_start: bool = Field(default=True, description="Trim leading silence")
    trim_end: bool = Field(default=True, description="Trim trailing silence")
    destination_storage_key: Optional[str] = None


class TrimSilenceResult(AIContractModel):
    """Result of silence trimming."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    trimmed_start_seconds: float = Field(ge=0.0)
    trimmed_end_seconds: float = Field(ge=0.0)
    original_duration_seconds: float = Field(ge=0.0)
    new_duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class ExtendAudioRequest(AIContractModel):
    """Request to extend audio duration."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_duration_seconds: float = Field(gt=0.0, description="Desired duration in seconds")
    method: str = Field(default="loop", description="Extension method: 'loop' or 'fade_extend'")
    auto_trim_silence_before_loop: bool = Field(default=True, description="Trim silence before looping")
    short_duration_threshold: float = Field(default=2.0, ge=0.1, description="One-shot threshold in seconds")
    destination_storage_key: Optional[str] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ("loop", "fade_extend"):
            raise ValueError(f"Unknown audio extend method: '{v}'. Must be 'loop' or 'fade_extend'.")
        return clean


class ExtendAudioResult(AIContractModel):
    """Result of audio extension."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    duration_seconds: float = Field(ge=0.0)
    is_one_shot: bool = Field(default=False, description="Whether audio was detected as one-shot")
    file_size_bytes: int = Field(ge=0)


class SilenceIntervalInfo(AIContractModel):
    """Detected silence interval."""
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)
    duration_seconds: float = Field(ge=0.0)


class DetectSilenceRequest(AIContractModel):
    """Request for read-only silence detection in audio."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    threshold_db: float = Field(default=-40.0, le=0.0, description="Noise threshold in dB")
    min_silence_duration: float = Field(default=0.1, ge=0.01, description="Minimum silence duration in seconds")


class DetectSilenceResult(AIContractModel):
    """Result of read-only silence detection."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    silence_intervals: List[SilenceIntervalInfo] = Field(default_factory=list)
    total_silence_duration_seconds: float = Field(ge=0.0)
    audio_duration_seconds: float = Field(ge=0.0)
    silence_ratio: float = Field(ge=0.0, le=1.0)
    threshold_used_db: float = Field()


class AnalyzeLoudnessRequest(AIContractModel):
    """Request for read-only loudness analysis (EBU R128)."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)


class AnalyzeLoudnessResult(AIContractModel):
    """Result of read-only loudness analysis."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    integrated_lufs: float = Field(description="Integrated loudness in LUFS")
    loudness_range: float = Field(ge=0.0, description="Loudness range (LRA) in LU")
    true_peak_db: float = Field(description="True peak level in dBFS")
    threshold_db: Optional[float] = Field(default=None, description="Measurement threshold in dB")
    measurement_standard: str = Field(default="EBU R128")
    duration_seconds: float = Field(ge=0.0)


class NormalizeAudioRequest(NormalizeMediaRequest):
    """Request for audio loudness normalization (canonical S28-M07 alias)."""
    pass


class NormalizeAudioResult(NormalizeMediaResult):
    """Result of audio loudness normalization (canonical S28-M07 alias)."""
    pass


# =============================================================================
# Frame Extraction & Remuxing Models
# =============================================================================

class ExtractedFrameInfo(AIContractModel):
    """Information regarding a single extracted frame."""
    frame_index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0.0)
    storage_key: str = Field(min_length=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    file_size_bytes: int = Field(ge=0)


class ExtractFramesRequest(AIContractModel):
    """Request to extract image frames from video."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    timestamps_seconds: Optional[List[float]] = Field(default=None, description="Explicit list of timestamps")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Extraction frame rate (e.g. 1/5 = 1 frame every 5s)")
    image_format: str = Field(default="png", description="Target image format ('png', 'jpg')")
    max_frames: int = Field(default=20, ge=1, le=100, description="Bounded maximum frames to extract")
    scale_width: Optional[int] = Field(default=None, gt=0)
    scale_height: Optional[int] = Field(default=None, gt=0)

    @field_validator("image_format")
    @classmethod
    def validate_img_fmt(cls, v: str) -> str:
        clean = v.lower().strip().lstrip(".")
        if clean not in ("png", "jpg", "jpeg", "webp"):
            raise ValueError(f"Image format '{clean}' not allowed.")
        return clean


class ExtractFramesResult(AIContractModel):
    """Result of frame extraction."""
    project_id: str = Field(min_length=1)
    frames: List[ExtractedFrameInfo] = Field(default_factory=list)
    total_frames: int = Field(ge=0)


class ConcatMediaRequest(AIContractModel):
    """Request to concatenate multiple media items."""
    project_id: str = Field(min_length=1)
    source_storage_keys: List[str] = Field(min_length=2, max_length=100, description="Ordered storage keys to concatenate")
    media_type: str = Field(default="video", description="'video' or 'audio'")
    reencode_if_needed: bool = Field(default=True, description="Whether to re-encode streams if parameters mismatch")
    destination_storage_key: Optional[str] = None


class ConcatMediaResult(AIContractModel):
    """Result of media concatenation."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    input_count: int = Field(ge=2)
    total_duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)


class ChangeContainerRequest(AIContractModel):
    """Request to remux media into a different container format without re-encoding."""
    project_id: str = Field(min_length=1)
    source_storage_key: str = Field(min_length=1)
    target_container: str = Field(min_length=2, description="Target container extension (e.g. 'mp4', 'mkv', 'mov')")
    destination_storage_key: Optional[str] = None

    @field_validator("target_container")
    @classmethod
    def validate_container(cls, v: str) -> str:
        clean = v.lower().strip().lstrip(".")
        if clean not in ("mp4", "mkv", "mov", "webm", "avi", "flv"):
            raise ValueError(f"Container '{clean}' not supported for remuxing.")
        return clean


class ChangeContainerResult(AIContractModel):
    """Result of container remuxing."""
    project_id: str = Field(min_length=1)
    output_storage_key: str = Field(min_length=1)
    container: str = Field(description="Output container format")
    duration_seconds: float = Field(ge=0.0)
    file_size_bytes: int = Field(ge=0)
