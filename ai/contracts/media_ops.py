"""
ai/contracts/media_ops.py
=========================
Canonical typed request and response contracts for product media capabilities (S28-M02.1).

Covers all deterministic media processing, domain state operations, cache management,
job lifecycle, and stock media search capabilities.

Invariants:
- Absolute host filesystem paths are NEVER exposed (ADR-004 DEC-06.5).
- Storage artifacts are referenced exclusively via project_id and canonical storage_key.
- Strict Pydantic models (no Dict[str, Any] at boundary contracts).
- Every model inherits from AIContractModel.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel
from ai.contracts.media import TechnicalMetadata, SpeechSegment


# =============================================================================
# Common Reusable Media Operation Items
# =============================================================================

class AudioSegmentItem(AIContractModel):
    """Segment item produced by splitting audio."""
    segment_id: str = Field(min_length=1, description="Identifier of the audio slice")
    storage_key: str = Field(min_length=1, description="StorageService key for slice payload")
    start_seconds: float = Field(ge=0.0, description="Start timestamp relative to source audio")
    end_seconds: float = Field(ge=0.0, description="End timestamp relative to source audio")
    text: Optional[str] = Field(default=None, description="Aligned verbatim transcript text")


class DownloadedAssetItem(AIContractModel):
    """Media asset downloaded from a remote source or webpage."""
    asset_id: str = Field(min_length=1, description="Unique project asset identifier")
    storage_key: str = Field(min_length=1, description="StorageService key for downloaded payload")
    source_url: str = Field(min_length=1, description="Original remote URL")
    content_type: str = Field(min_length=1, description="MIME content type")
    file_size_bytes: int = Field(ge=0, description="Size of payload in bytes")


class StockMediaItem(AIContractModel):
    """Normalized search result item across stock media providers."""
    media_id: str = Field(min_length=1, description="Provider-agnostic stock media identifier")
    media_type: str = Field(min_length=1, description="Media kind: image, video, audio, sound_effect")
    title: Optional[str] = Field(default=None, description="Title or description of the media item")
    preview_url: Optional[str] = Field(default=None, description="Low-resolution preview URL")
    download_url: Optional[str] = Field(default=None, description="Source download URL if available")
    width: Optional[int] = Field(default=None, ge=1, description="Visual width in pixels")
    height: Optional[int] = Field(default=None, ge=1, description="Visual height in pixels")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Media duration in seconds")
    license: Optional[str] = Field(default=None, description="License terms or category")


class IconSearchResultItem(AIContractModel):
    """Normalized icon metadata item."""
    icon_name: str = Field(min_length=1, description="Full canonical icon identifier (e.g. 'mdi:video')")
    collection: str = Field(min_length=1, description="Icon set collection identifier")
    name: str = Field(min_length=1, description="Short name within collection")
    svg_preview: Optional[str] = Field(default=None, description="Inline SVG preview string")


# =============================================================================
# 1. Speech Intelligence Contracts
# =============================================================================

class SpeechToTextInput(AIContractModel):
    """Input contract for transcribing speech audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio file")
    language: Optional[str] = Field(default=None, description="Expected spoken language code (e.g. 'ar', 'en')")
    model_size: Optional[str] = Field(default="base", description="Whisper model tier ('tiny', 'base', 'small', 'medium', 'large-v3')")
    detect_speakers: bool = Field(default=False, description="Whether to perform speaker diarization")


class SegmentSpeechInput(AIContractModel):
    """Input contract for slicing speech audio into segments."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio file")
    segments: Optional[List[SpeechSegment]] = Field(default=None, description="Pre-computed speech segments")
    min_duration_seconds: float = Field(default=1.0, ge=0.1, description="Minimum duration per slice")
    max_duration_seconds: float = Field(default=7.0, ge=1.0, description="Maximum duration per slice")


class SegmentSpeechOutput(AIContractModel):
    """Output contract for sliced speech audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    slices: List[AudioSegmentItem] = Field(default_factory=list, description="Generated audio slices")
    total_segments: int = Field(ge=0, description="Total number of generated slices")


class SpeechManifestInput(AIContractModel):
    """Input contract for generating voiceover manifest."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio file")
    manifest_version: str = Field(default="2.0.0", description="Target manifest version")


class SpeechManifestOutput(AIContractModel):
    """Output contract containing voiceover manifest reference."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    manifest_storage_key: str = Field(min_length=1, description="StorageService key for generated manifest artifact")
    sentence_count: int = Field(ge=0, description="Number of sentences in manifest")
    total_duration_seconds: float = Field(ge=0.0, description="Total voiceover duration")
    words_count: int = Field(ge=0, description="Total transcribed words")


class SpeechTimelineInput(AIContractModel):
    """Input contract for building voiceover timeline."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio file")
    fps: float = Field(default=30.0, gt=0.0, description="Composition frame rate")


class SpeechTimelineOutput(AIContractModel):
    """Output contract for built voiceover timeline."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    timeline_storage_key: str = Field(min_length=1, description="StorageService key for generated timeline artifact")
    total_frames: int = Field(ge=0, description="Total composition frame count")
    cue_points_count: int = Field(ge=0, description="Total timeline cues extracted")


class SpeechTextSegmentItem(AIContractModel):
    """Segment item produced by deterministic speech text splitting."""
    index: int = Field(ge=1, description="1-indexed segment position")
    text: str = Field(min_length=1, description="Segment text content")
    start_seconds: Optional[float] = Field(default=None, ge=0.0, description="Start timestamp if word timestamps provided")
    end_seconds: Optional[float] = Field(default=None, ge=0.0, description="End timestamp if word timestamps provided")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Segment duration in seconds")
    split_reason: str = Field(default="punctuation", description="Reason for boundary split ('punctuation', 'silence', 'duration_limit', 'end_of_text')")
    word_count: int = Field(ge=0, description="Number of words in segment")


class SplitSpeechTextInput(AIContractModel):
    """Input contract for deterministic speech text splitting."""
    text: str = Field(description="Full input speech text to segment")
    language: Optional[str] = Field(default=None, description="Language code (e.g. 'ar', 'en')")
    min_sentence_duration: float = Field(default=2.0, ge=0.1, description="Minimum target duration per sentence")
    max_sentence_duration: float = Field(default=10.0, ge=0.5, description="Maximum allowed duration before forced split")
    silence_threshold: float = Field(default=0.30, ge=0.05, description="Inter-word silence threshold to trigger boundary")


class SplitSpeechTextOutput(AIContractModel):
    """Output contract for split speech text segments."""
    segments: List[SpeechTextSegmentItem] = Field(default_factory=list, description="Extracted sentence segments")
    total_segments: int = Field(ge=0, description="Total number of segments extracted")
    total_words: int = Field(ge=0, description="Total word count processed")
    language: Optional[str] = Field(default=None, description="Detected or configured language")


class PreparedVoSegmentItem(AIContractModel):
    """Individual prepared voiceover segment item."""
    segment_id: str = Field(min_length=1, description="Unique segment identifier")
    index: int = Field(ge=1, description="1-indexed sequence position")
    text: str = Field(min_length=1, description="Voiceover line text")
    estimated_duration_seconds: float = Field(ge=0.0, description="Estimated duration in seconds")
    voice_id: Optional[str] = Field(default=None, description="Voice identifier")
    audio_mode: str = Field(default="voiceover_primary", description="Audio presentation mode")


class PrepareVoSegmentsInput(AIContractModel):
    """Input contract for preparing voiceover segment plan."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    text_segments: List[str] = Field(min_length=1, description="Text segments to prepare for voiceover")
    voice_id: Optional[str] = Field(default=None, description="Voice identifier")
    audio_mode: str = Field(default="voiceover_primary", description="Audio mode")
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="Target speaking rate multiplier")


class PrepareVoSegmentsOutput(AIContractModel):
    """Output contract for prepared voiceover segment plan."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    segments: List[PreparedVoSegmentItem] = Field(default_factory=list, description="Prepared voiceover segments")
    total_segments: int = Field(ge=0, description="Total segment count")
    total_estimated_duration_seconds: float = Field(ge=0.0, description="Total estimated duration")
    audio_mode: str = Field(description="Selected audio mode")


class AlignedWordItem(AIContractModel):
    """Individual aligned word metadata."""
    word: str = Field(min_length=1, description="Word text")
    start_seconds: float = Field(ge=0.0, description="Start timestamp in seconds")
    end_seconds: float = Field(ge=0.0, description="End timestamp in seconds")
    duration_seconds: float = Field(ge=0.0, description="Word duration in seconds")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Alignment confidence")


class AlignedSegmentItem(AIContractModel):
    """Individual aligned speech segment."""
    segment_id: str = Field(min_length=1, description="Segment identifier")
    index: int = Field(ge=1, description="1-indexed position")
    text: str = Field(min_length=1, description="Segment text")
    start_seconds: float = Field(ge=0.0, description="Start timestamp")
    end_seconds: float = Field(ge=0.0, description="End timestamp")
    duration_seconds: float = Field(ge=0.0, description="Segment duration")
    words: List[AlignedWordItem] = Field(default_factory=list, description="Aligned word list")


class AlignAudioMetadataInput(AIContractModel):
    """Input contract for aligning audio metadata."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    transcript: str = Field(description="Full transcript text")
    words: List[AlignedWordItem] = Field(default_factory=list, description="Timestamped words")
    audio_duration_seconds: float = Field(gt=0.0, description="Total audio duration in seconds")


class AlignAudioMetadataOutput(AIContractModel):
    """Output contract for aligned audio metadata."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    segments: List[AlignedSegmentItem] = Field(default_factory=list, description="Aligned segments")
    total_words: int = Field(ge=0, description="Total aligned word count")
    covered_duration_seconds: float = Field(ge=0.0, description="Sum of speech segment durations")
    audio_duration_seconds: float = Field(ge=0.0, description="Source audio duration")
    coverage_ratio: float = Field(ge=0.0, le=1.0, description="Speech duration to audio duration ratio")
    is_valid: bool = Field(default=True, description="Whether alignment passes boundary checks")


# =============================================================================
# 2. Audio Processing Contracts
# =============================================================================

class TrimAudioInput(AIContractModel):
    """Input contract for trimming audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    target_duration_seconds: float = Field(gt=0.0, description="Target duration in seconds")


class TrimAudioOutput(AIContractModel):
    """Output contract for trimmed audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for trimmed audio")
    duration_seconds: float = Field(ge=0.0, description="Final duration in seconds")


class ExtendAudioInput(AIContractModel):
    """Input contract for extending audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    target_duration_seconds: float = Field(gt=0.0, description="Target duration in seconds")
    mode: str = Field(default="loop", description="Extension mode ('loop', 'fade_extend')")
    fade_duration_seconds: float = Field(default=0.5, ge=0.0, description="Crossfade duration in seconds")
    auto_trim_silence: bool = Field(default=True, description="Whether to trim silence before looping")


class ExtendAudioOutput(AIContractModel):
    """Output contract for extended audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for extended audio")
    duration_seconds: float = Field(ge=0.0, description="Final duration in seconds")
    loop_count: int = Field(ge=1, description="Number of loop cycles applied")


class NormalizeLoudnessInput(AIContractModel):
    """Input contract for audio loudness normalization."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    target_lufs: float = Field(default=-16.0, le=0.0, ge=-70.0, description="Target integrated loudness in LUFS")
    peak_limit_db: float = Field(default=-1.0, le=0.0, description="True peak limit in dBFS")


class NormalizeLoudnessOutput(AIContractModel):
    """Output contract for normalized audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for normalized audio")
    measured_lufs: float = Field(description="Measured integrated loudness after normalization")
    normalization_applied: bool = Field(default=True, description="Whether gain adjustment was performed")


class TrimSilenceInput(AIContractModel):
    """Input contract for detecting and trimming silence."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    silence_threshold_db: float = Field(default=-40.0, le=0.0, description="Silence threshold in dBFS")
    min_silence_duration_seconds: float = Field(default=0.3, ge=0.05, description="Minimum silence duration to trigger trimming")


class TrimSilenceOutput(AIContractModel):
    """Output contract for silence-trimmed audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for trimmed audio")
    original_duration_seconds: float = Field(ge=0.0, description="Original audio duration")
    trimmed_duration_seconds: float = Field(ge=0.0, description="Final duration after silence removal")
    trimmed_start_seconds: float = Field(ge=0.0, description="Duration removed from beginning")
    trimmed_end_seconds: float = Field(ge=0.0, description="Duration removed from end")


class SilenceIntervalItem(AIContractModel):
    """Detected silence interval item."""
    start_seconds: float = Field(ge=0.0, description="Silence start timestamp in seconds")
    end_seconds: float = Field(ge=0.0, description="Silence end timestamp in seconds")
    duration_seconds: float = Field(ge=0.0, description="Interval duration in seconds")


class DetectSilenceInput(AIContractModel):
    """Input contract for read-only silence detection."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    threshold_db: float = Field(default=-40.0, le=0.0, description="Silence threshold in dBFS")
    min_silence_duration_seconds: float = Field(default=0.1, ge=0.01, description="Minimum silence interval to detect")


class DetectSilenceOutput(AIContractModel):
    """Output contract for read-only silence detection."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    silence_intervals: List[SilenceIntervalItem] = Field(default_factory=list, description="Detected silence intervals")
    total_silence_duration_seconds: float = Field(ge=0.0, description="Total cumulative silence duration")
    audio_duration_seconds: float = Field(ge=0.0, description="Total audio duration probed")
    silence_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of silence to total audio duration")
    threshold_used_db: float = Field(description="Threshold used for detection")


class AnalyzeLoudnessInput(AIContractModel):
    """Input contract for read-only audio loudness analysis."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")


class AnalyzeLoudnessOutput(AIContractModel):
    """Output contract for read-only audio loudness analysis."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    integrated_lufs: float = Field(description="Integrated loudness in LUFS")
    loudness_range: float = Field(ge=0.0, description="Loudness range (LRA) in LU")
    true_peak_db: float = Field(description="True peak level in dBFS")
    threshold_db: Optional[float] = Field(default=None, description="Measurement threshold in dB")
    measurement_standard: str = Field(default="EBU R128", description="Applied measurement standard")
    duration_seconds: float = Field(ge=0.0, description="Probed audio duration in seconds")


class NormalizeAudioInput(AIContractModel):
    """Input contract for audio loudness normalization (canonical S28-M07 alias)."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    audio_storage_key: str = Field(min_length=1, description="StorageService key for source audio")
    target_lufs: float = Field(default=-16.0, le=0.0, ge=-70.0, description="Target integrated loudness in LUFS")
    true_peak_db: float = Field(default=-1.5, le=0.0, description="True peak limit in dBFS")
    loudness_range: float = Field(default=11.0, gt=0.0, description="Target loudness range (LRA)")
    sample_rate: int = Field(default=44100, ge=8000, le=192000, description="Target sample rate in Hz")


class NormalizeAudioOutput(AIContractModel):
    """Output contract for normalized audio (canonical S28-M07 alias)."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for normalized audio")
    target_lufs: float = Field(description="Requested target LUFS")
    measured_lufs: float = Field(description="Measured integrated loudness after normalization")
    duration_seconds: float = Field(ge=0.0, description="Final audio duration in seconds")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")


# =============================================================================
# 3. Video Processing Contracts
# =============================================================================

class TrimVideoInput(AIContractModel):
    """Input contract for trimming video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    start_time_seconds: float = Field(default=0.0, ge=0.0, description="Start timestamp in seconds")
    duration_seconds: float = Field(gt=0.0, description="Clip duration in seconds")


class TrimVideoOutput(AIContractModel):
    """Output contract for trimmed video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for trimmed video")
    duration_seconds: float = Field(ge=0.0, description="Final duration in seconds")


class ExtendVideoInput(AIContractModel):
    """Input contract for extending video duration."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    target_duration_seconds: float = Field(gt=0.0, description="Target duration in seconds")
    mode: str = Field(default="loop", description="Extension mode ('loop', 'ping_pong')")


class ExtendVideoOutput(AIContractModel):
    """Output contract for extended video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for extended video")
    duration_seconds: float = Field(ge=0.0, description="Final duration in seconds")
    loop_count: int = Field(ge=1, description="Number of loop cycles")


class ResizeVideoInput(AIContractModel):
    """Input contract for resizing video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    target_width: int = Field(gt=0, description="Target width in pixels")
    target_height: int = Field(gt=0, description="Target height in pixels")
    mode: str = Field(default="contain", description="Fit mode ('contain', 'cover', 'stretch')")


class ResizeVideoOutput(AIContractModel):
    """Output contract for resized video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for resized video")
    width: int = Field(ge=1, description="Rendered width")
    height: int = Field(ge=1, description="Rendered height")


class DetectBlackFramesInput(AIContractModel):
    """Input contract for detecting and trimming black frames."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    black_ratio_threshold: float = Field(default=0.98, ge=0.5, le=1.0, description="Proportion of pixels that must be black")
    black_pixel_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Luminance threshold below which a pixel is black")


class DetectBlackFramesOutput(AIContractModel):
    """Output contract for black-frame trimmed video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for trimmed video")
    original_duration_seconds: float = Field(ge=0.0, description="Original duration")
    trimmed_duration_seconds: float = Field(ge=0.0, description="Final duration after black frames removed")
    black_segments_count: int = Field(ge=0, description="Number of black frame intervals removed")


class ChangeVideoSpeedInput(AIContractModel):
    """Input contract for adjusting video playback speed."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    speed_factor: float = Field(gt=0.0, le=16.0, description="Playback speed multiplier (e.g. 1.5 for 1.5x)")
    run_in_background: bool = Field(default=False, description="Whether to execute asynchronously via background job")


class ChangeVideoSpeedOutput(AIContractModel):
    """Output contract for speed adjustment."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: Optional[str] = Field(default=None, description="StorageService key if completed synchronously")
    job_id: Optional[str] = Field(default=None, description="Background job identifier if executed asynchronously")
    is_async: bool = Field(default=False, description="Whether execution was dispatched asynchronously")


class EnforceKeyframesInput(AIContractModel):
    """Input contract for enforcing GOP keyframe intervals."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    keyframe_interval: int = Field(default=1, ge=1, description="Keyframe distance (GOP size in frames)")


class EnforceKeyframesOutput(AIContractModel):
    """Output contract for keyframe-enforced video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for keyframe-aligned video")
    keyframe_interval: int = Field(ge=1, description="Enforced keyframe interval")


class ConcatenateVideosInput(AIContractModel):
    """Input contract for concatenating multiple video clips."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_keys: List[str] = Field(min_length=2, description="Ordered list of video storage keys to concatenate")
    transition: Optional[str] = Field(default=None, description="Optional transition effect name")


class ConcatenateVideosOutput(AIContractModel):
    """Output contract for concatenated video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for concatenated video")
    total_duration_seconds: float = Field(ge=0.0, description="Duration of concatenated output")
    input_count: int = Field(ge=2, description="Number of input clips joined")


# =============================================================================
# 4. Image Processing Contracts
# =============================================================================

class UpscaleImageInput(AIContractModel):
    """Input contract for upscaling or resizing an image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    scale_factor: float = Field(default=2.0, gt=0.0, le=8.0, description="Upscale multiplier")
    target_width: Optional[int] = Field(default=None, ge=1, description="Optional explicit target width")
    target_height: Optional[int] = Field(default=None, ge=1, description="Optional explicit target height")


class UpscaleImageOutput(AIContractModel):
    """Output contract for upscaled image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for upscaled image")
    width: int = Field(ge=1, description="Output width")
    height: int = Field(ge=1, description="Output height")


class CropRatioInput(AIContractModel):
    """Input contract for cropping an image to target aspect ratio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    aspect_ratio: str = Field(default="16:9", description="Target aspect ratio string (e.g. '16:9', '9:16', '1:1')")


class CropRatioOutput(AIContractModel):
    """Output contract for cropped image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for cropped image")
    width: int = Field(ge=1, description="Rendered width")
    height: int = Field(ge=1, description="Rendered height")
    aspect_ratio: str = Field(description="Applied aspect ratio")


class AutoCropInput(AIContractModel):
    """Input contract for auto-cropping whitespace / borders."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    padding_ratio: float = Field(default=0.05, ge=0.0, le=0.5, description="Safety padding ratio around detected content")


class AutoCropOutput(AIContractModel):
    """Output contract for auto-cropped image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for auto-cropped image")
    cropped_box: List[int] = Field(min_length=4, max_length=4, description="Bounding box [x, y, width, height]")
    original_width: int = Field(ge=1, description="Original width")
    original_height: int = Field(ge=1, description="Original height")
    output_width: int = Field(ge=1, description="Output width")
    output_height: int = Field(ge=1, description="Output height")


# =============================================================================
# 5. Media Acquisition & Stock Search Contracts
# =============================================================================

class DownloadRemoteMediaInput(AIContractModel):
    """Input contract for downloading remote media directly."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    url: str = Field(min_length=1, description="Remote media URL to download")
    media_type: str = Field(default="video", description="Media kind ('video', 'image', 'audio')")
    destination_asset_id: Optional[str] = Field(default=None, description="Optional explicit asset identifier")


class DownloadRemoteMediaOutput(AIContractModel):
    """Output contract for downloaded remote media."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Created asset identifier")
    storage_key: str = Field(min_length=1, description="StorageService key for stored file")
    file_size_bytes: int = Field(ge=0, description="Size of downloaded payload")
    content_type: str = Field(min_length=1, description="MIME content type")


class ExtractMediaPageInput(AIContractModel):
    """Input contract for extracting media assets from a webpage."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    page_url: str = Field(min_length=1, description="Webpage URL containing media assets")
    media_type: str = Field(default="video", description="Media kind filter ('video', 'image', 'audio')")


class ExtractMediaPageOutput(AIContractModel):
    """Output contract for webpage media extraction."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    extracted_assets: List[DownloadedAssetItem] = Field(default_factory=list, description="Extracted project assets")
    total_extracted: int = Field(ge=0, description="Number of media assets extracted")


class SearchIconsInput(AIContractModel):
    """Input contract for querying icons."""
    query: str = Field(min_length=1, description="Search term for icons")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results to return")
    collection: Optional[str] = Field(default=None, description="Optional icon set collection filter")


class SearchIconsOutput(AIContractModel):
    """Output contract for icon search results."""
    query: str = Field(description="Executed search query")
    icons: List[IconSearchResultItem] = Field(default_factory=list, description="Found icons")
    total_found: int = Field(ge=0, description="Total matching icons count")


class DownloadIconInput(AIContractModel):
    """Input contract for downloading an icon asset."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    icon_name: str = Field(min_length=1, description="Full canonical icon identifier (e.g. 'mdi:movie')")
    color: Optional[str] = Field(default=None, description="Optional fill color hex code (e.g. '#ffffff')")
    size: int = Field(default=64, ge=16, le=1024, description="Icon dimensions in pixels")


class DownloadIconOutput(AIContractModel):
    """Output contract for downloaded icon."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Created asset identifier")
    storage_key: str = Field(min_length=1, description="StorageService key for downloaded SVG/PNG icon")
    format: str = Field(default="svg", description="Icon format")


class SearchStockImagesInput(AIContractModel):
    """Input contract for searching stock photos."""
    query: str = Field(min_length=1, description="Search keyword query")
    page: int = Field(default=1, ge=1, description="Page index")
    per_page: int = Field(default=15, ge=1, le=100, description="Results per page")
    orientation: Optional[str] = Field(default=None, description="Optional orientation filter ('landscape', 'portrait', 'square')")


class SearchStockImagesOutput(AIContractModel):
    """Output contract for stock image results."""
    query: str = Field(description="Executed query")
    images: List[StockMediaItem] = Field(default_factory=list, description="List of matching stock image items")
    page: int = Field(ge=1, description="Current page number")
    total_results: int = Field(ge=0, description="Total results available across provider")


class SearchStockVideosInput(AIContractModel):
    """Input contract for searching stock footage."""
    query: str = Field(min_length=1, description="Search keyword query")
    page: int = Field(default=1, ge=1, description="Page index")
    per_page: int = Field(default=15, ge=1, le=100, description="Results per page")
    orientation: Optional[str] = Field(default=None, description="Optional orientation filter ('landscape', 'portrait', 'square')")


class SearchStockVideosOutput(AIContractModel):
    """Output contract for stock video footage results."""
    query: str = Field(description="Executed query")
    videos: List[StockMediaItem] = Field(default_factory=list, description="List of matching stock video items")
    page: int = Field(ge=1, description="Current page number")
    total_results: int = Field(ge=0, description="Total results available")


class SearchStockAudioInput(AIContractModel):
    """Input contract for searching stock music and audio tracks."""
    query: str = Field(min_length=1, description="Search keyword query")
    page: int = Field(default=1, ge=1, description="Page index")
    per_page: int = Field(default=15, ge=1, le=100, description="Results per page")


class SearchStockAudioOutput(AIContractModel):
    """Output contract for stock audio tracks."""
    query: str = Field(description="Executed query")
    audio_tracks: List[StockMediaItem] = Field(default_factory=list, description="List of matching audio items")
    page: int = Field(ge=1, description="Current page number")
    total_results: int = Field(ge=0, description="Total results available")


class SearchSoundEffectsInput(AIContractModel):
    """Input contract for searching sound effects."""
    query: str = Field(min_length=1, description="Search keyword query")
    page: int = Field(default=1, ge=1, description="Page index")
    per_page: int = Field(default=15, ge=1, le=100, description="Results per page")
    duration_range: Optional[List[float]] = Field(default=None, min_length=2, max_length=2, description="[min_seconds, max_seconds]")


class SearchSoundEffectsOutput(AIContractModel):
    """Output contract for sound effects."""
    query: str = Field(description="Executed query")
    sound_effects: List[StockMediaItem] = Field(default_factory=list, description="List of matching sound effect items")
    page: int = Field(ge=1, description="Current page number")
    total_results: int = Field(ge=0, description="Total results available")


# =============================================================================
# 6. Media Inspection Contracts
# =============================================================================

class InspectMediaInput(AIContractModel):
    """Input contract for technical media probing."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    storage_keys: List[str] = Field(min_length=1, description="List of media storage keys to probe")


class InspectMediaOutput(AIContractModel):
    """Output contract containing technical inspection metadata."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    files_info: List[TechnicalMetadata] = Field(default_factory=list, description="Extracted technical metadata per file")


# =============================================================================
# 7. Domain State, Cache & Job Lifecycle Contracts
# =============================================================================

class MutateAssetStatusInput(AIContractModel):
    """Input contract for updating asset lifecycle status."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Target asset identifier")
    new_status: str = Field(min_length=1, description="Target asset status (e.g. 'processing', 'ready', 'failed')")
    reason: Optional[str] = Field(default=None, description="Audit reason for status mutation")


class MutateAssetStatusOutput(AIContractModel):
    """Output contract for asset status mutation."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Target asset identifier")
    previous_status: str = Field(description="Previous status before mutation")
    current_status: str = Field(description="Current status after mutation")
    manifest_updated: bool = Field(default=True, description="Whether 02_asset_manifest.json was updated")


class CheckCacheInput(AIContractModel):
    """Input contract for querying project media cache."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Asset identifier")
    transformation_hash: str = Field(min_length=8, description="Deterministic hash of transformation parameters")


class CheckCacheOutput(AIContractModel):
    """Output contract for cache lookup."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Asset identifier")
    transformation_hash: str = Field(min_length=8, description="Transformation parameters hash")
    cache_hit: bool = Field(description="Whether a valid cached artifact exists")
    cached_storage_key: Optional[str] = Field(default=None, description="StorageService key if cache_hit is True")


class StoreCacheInput(AIContractModel):
    """Input contract for storing transformed media into project cache."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Asset identifier")
    transformation_hash: str = Field(min_length=8, description="Deterministic hash of transformation parameters")
    source_storage_key: str = Field(min_length=1, description="StorageService key of rendered variant to cache")


class StoreCacheOutput(AIContractModel):
    """Output contract for cache store operation."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Asset identifier")
    transformation_hash: str = Field(min_length=8, description="Transformation parameters hash")
    cached_storage_key: str = Field(min_length=1, description="StorageService key for cached artifact")
    stored: bool = Field(default=True, description="Whether caching succeeded")


class GetJobStatusInput(AIContractModel):
    """Input contract for checking asynchronous job state."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    job_id: str = Field(min_length=1, description="Unique job execution identifier")


class GetJobStatusOutput(AIContractModel):
    """Output contract for job execution state."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    job_id: str = Field(min_length=1, description="Job execution identifier")
    status: str = Field(min_length=1, description="Job state (e.g. 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')")
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Execution progress percentage")
    output_storage_key: Optional[str] = Field(default=None, description="StorageService key if job completed")
    error: Optional[str] = Field(default=None, description="Error message if job failed")


class CancelJobInput(AIContractModel):
    """Input contract for cancelling an ongoing asynchronous job."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    job_id: str = Field(min_length=1, description="Job execution identifier to cancel")
    reason: Optional[str] = Field(default=None, description="Cancellation reason")


class CancelJobOutput(AIContractModel):
    """Output contract for job cancellation."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    job_id: str = Field(min_length=1, description="Cancelled job identifier")
    cancelled: bool = Field(description="Whether the job was successfully cancelled")
    termination_status: str = Field(description="Post-cancellation state description")


# =============================================================================
# 8. S28-M06 Canonical Unified Media Processing Contracts
# =============================================================================

class ProbeMediaInput(AIContractModel):
    """Input contract for probing media technical properties."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    storage_key: str = Field(min_length=1, description="StorageService key for media object to probe")
    deep_probe: bool = Field(default=True, description="Whether to probe stream packets and technical details")


class ProbeMediaOutput(AIContractModel):
    """Output contract containing technical media probe result."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    storage_key: str = Field(min_length=1, description="Probed media storage key")
    metadata: TechnicalMetadata = Field(description="Technical metadata parsed from ffprobe")


class TranscodeVideoInput(AIContractModel):
    """Input contract for transcoding video into canonical profiles."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    target_container: str = Field(default="mp4", description="Target container format ('mp4', 'mkv', 'webm', 'mov')")
    video_codec: str = Field(default="libx264", description="Target video codec ('libx264', 'libx265', 'vp9', 'copy')")
    audio_codec: Optional[str] = Field(default="aac", description="Target audio codec ('aac', 'mp3', 'opus', 'pcm_s16le', 'copy')")
    crf: Optional[int] = Field(default=23, ge=0, le=51, description="Constant rate factor")
    preset: Optional[str] = Field(default="medium", description="Encoding speed preset")
    target_width: Optional[int] = Field(default=None, gt=0, description="Optional target width in pixels")
    target_height: Optional[int] = Field(default=None, gt=0, description="Optional target height in pixels")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Target frame rate")


class TranscodeVideoOutput(AIContractModel):
    """Output contract for transcoded video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for transcoded video")
    container: str = Field(description="Output container format")
    video_codec: str = Field(description="Output video codec")
    audio_codec: Optional[str] = Field(default=None, description="Output audio codec if present")
    width: int = Field(ge=1, description="Output width")
    height: int = Field(ge=1, description="Output height")
    duration_seconds: float = Field(ge=0.0, description="Output duration in seconds")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")


class ExtractAudioInput(AIContractModel):
    """Input contract for extracting audio stream from a video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    audio_format: str = Field(default="wav", description="Target audio format ('wav', 'mp3', 'aac', 'flac')")
    sample_rate: int = Field(default=44100, ge=8000, le=192000, description="Audio sample rate in Hz")
    channels: int = Field(default=2, ge=1, le=8, description="Number of audio channels")


class ExtractAudioOutput(AIContractModel):
    """Output contract for extracted audio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for extracted audio")
    audio_format: str = Field(description="Audio format")
    sample_rate: int = Field(ge=8000, description="Audio sample rate")
    channels: int = Field(ge=1, description="Number of audio channels")
    duration_seconds: float = Field(ge=0.0, description="Audio duration in seconds")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")


class ExtractedFrameItem(AIContractModel):
    """Item representing a single extracted video frame."""
    frame_index: int = Field(ge=0, description="Sequential index of the frame")
    timestamp_seconds: float = Field(ge=0.0, description="Timestamp within source video in seconds")
    storage_key: str = Field(min_length=1, description="StorageService key for extracted frame image")
    width: int = Field(ge=1, description="Frame width")
    height: int = Field(ge=1, description="Frame height")


class ExtractFramesInput(AIContractModel):
    """Input contract for extracting image frames from a video."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    video_storage_key: str = Field(min_length=1, description="StorageService key for source video")
    timestamps_seconds: Optional[List[float]] = Field(default=None, description="Explicit list of timestamps to extract")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Frame extraction rate")
    image_format: str = Field(default="png", description="Target image format ('png', 'jpg')")
    max_frames: int = Field(default=20, ge=1, le=100, description="Maximum number of frames allowed")
    scale_width: Optional[int] = Field(default=None, gt=0, description="Optional frame scale width")
    scale_height: Optional[int] = Field(default=None, gt=0, description="Optional frame scale height")


class ExtractFramesOutput(AIContractModel):
    """Output contract for extracted frames."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    frames: List[ExtractedFrameItem] = Field(default_factory=list, description="Extracted frame items")
    total_frames: int = Field(ge=0, description="Total number of frames extracted")


class ConcatMediaInput(AIContractModel):
    """Input contract for concatenating media streams."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    storage_keys: List[str] = Field(min_length=2, max_length=100, description="Ordered list of media storage keys to concatenate")
    media_type: str = Field(default="video", description="Media kind ('video', 'audio')")
    reencode_if_needed: bool = Field(default=True, description="Whether to re-encode streams if codecs/resolutions differ")


class ConcatMediaOutput(AIContractModel):
    """Output contract for concatenated media."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for concatenated output")
    input_count: int = Field(ge=2, description="Number of input clips concatenated")
    total_duration_seconds: float = Field(ge=0.0, description="Total duration of concatenated output")
    file_size_bytes: int = Field(ge=0, description="Size of concatenated output in bytes")


class ChangeContainerInput(AIContractModel):
    """Input contract for changing container format without re-encoding (remuxing)."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    source_storage_key: str = Field(min_length=1, description="StorageService key for source media")
    target_container: str = Field(min_length=2, description="Target container extension (e.g. 'mp4', 'mkv', 'mov')")


class ChangeContainerOutput(AIContractModel):
    """Output contract for remuxed container."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for remuxed media")
    container: str = Field(description="Output container format")
    duration_seconds: float = Field(ge=0.0, description="Media duration in seconds")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")


class NormalizeMediaInput(AIContractModel):
    """Input contract for loudness and audio normalization."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    media_storage_key: str = Field(min_length=1, description="StorageService key for source media")
    target_lufs: float = Field(default=-16.0, ge=-70.0, le=0.0, description="Target integrated loudness in LUFS")
    true_peak_db: float = Field(default=-1.5, le=0.0, description="True peak limit in dBFS")
    loudness_range: float = Field(default=11.0, gt=0.0, description="Target loudness range in LU")
    sample_rate: int = Field(default=44100, ge=8000, le=192000, description="Output sample rate in Hz")


class NormalizeMediaOutput(AIContractModel):
    """Output contract for normalized media."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for normalized media")
    target_lufs: float = Field(description="Requested target LUFS")
    measured_lufs: float = Field(description="Measured integrated LUFS after normalization")
    duration_seconds: float = Field(ge=0.0, description="Media duration in seconds")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")

