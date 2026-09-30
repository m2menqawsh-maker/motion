"""Path and Filesystem Confinement Policy.

In accordance with ASSET-009, DISC-S01-01, and the Trust Model (SEC-DOC-001):
- All path inputs must be validated against canonical constraints.
- No path traversal sequences ('..') or leading slashes are permitted in identifiers.
- Symlinks resolving outside designated workspace boundaries are strictly rejected.
- Path resolutions must use robust path semantics rather than simple prefix string matching.
- Destination confinement must be guaranteed before any write or copy operation occurs.
"""

import os
import re
from pathlib import Path
from typing import Union, List, Optional


class PathSecurityViolation(Exception):
    """Raised when a path violates confinement boundaries."""
    pass


PROJECT_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')
ASSET_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_project_id(project_id: str) -> str:
    """Validate that project_id is a safe identifier with no path traversal characters."""
    if not isinstance(project_id, str) or not PROJECT_ID_REGEX.match(project_id):
        raise ValueError(f"Invalid project_id: {project_id}")
    return project_id


def validate_asset_id(asset_id: str) -> str:
    """Validate that asset_id is a safe filename identifier without path traversal."""
    if not isinstance(asset_id, str) or not ASSET_ID_REGEX.match(asset_id):
        raise ValueError(f"Invalid or unsafe asset_id: {asset_id}")
    return asset_id


def resolve_safe_path(base_dir: Union[str, Path], user_path: Union[str, Path]) -> Path:
    """Safely resolve user_path relative to base_dir, ensuring strict descendant confinement."""
    base = Path(base_dir).resolve()
    raw = str(user_path)

    # Reject Windows drive letters (e.g., C:\ or C:/)
    if re.match(r'^[a-zA-Z]:', raw):
        raise ValueError(f"Path traversal detected (drive letter): {user_path}")

    # Normalize backslashes for cross-platform safety
    normalized = raw.replace("\\", "/")
    if normalized.startswith("/"):
        raise ValueError(f"Path traversal detected (absolute path): {user_path}")

    resolved = (base / normalized).resolve()

    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal detected (escapes base): {user_path}")

    return resolved


def validate_source_asset(
    src_path: Union[str, Path],
    allowed_roots: List[Union[str, Path]],
    forbidden_roots: Optional[List[Union[str, Path]]] = None
) -> Path:
    """Validate a source asset file before reading or copying.
    
    Checks:
    1. Broken symlinks are rejected.
    2. Path exists.
    3. Resolved real path is descendant of at least one allowed root.
    4. Resolved real path is NOT descendant of any forbidden root.
    """
    path_obj = Path(src_path)

    # 1. Broken symlink check
    if path_obj.is_symlink() and not path_obj.exists():
        raise PathSecurityViolation(f"Broken symlink detected: {src_path}")

    # 2. Existence check
    if not path_obj.exists():
        raise FileNotFoundError(f"Source asset missing or not found (غير موجود): {src_path}")

    # 3. Resolve real path through symlink chain
    real_target = path_obj.resolve()

    # 4. Check allowed roots
    resolved_allowed = [Path(r).resolve() for r in allowed_roots]
    is_inside_allowed = False
    for root in resolved_allowed:
        try:
            real_target.relative_to(root)
            is_inside_allowed = True
            break
        except ValueError:
            continue

    if not is_inside_allowed:
        raise PathSecurityViolation(
            f"Symlink or path escape detected: '{src_path}' resolves to '{real_target}', "
            f"which is outside allowed roots: {[str(r) for r in resolved_allowed]}."
        )

    # 5. Check forbidden roots
    if forbidden_roots:
        resolved_forbidden = [Path(f).resolve() for f in forbidden_roots]
        for f_root in resolved_forbidden:
            try:
                real_target.relative_to(f_root)
                raise PathSecurityViolation(
                    f"Forbidden root access: '{real_target}' is inside forbidden directory '{f_root}'."
                )
            except ValueError:
                continue

    return real_target
