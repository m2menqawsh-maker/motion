from mcp.server.fastmcp import FastMCP
import sys
import io
import logging

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.ffmpeg_ops import (
    trim_video_file,
    resize_video_file,
    extend_video_file,
    detect_and_trim_black_frames_file
)

# Initialize MCP server
mcp = FastMCP("video-tools-mcp")

@mcp.tool()
async def trim_video(file_path: str, target_duration: float, output_path: str | None = None) -> str:
    """
    Trims a video to the specified target_duration (in seconds) starting from the beginning.
    Returns the absolute path to the trimmed file.
    """
    return await trim_video_file(file_path, target_duration, output_path)

@mcp.tool()
async def extend_video(file_path: str, target_duration: float, method: str = "loop", short_duration_threshold: float = 2.0, output_path: str | None = None) -> str:
    """
    Extends a video to the target_duration (in seconds).
    method: "loop" (loops the video and audio) or "freeze_last_frame" (freezes the last frame of the video and pads audio with silence).
    short_duration_threshold: Used for "loop" method. If the original video is shorter than this, a warning is returned but the operation still proceeds.
    Returns a string containing the absolute path to the processed file, and any warnings.
    """
    out_path, warning_msg = await extend_video_file(file_path, target_duration, method, short_duration_threshold, output_path)
    if warning_msg:
        return f"{warning_msg}\nSuccess: Extended file saved to {out_path}"
    return f"Success: Extended file saved to {out_path}"

@mcp.tool()
async def resize_video(file_path: str, target_width: int, target_height: int, maintain_aspect_ratio: bool = True, output_path: str | None = None) -> str:
    """
    Resizes a video to target_width and target_height.
    If maintain_aspect_ratio is True, it will add black bars (letterboxing/pillarboxing) to exactly fit the dimensions.
    If maintain_aspect_ratio is False, it will force stretch the video.
    Returns the absolute path to the resized file.
    """
    return await resize_video_file(file_path, target_width, target_height, maintain_aspect_ratio, output_path)

@mcp.tool()
async def detect_and_trim_black_frames(file_path: str, threshold: float = 0.1, min_duration: float = 0.1, trim_start: bool = True, trim_end: bool = True, output_path: str | None = None) -> str:
    """
    Automatically detects and trims pure black frames from the start and/or end of a video.
    threshold: Pixel threshold for black detection (0.0 to 1.0). Default is 0.1.
    min_duration: Minimum duration of black frames to consider in seconds. Default is 0.1.
    Returns a JSON string containing the trimming information and the path to the output file.
    """
    import json
    res = await detect_and_trim_black_frames_file(file_path, threshold, min_duration, trim_start, trim_end, output_path)
    return json.dumps(res, indent=2)

if __name__ == "__main__":
    mcp.run()
