"""
Structured Exceptions for Manifest v2 and Canonical Governance (S11).
"""
from typing import Optional, List, Dict, Any


class ManifestError(Exception):
    """Base exception for all manifest-related failures."""
    pass


class ManifestNotFoundError(ManifestError):
    """Raised when an asset manifest file does not exist on disk (fail closed)."""
    def __init__(self, path: str, project_id: Optional[str] = None):
        self.path = str(path)
        self.project_id = project_id
        super().__init__(f"Manifest file not found: '{self.path}' (project_id='{project_id}')")


class ManifestValidationError(ManifestError):
    """
    Structured validation error for schema or semantic invariant breaches.
    """
    def __init__(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        asset_id: Optional[str] = None,
        manifest_version: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.field = field
        self.asset_id = asset_id
        self.manifest_version = manifest_version
        self.details = details or {}
        
        ctx_parts = [f"[{self.code}] {self.message}"]
        if self.field:
            ctx_parts.append(f"field='{self.field}'")
        if self.asset_id:
            ctx_parts.append(f"asset_id='{self.asset_id}'")
        if self.manifest_version:
            ctx_parts.append(f"manifest_version='{self.manifest_version}'")
        super().__init__(" | ".join(ctx_parts))


class ManifestMigrationError(ManifestError):
    """Raised when legacy manifest data cannot be safely and deterministically migrated."""
    def __init__(self, message: str, project_id: Optional[str] = None, raw_data: Optional[Dict[str, Any]] = None):
        self.project_id = project_id
        self.raw_data = raw_data
        super().__init__(f"Manifest migration failed: {message} (project_id='{project_id}')")


class ProjectIdentityMismatchError(ManifestError):
    """Raised when project identities diverge across artifacts or project directories."""
    def __init__(self, expected_project_id: str, found_identities: Dict[str, Optional[str]]):
        self.expected_project_id = expected_project_id
        self.found_identities = found_identities
        msg = (
            f"Project identity mismatch: expected '{expected_project_id}', "
            f"found conflicts: {found_identities}"
        )
        super().__init__(msg)
