import httpx
import os
import urllib.parse
import mimetypes
from pathlib import Path
import logging
import yt_dlp
import asyncio

logger = logging.getLogger(__name__)

BASE_ASSET_DIR = Path(r"c:\video\video-workspace\assets")

async def download_media(url: str, asset_type: str, source: str, asset_id: str, custom_path: str | None = None) -> str:
    """
    Downloads a file. Automatically routes it to incoming/{asset_type}/ unless custom_path is provided.
    Generates standard name: {source}_{asset_type}_{asset_id}.{ext}
    """
    if asset_type not in ["audio", "image", "video", "icons"]:
        raise ValueError(f"Invalid asset_type: {asset_type}")

    target_dir = Path(custom_path) if custom_path else BASE_ASSET_DIR / "incoming" / asset_type
    target_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # We use stream so we don't load huge video files entirely into memory at once
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                # Determine extension
                ext = None
                
                # 1. Check content-type header
                content_type = response.headers.get("content-type")
                if content_type:
                    ext = mimetypes.guess_extension(content_type.split(";")[0])
                
                # 2. If not found or unreliable, fallback to URL parsing
                if not ext or ext == ".bin":
                    parsed_url = urllib.parse.urlparse(url)
                    ext = Path(parsed_url.path).suffix
                
                # Default fallbacks if everything fails
                if not ext:
                    fallbacks = {"audio": ".mp3", "image": ".jpg", "video": ".mp4", "icons": ".svg"}
                    ext = fallbacks.get(asset_type, "")

                if ext == ".jpe":
                    ext = ".jpg" # normalize

                filename = f"{source}_{asset_type}_{asset_id}{ext}"
                file_path = target_dir / filename

                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                
                return str(file_path.absolute())
                
        except Exception as e:
            logger.error(f"Failed to download media from {url}: {e}")
            raise RuntimeError(f"Download failed: {e}") from e

async def download_via_ytdlp(url: str, asset_type: str, source: str, asset_id: str, custom_path: str | None = None) -> str:
    """
    Downloads media using yt-dlp (for pages).
    """
    if asset_type not in ["audio", "image", "video", "icons"]:
        raise ValueError(f"Invalid asset_type: {asset_type}")

    target_dir = Path(custom_path) if custom_path else BASE_ASSET_DIR / "incoming" / asset_type
    target_dir.mkdir(parents=True, exist_ok=True)
    
    filename_template = f"{source}_{asset_type}_{asset_id}.%(ext)s"
    output_template = str(target_dir / filename_template)
    
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }
    
    if asset_type == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif asset_type == "video":
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    
    def run_yt_dlp():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # handle cases where info_dict is a playlist
            if 'entries' in info_dict:
                info_dict = info_dict['entries'][0]
            
            # prepare_filename returns the original filename before postprocessing
            orig_file = ydl.prepare_filename(info_dict)
            return orig_file
            
    loop = asyncio.get_running_loop()
    try:
        orig_file = await loop.run_in_executor(None, run_yt_dlp)
        
        # In case of post-processing (e.g. mp3 conversion), yt-dlp changes the extension.
        # We can find the actual file by looking at the directory for matching prefix.
        prefix = f"{source}_{asset_type}_{asset_id}"
        for f in target_dir.iterdir():
            if f.name.startswith(prefix):
                return str(f.absolute())
        
        return orig_file
    except Exception as e:
        logger.error(f"Failed to download media via yt-dlp from {url}: {e}")
        raise RuntimeError(f"yt-dlp download failed: {e}") from e
