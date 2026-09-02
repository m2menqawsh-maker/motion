import httpx
from pathlib import Path
from utils.http_client import make_request
import logging

logger = logging.getLogger(__name__)

ICONIFY_API_URL = "https://api.iconify.design/search"
ICONIFY_DOWNLOAD_URL = "https://api.iconify.design/{prefix}/{name}.svg"

async def search_iconify(query: str, limit: int = 30) -> dict:
    """
    Search for icons in Iconify.
    Returns a dictionary containing 'icons', 'collections', etc.
    """
    params = {
        "query": query,
        "limit": limit
    }
    
    response = await make_request(ICONIFY_API_URL, params=params)
    return response

async def download_iconify(prefix: str, name: str, color: str | None = None, width: int | None = None, height: int | None = None, output_path: str | None = None) -> str:
    """
    Downloads an SVG icon from Iconify.
    """
    url = ICONIFY_DOWNLOAD_URL.format(prefix=prefix, name=name)
    params = {}
    if color:
        params["color"] = color
    if width:
        params["width"] = width
    if height:
        params["height"] = height
        
    target_dir = Path(output_path) if output_path else Path(r"c:\video\video-workspace\assets\incoming\icons")
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{prefix}_{name}.svg"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)
                
            return str(file_path.absolute())
        except Exception as e:
            logger.error(f"Failed to download iconify icon {prefix}/{name}: {e}")
            raise RuntimeError(f"Iconify download failed: {e}") from e
