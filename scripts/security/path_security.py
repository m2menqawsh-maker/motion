import os
import re
from pathlib import Path

def validate_project_id(project_id: str) -> str:
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise ValueError(f"Invalid project_id: {project_id}")
    return project_id

def safe_resolve(base_dir: Path, user_path: str) -> Path:
    raw = str(user_path)
    # Reject Windows drive letters (e.g. C:\ or C:/) regardless of host OS
    if re.match(r'^[a-zA-Z]:', raw):
        raise ValueError(f"Path traversal detected: {user_path}")

    # Normalize backslashes for cross-platform safety
    normalized_path = raw.replace("\\", "/")
    if normalized_path.startswith("/"):
        raise ValueError(f"Path traversal detected: {user_path}")
    
    # Resolve against base_dir and resolve symlinks/.. 
    resolved_path = (base_dir / normalized_path).resolve()
    
    # Check if the resolved path is inside the base_dir
    try:
        resolved_path.relative_to(base_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {user_path}")
        
    return resolved_path
