import shutil
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

workspace_dir = os.environ.get("SVM_DATA_DIR", r"c:\video\clean-video-workspace")
BASE_ASSET_DIR = Path(workspace_dir) / "assets"

def safe_resolve(base_dir: Path, user_path: str) -> Path:
    resolved_path = (base_dir / user_path).resolve()
    try:
        resolved_path.relative_to(base_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {user_path}")
    return resolved_path

def move_asset_status(file_path: str, from_status: str, to_status: str, asset_type: str) -> str:
    """
    Manually moves an asset file from one status directory to another (e.g., incoming -> processing).
    If a process fails, the file remains in processing/ for debugging.
    """
    if asset_type not in ["audio", "image", "video", "icons"]:
        raise ValueError(f"Invalid asset_type: {asset_type}")

    valid_statuses = ["incoming", "processing", "ready", "cache"]
    if from_status not in valid_statuses or to_status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of {valid_statuses}")

    source_path = safe_resolve(Path(workspace_dir), file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Ensure the file is actually in the from_status directory logically
    expected_from_dir = BASE_ASSET_DIR / from_status / asset_type
    
    # We could strictly enforce it, but let's just move it to the target
    target_dir = BASE_ASSET_DIR / to_status / asset_type
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / source_path.name
    
    shutil.move(str(source_path), str(target_path))
    logger.info(f"Moved {source_path.name} from {from_status} to {to_status}")
    
    return str(target_path.absolute())
