from mcp.server.fastmcp import FastMCP
import sys
import io
import logging
from typing import Optional

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.cache_ops import check_cache_file, save_to_cache_file

mcp = FastMCP("common-tools-mcp")

@mcp.tool()
def check_cache(asset_id: str, specs_hash: str, cache_dir: str) -> Optional[str]:
    """
    Checks if a processed media file exists in the cache directory.
    Matches any file that starts with "{asset_id}_{specs_hash}.".
    Returns the absolute path to the cached file if found, otherwise returns null/None.
    """
    return check_cache_file(asset_id, specs_hash, cache_dir)

@mcp.tool()
def save_to_cache(file_path: str, asset_id: str, specs_hash: str, cache_dir: str) -> str:
    """
    Copies a processed media file into the cache directory.
    The file will be renamed to "{asset_id}_{specs_hash}.{original_extension}".
    Returns the absolute path to the newly cached file.
    """
    return save_to_cache_file(file_path, asset_id, specs_hash, cache_dir)

if __name__ == "__main__":
    mcp.run()
