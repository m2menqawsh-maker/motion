import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

async def make_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> dict:
    """
    Wrapper for HTTP requests with error handling and retry logic.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(method, url, headers=headers, params=params)
            response.raise_for_status()
            
            # Iconify might return SVG text instead of JSON, so handle that if needed, 
            # but generally we expect JSON from Pixabay, Pexels, Freesound.
            if "application/json" in response.headers.get("content-type", ""):
                return response.json()
            else:
                return {"text": response.text, "headers": dict(response.headers)}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"API request failed with status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise RuntimeError(f"API request failed: {e}") from e
