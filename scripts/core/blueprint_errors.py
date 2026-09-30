"""
scripts/core/blueprint_errors.py — Blueprint Error Taxonomy (S12).
Typed failure modes for Blueprint loading, parsing, validation, and migration.
"""
from typing import Optional, Dict, Any, List


class BlueprintError(Exception):
    """Base class for all Blueprint domain errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class BlueprintNotFoundError(BlueprintError):
    """Raised when 05_blueprint.json is missing on disk."""
    def __init__(self, path: str):
        super().__init__(f"Blueprint file not found at: '{path}'", {"path": path})


class BlueprintParseError(BlueprintError):
    """Raised when 05_blueprint.json cannot be parsed as valid JSON."""
    def __init__(self, path: str, raw_error: str):
        super().__init__(f"Failed to parse blueprint JSON at '{path}': {raw_error}", {"path": path, "error": raw_error})


class BlueprintVersionError(BlueprintError):
    """Raised when blueprint_version is missing, malformed, or unsupported."""
    def __init__(self, version: Optional[str], supported_versions: List[str]):
        super().__init__(
            f"Unsupported blueprint_version: '{version}'. Supported versions: {supported_versions}",
            {"version": version, "supported_versions": supported_versions}
        )


class BlueprintValidationError(BlueprintError):
    """Raised when blueprint fails structural or semantic validation."""
    def __init__(self, errors: List[str]):
        super().__init__(f"Blueprint validation failed with {len(errors)} error(s): {'; '.join(errors)}", {"errors": errors})
        self.errors = errors


class BlueprintProjectMismatchError(BlueprintError):
    """Raised when blueprint.project_id does not match the expected project identity."""
    def __init__(self, blueprint_id: str, expected_id: str):
        super().__init__(
            f"Blueprint project_id mismatch: blueprint contains '{blueprint_id}', but expected '{expected_id}'",
            {"blueprint_id": blueprint_id, "expected_id": expected_id}
        )


class BlueprintAssetKindMismatchError(BlueprintError):
    """Raised when a referenced asset has an incompatible kind for its slot (e.g. image for voiceover)."""
    def __init__(self, slot: str, asset_id: str, found_kind: str, expected_kinds: List[str]):
        super().__init__(
            f"Asset kind mismatch in '{slot}': asset '{asset_id}' has kind '{found_kind}', expected one of {expected_kinds}",
            {"slot": slot, "asset_id": asset_id, "found_kind": found_kind, "expected_kinds": expected_kinds}
        )


class BlueprintReferencedAssetMissingError(BlueprintError):
    """Raised when an asset referenced in the Blueprint does not exist in Manifest v2."""
    def __init__(self, slot: str, asset_id: str):
        super().__init__(
            f"Referenced asset '{asset_id}' in slot '{slot}' not found in asset manifest",
            {"slot": slot, "asset_id": asset_id}
        )
