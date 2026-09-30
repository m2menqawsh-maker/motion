"""Backward-compatible adapter for path security.

Delegates canonical logic to scripts/core/security/path_policy.py.
"""

from scripts.core.security.path_policy import (
    validate_project_id,
    validate_asset_id,
    resolve_safe_path,
    validate_source_asset,
    PathSecurityViolation,
)

# Legacy alias
safe_resolve = resolve_safe_path

__all__ = [
    "validate_project_id",
    "validate_asset_id",
    "resolve_safe_path",
    "safe_resolve",
    "validate_source_asset",
    "PathSecurityViolation",
]
