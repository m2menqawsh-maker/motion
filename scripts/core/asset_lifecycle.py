"""
Canonical Asset Lifecycle & Storage Status Transition Subsystem (S13 - ASSET-004).

Authoritative rules:
1. All asset status transitions must enforce expected_status against canonical truth.
2. If actual status != expected_status, reject immediately with AssetStatusMismatchError.
3. Zero side effects on mismatch: no file move, no copy, no manifest mutation, no temp files.
4. Ordering with rollback prevents silent divergence between disk and manifest.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union

from scripts.core.manifest_errors import ManifestValidationError
from scripts.core.manifest_loader import load_manifest, save_manifest
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2


class AssetLifecycleError(Exception):
    """Base exception for asset lifecycle and transition operations."""
    pass


class AssetStatusMismatchError(AssetLifecycleError):
    """Raised when an asset's actual status does not match expected_status."""
    def __init__(self, asset_id: str, actual_status: str, expected_status: str, message: Optional[str] = None):
        self.asset_id = asset_id
        self.actual_status = actual_status
        self.expected_status = expected_status
        super().__init__(
            message or f"Status mismatch for asset '{asset_id}': expected '{expected_status}', found '{actual_status}'."
        )


class AssetNotFoundError(AssetLifecycleError):
    """Raised when an asset_id is not found in the manifest or storage."""
    def __init__(self, asset_id: str, message: Optional[str] = None):
        self.asset_id = asset_id
        super().__init__(message or f"Asset '{asset_id}' not found.")


class AssetFileMissingError(AssetLifecycleError):
    """Raised when the underlying file for an asset cannot be found."""
    def __init__(self, asset_id: str, file_path: str, message: Optional[str] = None):
        self.asset_id = asset_id
        self.file_path = file_path
        super().__init__(message or f"File for asset '{asset_id}' not found at '{file_path}'.")


def move_asset(
    project_dir_or_manifest: Union[str, Path, ManifestV2],
    asset_id: str,
    expected_status: Union[str, AssetStatus],
    target_status: Union[str, AssetStatus],
    destination_path: Optional[Union[str, Path]] = None,
    workspace_root: Optional[Union[str, Path]] = None,
) -> AssetV2:
    """
    Atomically moves an asset between lifecycle statuses with strict compare-before-move.
    
    1. Compares canonical stored status against expected_status.
    2. Rejects with AssetStatusMismatchError on any discrepancy with zero side effects.
    3. Moves file on disk (if required) and updates ManifestV2.
    4. Rolls back file move if manifest persistence fails.
    """
    expected_enum = (
        expected_status if isinstance(expected_status, AssetStatus)
        else AssetStatus.from_string(str(expected_status), asset_id=asset_id)
    )
    target_enum = (
        target_status if isinstance(target_status, AssetStatus)
        else AssetStatus.from_string(str(target_status), asset_id=asset_id)
    )

    manifest_file_path: Optional[Path] = None
    if isinstance(project_dir_or_manifest, ManifestV2):
        manifest = project_dir_or_manifest
    else:
        p = Path(project_dir_or_manifest)
        if p.is_dir():
            manifest_file_path = p / "02_asset_manifest.json"
        else:
            manifest_file_path = p
        manifest = load_manifest(manifest_file_path, allow_migrate=True)

    # 1. Look up asset
    asset = manifest.get_asset(asset_id)
    if not asset:
        raise AssetNotFoundError(asset_id)

    # 2. Canonical Status Verification (Zero side-effects on mismatch)
    current_status = asset.status
    if current_status != expected_enum:
        raise AssetStatusMismatchError(
            asset_id=asset_id,
            actual_status=current_status.value if isinstance(current_status, AssetStatus) else str(current_status),
            expected_status=expected_enum.value,
        )

    # 3. File movement logic (if applicable)
    source_file_str = asset.processed_path or asset.source_path
    moved_file_src: Optional[Path] = None
    moved_file_dst: Optional[Path] = None

    if source_file_str and destination_path:
        src = Path(source_file_str)
        dst = Path(destination_path)
        if not src.exists():
            raise AssetFileMissingError(asset_id, str(src))

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved_file_src = src
        moved_file_dst = dst

    # 4. Manifest update & atomic save with rollback
    old_status = asset.status
    old_processed_path = asset.processed_path

    asset.status = target_enum
    if moved_file_dst:
        asset.processed_path = str(moved_file_dst)

    if manifest_file_path:
        try:
            save_manifest(manifest, manifest_file_path, atomic=True)
        except Exception as e:
            # ROLLBACK file move
            if moved_file_dst and moved_file_dst.exists() and moved_file_src and not moved_file_src.exists():
                try:
                    shutil.move(str(moved_file_dst), str(moved_file_src))
                except Exception:
                    pass
            asset.status = old_status
            asset.processed_path = old_processed_path
            raise e

    return asset
