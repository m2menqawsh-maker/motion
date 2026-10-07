"""
ai/image_processing/contracts.py
================================
Canonical typed request and response contracts for image operations (S28-M08).

Invariants:
- All models inherit from AIContractModel (ADR-004 DEC-06.2).
- Strict bounds on all dimensions, scale factors, thresholds, and quality parameters.
- Storage artifacts referenced exclusively via project_id and canonical storage_key.
- No arbitrary flags, no arbitrary host filesystem paths, no unconfined paths.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel


# =============================================================================
# 1. Probe Image Contracts
# =============================================================================

class ProbeImageRequest(AIContractModel):
    """Request contract for probing image properties and technical metadata."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for image to probe")
    extract_metadata: bool = Field(default=True, description="Whether to parse EXIF and metadata summary")


class ProbeImageResult(AIContractModel):
    """Result contract containing technical image probe properties."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    storage_key: str = Field(min_length=1, description="Storage key of probed image")
    format: str = Field(min_length=1, description="Image format (PNG, JPEG, WEBP, GIF)")
    width: int = Field(ge=1, description="Image pixel width")
    height: int = Field(ge=1, description="Image pixel height")
    mode: str = Field(min_length=1, description="Color mode (RGB, RGBA, L, P, CMYK)")
    has_alpha: bool = Field(description="Whether the image contains an alpha channel")
    frame_count: int = Field(ge=1, description="Total frame count (1 for static images)")
    orientation: Optional[int] = Field(default=None, ge=1, le=8, description="EXIF orientation tag if present")
    file_size_bytes: int = Field(ge=0, description="Raw file payload size in bytes")
    is_animated: bool = Field(default=False, description="Whether image contains multiple frames")
    metadata_summary: Dict[str, str] = Field(default_factory=dict, description="Sanitized metadata summary")


# =============================================================================
# 2. Resize Image Contracts
# =============================================================================

class ResizeImageRequest(AIContractModel):
    """Request contract for resizing or scaling an image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    target_width: Optional[int] = Field(default=None, ge=1, le=8192, description="Target pixel width")
    target_height: Optional[int] = Field(default=None, ge=1, le=8192, description="Target pixel height")
    scale_factor: Optional[float] = Field(default=None, gt=0.0, le=16.0, description="Optional scaling multiplier")
    fit_mode: str = Field(default="contain", description="Fit mode: contain, cover, stretch, exact")
    maintain_aspect_ratio: bool = Field(default=True, description="Whether to preserve aspect ratio when one dimension provided")
    output_format: Optional[str] = Field(default=None, description="Target format: png, jpeg, webp")
    quality: int = Field(default=95, ge=1, le=100, description="Compression quality (1-100)")

    @model_validator(mode="after")
    def validate_resize_targets(self) -> Self:
        has_dims = self.target_width is not None or self.target_height is not None
        has_scale = self.scale_factor is not None
        if not has_dims and not has_scale:
            raise ValueError("Must provide at least one of target_width, target_height, or scale_factor.")
        return self


class ResizeImageResult(AIContractModel):
    """Result contract for resized image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for resized image")
    width: int = Field(ge=1, description="Rendered image width in pixels")
    height: int = Field(ge=1, description="Rendered image height in pixels")
    format: str = Field(min_length=1, description="Output image format")
    file_size_bytes: int = Field(ge=0, description="File size of output in bytes")


# =============================================================================
# 3. Crop Image to Aspect Ratio Contracts
# =============================================================================

class CropImageRatioRequest(AIContractModel):
    """Request contract for center-cropping an image to a target aspect ratio."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    target_ratio: str = Field(min_length=3, description="Target aspect ratio string (e.g. '16:9', '9:16', '1:1', '4:5')")
    output_format: Optional[str] = Field(default=None, description="Optional target format: png, jpeg, webp")
    quality: int = Field(default=95, ge=1, le=100, description="Compression quality (1-100)")

    @model_validator(mode="after")
    def validate_ratio_format(self) -> Self:
        parts = self.target_ratio.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid target_ratio '{self.target_ratio}'. Format must be 'W:H' (e.g. '16:9').")
        try:
            w, h = float(parts[0]), float(parts[1])
            if w <= 0 or h <= 0:
                raise ValueError()
        except ValueError:
            raise ValueError(f"Invalid target_ratio '{self.target_ratio}'. Ratio numbers must be positive.")
        return self


class CropImageRatioResult(AIContractModel):
    """Result contract for aspect-ratio cropped image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for cropped image")
    width: int = Field(ge=1, description="Rendered image width")
    height: int = Field(ge=1, description="Rendered image height")
    applied_ratio: str = Field(min_length=1, description="Applied aspect ratio string")
    format: str = Field(min_length=1, description="Output format")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")


# =============================================================================
# 4. Auto Crop Content Borders Contracts
# =============================================================================

class AutoCropImageRequest(AIContractModel):
    """Request contract for auto-detecting and stripping solid/transparent borders."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    background_color: str = Field(default="auto", description="Background mode: auto, transparent, white, black")
    background_threshold: int = Field(default=10, ge=0, le=255, description="Color difference tolerance (0-255)")
    padding_ratio: float = Field(default=0.0, ge=0.0, le=0.5, description="Safety padding ratio around detected content")
    output_format: Optional[str] = Field(default=None, description="Optional target format")
    quality: int = Field(default=95, ge=1, le=100, description="Compression quality (1-100)")


class AutoCropImageResult(AIContractModel):
    """Result contract for auto-cropped image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for auto-cropped image")
    original_width: int = Field(ge=1, description="Original image width")
    original_height: int = Field(ge=1, description="Original image height")
    output_width: int = Field(ge=1, description="Cropped output width")
    output_height: int = Field(ge=1, description="Cropped output height")
    cropped_box: List[int] = Field(min_length=4, max_length=4, description="Bounding box [left, top, right, bottom]")
    format: str = Field(min_length=1, description="Output format")
    file_size_bytes: int = Field(ge=0, description="Output file size in bytes")


# =============================================================================
# 5. Convert Image Format Contracts
# =============================================================================

class ConvertImageRequest(AIContractModel):
    """Request contract for converting image format with safe alpha handling."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    target_format: str = Field(min_length=3, description="Target format (PNG, JPEG, WEBP)")
    quality: int = Field(default=95, ge=1, le=100, description="Compression quality (1-100)")
    background_color: Optional[str] = Field(default="#ffffff", description="Background color for RGBA -> RGB conversions")
    strip_metadata: bool = Field(default=False, description="Whether to strip EXIF and metadata")

    @model_validator(mode="after")
    def validate_target_format(self) -> Self:
        clean = self.target_format.strip().upper()
        if clean not in ("PNG", "JPEG", "JPG", "WEBP"):
            raise ValueError(f"Target format '{self.target_format}' is not supported. Allowed: PNG, JPEG, WEBP.")
        return self


class ConvertImageResult(AIContractModel):
    """Result contract for converted image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for converted image")
    source_format: str = Field(min_length=1, description="Original image format")
    target_format: str = Field(min_length=1, description="Converted image format")
    width: int = Field(ge=1, description="Image pixel width")
    height: int = Field(ge=1, description="Image pixel height")
    file_size_bytes: int = Field(ge=0, description="Output payload size in bytes")


# =============================================================================
# 6. Optimize Image Contracts
# =============================================================================

class OptimizeImageRequest(AIContractModel):
    """Request contract for recompressing and optimizing an image."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    quality: int = Field(default=85, ge=1, le=100, description="Target quality factor (1-100)")
    strip_metadata: bool = Field(default=True, description="Whether to strip GPS, camera, and comments metadata")
    max_width: Optional[int] = Field(default=None, ge=1, le=8192, description="Optional bounding width constraint")
    max_height: Optional[int] = Field(default=None, ge=1, le=8192, description="Optional bounding height constraint")


class OptimizeImageResult(AIContractModel):
    """Result contract for optimized image with size reduction metrics."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for optimized image")
    input_bytes: int = Field(ge=0, description="Original image file size in bytes")
    output_bytes: int = Field(ge=0, description="Optimized image file size in bytes")
    compression_ratio: float = Field(ge=0.0, description="Ratio of output_bytes / input_bytes")
    format: str = Field(min_length=1, description="Image format")
    width: int = Field(ge=1, description="Final image width")
    height: int = Field(ge=1, description="Final image height")


# =============================================================================
# 7. Prepare Image Asset Contracts
# =============================================================================

class PrepareImageAssetRequest(AIContractModel):
    """
    Request contract orchestrating full asset ingestion: orientation normalization,
    optional resizing, optimization, storage persistence, and Manifest v2 registration.
    """
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    asset_id: Optional[str] = Field(default=None, description="Optional canonical asset ID to assign")
    normalize_orientation: bool = Field(default=True, description="Whether to transpose image based on EXIF orientation")
    target_format: Optional[str] = Field(default=None, description="Optional format conversion (PNG, JPEG, WEBP)")
    max_width: Optional[int] = Field(default=None, ge=1, le=8192, description="Max width bound")
    max_height: Optional[int] = Field(default=None, ge=1, le=8192, description="Max height bound")
    generate_thumbnail: bool = Field(default=True, description="Whether to generate companion thumbnail")
    thumbnail_size: int = Field(default=256, ge=32, le=1024, description="Thumbnail square dimension bound")
    quality: int = Field(default=90, ge=1, le=100, description="Output quality")


class PrepareImageAssetResult(AIContractModel):
    """Result contract for prepared and registered image asset."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    asset_id: str = Field(min_length=1, description="Registered canonical asset ID")
    primary_storage_key: str = Field(min_length=1, description="StorageService key for primary asset")
    thumbnail_storage_key: Optional[str] = Field(default=None, description="StorageService key for thumbnail")
    width: int = Field(ge=1, description="Primary asset width")
    height: int = Field(ge=1, description="Primary asset height")
    format: str = Field(min_length=1, description="Primary asset format")
    file_size_bytes: int = Field(ge=0, description="Primary asset file size in bytes")
    manifest_registered: bool = Field(default=True, description="Whether registered into 02_asset_manifest.json")


# =============================================================================
# 8. Thumbnail Generation Contracts
# =============================================================================

class ThumbnailRequest(AIContractModel):
    """Request contract for generating deterministic image thumbnails."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    image_storage_key: str = Field(min_length=1, description="StorageService key for source image")
    width: int = Field(default=256, ge=16, le=1024, description="Target thumbnail width")
    height: int = Field(default=256, ge=16, le=1024, description="Target thumbnail height")
    fit_mode: str = Field(default="contain", description="Fit mode: contain, cover, exact")
    output_format: str = Field(default="webp", description="Output format: webp, png, jpeg")
    quality: int = Field(default=85, ge=1, le=100, description="Quality factor (1-100)")


class ThumbnailResult(AIContractModel):
    """Result contract for generated thumbnail."""
    project_id: str = Field(min_length=1, description="Project context identifier")
    output_storage_key: str = Field(min_length=1, description="StorageService key for thumbnail")
    width: int = Field(ge=1, description="Thumbnail width in pixels")
    height: int = Field(ge=1, description="Thumbnail height in pixels")
    format: str = Field(min_length=1, description="Thumbnail image format")
    file_size_bytes: int = Field(ge=0, description="Thumbnail file size in bytes")


# =============================================================================
# Input/Output Contract Aliases
# =============================================================================
ProbeImageInput = ProbeImageRequest
ProbeImageOutput = ProbeImageResult
ResizeImageInput = ResizeImageRequest
ResizeImageOutput = ResizeImageResult
CropImageRatioInput = CropImageRatioRequest
CropImageRatioOutput = CropImageRatioResult
AutoCropImageInput = AutoCropImageRequest
AutoCropImageOutput = AutoCropImageResult
ConvertImageInput = ConvertImageRequest
ConvertImageOutput = ConvertImageResult
OptimizeImageInput = OptimizeImageRequest
OptimizeImageOutput = OptimizeImageResult
PrepareImageAssetInput = PrepareImageAssetRequest
PrepareImageAssetOutput = PrepareImageAssetResult
ThumbnailInput = ThumbnailRequest
ThumbnailOutput = ThumbnailResult

