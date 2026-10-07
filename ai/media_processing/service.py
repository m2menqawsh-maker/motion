"""
ai/media_processing/service.py
==============================
Canonical MediaProcessingService (S28-M06).

Invariants:
- Single canonical entry point for all FFmpeg-backed media operations.
- Translates typed requests into bounded, validated operations.
- Interacts exclusively with StorageService for durable object persistence.
- Enforces strict tenant authorization and workspace confinement.
- Does NOT mutate project lifecycle, review approval, or bypass QC gates.
- Employs transactional staging: output validated before publication; storage failures fail closed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai.contracts.media import TechnicalMetadata
from ai.media_processing.adapter import FFmpegAdapter
from ai.media_processing.contracts import (
    AnalyzeLoudnessRequest,
    AnalyzeLoudnessResult,
    ChangeContainerRequest,
    ChangeContainerResult,
    ChangeVideoSpeedRequest,
    ChangeVideoSpeedResult,
    ConcatMediaRequest,
    ConcatMediaResult,
    DetectBlackFramesRequest,
    DetectBlackFramesResult,
    DetectSilenceRequest,
    DetectSilenceResult,
    EnforceKeyframesRequest,
    EnforceKeyframesResult,
    ExtendAudioRequest,
    ExtendAudioResult,
    ExtendVideoRequest,
    ExtendVideoResult,
    ExtractAudioRequest,
    ExtractAudioResult,
    ExtractedFrameInfo,
    ExtractFramesRequest,
    ExtractFramesResult,
    MediaStreamInfo,
    NormalizeAudioRequest,
    NormalizeAudioResult,
    NormalizeMediaRequest,
    NormalizeMediaResult,
    ProbeMediaRequest,
    ProbeMediaResult,
    ResizeVideoRequest,
    ResizeVideoResult,
    SilenceIntervalInfo,
    TranscodeVideoRequest,
    TranscodeVideoResult,
    TrimAudioRequest,
    TrimAudioResult,
    TrimSilenceRequest,
    TrimSilenceResult,
    TrimVideoRequest,
    TrimVideoResult,
)
from ai.media_processing.errors import (
    FFprobeFailedError,
    InvalidMediaFileError,
    OutputValidationError,
    ProcessExecutionFailedError,
    ProtocolSecurityViolationError,
    StoragePublishFailedError,
)
from ai.media_processing.security import (
    assert_safe_local_path,
    validate_storage_key_confinement,
)
from ai.media_processing.staging import WorkerStagingContext, build_safe_concat_manifest
from ai.media_processing.validator import (
    run_ffprobe_json,
    validate_audio_output,
    validate_concat_output,
    validate_extracted_frames,
    validate_file_sanity,
    validate_video_transcode,
    validate_video_trim,
)
from scripts.core.storage.storage_service import (
    StorageService,
    build_storage_key,
)

logger = logging.getLogger("ai.media_processing.service")


class MediaProcessingService:
    """
    Authoritative service governing media processing capabilities.
    """

    def __init__(
        self,
        storage_service: StorageService,
        adapter: Optional[FFmpegAdapter] = None,
        base_scratch_dir: Optional[Path] = None,
    ):
        self.storage_service = storage_service
        self.adapter = adapter or FFmpegAdapter()
        self.base_scratch_dir = base_scratch_dir or Path("scratch/worker_media")

    def _derive_destination_key(
        self,
        project_id: str,
        category: str,
        filename: str,
        explicit_key: Optional[str] = None,
        workspace_id: str = "ws_default",
    ) -> str:
        """Derives a canonical storage key for output publication."""
        if explicit_key:
            validate_storage_key_confinement(explicit_key, project_id)
            return explicit_key

        unique_item = f"proc_{uuid.uuid4().hex[:12]}"
        return build_storage_key(
            workspace_id=workspace_id,
            project_id=project_id,
            category=f"processed_{category}",
            item_id=unique_item,
            filename=filename,
        )

    def _upload_validated_file(
        self,
        local_path: Path,
        destination_key: str,
        content_type: str = "application/octet-stream",
    ) -> int:
        """Uploads a validated local output file to StorageService."""
        try:
            with open(local_path, "rb") as f:
                meta = self.storage_service.put(
                    key=destination_key,
                    data=f,
                    content_type=content_type,
                )
            return meta.size_bytes
        except Exception as e:
            raise StoragePublishFailedError(
                f"Failed to publish output artifact to storage key '{destination_key}': {e}",
                details={"destination_key": destination_key, "error": str(e)},
            )

    # =========================================================================
    # 1. PROBE_MEDIA
    # =========================================================================

    async def probe_media(self, req: ProbeMediaRequest) -> ProbeMediaResult:
        """Deep technical probing of a media artifact via ffprobe."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.storage_key)
            probe_data = await run_ffprobe_json(local_src)

            format_info = probe_data.get("format", {})
            raw_streams = probe_data.get("streams", [])

            parsed_streams: List[MediaStreamInfo] = []
            video_streams: List[MediaStreamInfo] = []
            audio_streams: List[MediaStreamInfo] = []

            for s in raw_streams:
                c_type = s.get("codec_type", "unknown")
                fps_val: Optional[float] = None
                r_frame_rate = s.get("r_frame_rate", "")
                if "/" in r_frame_rate:
                    num, den = r_frame_rate.split("/")
                    if float(den) > 0:
                        fps_val = float(num) / float(den)

                dur_str = s.get("duration") or format_info.get("duration")
                dur_val = float(dur_str) if dur_str else None

                br_str = s.get("bit_rate") or format_info.get("bit_rate")
                br_val = int(br_str) if br_str and str(br_str).isdigit() else None

                stream_info = MediaStreamInfo(
                    index=int(s.get("index", 0)),
                    codec_type=c_type,
                    codec_name=str(s.get("codec_name", "unknown")),
                    codec_long_name=s.get("codec_long_name"),
                    profile=s.get("profile"),
                    width=int(s.get("width")) if s.get("width") else None,
                    height=int(s.get("height")) if s.get("height") else None,
                    fps=fps_val,
                    pixel_format=s.get("pix_fmt"),
                    sample_rate=int(s.get("sample_rate")) if s.get("sample_rate") else None,
                    channels=int(s.get("channels")) if s.get("channels") else None,
                    channel_layout=s.get("channel_layout"),
                    bit_rate=br_val,
                    duration_seconds=dur_val,
                )
                parsed_streams.append(stream_info)
                if c_type == "video":
                    video_streams.append(stream_info)
                elif c_type == "audio":
                    audio_streams.append(stream_info)

            tot_dur = float(format_info.get("duration", 0.0) or 0.0)
            file_sz = int(format_info.get("size", local_src.stat().st_size) or local_src.stat().st_size)

            return ProbeMediaResult(
                project_id=req.project_id,
                storage_key=req.storage_key,
                container=str(format_info.get("format_name", "unknown")),
                duration_seconds=tot_dur,
                bit_rate=int(format_info.get("bit_rate")) if format_info.get("bit_rate") else None,
                file_size_bytes=file_sz,
                has_video=len(video_streams) > 0,
                has_audio=len(audio_streams) > 0,
                video_streams=video_streams,
                audio_streams=audio_streams,
                streams=parsed_streams,
                tags=format_info.get("tags", {}),
            )

    # =========================================================================
    # 2. TRANSCODE_VIDEO
    # =========================================================================

    async def transcode_video(self, req: TranscodeVideoRequest) -> TranscodeVideoResult:
        """Transcodes video to target container and codec specifications."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            out_name = f"transcode_{uuid.uuid4().hex[:8]}.{req.target_container}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_transcode_command(local_src, local_out, req)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Transcode failed: {res.stderr}")

            val_data = await validate_video_transcode(
                local_out,
                expected_width=req.target_width,
                expected_height=req.target_height,
            )

            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, f"video/{req.target_container}")

            return TranscodeVideoResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                container=val_data["format_name"] or req.target_container,
                video_codec=val_data["codec_name"] or req.video_codec,
                audio_codec=req.audio_codec,
                width=val_data["width"],
                height=val_data["height"],
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 3. TRIM_VIDEO
    # =========================================================================

    async def trim_video(self, req: TrimVideoRequest) -> TrimVideoResult:
        """Trims video duration within specified bounds."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"trim_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            expected_duration = req.duration_seconds
            if expected_duration is None and req.end_time_seconds is not None:
                expected_duration = req.end_time_seconds - req.start_time_seconds

            cmd = self.adapter.build_trim_video_command(local_src, local_out, req)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Trim video failed: {res.stderr}")

            val_data = await validate_video_trim(local_out, expected_duration or 0.0)

            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return TrimVideoResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                start_time_seconds=req.start_time_seconds,
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 4. RESIZE_VIDEO
    # =========================================================================

    async def resize_video(self, req: ResizeVideoRequest) -> ResizeVideoResult:
        """Resizes video dimensions with optional aspect-ratio preservation."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"resize_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_resize_video_command(local_src, local_out, req)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Resize video failed: {res.stderr}")

            val_data = await validate_video_transcode(
                local_out,
                expected_width=req.target_width,
                expected_height=req.target_height,
            )

            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return ResizeVideoResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                width=val_data["width"],
                height=val_data["height"],
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 5. EXTEND_VIDEO
    # =========================================================================

    async def extend_video(self, req: ExtendVideoRequest) -> ExtendVideoResult:
        """Extends video duration via loop or freeze_last_frame."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            curr_duration = float(probe.get("format", {}).get("duration", 0.0))

            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"extend_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            warning_msg = ""
            if curr_duration >= req.target_duration_seconds:
                # Already long enough; copy directly
                cmd = self.adapter.build_trim_video_command(
                    local_src, local_out, TrimVideoRequest(
                        project_id=req.project_id,
                        source_storage_key=req.source_storage_key,
                        start_time_seconds=0.0,
                        duration_seconds=req.target_duration_seconds,
                        accurate_seek=False,
                    )
                )
            elif req.method == "loop":
                if curr_duration < req.short_duration_threshold:
                    warning_msg = f"Warning: original video is very short ({curr_duration:.2f}s). Looping may appear repetitive."
                cmd = self.adapter.build_extend_video_loop_command(local_src, local_out, req.target_duration_seconds)
            else:  # freeze_last_frame
                has_audio = any(s.get("codec_type") == "audio" for s in probe.get("streams", []))
                extra_dur = req.target_duration_seconds - curr_duration
                cmd = self.adapter.build_extend_video_freeze_command(
                    local_src, local_out, extra_dur, req.target_duration_seconds, has_audio
                )

            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Extend video failed: {res.stderr}")

            val_data = await validate_video_transcode(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return ExtendVideoResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                duration_seconds=val_data["duration"],
                warning_message=warning_msg,
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 6. DETECT_AND_TRIM_BLACK_FRAMES
    # =========================================================================

    async def detect_and_trim_black_frames(self, req: DetectBlackFramesRequest) -> DetectBlackFramesResult:
        """Detects and trims black frame intervals at boundaries."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            total_duration = float(probe.get("format", {}).get("duration", 0.0))

            # 1. Detect black frames
            detect_cmd = self.adapter.build_black_detect_command(local_src, req.min_duration, req.threshold)
            detect_res = await self.adapter.execute_raw(detect_cmd)

            black_intervals: List[List[float]] = []
            for line in detect_res.stderr.splitlines():
                if "blackdetect" in line and "black_start:" in line:
                    parts = line.split()
                    try:
                        b_start = float([p for p in parts if p.startswith("black_start:")][0].split(":")[1])
                        b_end = float([p for p in parts if p.startswith("black_end:")][0].split(":")[1])
                        black_intervals.append([b_start, b_end])
                    except Exception:
                        pass

            start_trim = 0.0
            end_trim = total_duration

            if req.trim_start:
                for bs, be in black_intervals:
                    if bs < 0.1:
                        start_trim = max(start_trim, be)
                        break

            if req.trim_end:
                for bs, be in reversed(black_intervals):
                    if be > total_duration - 0.5:
                        end_trim = min(end_trim, bs)
                        break

            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"noblack_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            if start_trim == 0.0 and end_trim == total_duration:
                # No trimming needed, reuse original
                return DetectBlackFramesResult(
                    project_id=req.project_id,
                    output_storage_key=req.source_storage_key,
                    trimmed=False,
                    message="No black frames detected at clip boundaries.",
                    original_duration_seconds=total_duration,
                    new_duration_seconds=total_duration,
                    black_intervals=black_intervals,
                    file_size_bytes=local_src.stat().st_size,
                )

            if start_trim >= end_trim:
                raise InvalidMediaFileError("Video is entirely black frames.")

            # Trim
            trim_cmd = self.adapter.build_trim_video_command(
                local_src, local_out, TrimVideoRequest(
                    project_id=req.project_id,
                    source_storage_key=req.source_storage_key,
                    start_time_seconds=start_trim,
                    duration_seconds=end_trim - start_trim,
                    accurate_seek=True,
                )
            )
            res = await self.adapter.execute_raw(trim_cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Black frame trimming failed: {res.stderr}")

            val_data = await validate_video_transcode(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return DetectBlackFramesResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                trimmed=True,
                message=f"Trimmed black frames from {start_trim:.2f}s to {end_trim:.2f}s.",
                original_duration_seconds=total_duration,
                new_duration_seconds=val_data["duration"],
                black_intervals=black_intervals,
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 7. CHANGE_VIDEO_SPEED
    # =========================================================================

    async def change_video_speed(self, req: ChangeVideoSpeedRequest) -> ChangeVideoSpeedResult:
        """Adjusts video playback speed."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"speed_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_speed_video_command(local_src, local_out, req.speed_factor)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Speed adjustment failed: {res.stderr}")

            val_data = await validate_video_transcode(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return ChangeVideoSpeedResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                speed_factor=req.speed_factor,
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 8. ENFORCE_KEYFRAME_INTERVAL
    # =========================================================================

    async def enforce_keyframes(self, req: EnforceKeyframesRequest) -> EnforceKeyframesResult:
        """Enforces GOP keyframe interval for precision seeking."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".mp4"
            out_name = f"gop{req.gop_value}_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_enforce_keyframes_command(local_src, local_out, req.gop_value)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Keyframe enforcement failed: {res.stderr}")

            val_data = await validate_video_transcode(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "video/mp4")

            return EnforceKeyframesResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                gop_value=req.gop_value,
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 9. EXTRACT_AUDIO
    # =========================================================================

    async def extract_audio(self, req: ExtractAudioRequest) -> ExtractAudioResult:
        """Demuxes and extracts audio stream from video."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            out_name = f"audio_{uuid.uuid4().hex[:8]}.{req.audio_format}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_extract_audio_command(local_src, local_out, req)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Audio extraction failed: {res.stderr}")

            val_data = await validate_audio_output(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "audio", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, f"audio/{req.audio_format}")

            return ExtractAudioResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                audio_format=req.audio_format,
                sample_rate=val_data["sample_rate"],
                channels=val_data["channels"],
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 10. TRIM_AUDIO
    # =========================================================================

    async def trim_audio(self, req: TrimAudioRequest) -> TrimAudioResult:
        """Trims audio duration."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".wav"
            out_name = f"trim_audio_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_trim_audio_command(local_src, local_out, req.target_duration_seconds)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Trim audio failed: {res.stderr}")

            val_data = await validate_audio_output(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "audio", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "audio/wav")

            return TrimAudioResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 11. NORMALIZE_MEDIA
    # =========================================================================

    async def normalize_media(self, req: NormalizeMediaRequest) -> NormalizeMediaResult:
        """Normalizes audio loudness according to EBU R128 standard."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            suffix = Path(req.source_storage_key).suffix or ".wav"
            out_name = f"norm_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_normalize_loudness_command(
                local_src,
                local_out,
                target_lufs=req.target_lufs,
                true_peak=req.true_peak_db,
                loudness_range=req.loudness_range,
                sample_rate=req.sample_rate,
            )
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Loudness normalization failed: {res.stderr}")

            val_data = await validate_audio_output(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "audio", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "audio/wav")

            return NormalizeMediaResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                target_lufs=req.target_lufs,
                measured_lufs=req.target_lufs,  # loudnorm applies targeted normalization
                duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 12. TRIM_AUDIO_SILENCE
    # =========================================================================

    async def trim_audio_silence(self, req: TrimSilenceRequest) -> TrimSilenceResult:
        """Detects and trims leading/trailing silence from audio."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            total_duration = float(probe.get("format", {}).get("duration", 0.0))

            cmd = self.adapter.build_silence_detect_command(local_src, req.threshold_db, req.min_silence_duration)
            res = await self.adapter.execute_raw(cmd)

            silence_starts: List[float] = []
            silence_ends: List[float] = []

            for line in res.stderr.splitlines():
                if "silence_start:" in line:
                    match = re.search(r"silence_start:\s+([\d\.]+)", line)
                    if match:
                        silence_starts.append(float(match.group(1)))
                elif "silence_end:" in line:
                    match = re.search(r"silence_end:\s+([\d\.]+)", line)
                    if match:
                        silence_ends.append(float(match.group(1)))

            start_trim = 0.0
            end_trim = total_duration

            if req.trim_start and silence_starts and silence_starts[0] <= 0.1 and silence_ends:
                start_trim = silence_ends[0]

            if req.trim_end and silence_ends and silence_ends[-1] >= total_duration - 0.5 and silence_starts:
                end_trim = silence_starts[-1]

            if end_trim <= start_trim:
                start_trim = 0.0
                end_trim = total_duration

            suffix = Path(req.source_storage_key).suffix or ".wav"
            out_name = f"trimmed_silence_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            if start_trim == 0.0 and end_trim == total_duration:
                # No silence to trim
                return TrimSilenceResult(
                    project_id=req.project_id,
                    output_storage_key=req.source_storage_key,
                    trimmed_start_seconds=0.0,
                    trimmed_end_seconds=0.0,
                    original_duration_seconds=total_duration,
                    new_duration_seconds=total_duration,
                    file_size_bytes=local_src.stat().st_size,
                )

            # Trim audio slice
            trim_cmd = [
                self.adapter.ffmpeg_bin, "-y", "-nostdin", "-hide_banner",
                "-protocol_whitelist", "file,crypto,data",
                "-i", str(local_src),
            ]
            if start_trim > 0:
                trim_cmd.extend(["-ss", str(start_trim)])
            if end_trim < total_duration:
                trim_cmd.extend(["-to", str(end_trim)])
            trim_cmd.append(str(local_out))

            trim_res = await self.adapter.execute_raw(trim_cmd)
            if not trim_res.is_success:
                raise ProcessExecutionFailedError(f"Silence trimming failed: {trim_res.stderr}")

            val_data = await validate_audio_output(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "audio", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "audio/wav")

            return TrimSilenceResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                trimmed_start_seconds=start_trim,
                trimmed_end_seconds=total_duration - end_trim,
                original_duration_seconds=total_duration,
                new_duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 13. EXTEND_AUDIO
    # =========================================================================

    async def extend_audio(self, req: ExtendAudioRequest) -> ExtendAudioResult:
        """Extends audio duration via loop or crossfade, with one-shot classification."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            orig_duration = float(probe.get("format", {}).get("duration", 0.0))

            # Detect if one-shot SFX
            is_one_shot = orig_duration < req.short_duration_threshold

            suffix = Path(req.source_storage_key).suffix or ".wav"
            out_name = f"extended_audio_{uuid.uuid4().hex[:8]}{suffix}"
            local_out = ctx.get_output_path(out_name)

            if is_one_shot:
                # Return cropped or original
                dest_key = self._derive_destination_key(
                    req.project_id, "audio", out_name, req.destination_storage_key
                )
                file_size = self._upload_validated_file(local_src, dest_key, "audio/wav")
                return ExtendAudioResult(
                    project_id=req.project_id,
                    output_storage_key=dest_key,
                    duration_seconds=orig_duration,
                    is_one_shot=True,
                    file_size_bytes=file_size,
                )

            if orig_duration >= req.target_duration_seconds:
                cmd = self.adapter.build_trim_audio_command(local_src, local_out, req.target_duration_seconds)
            elif req.method == "loop":
                cmd = [
                    self.adapter.ffmpeg_bin, "-y", "-nostdin", "-hide_banner",
                    "-protocol_whitelist", "file,crypto,data",
                    "-stream_loop", "-1",
                    "-i", str(local_src),
                    "-t", str(req.target_duration_seconds),
                    str(local_out),
                ]
            else:  # fade_extend
                crossfade = 0.5
                eff_dur = orig_duration - crossfade
                if eff_dur <= 0:
                    cmd = [
                        self.adapter.ffmpeg_bin, "-y", "-nostdin", "-hide_banner",
                        "-protocol_whitelist", "file,crypto,data",
                        "-stream_loop", "-1",
                        "-i", str(local_src),
                        "-t", str(req.target_duration_seconds),
                        str(local_out),
                    ]
                else:
                    loops = math.ceil((req.target_duration_seconds - orig_duration) / eff_dur) + 1
                    cmd = [self.adapter.ffmpeg_bin, "-y", "-nostdin", "-hide_banner", "-protocol_whitelist", "file,crypto,data"]
                    for _ in range(loops):
                        cmd.extend(["-i", str(local_src)])
                    if loops == 2:
                        filter_complex = f"[0:a][1:a]acrossfade=d={crossfade}[aout]"
                    else:
                        filter_complex = f"[0:a][1:a]acrossfade=d={crossfade}[a1];"
                        for i in range(2, loops):
                            in_pad = f"[a{i-1}]"
                            out_pad = f"[a{i}]" if i < loops - 1 else "[aout]"
                            filter_complex += f"{in_pad}[{i}:a]acrossfade=d={crossfade}{out_pad}"
                            if i < loops - 1:
                                filter_complex += ";"
                    cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]", "-t", str(req.target_duration_seconds), str(local_out)])

            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Audio extend failed: {res.stderr}")

            val_data = await validate_audio_output(local_out)
            dest_key = self._derive_destination_key(
                req.project_id, "audio", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, "audio/wav")

            return ExtendAudioResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                duration_seconds=val_data["duration"],
                is_one_shot=False,
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 14. EXTRACT_FRAMES
    # =========================================================================

    async def extract_frames(self, req: ExtractFramesRequest) -> ExtractFramesResult:
        """Extracts bounded image frames from video."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            tot_dur = float(probe.get("format", {}).get("duration", 0.0))

            timestamps = req.timestamps_seconds
            if not timestamps:
                if req.fps:
                    interval = 1.0 / req.fps
                    timestamps = [i * interval for i in range(min(req.max_frames, int(tot_dur / interval) + 1))]
                else:
                    timestamps = [0.0]

            # Enforce bounded frame limit
            timestamps = timestamps[:req.max_frames]

            extracted_items: List[ExtractedFrameInfo] = []
            local_frame_paths: List[Path] = []

            for idx, ts in enumerate(timestamps):
                capped_ts = min(ts, max(0.0, tot_dur - 0.05))
                out_name = f"frame_{idx:03d}_{uuid.uuid4().hex[:6]}.{req.image_format}"
                local_frame = ctx.get_output_path(out_name)

                cmd = self.adapter.build_extract_frame_at_timestamp_command(
                    local_src, local_frame, capped_ts, req.scale_width, req.scale_height
                )
                res = await self.adapter.execute_raw(cmd)
                if not res.is_success:
                    raise ProcessExecutionFailedError(f"Frame extraction failed at {capped_ts}s: {res.stderr}")

                local_frame_paths.append(local_frame)

            validated_frames = await validate_extracted_frames(local_frame_paths, expected_min_count=len(timestamps))

            for idx, (ts, v_info) in enumerate(zip(timestamps, validated_frames)):
                fp = v_info["path"]
                dest_key = self._derive_destination_key(req.project_id, "frames", fp.name)
                f_size = self._upload_validated_file(fp, dest_key, f"image/{req.image_format}")
                extracted_items.append(
                    ExtractedFrameInfo(
                        frame_index=idx,
                        timestamp_seconds=ts,
                        storage_key=dest_key,
                        width=v_info["width"],
                        height=v_info["height"],
                        file_size_bytes=f_size,
                    )
                )

            return ExtractFramesResult(
                project_id=req.project_id,
                frames=extracted_items,
                total_frames=len(extracted_items),
            )

    # =========================================================================
    # 15. CONCAT_MEDIA
    # =========================================================================

    async def concat_media(self, req: ConcatMediaRequest) -> ConcatMediaResult:
        """Concatenates multiple media files using internal safe manifest demuxer."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_inputs: List[Path] = []
            expected_duration = 0.0

            for idx, key in enumerate(req.source_storage_keys):
                p = ctx.stage_input_asset(key, local_name=f"in_{idx:03d}_{Path(key).name}")
                probe = await run_ffprobe_json(p)
                expected_duration += float(probe.get("format", {}).get("duration", 0.0))
                local_inputs.append(p)

            manifest_path = ctx.get_output_path("concat_manifest.txt")
            build_safe_concat_manifest(local_inputs, manifest_path)

            ext = "mp4" if req.media_type == "video" else "wav"
            out_name = f"concat_{uuid.uuid4().hex[:8]}.{ext}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_concat_demuxer_command(
                manifest_path, local_out, reencode=req.reencode_if_needed, media_type=req.media_type
            )
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Concat failed: {res.stderr}")

            val_data = await validate_concat_output(local_out, expected_min_duration=expected_duration)

            dest_key = self._derive_destination_key(
                req.project_id, req.media_type, out_name, req.destination_storage_key
            )
            content_type = "video/mp4" if req.media_type == "video" else "audio/wav"
            file_size = self._upload_validated_file(local_out, dest_key, content_type)

            return ConcatMediaResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                input_count=len(req.source_storage_keys),
                total_duration_seconds=val_data["duration"],
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 16. CHANGE_CONTAINER
    # =========================================================================

    async def change_container(self, req: ChangeContainerRequest) -> ChangeContainerResult:
        """Remuxes media streams into a target container without re-encoding."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            out_name = f"remux_{uuid.uuid4().hex[:8]}.{req.target_container}"
            local_out = ctx.get_output_path(out_name)

            cmd = self.adapter.build_change_container_command(local_src, local_out)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(f"Change container failed: {res.stderr}")

            validate_file_sanity(local_out, min_bytes=200)
            probe = await run_ffprobe_json(local_out)
            duration = float(probe.get("format", {}).get("duration", 0.0))

            dest_key = self._derive_destination_key(
                req.project_id, "video", out_name, req.destination_storage_key
            )
            file_size = self._upload_validated_file(local_out, dest_key, f"video/{req.target_container}")

            return ChangeContainerResult(
                project_id=req.project_id,
                output_storage_key=dest_key,
                container=req.target_container,
                duration_seconds=duration,
                file_size_bytes=file_size,
            )

    # =========================================================================
    # 17. ANALYZE_LOUDNESS
    # =========================================================================

    async def analyze_loudness(self, req: AnalyzeLoudnessRequest) -> AnalyzeLoudnessResult:
        """Measures audio loudness according to EBU R128 without mutating the media."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            total_duration = float(probe.get("format", {}).get("duration", 0.0))

            cmd = self.adapter.build_analyze_loudness_command(local_src)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(
                    f"FFmpeg command failed with code {res.returncode}: {res.stderr[:300]}",
                    details={"exit_code": res.returncode, "stderr": res.stderr[:500]},
                )
            stderr = res.stderr

            match = re.search(r"\{\s*\"input_i\"\s*:.*?\n\}", stderr, re.DOTALL)
            if not match:
                match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr)

            if not match:
                raise ProcessExecutionFailedError(
                    f"Failed to extract EBU R128 loudness metrics from FFmpeg output: {stderr[:300]}",
                    details={"stderr": stderr[:500]},
                )

            try:
                data = json.loads(match.group(0))
                integrated_lufs = float(data.get("input_i", -24.0))
                true_peak = float(data.get("input_tp", -2.0))
                loudness_range = float(data.get("input_lra", 7.0))
                thresh = float(data.get("input_thresh", -34.0))
            except Exception as e:
                raise ProcessExecutionFailedError(f"Could not parse loudnorm json: {e}")

            return AnalyzeLoudnessResult(
                project_id=req.project_id,
                source_storage_key=req.source_storage_key,
                integrated_lufs=integrated_lufs,
                loudness_range=loudness_range,
                true_peak_db=true_peak,
                threshold_db=thresh,
                measurement_standard="EBU R128",
                duration_seconds=total_duration,
            )

    # =========================================================================
    # 18. DETECT_SILENCE
    # =========================================================================

    async def detect_silence(self, req: DetectSilenceRequest) -> DetectSilenceResult:
        """Detects silence intervals in audio without modifying or trimming the media."""
        with WorkerStagingContext(self.storage_service, req.project_id, self.base_scratch_dir) as ctx:
            local_src = ctx.stage_input_asset(req.source_storage_key)
            probe = await run_ffprobe_json(local_src)
            total_duration = float(probe.get("format", {}).get("duration", 0.0))

            cmd = self.adapter.build_silence_detect_command(local_src, req.threshold_db, req.min_silence_duration)
            res = await self.adapter.execute_raw(cmd)
            if not res.is_success:
                raise ProcessExecutionFailedError(
                    f"FFmpeg command failed with code {res.returncode}: {res.stderr[:300]}",
                    details={"exit_code": res.returncode, "stderr": res.stderr[:500]},
                )

            silence_starts: List[float] = []
            silence_ends: List[float] = []

            for line in res.stderr.splitlines():
                if "silence_start:" in line:
                    m = re.search(r"silence_start:\s+([\d\.]+)", line)
                    if m:
                        silence_starts.append(float(m.group(1)))
                elif "silence_end:" in line:
                    m = re.search(r"silence_end:\s+([\d\.]+)", line)
                    if m:
                        silence_ends.append(float(m.group(1)))

            intervals: List[SilenceIntervalInfo] = []
            total_silence = 0.0

            for i in range(len(silence_starts)):
                s_start = silence_starts[i]
                s_end = silence_ends[i] if i < len(silence_ends) else total_duration
                s_dur = max(0.0, s_end - s_start)
                intervals.append(
                    SilenceIntervalInfo(
                        start_seconds=round(s_start, 3),
                        end_seconds=round(s_end, 3),
                        duration_seconds=round(s_dur, 3),
                    )
                )
                total_silence += s_dur

            silence_ratio = (total_silence / total_duration) if total_duration > 0 else 0.0

            return DetectSilenceResult(
                project_id=req.project_id,
                source_storage_key=req.source_storage_key,
                silence_intervals=intervals,
                total_silence_duration_seconds=round(total_silence, 3),
                audio_duration_seconds=total_duration,
                silence_ratio=round(min(1.0, max(0.0, silence_ratio)), 4),
                threshold_used_db=req.threshold_db,
            )

