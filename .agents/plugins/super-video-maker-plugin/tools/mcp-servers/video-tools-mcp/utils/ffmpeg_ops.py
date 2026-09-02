import os
import asyncio
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

def resolve_output_path(input_path: str, provided_output: str | None, suffix: str) -> str:
    input_p = Path(input_path)
    if provided_output:
        out_p = Path(provided_output)
        if not out_p.suffix:
            out_p = out_p.with_suffix(input_p.suffix)
        return str(out_p.absolute())
    
    return str((input_p.parent / f"{input_p.stem}_{suffix}{input_p.suffix}").absolute())

async def get_video_duration(file_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")
    return float(stdout.decode().strip())

async def trim_video_file(file_path: str, target_duration: float, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "trimmed")
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-t", str(target_duration),
        "-c", "copy",
        out_path
    ]
    logger.info(f"Running: {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    return out_path

async def resize_video_file(file_path: str, target_width: int, target_height: int, maintain_aspect_ratio: bool = True, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "resized")
    
    if maintain_aspect_ratio:
        vf_expr = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
    else:
        vf_expr = f"scale={target_width}:{target_height}"
        
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-vf", vf_expr,
        "-c:v", "libx264",
        "-c:a", "copy",
        out_path
    ]
    logger.info(f"Running: {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    return out_path

async def has_audio_stream(file_path: str) -> bool:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return len(stdout.decode().strip()) > 0

async def extend_video_file(file_path: str, target_duration: float, method: str = "loop", short_duration_threshold: float = 2.0, output_path: str | None = None) -> tuple[str, str]:
    """
    Returns (output_path, warning_message)
    """
    out_path = resolve_output_path(file_path, output_path, "extended")
    warning_msg = ""
    
    current_duration = await get_video_duration(file_path)
    if current_duration >= target_duration:
        logger.info("Video is already longer than target_duration. Copying as is.")
        # Just copy
        cmd = ["ffmpeg", "-y", "-i", file_path, "-c", "copy", out_path]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        return out_path, warning_msg

    if method == "loop":
        if current_duration < short_duration_threshold:
            warning_msg = f"Warning: The original video is very short ({current_duration:.2f}s). Looping it may look like an unnatural 'one-shot' repetition."
            
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", file_path,
            "-t", str(target_duration),
            "-c", "copy",
            out_path
        ]
    elif method == "freeze_last_frame":
        extra_duration = target_duration - current_duration
        has_audio = await has_audio_stream(file_path)
        
        if has_audio:
            cmd = [
                "ffmpeg", "-y",
                "-i", file_path,
                "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={extra_duration}[v];[0:a]apad[a]",
                "-map", "[v]",
                "-map", "[a]",
                "-t", str(target_duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                out_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", file_path,
                "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={extra_duration}[v]",
                "-map", "[v]",
                "-t", str(target_duration),
                "-c:v", "libx264",
                out_path
            ]
    else:
        raise ValueError(f"Unknown extend method: {method}")

    logger.info(f"Running: {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
        
    return out_path, warning_msg

async def detect_and_trim_black_frames_file(file_path: str, threshold: float = 0.1, min_duration: float = 0.1, trim_start: bool = True, trim_end: bool = True, output_path: str | None = None) -> dict:
    """
    Returns a dict with trimming info and the output path.
    """
    # 1. Detect black frames
    cmd_detect = [
        "ffmpeg",
        "-i", file_path,
        "-vf", f"blackdetect=d={min_duration}:pic_th={threshold}",
        "-f", "null", "-"
    ]
    logger.info(f"Running blackdetect: {' '.join(cmd_detect)}")
    process = await asyncio.create_subprocess_exec(
        *cmd_detect,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    output = stderr.decode()
    
    total_duration = await get_video_duration(file_path)
    
    black_intervals = []
    for line in output.splitlines():
        if "blackdetect" in line and "black_start:" in line:
            parts = line.split()
            try:
                start = float([p for p in parts if p.startswith("black_start:")][0].split(":")[1])
                end = float([p for p in parts if p.startswith("black_end:")][0].split(":")[1])
                black_intervals.append((start, end))
            except Exception as e:
                logger.warning(f"Failed to parse line: {line} - {e}")
                
    if not black_intervals:
        return {
            "trimmed": False,
            "message": "No black frames detected.",
            "output_path": file_path,
            "original_duration": total_duration,
            "new_duration": total_duration
        }
        
    start_time = 0.0
    end_time = total_duration
    
    if trim_start:
        # If there's a black interval at the very beginning (starting near 0)
        for bs, be in black_intervals:
            if bs < 0.1: # starts very close to 0
                start_time = max(start_time, be)
                break
                
    if trim_end:
        # If there's a black interval at the very end
        for bs, be in reversed(black_intervals):
            if be > total_duration - 0.5: # ends very close to the end
                end_time = min(end_time, bs)
                break
                
    if start_time == 0.0 and end_time == total_duration:
        return {
            "trimmed": False,
            "message": "Black frames detected, but not at the very start or end (or trimming disabled).",
            "output_path": file_path,
            "original_duration": total_duration,
            "new_duration": total_duration
        }
        
    if start_time >= end_time:
        raise ValueError("Video is entirely black frames.")
        
    # 2. Trim the video
    out_path = resolve_output_path(file_path, output_path, "noblack")
    cmd_trim = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", file_path,
        "-c", "copy",
        out_path
    ]
    logger.info(f"Running trim: {' '.join(cmd_trim)}")
    process_trim = await asyncio.create_subprocess_exec(
        *cmd_trim,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr_trim = await process_trim.communicate()
    if process_trim.returncode != 0:
        raise RuntimeError(f"ffmpeg failed during trim: {stderr_trim.decode()}")
        
    return {
        "trimmed": True,
        "message": f"Trimmed from {start_time:.2f}s to {end_time:.2f}s.",
        "output_path": out_path,
        "original_duration": total_duration,
        "new_duration": end_time - start_time,
        "black_intervals_detected": black_intervals
    }
