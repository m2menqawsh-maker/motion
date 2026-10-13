"""Backward-compatible adapter for path security.

Delegates canonical logic to scripts/core/security/path_policy.py.
"""

from scripts.core.security.path_policy import (
    validate_project_id,
    validate_workspace_id,
    validate_asset_id,
    resolve_safe_path,
    resolve_project_dir,
    get_canonical_project_dir,
    check_confinement_and_symlink,
    validate_source_asset,
    PathSecurityViolation,
    PathTraversalError,
    TenantSecurityError,
)

# Legacy alias
safe_resolve = resolve_safe_path

__all__ = [
    "validate_project_id",
    "validate_workspace_id",
    "validate_asset_id",
    "resolve_safe_path",
    "safe_resolve",
    "resolve_project_dir",
    "get_canonical_project_dir",
    "check_confinement_and_symlink",
    "validate_source_asset",
    "PathSecurityViolation",
    "PathTraversalError",
    "TenantSecurityError",
]
