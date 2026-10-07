"""
ai/tools/adapters/media_processing.py
=====================================
Canonical ToolGateway adapter for MediaProcessingService (S28-M06).

Invariants:
- AI callers submit provider-neutral CapabilityRequest objects to ToolGateway.
- Calls are dispatched to MediaProcessingService and FFmpegAdapter.
- AI callers never supply arbitrary shell commands, raw host paths, or flags.
- Translates canonical MediaProcessingService results into strongly-typed output dictionaries.
- Unblocks CONCATENATE_VIDEOS / CONCAT_MEDIA safely.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

from ai.contracts import (
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityRequest,
    CapabilityType,
    ImplementationDescriptor,
)
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.media import TechnicalMetadata
from ai.media_processing.contracts import (
    AnalyzeLoudnessRequest,
    ChangeContainerRequest,
    ChangeVideoSpeedRequest,
    ConcatMediaRequest,
    DetectBlackFramesRequest,
    DetectSilenceRequest,
    EnforceKeyframesRequest,
    ExtendAudioRequest,
    ExtendVideoRequest,
    ExtractAudioRequest,
    ExtractFramesRequest,
    NormalizeMediaRequest,
    ProbeMediaRequest,
    ResizeVideoRequest,
    TranscodeVideoRequest,
    TrimAudioRequest,
    TrimSilenceRequest,
    TrimVideoRequest,
)
from ai.media_processing.errors import MediaProcessingError
from ai.media_processing.service import MediaProcessingService
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.storage.storage_service import StorageService, get_storage_service

logger = logging.getLogger("ai.tools.adapters.media_processing")


class MediaProcessingAdapter(CapabilityAdapter):
    """
    Adapter executing unified media processing capabilities via MediaProcessingService.
    """

    HANDLED_CAPABILITY_TYPES: Set[str] = {
        # Canonical S28-M06 & S28-M07 Capabilities
        CapabilityType.PROBE_MEDIA.value,
        CapabilityType.TRANSCODE_VIDEO.value,
        CapabilityType.EXTRACT_AUDIO.value,
        CapabilityType.EXTRACT_FRAMES.value,
        CapabilityType.CONCAT_MEDIA.value,
        CapabilityType.CHANGE_CONTAINER.value,
        CapabilityType.NORMALIZE_MEDIA.value,
        CapabilityType.NORMALIZE_AUDIO.value,
        CapabilityType.ANALYZE_LOUDNESS.value,
        CapabilityType.DETECT_SILENCE.value,

        # Preserved Legacy Capabilities
        CapabilityType.TRIM_VIDEO.value,
        CapabilityType.EXTEND_VIDEO.value,
        CapabilityType.RESIZE_VIDEO.value,
        CapabilityType.TRIM_BLACK_FRAMES.value,
        CapabilityType.CHANGE_VIDEO_SPEED.value,
        CapabilityType.ENFORCE_KEYFRAME_INTERVAL.value,
        CapabilityType.CONCATENATE_VIDEOS.value,
        CapabilityType.TRIM_AUDIO.value,
        CapabilityType.EXTEND_AUDIO.value,
        CapabilityType.NORMALIZE_AUDIO_LOUDNESS.value,
        CapabilityType.TRIM_AUDIO_SILENCE.value,
        CapabilityType.INSPECT_MEDIA.value,
    }

    CANONICAL_S28_M06_CAPS: Set[str] = {
        CapabilityType.PROBE_MEDIA.value,
        CapabilityType.TRANSCODE_VIDEO.value,
        CapabilityType.EXTRACT_AUDIO.value,
        CapabilityType.EXTRACT_FRAMES.value,
        CapabilityType.CONCAT_MEDIA.value,
        CapabilityType.CHANGE_CONTAINER.value,
        CapabilityType.NORMALIZE_MEDIA.value,
        CapabilityType.NORMALIZE_AUDIO.value,
        CapabilityType.ANALYZE_LOUDNESS.value,
        CapabilityType.DETECT_SILENCE.value,
    }

    def __init__(
        self,
        service: Optional[MediaProcessingService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        super().__init__(name="canonical_media_processing_adapter", adapter_kind="CANONICAL_MEDIA_PROCESSING")
        self._storage_service = storage_service or get_storage_service()
        self._service = service or MediaProcessingService(storage_service=self._storage_service)

    @property
    def service(self) -> MediaProcessingService:
        return self._service

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        cap_val = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        if cap_val in self.CANONICAL_S28_M06_CAPS:
            return True

        # If a legacy MCP implementation descriptor is requested, defer to MCPToolAdapter
        if implementation and (
            implementation.implementation_id.startswith("legacy_")
            or getattr(implementation, "implementation_kind", None) == "LEGACY_MCP"
        ):
            return False

        return cap_val in self.HANDLED_CAPABILITY_TYPES

    async def get_health(self) -> Dict[str, Any]:
        """Returns health probe info for ffmpeg and ffprobe executables."""
        adapter_health = self._service.adapter.get_health()
        return {
            "healthy": adapter_health.get("healthy", False),
            "adapter": self.name,
            "ffmpeg_path": adapter_health.get("ffmpeg_path"),
            "ffprobe_path": adapter_health.get("ffprobe_path"),
        }

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        """Executes canonical media processing capability via MediaProcessingService."""
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)
        inp = validated_input.model_dump() if hasattr(validated_input, "model_dump") else request.input

        try:
            # 1. PROBE_MEDIA / INSPECT_MEDIA
            if cap_val in (CapabilityType.PROBE_MEDIA.value, CapabilityType.INSPECT_MEDIA.value):
                storage_key = inp.get("storage_key")
                if not storage_key and inp.get("storage_keys"):
                    storage_key = inp["storage_keys"][0]
                req = ProbeMediaRequest(
                    project_id=request.project_id,
                    storage_key=storage_key or "",
                    deep_probe=inp.get("deep_probe", True),
                )
                res = await self._service.probe_media(req)
                if cap_val == CapabilityType.INSPECT_MEDIA.value:
                    v_stream = res.video_streams[0] if res.video_streams else None
                    a_stream = res.audio_streams[0] if res.audio_streams else None
                    tech_meta = TechnicalMetadata(
                        format=res.container,
                        duration_seconds=res.duration_seconds,
                        file_size_bytes=res.file_size_bytes,
                        has_audio=res.has_audio,
                        has_video=res.has_video,
                        audio_channels=a_stream.channels if a_stream else None,
                        audio_sample_rate=a_stream.sample_rate if a_stream else None,
                        audio_bitrate=a_stream.bit_rate if a_stream else None,
                        audio_codec=a_stream.codec_name if a_stream else None,
                        width=v_stream.width if v_stream else None,
                        height=v_stream.height if v_stream else None,
                        fps=v_stream.fps if v_stream else None,
                        video_codec=v_stream.codec_name if v_stream else None,
                    )
                    return {
                        "project_id": request.project_id,
                        "files_info": [tech_meta.model_dump()],
                    }
                return res.model_dump()

            # 2. TRANSCODE_VIDEO
            elif cap_val == CapabilityType.TRANSCODE_VIDEO.value:
                req = TranscodeVideoRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    target_container=inp.get("target_container", "mp4"),
                    video_codec=inp.get("video_codec", "libx264"),
                    audio_codec=inp.get("audio_codec", "aac"),
                    crf=inp.get("crf", 23),
                    preset=inp.get("preset", "medium"),
                    target_width=inp.get("target_width"),
                    target_height=inp.get("target_height"),
                    fps=inp.get("fps"),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.transcode_video(req)
                return res.model_dump()

            # 3. TRIM_VIDEO
            elif cap_val == CapabilityType.TRIM_VIDEO.value:
                req = TrimVideoRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    start_time_seconds=inp.get("start_time_seconds", 0.0),
                    duration_seconds=inp.get("duration_seconds"),
                    end_time_seconds=inp.get("end_time_seconds"),
                    accurate_seek=inp.get("accurate_seek", True),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.trim_video(req)
                return {
                    "project_id": res.project_id,
                    "output_storage_key": res.output_storage_key,
                    "duration_seconds": res.duration_seconds,
                }

            # 4. RESIZE_VIDEO
            elif cap_val == CapabilityType.RESIZE_VIDEO.value:
                req = ResizeVideoRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    target_width=inp.get("target_width", 1920),
                    target_height=inp.get("target_height", 1080),
                    maintain_aspect_ratio=inp.get("maintain_aspect_ratio", True),
                    mode=inp.get("mode", "contain"),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.resize_video(req)
                return {
                    "project_id": res.project_id,
                    "output_storage_key": res.output_storage_key,
                    "width": res.width,
                    "height": res.height,
                }

            # 5. EXTEND_VIDEO
            elif cap_val == CapabilityType.EXTEND_VIDEO.value:
                req = ExtendVideoRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    target_duration_seconds=inp.get("target_duration_seconds", 5.0),
                    method=inp.get("method") or inp.get("mode", "loop"),
                    short_duration_threshold=inp.get("short_duration_threshold", 2.0),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.extend_video(req)
                return res.model_dump()

            # 6. TRIM_BLACK_FRAMES
            elif cap_val == CapabilityType.TRIM_BLACK_FRAMES.value:
                threshold_val = inp.get("threshold") or inp.get("black_ratio_threshold", 0.98)
                req = DetectBlackFramesRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    threshold=threshold_val,
                    min_duration=inp.get("min_duration", 0.1),
                    trim_start=inp.get("trim_start", True),
                    trim_end=inp.get("trim_end", True),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.detect_and_trim_black_frames(req)
                return res.model_dump()

            # 7. CHANGE_VIDEO_SPEED
            elif cap_val == CapabilityType.CHANGE_VIDEO_SPEED.value:
                req = ChangeVideoSpeedRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    speed_factor=inp.get("speed_factor", 1.0),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.change_video_speed(req)
                return res.model_dump()

            # 8. ENFORCE_KEYFRAME_INTERVAL
            elif cap_val == CapabilityType.ENFORCE_KEYFRAME_INTERVAL.value:
                req = EnforceKeyframesRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    gop_value=inp.get("keyframe_interval") or inp.get("gop_value", 1),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.enforce_keyframes(req)
                return res.model_dump()

            # 9. EXTRACT_AUDIO
            elif cap_val == CapabilityType.EXTRACT_AUDIO.value:
                req = ExtractAudioRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    audio_format=inp.get("audio_format", "wav"),
                    sample_rate=inp.get("sample_rate", 44100),
                    channels=inp.get("channels", 2),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.extract_audio(req)
                return res.model_dump()

            # 10. TRIM_AUDIO
            elif cap_val == CapabilityType.TRIM_AUDIO.value:
                req = TrimAudioRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("source_storage_key", ""),
                    target_duration_seconds=inp.get("target_duration_seconds", 1.0),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.trim_audio(req)
                return res.model_dump()

            # 11. NORMALIZE_MEDIA / NORMALIZE_AUDIO_LOUDNESS / NORMALIZE_AUDIO
            elif cap_val in (CapabilityType.NORMALIZE_MEDIA.value, CapabilityType.NORMALIZE_AUDIO_LOUDNESS.value, CapabilityType.NORMALIZE_AUDIO.value):
                req = NormalizeMediaRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("media_storage_key") or inp.get("source_storage_key", ""),
                    target_lufs=inp.get("target_lufs", -16.0),
                    true_peak_db=inp.get("peak_limit_db") or inp.get("true_peak_db", -1.5),
                    loudness_range=inp.get("loudness_range", 11.0),
                    sample_rate=inp.get("sample_rate", 44100),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.normalize_media(req)
                return res.model_dump()

            # 12. TRIM_AUDIO_SILENCE
            elif cap_val == CapabilityType.TRIM_AUDIO_SILENCE.value:
                req = TrimSilenceRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("source_storage_key", ""),
                    threshold_db=inp.get("silence_threshold_db") or inp.get("threshold_db", -40.0),
                    min_silence_duration=inp.get("min_silence_duration_seconds") or inp.get("min_silence_duration", 0.1),
                    trim_start=inp.get("trim_start", True),
                    trim_end=inp.get("trim_end", True),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.trim_audio_silence(req)
                return res.model_dump()

            # 13. EXTEND_AUDIO
            elif cap_val == CapabilityType.EXTEND_AUDIO.value:
                req = ExtendAudioRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("source_storage_key", ""),
                    target_duration_seconds=inp.get("target_duration_seconds", 5.0),
                    method=inp.get("mode") or inp.get("method", "loop"),
                    auto_trim_silence_before_loop=inp.get("auto_trim_silence", True),
                    short_duration_threshold=inp.get("short_duration_threshold", 2.0),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.extend_audio(req)
                return res.model_dump()

            # 14. EXTRACT_FRAMES
            elif cap_val == CapabilityType.EXTRACT_FRAMES.value:
                req = ExtractFramesRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("video_storage_key") or inp.get("source_storage_key", ""),
                    timestamps_seconds=inp.get("timestamps_seconds"),
                    fps=inp.get("fps"),
                    image_format=inp.get("image_format", "png"),
                    max_frames=inp.get("max_frames", 20),
                    scale_width=inp.get("scale_width"),
                    scale_height=inp.get("scale_height"),
                )
                res = await self._service.extract_frames(req)
                return res.model_dump()

            # 15. CONCAT_MEDIA / CONCATENATE_VIDEOS
            elif cap_val in (CapabilityType.CONCAT_MEDIA.value, CapabilityType.CONCATENATE_VIDEOS.value):
                keys = inp.get("storage_keys") or inp.get("video_storage_keys", [])
                req = ConcatMediaRequest(
                    project_id=request.project_id,
                    source_storage_keys=keys,
                    media_type=inp.get("media_type", "video"),
                    reencode_if_needed=inp.get("reencode_if_needed", True),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.concat_media(req)
                return res.model_dump()

            # 16. CHANGE_CONTAINER
            elif cap_val == CapabilityType.CHANGE_CONTAINER.value:
                req = ChangeContainerRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("source_storage_key", ""),
                    target_container=inp.get("target_container", "mp4"),
                    destination_storage_key=inp.get("destination_storage_key"),
                )
                res = await self._service.change_container(req)
                return res.model_dump()

            # 17. ANALYZE_LOUDNESS
            elif cap_val == CapabilityType.ANALYZE_LOUDNESS.value:
                req = AnalyzeLoudnessRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("source_storage_key", ""),
                )
                res = await self._service.analyze_loudness(req)
                d = res.model_dump()
                d["audio_storage_key"] = d.pop("source_storage_key", "")
                return d

            # 18. DETECT_SILENCE
            elif cap_val == CapabilityType.DETECT_SILENCE.value:
                req = DetectSilenceRequest(
                    project_id=request.project_id,
                    source_storage_key=inp.get("audio_storage_key") or inp.get("source_storage_key", ""),
                    threshold_db=inp.get("threshold_db") or inp.get("silence_threshold_db", -40.0),
                    min_silence_duration=inp.get("min_silence_duration") or inp.get("min_silence_duration_seconds", 0.1),
                )
                res = await self._service.detect_silence(req)
                d = res.model_dump()
                d["audio_storage_key"] = d.pop("source_storage_key", "")
                return d

            else:
                raise MediaProcessingError(
                    f"Unsupported media processing capability '{cap_val}'.",
                    code="UNSUPPORTED_MEDIA_OPERATION",
                    ai_code=AIErrorCode.CAPABILITY_UNAVAILABLE,
                )

        except MediaProcessingError:
            raise
        except Exception as ex:
            raise MediaProcessingError(
                f"Media processing operation failed: {ex}",
                details={"capability_id": cap_val, "error": str(ex)},
            )
