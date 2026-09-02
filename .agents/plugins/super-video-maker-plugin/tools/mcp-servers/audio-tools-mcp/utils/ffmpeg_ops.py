import asyncio
import os
import re
import math
import uuid
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

async def run_ffmpeg(cmd: list[str]) -> tuple[str, str]:
    """Runs an ffmpeg command asynchronously and returns (stdout, stderr)."""
    # ffmpeg usually logs to stderr
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_msg = stderr.decode('utf-8', errors='replace')
        logger.error(f"ffmpeg command failed: {' '.join(cmd)}\nError: {error_msg}")
        raise RuntimeError(f"ffmpeg error: {error_msg}")
        
    return stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')

async def get_audio_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffprobe error: {stderr.decode('utf-8', errors='replace')}")
    try:
        return float(stdout.decode('utf-8', errors='replace').strip())
    except ValueError:
        raise RuntimeError(f"Could not parse duration from ffprobe: {stdout}")

def resolve_output_path(input_path: str, provided_output: str | None, suffix: str) -> str:
    input_p = Path(input_path)
    if provided_output:
        out_p = Path(provided_output)
        if not out_p.suffix:
            # If provided_output lacks extension, inherit original extension
            out_p = out_p.with_suffix(input_p.suffix)
        return str(out_p.absolute())
    
    # Default suffix logic
    return str((input_p.parent / f"{input_p.stem}_{suffix}{input_p.suffix}").absolute())

async def trim_audio_file(file_path: str, target_duration: float, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "trimmed")
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-t", str(target_duration),
        out_path
    ]
    await run_ffmpeg(cmd)
    return out_path

async def detect_and_trim_silence_file(
    file_path: str, 
    threshold_db: float = -40.0, 
    min_silence_duration: float = 0.1, 
    trim_start: bool = True, 
    trim_end: bool = True, 
    output_path: str | None = None
) -> dict:
    
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_silence_duration}",
        "-f", "null", "-"
    ]
    
    # ffmpeg with -f null writes progress and silencedetect info to stderr
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    
    # We ignore return code here if it's 0, but sometimes ffmpeg exits non-zero if stream fails, so check it.
    if process.returncode != 0 and "silencedetect" not in stderr.decode('utf-8', errors='replace'):
        raise RuntimeError(f"silencedetect failed: {stderr.decode('utf-8', errors='replace')}")
        
    stderr_str = stderr.decode('utf-8', errors='replace')
    
    silence_starts = []
    silence_ends = []
    
    for line in stderr_str.splitlines():
        if "silence_start" in line:
            match = re.search(r"silence_start:\s+([\d\.]+)", line)
            if match:
                silence_starts.append(float(match.group(1)))
        elif "silence_end" in line:
            match = re.search(r"silence_end:\s+([\d\.]+)", line)
            if match:
                silence_ends.append(float(match.group(1)))
                
    total_duration = await get_audio_duration(file_path)
    
    start_trim_point = 0.0
    end_trim_point = total_duration
    
    trimmed_start_sec = 0.0
    trimmed_end_sec = 0.0
    
    # Start silence: if a silence block starts at ~0.0
    if trim_start and silence_starts and silence_starts[0] <= 0.1:
        if len(silence_ends) > 0:
            start_trim_point = silence_ends[0]
            trimmed_start_sec = start_trim_point
            
    # End silence: if a silence block ends at ~total_duration
    if trim_end and silence_ends:
        last_silence_end = silence_ends[-1]
        # Allow up to 0.5s margin of error for duration mismatches
        if last_silence_end >= total_duration - 0.5:
            if len(silence_starts) >= len(silence_ends):
                end_trim_point = silence_starts[-1]
                trimmed_end_sec = total_duration - end_trim_point

    # Safety check in case it detects the entire file as silence
    if end_trim_point <= start_trim_point:
        logger.warning(f"File {file_path} seems completely silent. No trim applied.")
        start_trim_point = 0.0
        end_trim_point = total_duration
        trimmed_start_sec = 0.0
        trimmed_end_sec = 0.0

    if start_trim_point == 0.0 and end_trim_point == total_duration:
        # Nothing to trim
        return {
            "output_path": str(Path(file_path).absolute()),
            "trimmed_start_seconds": 0.0,
            "trimmed_end_seconds": 0.0
        }
        
    out_path = resolve_output_path(file_path, output_path, "not_silent")
    
    trim_cmd = ["ffmpeg", "-y", "-i", file_path]
    if start_trim_point > 0:
        trim_cmd.extend(["-ss", str(start_trim_point)])
    if end_trim_point < total_duration:
        trim_cmd.extend(["-to", str(end_trim_point)])
    trim_cmd.append(out_path)
    
    await run_ffmpeg(trim_cmd)
    
    return {
        "output_path": out_path,
        "trimmed_start_seconds": trimmed_start_sec,
        "trimmed_end_seconds": trimmed_end_sec
    }

async def normalize_loudness_file(file_path: str, target_lufs: float, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "norm")
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        "-ar", "44100",
        out_path
    ]
    await run_ffmpeg(cmd)
    return out_path

async def analyze_audio_type(file_path: str, short_duration_threshold: float = 2.0) -> bool:
    """
    Detects whether an audio file is a "one-shot" sound effect (returns True) or a "loopable" track (returns False).
    A one-shot is defined as:
    1. The active audio duration (without leading/trailing silence) is less than `short_duration_threshold`.
    2. OR there is a significant trailing silence block before the end of the file indicating an abrupt end.
    """
    total_duration = await get_audio_duration(file_path)
    
    # We use a relatively strict threshold to find obvious silence (-35dB for 0.2s minimum)
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", f"silencedetect=noise=-35dB:d=0.2",
        "-f", "null", "-"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    
    stderr_str = stderr.decode('utf-8', errors='replace')
    silence_starts = []
    silence_ends = []
    
    for line in stderr_str.splitlines():
        if "silence_start" in line:
            match = re.search(r"silence_start:\s+([\d\.]+)", line)
            if match: silence_starts.append(float(match.group(1)))
        elif "silence_end" in line:
            match = re.search(r"silence_end:\s+([\d\.]+)", line)
            if match: silence_ends.append(float(match.group(1)))
            
    # Calculate active duration by excluding leading and trailing silence
    start_trim_point = 0.0
    end_trim_point = total_duration
    
    if silence_starts and silence_starts[0] <= 0.1 and len(silence_ends) > 0:
        start_trim_point = silence_ends[0]
        
    if silence_ends and silence_ends[-1] >= total_duration - 0.5 and len(silence_starts) >= len(silence_ends):
        end_trim_point = silence_starts[-1]
        
    active_duration = end_trim_point - start_trim_point
    if active_duration <= 0: 
        return True # Completely silent -> treat as one-shot so we don't loop silence
        
    # Rule 1: Active duration is shorter than the threshold
    if active_duration < short_duration_threshold:
        logger.info(f"Audio '{file_path}' classified as ONE-SHOT (Rule 1: active duration {active_duration:.2f}s < {short_duration_threshold}s)")
        return True
        
    # Rule 2: Long trailing silence. If there is a silence block that starts before the end but continues until the end,
    # and it is significant (e.g., > 10% of the active duration or simply a long trailing silence), it's a one-shot.
    if end_trim_point < total_duration:
        trailing_silence_duration = total_duration - end_trim_point
        # Significant if it's more than 20% of the active sound, with a minimum of 0.5s
        if trailing_silence_duration > max(0.5, active_duration * 0.2):
            logger.info(f"Audio '{file_path}' classified as ONE-SHOT (Rule 2: trailing silence of {trailing_silence_duration:.2f}s detected, which is significant relative to active duration {active_duration:.2f}s)")
            return True

    logger.info(f"Audio '{file_path}' classified as LOOPABLE.")
    return False

async def extend_audio_file(
    file_path: str, 
    target_duration: float, 
    method: str = "loop", 
    output_path: str | None = None, 
    auto_trim_silence_before_loop: bool = True,
    short_duration_threshold: float = 2.0
) -> str:
    out_path = resolve_output_path(file_path, output_path, "extended")
    
    is_one_shot = await analyze_audio_type(file_path, short_duration_threshold)
    
    if is_one_shot:
        # For one-shots, we just trim silence (if requested/possible) and return it, ignoring target_duration entirely.
        logger.info(f"'{file_path}' is a one-shot. Ignoring target_duration and returning cropped version.")
        trim_res = await detect_and_trim_silence_file(
            file_path, 
            threshold_db=-40.0, 
            min_silence_duration=0.1, 
            output_path=out_path
        )
        return trim_res["output_path"]
    
    working_file = file_path
    temp_file = None
    
    try:
        if auto_trim_silence_before_loop:
            # We want to use a temporary file for the trimmed version to not pollute the folder
            # If the user requested auto-trim, we run silencedetect and use that output
            temp_file = str(Path(file_path).parent / f"temp_{uuid.uuid4().hex}{Path(file_path).suffix}")
            trim_res = await detect_and_trim_silence_file(
                file_path, 
                threshold_db=-40.0, 
                min_silence_duration=0.1, 
                output_path=temp_file
            )
            working_file = trim_res["output_path"]

        orig_duration = await get_audio_duration(working_file)
        
        if orig_duration >= target_duration:
            # Already long enough, just trim to exact target
            cmd = ["ffmpeg", "-y", "-i", working_file, "-t", str(target_duration), out_path]
            await run_ffmpeg(cmd)
            return out_path
            
        if method == "loop":
            # Simple loop
            cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", working_file, "-t", str(target_duration), out_path]
            await run_ffmpeg(cmd)
            
        elif method == "fade_extend":
            crossfade_duration = 0.5
            # We need to loop the audio, but apply a crossfade between iterations
            # Number of copies needed:
            # each copy after the first contributes (orig_duration - crossfade_duration) to total length
            # Target: orig_duration + (loops-1)*(orig_duration - crossfade_duration) >= target_duration
            effective_duration = orig_duration - crossfade_duration
            if effective_duration <= 0:
                # File too short to crossfade safely, just simple loop
                cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", working_file, "-t", str(target_duration), out_path]
                await run_ffmpeg(cmd)
                return out_path
                
            loops = math.ceil((target_duration - orig_duration) / effective_duration) + 1
            
            cmd = ["ffmpeg", "-y"]
            for _ in range(loops):
                cmd.extend(["-i", working_file])
                
            filter_complex = ""
            if loops == 2:
                filter_complex = f"[0:a][1:a]acrossfade=d={crossfade_duration}[aout]"
            else:
                filter_complex = f"[0:a][1:a]acrossfade=d={crossfade_duration}[a1];"
                for i in range(2, loops):
                    in_pad = f"[a{i-1}]"
                    out_pad = f"[a{i}]" if i < loops - 1 else "[aout]"
                    filter_complex += f"{in_pad}[{i}:a]acrossfade=d={crossfade_duration}{out_pad}"
                    if i < loops - 1:
                        filter_complex += ";"
                        
            cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]", "-t", str(target_duration), out_path])
            await run_ffmpeg(cmd)
            
        else:
            raise ValueError(f"Unknown extend method: {method}")
            
        return out_path
        
    finally:
        # Cleanup temporary trimmed file if we created one and it's not the original file
        if temp_file and os.path.exists(temp_file) and working_file == temp_file:
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
