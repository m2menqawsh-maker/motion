import os
from utils.http_client import make_request

PIXABAY_API_URL = "https://pixabay.com/api/"
PIXABAY_VIDEO_API_URL = "https://pixabay.com/api/videos/"

async def search_pixabay_images(query: str, per_page: int = 20, orientation: str = "all") -> list[dict]:
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        raise ValueError("PIXABAY_API_KEY environment variable not set")
        
    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "orientation": orientation,
        "image_type": "photo"
    }
    
    response = await make_request(PIXABAY_API_URL, params=params)
    return response.get("hits", [])

async def search_pixabay_videos(query: str, per_page: int = 20) -> list[dict]:
    api_key = os.environ.get("PIXABAY_API_KEY")
    if not api_key:
        raise ValueError("PIXABAY_API_KEY environment variable not set")
        
    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page
    }
    
    response = await make_request(PIXABAY_VIDEO_API_URL, params=params)
    return response.get("hits", [])
