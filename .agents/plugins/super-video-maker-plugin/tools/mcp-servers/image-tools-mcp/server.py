from mcp.server.fastmcp import FastMCP
import os
import sys
import io
import logging

# Setup standard output to handle UTF-8 properly on Windows
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.image_ops import (
    upscale_image_file,
    crop_to_ratio_file,
    auto_crop_content_file
)

# Initialize MCP server
mcp = FastMCP("image-tools-mcp")

@mcp.tool()
def upscale_image(file_path: str, target_width: int = 0, target_height: int = 0, output_path: str | None = None) -> str:
    """
    Upscales or downscales an image using Lanczos resampling.
    If BOTH target_width and target_height are provided (> 0), the image will be forcefully STRETCHED to exactly those dimensions.
    If only ONE dimension is provided, the other will be calculated automatically to preserve the original aspect ratio.
    Returns the absolute path to the processed file.
    """
    return upscale_image_file(file_path, target_width, target_height, output_path)

@mcp.tool()
def crop_to_ratio(file_path: str, target_ratio: str, output_path: str | None = None) -> str:
    """
    Crops an image to a specific aspect ratio using a center crop.
    target_ratio must be a string like "9:16", "1:1", or "16:9".
    Returns the absolute path to the processed file.
    """
    return crop_to_ratio_file(file_path, target_ratio, output_path)

@mcp.tool()
def auto_crop_content(file_path: str, background_color: str = "auto", background_threshold: int = 10, output_path: str | None = None) -> str:
    """
    Automatically detects and removes empty/solid borders around the actual content of an image.
    background_color: "auto" (checks alpha transparency, then corner pixel), "transparent", "white", or "black".
    background_threshold: Tolerance for color differences (0-255). Default 10.
    Returns the absolute path to the processed file.
    """
    return auto_crop_content_file(file_path, background_color, background_threshold, output_path)

if __name__ == "__main__":
    mcp.run()
