import os
from utils.http_client import make_request

FREESOUND_API_URL = "https://freesound.org/apiv2/search/text/"

async def search_freesound(query: str, page: int = 1, page_size: int = 15) -> list[dict]:
    api_key = os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        raise ValueError("FREESOUND_API_KEY environment variable not set")
        
    params = {
        "token": api_key,
        "query": query,
        "page": page,
        "page_size": page_size,
        "fields": "id,name,previews,tags,description,duration"
    }
    
    response = await make_request(FREESOUND_API_URL, params=params)
    return response.get("results", [])
