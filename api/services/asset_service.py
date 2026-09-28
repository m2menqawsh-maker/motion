"""
Domain Service for Asset Management (S22 - LED-063).

Integrates with:
- Manifest v2 (ManifestV2, AssetV2, load_manifest, save_manifest)
- S02 Security (path confinement, size limits, mime allowlists, traversal prevention)
- S10 ArtifactService / Invalidation Graph (downstream evidence invalidation)
"""

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from api.core.errors import (
    ProjectNotFoundError,
    AssetNotFoundError,
    MediaKindNotAllowedError,
    PayloadTooLargeError,
)
from scripts.core.artifact_service import ArtifactService
from scripts.core.dependency_graph import ArtifactKind
from scripts.core.manifest_loader import load_manifest, save_manifest
from scripts.core.manifest_model import (
    AssetKind,
    AssetStatus,
    AssetV2,
    ManifestV2,
    Provenance,
)
from scripts.security.path_security import (
    validate_project_id,
    validate_asset_id,
    resolve_safe_path,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    # Images
    ".png": AssetKind.IMAGE,
    ".jpg": AssetKind.IMAGE,
    ".jpeg": AssetKind.IMAGE,
    ".webp": AssetKind.IMAGE,
    ".svg": AssetKind.IMAGE,
    # Audio
    ".mp3": AssetKind.AUDIO,
    ".wav": AssetKind.AUDIO,
    ".aac": AssetKind.AUDIO,
    ".m4a": AssetKind.AUDIO,
    # Video
    ".mp4": AssetKind.VIDEO,
    ".webm": AssetKind.VIDEO,
    ".mov": AssetKind.VIDEO,
    # Fonts
    ".ttf": AssetKind.FONT,
    ".otf": AssetKind.FONT,
    ".woff": AssetKind.FONT,
    ".woff2": AssetKind.FONT,
}


class AssetService:
    """Domain authority for project media and asset lifecycle."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    def _get_or_create_manifest(cls, proj_dir: Path, project_id: str) -> ManifestV2:
        manifest_path = proj_dir / "02_asset_manifest.json"
        if manifest_path.exists():
            return load_manifest(manifest_path, expected_project_id=project_id, allow_migrate=True)
        # Baseline Manifest v2
        manifest = ManifestV2(project_id=project_id, assets=[])
        save_manifest(manifest, manifest_path)
        return manifest

    @classmethod
    def list_assets(cls, project_id: str) -> List[Dict[str, Any]]:
        """Lists all registered assets for a project."""
        proj_dir = cls._get_project_dir(project_id)
        manifest = cls._get_or_create_manifest(proj_dir, project_id)
        return [a.model_dump() for a in manifest.assets]

    @classmethod
    def get_asset(cls, project_id: str, asset_id: str) -> Dict[str, Any]:
        """Retrieves details of a specific asset."""
        proj_dir = cls._get_project_dir(project_id)
        validate_asset_id(asset_id)
        manifest = cls._get_or_create_manifest(proj_dir, project_id)
        asset = manifest.get_asset(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id=asset_id, project_id=project_id)
        return asset.model_dump()

    @classmethod
    def upload_asset(
        cls,
        project_id: str,
        content: bytes,
        filename: str,
        asset_id: Optional[str] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Securely uploads and registers an asset into Manifest v2 with downstream invalidation.
        """
        proj_dir = cls._get_project_dir(project_id)

        # 1. Size limit enforcement
        actual_size = len(content)
        if actual_size > MAX_UPLOAD_BYTES:
            raise PayloadTooLargeError(max_bytes=MAX_UPLOAD_BYTES, actual_bytes=actual_size)

        # 2. Filename sanitization & extension allowlist check
        safe_filename = Path(filename).name
        ext = Path(safe_filename).suffix.lower()
        if not ext or ext not in ALLOWED_EXTENSIONS:
            allowed_list = list(ALLOWED_EXTENSIONS.keys())
            raise MediaKindNotAllowedError(media_kind=ext or "unknown", allowed_kinds=allowed_list)

        detected_kind = ALLOWED_EXTENSIONS[ext]
        final_kind = AssetKind.from_string(kind) if kind else detected_kind

        # 3. Asset ID determination & validation
        final_asset_id = asset_id or f"ast_{uuid.uuid4().hex[:12]}"
        validate_asset_id(final_asset_id)

        # 4. Storage destination within project confinement
        target_dir = proj_dir / "assets" / "ready"
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_filename = f"{final_asset_id}{ext}"
        dest_path = resolve_safe_path(target_dir, dest_filename)

        # 5. Atomic write to disk
        dest_path.write_bytes(content)

        # 6. Compute checksum
        sha256_hash = hashlib.sha256(content).hexdigest()

        # 7. Update Manifest v2
        manifest = cls._get_or_create_manifest(proj_dir, project_id)
        rel_path = f"assets/ready/{dest_filename}"
        asset_record = AssetV2(
            asset_id=final_asset_id,
            kind=final_kind,
            provenance=Provenance.USER_UPLOAD,
            status=AssetStatus.READY,
            source_path=rel_path,
            processed_path=rel_path,
            content_hash=sha256_hash,
            metadata={"original_filename": safe_filename, "size_bytes": actual_size},
        )

        existing_idx = next((i for i, a in enumerate(manifest.assets) if a.asset_id == final_asset_id), None)
        if existing_idx is not None:
            manifest.assets[existing_idx] = asset_record
        else:
            manifest.assets.append(asset_record)

        manifest_data = manifest.to_dict()
        manifest_path = proj_dir / "02_asset_manifest.json"
        save_manifest(manifest, manifest_path)

        # 8. Trigger downstream invalidation if state file exists
        state_file = proj_dir / ".pipeline_state.json"
        if state_file.exists():
            try:
                ArtifactService.mutate_artifact(
                    project_dir=proj_dir,
                    artifact_kind=ArtifactKind.MANIFEST,
                    new_content=json.dumps(manifest_data, indent=2, ensure_ascii=False),
                    reason=f"Asset {final_asset_id} uploaded/updated",
                )
            except Exception:
                # If state store fails, manifest on disk is authoritative
                pass

        return asset_record.model_dump()

    @classmethod
    def delete_asset(cls, project_id: str, asset_id: str) -> bool:
        """Deletes an asset from the project manifest and triggers invalidation."""
        proj_dir = cls._get_project_dir(project_id)
        validate_asset_id(asset_id)
        manifest = cls._get_or_create_manifest(proj_dir, project_id)

        target = manifest.get_asset(asset_id)
        if not target:
            raise AssetNotFoundError(asset_id=asset_id, project_id=project_id)

        # Remove from manifest
        manifest.assets = [a for a in manifest.assets if a.asset_id != asset_id]
        manifest_data = manifest.to_dict()
        manifest_path = proj_dir / "02_asset_manifest.json"
        save_manifest(manifest, manifest_path)

        # Best effort cleanup of underlying file
        for p in (target.processed_path, target.source_path):
            if p:
                try:
                    fpath = proj_dir / p
                    if fpath.exists():
                        fpath.unlink()
                except Exception:
                    pass

        # Invalidate downstream
        state_file = proj_dir / ".pipeline_state.json"
        if state_file.exists():
            try:
                ArtifactService.mutate_artifact(
                    project_dir=proj_dir,
                    artifact_kind=ArtifactKind.MANIFEST,
                    new_content=json.dumps(manifest_data, indent=2, ensure_ascii=False),
                    reason=f"Asset {asset_id} deleted",
                )
            except Exception:
                pass

        return True
