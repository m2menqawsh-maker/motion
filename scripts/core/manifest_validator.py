"""
Semantic and Schema Validator for Manifest v2 (S11).
Enforces zero tolerance for duplicate IDs, identity mismatches, and contract breaches.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:
    Draft7Validator = None

from scripts.core.manifest_errors import ManifestValidationError
from scripts.core.manifest_model import (
    ManifestV2,
    AssetV2,
    AssetKind,
    Provenance,
    AssetStatus,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "manifest.v2.schema.json"
_CACHED_SCHEMA: Optional[Dict[str, Any]] = None
_CACHED_VALIDATOR: Optional[Any] = None


def _get_schema_validator() -> Optional[Any]:
    global _CACHED_SCHEMA, _CACHED_VALIDATOR
    if _CACHED_VALIDATOR is not None:
        return _CACHED_VALIDATOR
    if Draft7Validator is None or not SCHEMA_PATH.exists():
        return None
    try:
        _CACHED_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        _CACHED_VALIDATOR = Draft7Validator(_CACHED_SCHEMA)
        return _CACHED_VALIDATOR
    except Exception:
        return None


def validate_manifest_schema(data: Dict[str, Any]) -> None:
    """
    Validates dictionary against the canonical manifest.v2.schema.json.
    Categorizes errors with specific domain codes when applicable.
    """
    validator = _get_schema_validator()
    if validator is None:
        return

    errors = list(validator.iter_errors(data))
    if errors:
        first_err = sorted(errors, key=lambda e: list(e.path))[0]
        field_path = ".".join(str(p) for p in first_err.absolute_path) or "root"
        last_prop = str(first_err.absolute_path[-1]) if first_err.absolute_path else ""

        # Map schema enum errors to domain error codes
        if last_prop == "kind":
            raise ManifestValidationError(
                code="INVALID_ASSET_KIND",
                message=f"Invalid asset kind: {first_err.message}",
                field=field_path,
                manifest_version=data.get("manifest_version"),
            )
        elif last_prop == "provenance":
            raise ManifestValidationError(
                code="INVALID_PROVENANCE",
                message=f"Invalid provenance: {first_err.message}",
                field=field_path,
                manifest_version=data.get("manifest_version"),
            )
        elif last_prop == "status":
            raise ManifestValidationError(
                code="INVALID_STATUS",
                message=f"Invalid status: {first_err.message}",
                field=field_path,
                manifest_version=data.get("manifest_version"),
            )
        elif last_prop == "manifest_version":
            raise ManifestValidationError(
                code="UNSUPPORTED_VERSION",
                message=f"Unsupported manifest version: {first_err.message}",
                field=field_path,
                manifest_version=data.get("manifest_version"),
            )

        raise ManifestValidationError(
            code="SCHEMA_VALIDATION_ERROR",
            message=f"JSON Schema error at '{field_path}': {first_err.message}",
            field=field_path,
            manifest_version=data.get("manifest_version"),
        )


def validate_manifest_semantic(data: Dict[str, Any], expected_project_id: Optional[str] = None) -> ManifestV2:
    """
    Validates semantic invariants for Manifest v2.
    Returns typed, immutable ManifestV2 instance upon success.
    Fails closed before any side effects.
    """
    if not isinstance(data, dict):
        raise ManifestValidationError(
            code="INVALID_MANIFEST_STRUCTURE",
            message=f"Manifest root must be an object/dict, got {type(data).__name__}"
        )

    # 1. Version enforcement
    version = data.get("manifest_version")
    if not version:
        raise ManifestValidationError(
            code="MISSING_VERSION",
            message="Missing required field 'manifest_version'"
        )
    if version not in ("2.0.0", "2.0"):
        raise ManifestValidationError(
            code="UNSUPPORTED_VERSION",
            message=f"Manifest version '{version}' is unsupported. Only '2.0.0' or '2.0' are accepted.",
            manifest_version=str(version)
        )

    # 2. Project ID invariant
    project_id = data.get("project_id")
    if not project_id:
        raise ManifestValidationError(
            code="MISSING_PROJECT_ID",
            message="Missing required field 'project_id'",
            manifest_version=version
        )
    if expected_project_id and project_id != expected_project_id:
        raise ManifestValidationError(
            code="PROJECT_ID_MISMATCH",
            message=f"Manifest project_id '{project_id}' does not match expected project_id '{expected_project_id}'",
            field="project_id",
            manifest_version=version
        )

    # 3. Schema validation
    validate_manifest_schema(data)

    # 4. Assets collection semantic checks
    raw_assets = data.get("assets")
    if not isinstance(raw_assets, list):
        raise ManifestValidationError(
            code="INVALID_ASSETS_FIELD",
            message=f"'assets' field must be a list, got {type(raw_assets).__name__}",
            field="assets",
            manifest_version=version
        )

    seen_asset_ids: set[str] = set()
    validated_assets: List[AssetV2] = []

    for idx, item in enumerate(raw_assets):
        if not isinstance(item, dict):
            raise ManifestValidationError(
                code="INVALID_ASSET_ITEM",
                message=f"Asset at index {idx} must be a dict",
                field=f"assets[{idx}]",
                manifest_version=version
            )

        aid = item.get("asset_id")
        if not aid or not isinstance(aid, str):
            raise ManifestValidationError(
                code="INVALID_ASSET_ID",
                message=f"Asset at index {idx} has invalid or missing asset_id",
                field=f"assets[{idx}].asset_id",
                manifest_version=version
            )

        aid = aid.strip()
        # Semantic Invariant: Duplicate Asset IDs strictly rejected
        if aid in seen_asset_ids:
            raise ManifestValidationError(
                code="DUPLICATE_ASSET_ID",
                message=f"Duplicate asset_id '{aid}' detected at index {idx}",
                field=f"assets[{idx}].asset_id",
                asset_id=aid,
                manifest_version=version
            )
        seen_asset_ids.add(aid)

        # Kind vocabulary
        raw_kind = item.get("kind")
        kind_enum = AssetKind.from_string(raw_kind, asset_id=aid)

        # Provenance vocabulary
        raw_provenance = item.get("provenance")
        provenance_enum = Provenance.from_string(raw_provenance, asset_id=aid)

        # Status vocabulary
        raw_status = item.get("status")
        status_enum = AssetStatus.from_string(raw_status, asset_id=aid)

        src_path = item.get("source_path")
        proc_path = item.get("processed_path")

        # Semantic Invariant: Path requirements based on status
        if status_enum == AssetStatus.READY:
            if not src_path and not proc_path:
                raise ManifestValidationError(
                    code="MISSING_REQUIRED_PATH",
                    message=f"Asset '{aid}' has status 'ready' but neither source_path nor processed_path is specified",
                    field=f"assets[{idx}].processed_path",
                    asset_id=aid,
                    manifest_version=version
                )
        elif status_enum == AssetStatus.INCOMING:
            if not src_path:
                raise ManifestValidationError(
                    code="MISSING_REQUIRED_PATH",
                    message=f"Asset '{aid}' has status 'incoming' but source_path is missing",
                    field=f"assets[{idx}].source_path",
                    asset_id=aid,
                    manifest_version=version
                )

        item_meta = item.get("metadata") or {}
        proj_meta = data.get("metadata") or {}
        ws_id = proj_meta.get("workspace_id") or item_meta.get("workspace_id")

        storage_key = item_meta.get("storage_key")
        if storage_key:
            from scripts.core.storage import validate_storage_key, StorageSecurityError
            try:
                validate_storage_key(storage_key)
            except StorageSecurityError as e:
                raise ManifestValidationError(
                    code="MALFORMED_STORAGE_KEY",
                    message=f"Asset '{aid}' has invalid storage_key: {e}",
                    field=f"assets[{idx}].metadata.storage_key",
                    asset_id=aid,
                    manifest_version=version
                )
            if ws_id and not storage_key.startswith(f"workspaces/{ws_id}/projects/{project_id}/"):
                raise ManifestValidationError(
                    code="CROSS_TENANT_ASSET_REFERENCE",
                    message=f"Cross-tenant asset reference rejected: storage_key '{storage_key}' does not belong to workspace '{ws_id}' and project '{project_id}'",
                    field=f"assets[{idx}].metadata.storage_key",
                    asset_id=aid,
                    manifest_version=version
                )

        validated_asset = AssetV2(
            asset_id=aid,
            kind=kind_enum,
            provenance=provenance_enum,
            status=status_enum,
            source_path=src_path,
            processed_path=proc_path,
            content_hash=item.get("content_hash"),
            processing_spec_hash=item.get("processing_spec_hash"),
            metadata=item_meta
        )
        validated_assets.append(validated_asset)

    return ManifestV2(
        manifest_version=version,
        project_id=project_id,
        created_at=data.get("created_at") or "",
        updated_at=data.get("updated_at"),
        assets=validated_assets,
        metadata=data.get("metadata") or {}
    )


def validate_tenant_assets(data: Dict[str, Any], workspace_id: str) -> None:
    """
    Validates that all assets and storage keys in a manifest belong exclusively
    to the given workspace_id. Fails closed with ManifestValidationError on any
    cross-tenant reference or traversal.
    """
    if not isinstance(data, dict):
        return

    assets = data.get("assets", [])
    if isinstance(assets, dict):
        assets = list(assets.values())
    elif not isinstance(assets, list):
        return

    for idx, item in enumerate(assets):
        if not isinstance(item, dict):
            continue
        aid = item.get("asset_id", f"asset_{idx}")
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        storage_key = item.get("storage_key") or meta.get("storage_key")
        item_ws = meta.get("workspace_id") or item.get("workspace_id")

        if item_ws and item_ws != workspace_id:
            raise ManifestValidationError(
                code="CROSS_TENANT_ASSET_REFERENCE",
                message=f"Cross-tenant asset violation: asset '{aid}' specifies workspace_id '{item_ws}' but job belongs to '{workspace_id}'",
                asset_id=aid,
            )

        if storage_key:
            from scripts.core.storage import validate_storage_key
            validate_storage_key(storage_key)
            expected_prefix = f"workspaces/{workspace_id}/"
            if not storage_key.startswith(expected_prefix):
                raise ManifestValidationError(
                    code="CROSS_TENANT_ASSET_REFERENCE",
                    message=f"Cross-tenant asset violation: asset '{aid}' storage_key '{storage_key}' does not start with expected workspace prefix '{expected_prefix}'",
                    asset_id=aid,
                )


class ManifestValidator:
    """Static wrapper for manifest validation."""
    validate_schema = staticmethod(validate_manifest_schema)
    validate_semantic = staticmethod(validate_manifest_semantic)
    validate_tenant_assets = staticmethod(validate_tenant_assets)

