from mcp.server.fastmcp import FastMCP
import os
import sys
import io
import re
import logging
from typing import Optional
from pathlib import Path

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Canonical repository root discovery
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.cache_ops import check_cache_file, save_to_cache_file

def _extract_project_id(cache_dir: Optional[str]) -> Optional[str]:
    """Helper to detect project ID from cache_dir path or environment."""
    env_proj = os.environ.get("SVM_PROJECT_ID")
    if env_proj:
        return env_proj
    if not cache_dir:
        return None
    normalized = str(cache_dir).replace("\\", "/")
    # Matches patterns like 'projects/<proj_id>/...'
    match = re.search(r"projects/([^/]+)", normalized)
    if match:
        return match.group(1)
    return None

mcp = FastMCP("common-tools-mcp")

@mcp.tool()
def check_cache(asset_id: str, specs_hash: str, cache_dir: str) -> Optional[str]:
    """
    Checks if a processed media file exists in the cache directory.
    Matches any file that starts with "{asset_id}_{specs_hash}.".
    Returns the absolute path to the cached file if found, otherwise returns null/None.
    Delegates to canonical AssetService if project context is detected, with fallback to legacy file cache.
    """
    proj_id = _extract_project_id(cache_dir)
    if proj_id:
        try:
            from api.services.asset_service import AssetService
            cached = AssetService.check_asset_cache(project_id=proj_id, asset_id=asset_id, specs_hash=specs_hash)
            if cached:
                logger.info(f"Canonical AssetService cache hit: {cached}")
                return str(cached)
        except Exception as e:
            logger.warning(f"Canonical AssetService check_cache failed: {e}; falling back to file check.")
    return check_cache_file(asset_id, specs_hash, cache_dir)

@mcp.tool()
def save_to_cache(file_path: str, asset_id: str, specs_hash: str, cache_dir: str) -> str:
    """
    Copies a processed media file into the cache directory.
    The file will be renamed to "{asset_id}_{specs_hash}.{original_extension}".
    Returns the absolute path to the newly cached file.
    Delegates to canonical AssetService if project context is detected, with fallback to legacy file cache.
    """
    proj_id = _extract_project_id(cache_dir)
    if proj_id:
        try:
            from api.services.asset_service import AssetService
            saved = AssetService.save_asset_to_cache(
                project_id=proj_id,
                asset_id=asset_id,
                file_path=file_path,
                specs_hash=specs_hash,
            )
            if saved:
                logger.info(f"Canonical AssetService saved to cache: {saved}")
                return str(saved)
        except Exception as e:
            logger.warning(f"Canonical AssetService save_to_cache failed: {e}; falling back to file copy.")
    return save_to_cache_file(file_path, asset_id, specs_hash, cache_dir)

if __name__ == "__main__":
    mcp.run()
