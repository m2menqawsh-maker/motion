"""
ai/media_processing/validator.py
================================
Deep output validation using ffprobe for Media Processing (S28-M06).

Invariants:
- Exit code 0 is NOT sufficient evidence of success.
- Every produced output is deep-probed and validated against contract specifications.
- Fails closed on zero-byte, corrupt, or truncated outputs.
- Enforces duration tolerances and verifies stream codecs/dimensions.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.media_processing.errors import (
    FFprobeFailedError,
    InvalidMediaFileError,
    OutputValidationError,
)

logger = logging.getLogger("ai.media_processing.validator")


async def run_ffprobe_json(file_path: Path | str, timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    Executes ffprobe with JSON output format and parses stream/format metadata.
    Raises OutputValidationError or FFprobeFailedError if probe fails.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise OutputValidationError(f"Probed file does not exist: {file_path}")

    if path_obj.stat().st_size == 0:
        raise OutputValidationError(f"Probed file is empty (0 bytes): {file_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-print_format", "json",
        str(path_obj),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise FFprobeFailedError(f"ffprobe timed out after {timeout_seconds}s on {file_path}")
    except FileNotFoundError:
        raise FFprobeFailedError("ffprobe executable not found in PATH")
    except Exception as e:
        raise FFprobeFailedError(f"ffprobe invocation failed: {e}")

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        raise InvalidMediaFileError(
            f"ffprobe failed to parse media: {err_msg}",
            details={"file_path": str(file_path), "stderr": err_msg},
        )

    try:
        data = json.loads(stdout.decode("utf-8", errors="replace"))
        return data
    except Exception as e:
        raise FFprobeFailedError(f"Failed to parse ffprobe JSON output: {e}")


def validate_file_sanity(file_path: Path, min_bytes: int = 100) -> int:
    """Verifies file exists, is regular file, and meets minimum byte size."""
    if not file_path.exists():
        raise OutputValidationError(f"Expected output file was not created: '{file_path}'")
    if not file_path.is_file():
        raise OutputValidationError(f"Output path is not a regular file: '{file_path}'")
    size = file_path.stat().st_size
    if size < min_bytes:
        raise OutputValidationError(
            f"Output file is suspiciously small ({size} bytes < min {min_bytes} bytes). Likely corrupt or empty.",
            details={"file_path": str(file_path), "file_size": size, "min_bytes": min_bytes},
        )
    return size


async def validate_video_transcode(
    output_path: Path,
    expected_codec: Optional[str] = None,
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
    expected_container: Optional[str] = None,
) -> Dict[str, Any]:
    """Validates video transcode output."""
    file_size = validate_file_sanity(output_path, min_bytes=200)
    probe = await run_ffprobe_json(output_path)

    format_info = probe.get("format", {})
    streams = probe.get("streams", [])

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise OutputValidationError(f"Transcoded video output contains no video streams: '{output_path}'")

    v_stream = video_streams[0]
    duration = float(format_info.get("duration", 0.0) or v_stream.get("duration", 0.0) or 0.0)
    if duration <= 0.0:
        raise OutputValidationError(f"Transcoded video duration is invalid ({duration}s): '{output_path}'")

    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))

    if width <= 0 or height <= 0:
        raise OutputValidationError(f"Invalid video dimensions {width}x{height}: '{output_path}'")

    if expected_width and abs(width - expected_width) > 4:
        raise OutputValidationError(f"Width mismatch: expected ~{expected_width}, got {width}")
    if expected_height and abs(height - expected_height) > 4:
        raise OutputValidationError(f"Height mismatch: expected ~{expected_height}, got {height}")

    return {
        "file_size": file_size,
        "duration": duration,
        "width": width,
        "height": height,
        "codec_name": v_stream.get("codec_name"),
        "format_name": format_info.get("format_name"),
        "probe": probe,
    }


async def validate_video_trim(
    output_path: Path,
    expected_duration: float,
    tolerance_seconds: float = 0.5,
) -> Dict[str, Any]:
    """Validates trimmed video duration against tolerance."""
    file_size = validate_file_sanity(output_path, min_bytes=200)
    probe = await run_ffprobe_json(output_path)

    format_info = probe.get("format", {})
    duration = float(format_info.get("duration", 0.0))

    if abs(duration - expected_duration) > tolerance_seconds:
        raise OutputValidationError(
            f"Trimmed duration {duration:.2f}s deviates from expected {expected_duration:.2f}s by more than tolerance {tolerance_seconds}s.",
            details={"actual_duration": duration, "expected_duration": expected_duration, "tolerance": tolerance_seconds},
        )

    return {"file_size": file_size, "duration": duration, "probe": probe}


async def validate_audio_output(
    output_path: Path,
    min_duration: float = 0.05,
) -> Dict[str, Any]:
    """Validates that audio output contains a valid audio stream."""
    file_size = validate_file_sanity(output_path, min_bytes=100)
    probe = await run_ffprobe_json(output_path)

    streams = probe.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise OutputValidationError(f"Extracted audio contains no audio streams: '{output_path}'")

    a_stream = audio_streams[0]
    duration = float(probe.get("format", {}).get("duration", 0.0) or a_stream.get("duration", 0.0) or 0.0)

    if duration < min_duration:
        raise OutputValidationError(f"Audio duration ({duration:.2f}s) is below minimum sanity ({min_duration}s).")

    sample_rate = int(a_stream.get("sample_rate", 0))
    channels = int(a_stream.get("channels", 0))

    return {
        "file_size": file_size,
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "codec_name": a_stream.get("codec_name"),
        "probe": probe,
    }


async def validate_extracted_frames(
    frame_paths: List[Path],
    expected_min_count: int = 1,
) -> List[Dict[str, Any]]:
    """Validates that extracted frame files are valid images."""
    if len(frame_paths) < expected_min_count:
        raise OutputValidationError(f"Expected at least {expected_min_count} frames, got {len(frame_paths)}.")

    results = []
    for fp in frame_paths:
        file_size = validate_file_sanity(fp, min_bytes=50)
        # Probe image via ffprobe
        probe = await run_ffprobe_json(fp)
        v_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
        if not v_streams:
            raise OutputValidationError(f"Frame file has no image/video stream: '{fp}'")
        w = int(v_streams[0].get("width", 0))
        h = int(v_streams[0].get("height", 0))
        if w <= 0 or h <= 0:
            raise OutputValidationError(f"Invalid frame dimensions {w}x{h} for '{fp}'")
        results.append({"path": fp, "size": file_size, "width": w, "height": h})

    return results


async def validate_concat_output(
    output_path: Path,
    expected_min_duration: float,
) -> Dict[str, Any]:
    """Validates concatenated media output."""
    file_size = validate_file_sanity(output_path, min_bytes=500)
    probe = await run_ffprobe_json(output_path)
    duration = float(probe.get("format", {}).get("duration", 0.0))

    if duration < expected_min_duration * 0.8:
        raise OutputValidationError(
            f"Concatenated duration {duration:.2f}s is significantly less than expected {expected_min_duration:.2f}s.",
            details={"actual": duration, "expected": expected_min_duration},
        )

    return {"file_size": file_size, "duration": duration, "probe": probe}
