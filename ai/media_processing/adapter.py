"""
ai/media_processing/adapter.py
==============================
Canonical FFmpeg execution adapter (S28-M06).

Invariants:
- FFmpeg is an execution engine, NOT domain or architecture authority.
- ALL command construction is strictly argument vectors (argv: list[str]).
- shell=True is NEVER used.
- Callers and AI cannot pass arbitrary flag strings or command lines.
- Safe protocol allowlist (-protocol_whitelist "file,crypto,data") enforced on every command.
- Resource controls: bounded timeout, bounded stdout/stderr buffers, process-group termination on cancellation.
- ZERO orphan processes left running after timeouts or cancellation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ai.media_processing.contracts import (
    ChangeContainerRequest,
    ChangeVideoSpeedRequest,
    ConcatMediaRequest,
    DetectBlackFramesRequest,
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
from ai.media_processing.errors import (
    FFmpegUnavailableError,
    ProcessCancelledError,
    ProcessExecutionFailedError,
    ProcessTimeoutError,
    ProtocolSecurityViolationError,
)
from ai.media_processing.security import (
    assert_safe_protocol,
    assert_no_shell_injection,
)

logger = logging.getLogger("ai.media_processing.adapter")

# Max stdout/stderr capture buffer to prevent memory exhaustion (1MB)
MAX_LOG_CAPTURE_BYTES = 1024 * 1024


class FFmpegProcessResult:
    """Structured result of a subprocess execution."""
    def __init__(
        self,
        command: List[str],
        returncode: int,
        stdout: str,
        stderr: str,
        duration_ms: float,
    ):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms

    @property
    def is_success(self) -> bool:
        return self.returncode == 0


class FFmpegAdapter:
    """
    Authoritative adapter governing safe subprocess invocations of ffmpeg and ffprobe.
    """

    def __init__(
        self,
        ffmpeg_bin: str = "ffmpeg",
        ffprobe_bin: str = "ffprobe",
        max_concurrency: int = 4,
        default_timeout_seconds: float = 120.0,
    ):
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.default_timeout_seconds = default_timeout_seconds

    async def execute_ffmpeg(
        self,
        cmd: List[str],
        timeout_seconds: Optional[float] = None,
        cwd: Optional[Path] = None,
    ) -> FFmpegProcessResult:
        """Alias for execute_raw."""
        return await self.execute_raw(cmd, timeout_seconds=timeout_seconds, cwd=cwd)

    async def execute_ffmpeg_checked(
        self,
        cmd: List[str],
        timeout_seconds: Optional[float] = None,
        cwd: Optional[Path] = None,
    ) -> FFmpegProcessResult:
        """Executes FFmpeg and raises ProcessExecutionFailedError if returncode != 0."""
        res = await self.execute_raw(cmd, timeout_seconds=timeout_seconds, cwd=cwd)
        if res.returncode != 0:
            raise ProcessExecutionFailedError(
                f"FFmpeg process execution failed with exit code {res.returncode}: {res.stderr[:200]}",
                details={"exit_code": res.returncode, "stderr": res.stderr[:500]},
            )
        return res

    def build_trim_command(self, *args, **kwargs) -> List[str]:
        """Alias for build_trim_video_command."""
        return self.build_trim_video_command(*args, **kwargs)
    def get_health(self) -> Dict[str, Any]:
        """Probes presence of ffmpeg and ffprobe executables."""
        import shutil
        ff_path = shutil.which(self.ffmpeg_bin)
        pr_path = shutil.which(self.ffprobe_bin)
        return {
            "healthy": bool(ff_path and pr_path),
            "ffmpeg_path": ff_path,
            "ffprobe_path": pr_path,
        }

    # =========================================================================
    # Subprocess Execution & Process-Group Management
    # =========================================================================

    async def execute_raw(
        self,
        cmd: List[str],
        timeout_seconds: Optional[float] = None,
        cwd: Optional[Path] = None,
    ) -> FFmpegProcessResult:
        """
        Executes an argument vector securely within a process group.
        Guarantees termination of child processes upon timeout or cancellation.
        """
        # Security sanity checks on command vector
        for arg in cmd:
            assert_safe_protocol(arg, "command_arg")
            assert_no_shell_injection(arg, "command_arg")

        timeout = timeout_seconds or self.default_timeout_seconds
        start_time = time.monotonic()

        async with self.semaphore:
            # On POSIX, start_new_session=True creates a new process group
            is_posix = os.name != "nt"
            kwargs: Dict[str, Any] = {
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
            }
            if cwd:
                kwargs["cwd"] = str(cwd)
            if is_posix:
                kwargs["start_new_session"] = True

            try:
                proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
            except FileNotFoundError as fnf:
                executable = cmd[0] if cmd else "ffmpeg"
                raise FFmpegUnavailableError(f"Executable '{executable}' not found: {fnf}")
            except Exception as ex:
                raise ProcessExecutionFailedError(f"Failed to spawn FFmpeg process: {ex}")

            stdout_bytes = b""
            stderr_bytes = b""

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                self._terminate_process_group(proc)
                duration_ms = (time.monotonic() - start_time) * 1000
                raise ProcessTimeoutError(
                    f"FFmpeg process exceeded timeout limit of {timeout:.1f}s.",
                    details={"command": " ".join(cmd[:4]) + "...", "timeout_seconds": timeout, "duration_ms": duration_ms},
                )
            except asyncio.CancelledError:
                self._terminate_process_group(proc)
                duration_ms = (time.monotonic() - start_time) * 1000
                raise ProcessCancelledError(
                    "FFmpeg process was cancelled.",
                    details={"command": " ".join(cmd[:4]) + "...", "duration_ms": duration_ms},
                )

            duration_ms = (time.monotonic() - start_time) * 1000

            # Bounded log truncation
            stdout_str = stdout_bytes[:MAX_LOG_CAPTURE_BYTES].decode("utf-8", errors="replace")
            stderr_str = stderr_bytes[:MAX_LOG_CAPTURE_BYTES].decode("utf-8", errors="replace")

            return FFmpegProcessResult(
                command=cmd,
                returncode=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
            )

    def _terminate_process_group(self, proc: asyncio.subprocess.Process) -> None:
        """Kills process group to prevent orphan background processes."""
        if proc.returncode is not None:
            return

        pid = proc.pid
        try:
            if os.name != "nt":
                # Send SIGKILL to the entire process group
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError, OSError) as e:
            logger.debug("Process termination handled: %s", e)

    # =========================================================================
    # Typed Command Builders
    # =========================================================================

    def _base_ffmpeg_flags(self) -> List[str]:
        return [
            self.ffmpeg_bin,
            "-y",
            "-nostdin",
            "-hide_banner",
            "-protocol_whitelist", "file,crypto,data",
        ]

    def build_transcode_command(
        self,
        input_path: Path,
        output_path: Path,
        req: TranscodeVideoRequest,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path)])

        # Video codec
        cmd.extend(["-c:v", req.video_codec])
        if req.video_codec != "copy":
            if req.crf is not None:
                cmd.extend(["-crf", str(req.crf)])
            if req.preset:
                cmd.extend(["-preset", req.preset])
            if req.fps:
                cmd.extend(["-r", str(req.fps)])

        # Resolution scaling
        vf_filters: List[str] = []
        if req.target_width and req.target_height:
            vf_filters.append(f"scale={req.target_width}:{req.target_height}")
        elif req.target_width:
            vf_filters.append(f"scale={req.target_width}:-2")
        elif req.target_height:
            vf_filters.append(f"scale=-2:{req.target_height}")

        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])

        # Audio codec
        if req.audio_codec:
            cmd.extend(["-c:a", req.audio_codec])
        else:
            cmd.extend(["-an"])

        cmd.append(str(output_path))
        return cmd

    def build_trim_video_command(
        self,
        input_path: Path,
        output_path: Path,
        req: TrimVideoRequest,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        # Fast input seeking or accurate output seeking
        cmd.extend(["-ss", str(req.start_time_seconds)])
        cmd.extend(["-i", str(input_path)])

        duration = req.duration_seconds
        if duration is None and req.end_time_seconds is not None:
            duration = req.end_time_seconds - req.start_time_seconds

        if duration is not None:
            cmd.extend(["-t", str(duration)])

        if req.accurate_seek:
            cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
        else:
            cmd.extend(["-c", "copy"])

        cmd.append(str(output_path))
        return cmd

    def build_resize_video_command(
        self,
        input_path: Path,
        output_path: Path,
        req: ResizeVideoRequest,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path)])

        w = req.target_width
        h = req.target_height

        if req.maintain_aspect_ratio:
            vf_expr = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
        else:
            vf_expr = f"scale={w}:{h}"

        cmd.extend(["-vf", vf_expr, "-c:v", "libx264", "-c:a", "copy", str(output_path)])
        return cmd

    def build_extend_video_loop_command(
        self,
        input_path: Path,
        output_path: Path,
        target_duration: float,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-stream_loop", "-1",
            "-i", str(input_path),
            "-t", str(target_duration),
            "-c", "copy",
            str(output_path),
        ])
        return cmd

    def build_extend_video_freeze_command(
        self,
        input_path: Path,
        output_path: Path,
        extra_duration: float,
        target_duration: float,
        has_audio: bool,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path)])

        if has_audio:
            filter_expr = f"[0:v]tpad=stop_mode=clone:stop_duration={extra_duration}[v];[0:a]apad[a]"
            cmd.extend([
                "-filter_complex", filter_expr,
                "-map", "[v]",
                "-map", "[a]",
                "-t", str(target_duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                str(output_path),
            ])
        else:
            filter_expr = f"[0:v]tpad=stop_mode=clone:stop_duration={extra_duration}[v]"
            cmd.extend([
                "-filter_complex", filter_expr,
                "-map", "[v]",
                "-t", str(target_duration),
                "-c:v", "libx264",
                str(output_path),
            ])
        return cmd

    def build_black_detect_command(
        self,
        input_path: Path,
        min_duration: float,
        threshold: float,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-i", str(input_path),
            "-vf", f"blackdetect=d={min_duration}:pic_th={threshold}",
            "-f", "null", "-",
        ])
        return cmd

    def build_speed_video_command(
        self,
        input_path: Path,
        output_path: Path,
        speed_factor: float,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        pts_val = (1.0 / speed_factor)
        cmd.extend([
            "-i", str(input_path),
            "-filter:v", f"setpts={pts_val:.4f}*PTS",
            "-r", "30",
            "-an",
            "-c:v", "libx264",
            str(output_path),
        ])
        return cmd

    def build_enforce_keyframes_command(
        self,
        input_path: Path,
        output_path: Path,
        gop_value: int,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-i", str(input_path),
            "-c:v", "libx264",
            "-g", str(gop_value),
            "-c:a", "copy",
            str(output_path),
        ])
        return cmd

    def build_extract_audio_command(
        self,
        input_path: Path,
        output_path: Path,
        req: ExtractAudioRequest,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path), "-vn"])

        if req.audio_format == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif req.audio_format == "mp3":
            cmd.extend(["-c:a", "libmp3lame"])
        elif req.audio_format in ("aac", "m4a"):
            cmd.extend(["-c:a", "aac"])

        cmd.extend(["-ar", str(req.sample_rate), "-ac", str(req.channels), str(output_path)])
        return cmd

    def build_trim_audio_command(
        self,
        input_path: Path,
        output_path: Path,
        target_duration: float,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path), "-t", str(target_duration), str(output_path)])
        return cmd

    def build_normalize_loudness_command(
        self,
        input_path: Path,
        output_path: Path,
        target_lufs: float,
        true_peak: float = -1.5,
        loudness_range: float = 11.0,
        sample_rate: int = 44100,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={loudness_range}",
            "-ar", str(sample_rate),
            str(output_path),
        ])
        return cmd

    def build_analyze_loudness_command(
        self,
        input_path: Path,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-i", str(input_path),
            "-af", "loudnorm=print_format=json",
            "-f", "null", "-",
        ])
        return cmd

    def build_silence_detect_command(
        self,
        input_path: Path,
        threshold_db: float = -40.0,
        min_duration: float = 0.1,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend([
            "-i", str(input_path),
            "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration}",
            "-f", "null", "-",
        ])
        return cmd

    def build_extract_frame_at_timestamp_command(
        self,
        input_path: Path,
        output_frame_path: Path,
        timestamp_seconds: float,
        scale_width: Optional[int] = None,
        scale_height: Optional[int] = None,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-ss", f"{timestamp_seconds:.3f}", "-i", str(input_path), "-vframes", "1"])
        if scale_width and scale_height:
            cmd.extend(["-vf", f"scale={scale_width}:{scale_height}"])
        cmd.append(str(output_frame_path))
        return cmd

    def build_concat_demuxer_command(
        self,
        manifest_path: Path,
        output_path: Path,
        reencode: bool = False,
        media_type: str = "video",
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-f", "concat", "-safe", "0", "-i", str(manifest_path)])
        if reencode:
            if media_type == "video":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
            else:
                cmd.extend(["-c:a", "pcm_s16le"])
        else:
            cmd.extend(["-c", "copy"])
        cmd.append(str(output_path))
        return cmd

    def build_change_container_command(
        self,
        input_path: Path,
        output_path: Path,
    ) -> List[str]:
        cmd = self._base_ffmpeg_flags()
        cmd.extend(["-i", str(input_path), "-c", "copy", str(output_path)])
        return cmd
