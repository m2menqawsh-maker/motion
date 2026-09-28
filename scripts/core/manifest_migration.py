"""
Manifest v1 -> v2 Migration Engine (S11).
Provides deterministic, idempotent, and verified migration of legacy asset manifests.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone

from scripts.core.manifest_errors import (
    ManifestMigrationError,
    ManifestNotFoundError,
    ManifestValidationError,
)
from scripts.core.manifest_model import (
    AssetKind,
    Provenance,
    AssetStatus,
)
from scripts.core.manifest_validator import validate_manifest_semantic


def detect_manifest_version(data: Dict[str, Any]) -> str:
    """
    Detects manifest version explicitly without heuristics.
    Returns: '2.0.0', '1.0.0', or 'unknown'.
    """
    if not isinstance(data, dict) or not data:
        return "unknown"

    version = data.get("manifest_version")
    if version in ("2.0.0", "2.0"):
        return "2.0.0"
    if version is not None:
        return str(version)

    # Legacy v1 manifests lacked 'manifest_version'
    if "assets" in data and ("project_id" in data or "generated_at" in data):
        return "1.0.0"

    # Minimal assets-only legacy payload
    if "assets" in data and isinstance(data["assets"], list):
        return "1.0.0"

    return "unknown"


def migrate_manifest_data(
    data: Dict[str, Any],
    project_id: Optional[str] = None
) -> Tuple[Dict[str, Any], bool]:
    """
    Deterministically converts legacy manifest dict to canonical Manifest v2.
    Returns: (migrated_dict, was_migrated: bool).
    Strictly idempotent: if data is already v2, returns (data, False) with zero mutations.
    """
    detected = detect_manifest_version(data)

    # 1. Idempotency: Already v2
    if detected == "2.0.0":
        return data, False

    # 2. Ambiguous / empty data: fail closed, do not guess
    if detected == "unknown":
        raise ManifestMigrationError(
            "Cannot migrate ambiguous or unrecognized manifest data",
            project_id=project_id,
            raw_data=data
        )

    if detected != "1.0.0":
        raise ManifestMigrationError(
            f"Cannot migrate unsupported manifest version '{detected}'",
            project_id=project_id,
            raw_data=data
        )

    # 3. Resolve Project ID
    target_project_id = data.get("project_id") or project_id
    if not target_project_id:
        raise ManifestMigrationError(
            "Cannot migrate legacy manifest without project identity",
            project_id=project_id,
            raw_data=data
        )

    # 4. Migrate assets
    raw_assets = data.get("assets", [])
    migrated_assets: List[Dict[str, Any]] = []

    for idx, item in enumerate(raw_assets):
        if not isinstance(item, dict):
            raise ManifestMigrationError(
                f"Legacy asset at index {idx} is not an object",
                project_id=target_project_id
            )

        aid = item.get("asset_id") or item.get("id")
        if not aid:
            raise ManifestMigrationError(
                f"Legacy asset at index {idx} is missing asset ID",
                project_id=target_project_id
            )

        # Kind mapping
        legacy_type = item.get("type", "other")
        try:
            kind_enum = AssetKind.from_string(legacy_type, asset_id=aid)
        except ManifestValidationError as e:
            raise ManifestMigrationError(
                f"Failed to map asset kind '{legacy_type}': {e}",
                project_id=target_project_id
            )

        # Provenance mapping
        legacy_origin = item.get("origin")
        legacy_source = item.get("source")
        
        if legacy_source == "cache":
            provenance_enum = Provenance.CACHE_REUSE
        elif legacy_origin:
            try:
                provenance_enum = Provenance.from_string(legacy_origin, asset_id=aid)
            except ManifestValidationError:
                provenance_enum = Provenance.USER_UPLOAD
        elif legacy_source in ("user_upload", "mcp_fetch", "generated", "cache_reuse"):
            provenance_enum = Provenance.from_string(legacy_source, asset_id=aid)
        elif legacy_source == "incoming":
            provenance_enum = Provenance.USER_UPLOAD
        elif legacy_source == "ready":
            provenance_enum = Provenance.USER_UPLOAD
        else:
            provenance_enum = Provenance.USER_UPLOAD

        # Status mapping
        if legacy_source == "ready" or legacy_source == "cache":
            status_enum = AssetStatus.READY
        elif legacy_source == "incoming":
            status_enum = AssetStatus.INCOMING
        elif legacy_source == "processing":
            status_enum = AssetStatus.PROCESSING
        else:
            # Default for materialized assets with paths
            status_enum = AssetStatus.READY

        # Path mapping
        legacy_path = item.get("path")
        if status_enum == AssetStatus.READY:
            processed_path = legacy_path
            source_path = item.get("source_path") or legacy_path
        else:
            source_path = legacy_path
            processed_path = None

        # Metadata preservation
        metadata: Dict[str, Any] = {}
        for key in ("thumb", "durationFrames", "width", "height", "cache_checked"):
            if key in item and item[key] is not None:
                metadata[key] = item[key]
        if "approved" in item:
            metadata["approved"] = bool(item["approved"])
        if legacy_origin:
            metadata["origin_detail"] = legacy_origin

        migrated_assets.append({
            "asset_id": aid,
            "kind": kind_enum.value,
            "provenance": provenance_enum.value,
            "status": status_enum.value,
            "source_path": source_path,
            "processed_path": processed_path,
            "content_hash": item.get("hash") or item.get("content_hash"),
            "processing_spec_hash": item.get("processing_spec_hash"),
            "metadata": metadata,
        })

    v2_dict = {
        "manifest_version": "2.0.0",
        "project_id": target_project_id,
        "created_at": data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "assets": migrated_assets,
        "metadata": data.get("metadata") or {},
    }

    # Validate resulting payload before returning
    validate_manifest_semantic(v2_dict, expected_project_id=target_project_id)
    return v2_dict, True


def migrate_manifest_file(
    file_path: Path,
    dry_run: bool = False,
    backup: bool = True
) -> Tuple[Dict[str, Any], bool]:
    """
    Safely migrates a manifest file on disk.
    Creates backup (.bak) before replacement. Writes atomically.
    """
    if not file_path.exists():
        raise ManifestNotFoundError(str(file_path))

    try:
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ManifestMigrationError(f"Could not read JSON from {file_path}: {e}")

    # Determine project ID from path if not in data
    inferred_project_id = file_path.parent.name if file_path.parent.name.startswith("prj_") or file_path.parent.name.startswith("test_") else None

    migrated_dict, was_migrated = migrate_manifest_data(raw_data, project_id=inferred_project_id)

    if was_migrated and not dry_run:
        if backup:
            bak_path = file_path.with_suffix(".json.bak")
            shutil.copy2(file_path, bak_path)

        tmp_path = file_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(migrated_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(file_path)

    return migrated_dict, was_migrated


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.core.manifest_migration <path_or_project_id> [--dry-run] [--no-backup]")
        sys.exit(1)

    target_str = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    backup = "--no-backup" not in sys.argv

    target_path = Path(target_str)
    if not target_path.exists():
        proj_candidate = Path("projects") / target_str / "02_asset_manifest.json"
        if proj_candidate.exists():
            target_path = proj_candidate
        else:
            print(f"Error: Target '{target_str}' does not exist.")
            sys.exit(1)

    if target_path.is_dir():
        target_path = target_path / "02_asset_manifest.json"

    try:
        migrated, changed = migrate_manifest_file(target_path, dry_run=dry_run, backup=backup)
        if changed:
            print(f"✅ Migrated {target_path} to Manifest v2 (dry_run={dry_run})")
        else:
            print(f"ℹ️ {target_path} is already Manifest v2. No action taken.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
