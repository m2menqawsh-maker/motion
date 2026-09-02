import os
from utils.http_client import make_request

PEXELS_IMAGE_API_URL = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_API_URL = "https://api.pexels.com/videos/search"

def get_headers():
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        raise ValueError("PEXELS_API_KEY environment variable not set")
    return {"Authorization": api_key}

async def search_pexels_images(query: str, per_page: int = 15, orientation: str | None = None) -> list[dict]:
    params = {
        "query": query,
        "per_page": per_page
    }
    if orientation:
        params["orientation"] = orientation
        
    response = await make_request(PEXELS_IMAGE_API_URL, headers=get_headers(), params=params)
    return response.get("photos", [])

async def search_pexels_videos(query: str, per_page: int = 15, orientation: str | None = None) -> list[dict]:
    params = {
        "query": query,
        "per_page": per_page
    }
    if orientation:
        params["orientation"] = orientation
        
    response = await make_request(PEXELS_VIDEO_API_URL, headers=get_headers(), params=params)
    return response.get("videos", [])
