from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import sys
import io
import asyncio

# Force UTF-8 encoding for stdio to prevent UnicodeEncodeError on Windows
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables from .env
load_dotenv()

# Import utilities
from utils.downloader import download_media, download_via_ytdlp
from utils.file_organizer import move_asset_status

# Import tools
from tools.pixabay import search_pixabay_images, search_pixabay_videos
from utils.pixabay_scraper import search_pixabay_audio
from tools.freesound import search_freesound
from tools.pexels import search_pexels_images, search_pexels_videos
from tools.iconify import search_iconify, download_iconify

# Initialize MCP server
mcp = FastMCP("media-sources-mcp")

# ---------------------------------------------------------
# Asset Management Tools
# ---------------------------------------------------------
@mcp.tool()
async def download_direct_file(url: str, asset_type: str, source: str, asset_id: str, custom_path: str | None = None) -> str:
    """
    Use ONLY when the URL points directly to a downloadable media file such as MP3, WAV, MP4, JPG, PNG, etc. Do not use for webpage URLs.
    """
    path = await download_media(url, asset_type, source, asset_id, custom_path)
    return path

@mcp.tool()
async def download_media_page(url: str, asset_type: str, source: str, asset_id: str, custom_path: str | None = None) -> str:
    """
    Use when the URL is a webpage containing media and requires extraction through yt-dlp. Do not use when you already have a direct file URL.
    """
    path = await download_via_ytdlp(url, asset_type, source, asset_id, custom_path)
    return path

@mcp.tool()
def change_asset_status(file_path: str, from_status: str, to_status: str, asset_type: str) -> str:
    """
    Manually moves an asset file from one status directory to another.
    Statuses: 'incoming', 'processing', 'ready', 'cache'.
    Valid asset_type: 'audio', 'image', 'video', 'icons'.
    Returns the new absolute path.
    """
    return move_asset_status(file_path, from_status, to_status, asset_type)

# ---------------------------------------------------------
# Pixabay Tools
# ---------------------------------------------------------
@mcp.tool()
async def pixabay_search_images(query: str, per_page: int = 20, orientation: str = "all") -> list[dict]:
    """Search for images on Pixabay."""
    return await search_pixabay_images(query, per_page, orientation)

@mcp.tool()
async def pixabay_search_videos(query: str, per_page: int = 20) -> list[dict]:
    """Search for videos on Pixabay."""
    return await search_pixabay_videos(query, per_page)

@mcp.tool()
async def pixabay_search_audio(query: str, max_results: int = 10) -> list[dict]:
    """Search for audio/music on Pixabay using Playwright."""
    return await search_pixabay_audio(query, max_results)

# ---------------------------------------------------------
# Freesound Tools
# ---------------------------------------------------------
@mcp.tool()
async def freesound_search(query: str, page: int = 1, page_size: int = 15) -> list[dict]:
    """Search for sound effects on Freesound."""
    return await search_freesound(query, page, page_size)

# ---------------------------------------------------------
# Pexels Tools
# ---------------------------------------------------------
@mcp.tool()
async def pexels_search_images(query: str, per_page: int = 15, orientation: str | None = None) -> list[dict]:
    """Search for images on Pexels. Optional orientation: 'landscape', 'portrait', 'square'."""
    return await search_pexels_images(query, per_page, orientation)

@mcp.tool()
async def pexels_search_videos(query: str, per_page: int = 15, orientation: str | None = None) -> list[dict]:
    """Search for videos on Pexels. Optional orientation: 'landscape', 'portrait', 'square'."""
    return await search_pexels_videos(query, per_page, orientation)

# ---------------------------------------------------------

# Iconify Tools
# ---------------------------------------------------------
@mcp.tool()
async def iconify_search(query: str, limit: int = 30) -> dict:
    """Search for SVG icons on Iconify."""
    return await search_iconify(query, limit)

@mcp.tool()
async def download_iconify_icon(prefix: str, name: str, color: str | None = None, width: int | None = None, height: int | None = None, output_path: str | None = None) -> str:
    """
    Downloads an SVG icon from Iconify with optional color and sizing parameters.
    Returns the absolute path to the downloaded .svg file.
    """
    return await download_iconify(prefix, name, color, width, height, output_path)

if __name__ == "__main__":
    # Start the server via stdio
    mcp.run()
