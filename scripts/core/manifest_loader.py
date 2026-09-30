"""
Canonical Manifest Loader and Persistence (S11).
Single authoritative entrypoint for loading, parsing, and validating asset manifests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union, Optional, Dict, Any

from scripts.core.manifest_errors import (
    ManifestNotFoundError,
    ManifestValidationError,
)
from scripts.core.manifest_model import ManifestV2
from scripts.core.manifest_validator import validate_manifest_semantic
from scripts.core.manifest_migration import (
    detect_manifest_version,
    migrate_manifest_data,
)


def validate_manifest_dict(
    data: Dict[str, Any],
    expected_project_id: Optional[str] = None,
    allow_migrate: bool = False,
) -> ManifestV2:
    """
    Validates an in-memory dictionary representation of Manifest v2.
    """
    if not isinstance(data, dict):
        raise ManifestValidationError(
            code="INVALID_MANIFEST_STRUCTURE",
            message=f"Manifest must be a dictionary, got {type(data).__name__}"
        )

    version = detect_manifest_version(data)
    if version == "2.0.0":
        return validate_manifest_semantic(data, expected_project_id=expected_project_id)

    if version == "1.0.0":
        if allow_migrate:
            migrated_dict, _ = migrate_manifest_data(data, project_id=expected_project_id)
            return validate_manifest_semantic(migrated_dict, expected_project_id=expected_project_id)
        raise ManifestValidationError(
            code="LEGACY_VERSION_NOT_MIGRATED",
            message="Legacy manifest version 1.0.0 detected. Migration to Manifest v2 is required.",
            manifest_version=version
        )

    raise ManifestValidationError(
        code="UNSUPPORTED_VERSION",
        message=f"Manifest version '{version}' is unsupported.",
        manifest_version=version
    )


def load_manifest(
    path_or_dir: Union[str, Path],
    expected_project_id: Optional[str] = None,
    allow_migrate: bool = False,
) -> ManifestV2:
    """
    Loads, parses, and strictly validates an asset manifest from disk.
    Fails closed immediately if missing or invalid.
    """
    target = Path(path_or_dir)
    if target.is_dir():
        manifest_file = target / "02_asset_manifest.json"
    else:
        manifest_file = target

    if not manifest_file.exists():
        raise ManifestNotFoundError(str(manifest_file), project_id=expected_project_id)

    try:
        raw_text = manifest_file.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ManifestValidationError(
            code="INVALID_JSON",
            message=f"Failed to decode manifest JSON from '{manifest_file}': {e}",
            field="root"
        )
    except Exception as e:
        raise ManifestValidationError(
            code="FILE_READ_ERROR",
            message=f"Could not read manifest file '{manifest_file}': {e}",
            field="root"
        )

    # Inferred project id if within projects/ directory
    inferred_expected = expected_project_id
    if not inferred_expected and manifest_file.parent.name.startswith("prj_"):
        inferred_expected = manifest_file.parent.name

    return validate_manifest_dict(data, expected_project_id=inferred_expected, allow_migrate=allow_migrate)


def save_manifest(
    manifest: Union[ManifestV2, Dict[str, Any]],
    target_path_or_dir: Union[str, Path],
    atomic: bool = True,
) -> Path:
    """
    Persists a verified ManifestV2 instance to disk.
    Validates before writing and writes atomically.
    """
    target = Path(target_path_or_dir)
    if target.is_dir():
        dest = target / "02_asset_manifest.json"
    else:
        dest = target

    if isinstance(manifest, dict):
        validated_manifest = validate_manifest_semantic(manifest)
    elif isinstance(manifest, ManifestV2):
        validated_manifest = manifest
    else:
        raise ManifestValidationError(
            code="INVALID_MANIFEST_TYPE",
            message=f"Expected ManifestV2 or dict, got {type(manifest).__name__}"
        )

    data = validated_manifest.to_dict()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if atomic:
        tmp_path = dest.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(dest)
    else:
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return dest
