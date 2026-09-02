import os
import shutil
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

def _dirs():
    data = Path(os.environ.get("SVM_DATA_DIR", "C:/video/clean-video-workspace"))
    plugin = Path(os.environ.get("SVM_PLUGIN_ROOT",
               str(data / ".agents" / "plugins" / "super-video-maker-plugin")))
    return data, plugin

DATA_DIR, PLUGIN_ROOT = _dirs()
INDEX_PATH = PLUGIN_ROOT / "ground-truth" / "ASSET_INDEX.json"
READY_DIR  = DATA_DIR / "assets" / "ready"
CACHE_DIR  = DATA_DIR / "assets" / "cache"

def check_cache_file(asset_id: str, specs_hash: str, cache_dir: str) -> str | None:
    # 1. Check ASSET_INDEX.json
    if INDEX_PATH.exists():
        try:
            with open(INDEX_PATH, 'r', encoding='utf-8') as f:
                index = json.load(f)
            for entry in index:
                if entry.get("base") == asset_id and entry.get("state") == "ready":
                    path_str = entry.get("path")
                    if path_str:
                        abs_path = DATA_DIR / path_str
                        if abs_path.exists():
                            logger.info(f"Cache hit (index): {abs_path}")
                            return str(abs_path)
        except Exception as e:
            logger.warning(f"Failed to read index: {e}")

    # 2. Check assets/ready
    if READY_DIR.exists():
        for root, _, files in os.walk(READY_DIR):
            for file in files:
                if file.startswith(asset_id + "_") or file.startswith(asset_id + "."):
                    abs_path = Path(root) / file
                    logger.info(f"Cache hit (ready dir): {abs_path}")
                    return str(abs_path)

    # 3. Check cache_dir
    c_dir = Path(cache_dir)
    if not c_dir.is_absolute():
        c_dir = DATA_DIR / cache_dir
        
    if c_dir.exists():
        prefix = f"{asset_id}_{specs_hash}."
        for file in c_dir.iterdir():
            if file.is_file() and file.name.startswith(prefix):
                logger.info(f"Cache hit (cache dir): found {file.name}")
                return str(file.absolute())
                
    logger.info("Cache miss.")
    return None

def save_to_cache_file(file_path: str, asset_id: str, specs_hash: str, cache_dir: str) -> str:
    src_path = Path(file_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")
        
    cache_path = CACHE_DIR
    cache_path.mkdir(parents=True, exist_ok=True)
    
    ext = src_path.suffix
    dest_name = f"{asset_id}_{specs_hash}{ext}"
    dest_path = cache_path / dest_name
    
    shutil.copy2(src_path, dest_path)
    logger.info(f"Saved to cache: {dest_path}")
    
    return str(dest_path.absolute())
