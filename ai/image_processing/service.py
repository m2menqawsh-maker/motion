"""
ai/image_processing/service.py
==============================
Canonical ImageProcessingService (S28-M08).

Invariants:
- Sole canonical operation authority for all image transformations.
- StorageService is the sole byte persistence authority.
- AssetService is the sole asset domain/manifest registration authority.
- Enforces strict tenant confinement on all inputs and outputs.
- Employs content-addressed caching with deterministic normalization and processor versioning.
- Performs rigorous output validation before publishing to storage or registering assets.
- Transactional atomicity: storage failures fail closed; no corrupt or orphan asset records.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ai.image_processing.adapter import PillowImageAdapter
from ai.image_processing.cache import ImageCacheManager, PROCESSOR_VERSION
from ai.image_processing.contracts import (
    AutoCropImageRequest,
    AutoCropImageResult,
    ConvertImageRequest,
    ConvertImageResult,
    CropImageRatioRequest,
    CropImageRatioResult,
    OptimizeImageRequest,
    OptimizeImageResult,
    PrepareImageAssetRequest,
    PrepareImageAssetResult,
    ProbeImageRequest,
    ProbeImageResult,
    ResizeImageRequest,
    ResizeImageResult,
    ThumbnailRequest,
    ThumbnailResult,
)
from ai.image_processing.errors import (
    ImageProcessingError,
    ImageTenantConfinementError,
    OutputValidationError,
)
from ai.image_processing.security import (
    detect_image_format_from_magic,
    validate_storage_key_confinement,
)
from ai.image_processing.validator import validate_image_output
from api.services.asset_service import AssetService
from scripts.core.storage.storage_service import StorageService, get_storage_service

logger = logging.getLogger("ai.image_processing.service")


class ImageProcessingService:
    """
    Authoritative service orchestrating typed, tenant-safe image processing,
    content-addressed caching, durable storage, and canonical asset lifecycle.
    """

    def __init__(
        self,
        storage: Optional[StorageService] = None,
        asset_service: Optional[Any] = None,
        processor_version: str = PROCESSOR_VERSION,
    ) -> None:
        self.storage: StorageService = storage or get_storage_service()
        self.asset_service = asset_service or AssetService
        self.cache: ImageCacheManager = ImageCacheManager(self.storage, processor_version=processor_version)

    def _read_source_bytes(self, project_id: str, storage_key: str) -> bytes:
        """Reads and validates source bytes from StorageService within project confinement."""
        confined_key = validate_storage_key_confinement(project_id, storage_key)
        if not self.storage.exists(confined_key):
            raise ImageProcessingError(
                f"Source image storage object not found: '{confined_key}'.",
                code="STORAGE_OBJECT_NOT_FOUND",
            )
        data = self.storage.get(confined_key)
        if not data or len(data) == 0:
            raise ImageProcessingError(
                f"Source image storage object is empty: '{confined_key}'.",
                code="EMPTY_SOURCE_PAYLOAD",
            )
        return data

    def probe_image(self, request: ProbeImageRequest) -> ProbeImageResult:
        """
        Read-only probe extracting technical image properties and metadata.
        Does not mutate storage or state.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        props = PillowImageAdapter.probe(data, extract_metadata=request.extract_metadata)

        return ProbeImageResult(
            project_id=request.project_id,
            storage_key=request.image_storage_key,
            format=props["format"],
            width=props["width"],
            height=props["height"],
            mode=props["mode"],
            has_alpha=props["has_alpha"],
            frame_count=props["frame_count"],
            orientation=props["orientation"],
            file_size_bytes=props["file_size_bytes"],
            is_animated=props["is_animated"],
            metadata_summary=props["metadata_summary"],
        )

    def resize_image(self, request: ResizeImageRequest) -> ResizeImageResult:
        """
        Resizes an image according to specified dimensions, fit mode, and quality.
        Employs content-addressed caching and output validation before publication.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        target_ext = (request.output_format or "png").lower()

        # Check cache
        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            return ResizeImageResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                width=w,
                height=h,
                format=fmt,
                file_size_bytes=len(out_bytes),
            )

        # Process
        out_bytes, fmt, w, h = PillowImageAdapter.resize(
            data=data,
            target_width=request.target_width,
            target_height=request.target_height,
            scale_factor=request.scale_factor,
            fit_mode=request.fit_mode,
            maintain_aspect_ratio=request.maintain_aspect_ratio,
            output_format=request.output_format,
            quality=request.quality,
        )

        # Validate
        validate_image_output(out_bytes, expected_format=fmt, expected_width=w, expected_height=h)

        # Persist to cache & storage
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, fmt.lower())

        return ResizeImageResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            width=w,
            height=h,
            format=fmt,
            file_size_bytes=len(out_bytes),
        )

    def crop_image_to_ratio(self, request: CropImageRatioRequest) -> CropImageRatioResult:
        """
        Center-crops an image to match a target aspect ratio.
        Employs content-addressed caching and output validation.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        target_ext = (request.output_format or "png").lower()

        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            return CropImageRatioResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                width=w,
                height=h,
                applied_ratio=request.target_ratio,
                format=fmt,
                file_size_bytes=len(out_bytes),
            )

        out_bytes, fmt, w, h, ratio_str = PillowImageAdapter.crop_to_ratio(
            data=data,
            target_ratio=request.target_ratio,
            output_format=request.output_format,
            quality=request.quality,
        )

        validate_image_output(out_bytes, expected_format=fmt, expected_width=w, expected_height=h)
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, fmt.lower())

        return CropImageRatioResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            width=w,
            height=h,
            applied_ratio=ratio_str,
            format=fmt,
            file_size_bytes=len(out_bytes),
        )

    def auto_crop_image(self, request: AutoCropImageRequest) -> AutoCropImageResult:
        """
        Auto-detects and strips outer solid or transparent borders.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        target_ext = (request.output_format or "png").lower()

        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            orig_props = PillowImageAdapter.probe(data, extract_metadata=False)
            return AutoCropImageResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                original_width=orig_props["width"],
                original_height=orig_props["height"],
                output_width=w,
                output_height=h,
                cropped_box=[0, 0, w, h],
                format=fmt,
                file_size_bytes=len(out_bytes),
            )

        out_bytes, fmt, orig_w, orig_h, out_w, out_h, bbox = PillowImageAdapter.auto_crop_content(
            data=data,
            background_color=request.background_color,
            background_threshold=request.background_threshold,
            padding_ratio=request.padding_ratio,
            output_format=request.output_format,
            quality=request.quality,
        )

        validate_image_output(out_bytes, expected_format=fmt, expected_width=out_w, expected_height=out_h)
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, fmt.lower())

        return AutoCropImageResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            original_width=orig_w,
            original_height=orig_h,
            output_width=out_w,
            output_height=out_h,
            cropped_box=bbox,
            format=fmt,
            file_size_bytes=len(out_bytes),
        )

    def convert_image(self, request: ConvertImageRequest) -> ConvertImageResult:
        """
        Converts an image from one format to another with safe alpha handling.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        target_ext = request.target_format.lower()

        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            orig_props = PillowImageAdapter.probe(data, extract_metadata=False)
            return ConvertImageResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                source_format=orig_props["format"],
                target_format=fmt,
                width=w,
                height=h,
                file_size_bytes=len(out_bytes),
            )

        out_bytes, src_fmt, tgt_fmt, w, h = PillowImageAdapter.convert(
            data=data,
            target_format=request.target_format,
            quality=request.quality,
            background_color=request.background_color,
            strip_metadata=request.strip_metadata,
        )

        validate_image_output(out_bytes, expected_format=tgt_fmt, expected_width=w, expected_height=h)
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, tgt_fmt.lower())

        return ConvertImageResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            source_format=src_fmt,
            target_format=tgt_fmt,
            width=w,
            height=h,
            file_size_bytes=len(out_bytes),
        )

    def optimize_image(self, request: OptimizeImageRequest) -> OptimizeImageResult:
        """
        Recompresses an image with quality tuning and metadata stripping, measuring bytes saved.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        orig_props = PillowImageAdapter.probe(data, extract_metadata=False)
        target_ext = orig_props["format"].lower()

        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            ratio = len(out_bytes) / len(data) if len(data) > 0 else 1.0
            return OptimizeImageResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                input_bytes=len(data),
                output_bytes=len(out_bytes),
                compression_ratio=round(ratio, 4),
                format=fmt,
                width=w,
                height=h,
            )

        out_bytes, fmt, w, h = PillowImageAdapter.optimize(
            data=data,
            quality=request.quality,
            strip_metadata=request.strip_metadata,
            max_width=request.max_width,
            max_height=request.max_height,
        )

        validate_image_output(out_bytes, expected_format=fmt, expected_width=w, expected_height=h)
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, fmt.lower())
        ratio = len(out_bytes) / len(data) if len(data) > 0 else 1.0

        return OptimizeImageResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            input_bytes=len(data),
            output_bytes=len(out_bytes),
            compression_ratio=round(ratio, 4),
            format=fmt,
            width=w,
            height=h,
        )

    def generate_thumbnail(self, request: ThumbnailRequest) -> ThumbnailResult:
        """
        Generates a deterministic thumbnail for an image.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        spec = request.model_dump()
        target_ext = request.output_format.lower()

        cached = self.cache.lookup(request.project_id, data, spec, target_ext)
        if cached:
            cache_key, out_bytes = cached
            fmt, w, h = validate_image_output(out_bytes)
            return ThumbnailResult(
                project_id=request.project_id,
                output_storage_key=cache_key,
                width=w,
                height=h,
                format=fmt,
                file_size_bytes=len(out_bytes),
            )

        out_bytes, fmt, w, h = PillowImageAdapter.generate_thumbnail(
            data=data,
            width=request.width,
            height=request.height,
            fit_mode=request.fit_mode,
            output_format=request.output_format,
            quality=request.quality,
        )

        validate_image_output(out_bytes, expected_format=fmt, expected_width=w, expected_height=h)
        out_storage_key = self.cache.store(request.project_id, data, spec, out_bytes, fmt.lower())

        return ThumbnailResult(
            project_id=request.project_id,
            output_storage_key=out_storage_key,
            width=w,
            height=h,
            format=fmt,
            file_size_bytes=len(out_bytes),
        )

    def prepare_image_asset(self, request: PrepareImageAssetRequest) -> PrepareImageAssetResult:
        """
        Orchestrates full asset preparation:
        1. Orientation normalization.
        2. Format conversion if requested.
        3. Dimension bounding / resizing if requested.
        4. Optimization.
        5. Publishing primary asset to StorageService.
        6. Optional companion thumbnail generation and publication.
        7. Registration in AssetService with provenance.
        """
        data = self._read_source_bytes(request.project_id, request.image_storage_key)
        props = PillowImageAdapter.probe(data, extract_metadata=True)

        # 1-4. Normalize & process primary
        out_bytes, fmt, w, h = PillowImageAdapter.resize(
            data=data,
            target_width=request.max_width,
            target_height=request.max_height,
            fit_mode="contain",
            maintain_aspect_ratio=True,
            output_format=request.target_format or props["format"],
            quality=request.quality,
        )
        validate_image_output(out_bytes, expected_format=fmt, expected_width=w, expected_height=h)

        asset_id = request.asset_id or f"ast_img_{uuid.uuid4().hex[:10]}"
        ext = fmt.lower()
        if ext == "jpeg":
            ext = "jpg"
        primary_filename = f"{asset_id}.{ext}"
        primary_storage_key = validate_storage_key_confinement(
            request.project_id,
            "/".join(["projects", request.project_id, "assets", "ready", primary_filename]),
        )

        # 5. Persist primary asset to StorageService
        try:
            self.storage.put(primary_storage_key, out_bytes)
        except Exception as e:
            raise ImageProcessingError(
                f"Failed to persist primary image asset to StorageService: {e}",
                code="STORAGE_ERROR",
            )

        # 6. Optional Thumbnail
        thumb_storage_key = None
        if request.generate_thumbnail:
            try:
                thumb_bytes, thumb_fmt, tw, th = PillowImageAdapter.generate_thumbnail(
                    data=out_bytes,
                    width=request.thumbnail_size,
                    height=request.thumbnail_size,
                    fit_mode="contain",
                    output_format="webp",
                    quality=80,
                )
                validate_image_output(thumb_bytes, expected_format=thumb_fmt, expected_width=tw, expected_height=th)
                thumb_storage_key = validate_storage_key_confinement(
                    request.project_id,
                    "/".join(["projects", request.project_id, "assets", "cache", f"{asset_id}_thumb.webp"]),
                )
                self.storage.put(thumb_storage_key, thumb_bytes)
            except Exception as e:
                logger.warning(f"Companion thumbnail generation failed for asset '{asset_id}': {e}")
                thumb_storage_key = None

        # 7. Register in AssetService
        registered = False
        try:
            self.asset_service.upload_asset(
                project_id=request.project_id,
                content=out_bytes,
                filename=primary_filename,
                asset_id=asset_id,
                kind="IMAGE",
                status="ready",
            )
            registered = True
        except Exception as e:
            logger.warning(f"AssetService registration failed for asset '{asset_id}': {e}")
            # Storage cleanup if registration failed to prevent orphan payload
            try:
                self.storage.delete(primary_storage_key)
                if thumb_storage_key:
                    self.storage.delete(thumb_storage_key)
            except Exception:
                pass
            raise ImageProcessingError(
                f"Failed to register prepared asset with AssetService: {e}",
                code="ASSET_REGISTRATION_FAILED",
            )

        return PrepareImageAssetResult(
            project_id=request.project_id,
            asset_id=asset_id,
            primary_storage_key=primary_storage_key,
            thumbnail_storage_key=thumb_storage_key,
            width=w,
            height=h,
            format=fmt,
            file_size_bytes=len(out_bytes),
            manifest_registered=registered,
        )


_default_image_service: Optional[ImageProcessingService] = None


def get_image_processing_service() -> ImageProcessingService:
    """Returns singleton canonical ImageProcessingService instance."""
    global _default_image_service
    if _default_image_service is None:
        _default_image_service = ImageProcessingService()
    return _default_image_service
