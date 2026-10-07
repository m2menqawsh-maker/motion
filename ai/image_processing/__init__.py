"""
ai/image_processing/__init__.py
==============================
Canonical Image Processing Subsystem (S28-M08).
"""

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
    DecompressionBombError,
    DimensionLimitExceededError,
    ImageCorruptedError,
    ImageProcessingError,
    ImageTenantConfinementError,
    ImageTooLargeError,
    InvalidImageRequestError,
    OutputValidationError,
    UnsupportedImageFormatError,
)
from ai.image_processing.adapter import PillowImageAdapter
from ai.image_processing.cache import ImageCacheManager, PROCESSOR_VERSION, build_cache_key
from ai.image_processing.security import (
    ALLOWED_FORMATS,
    DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    MAX_DIMENSION,
    MAX_FILE_BYTES,
    MAX_TOTAL_PIXELS,
    MIN_DIMENSION,
    detect_image_format_from_magic,
    safe_open_image,
    validate_dimensions,
    validate_image_payload_size,
    validate_storage_key_confinement,
)
from ai.image_processing.validator import validate_image_output
from ai.image_processing.service import (
    ImageProcessingService,
    get_image_processing_service,
)

__all__ = [
    # Contracts
    "ProbeImageRequest",
    "ProbeImageResult",
    "ResizeImageRequest",
    "ResizeImageResult",
    "CropImageRatioRequest",
    "CropImageRatioResult",
    "AutoCropImageRequest",
    "AutoCropImageResult",
    "ConvertImageRequest",
    "ConvertImageResult",
    "OptimizeImageRequest",
    "OptimizeImageResult",
    "PrepareImageAssetRequest",
    "PrepareImageAssetResult",
    "ThumbnailRequest",
    "ThumbnailResult",
    # Errors
    "ImageProcessingError",
    "InvalidImageRequestError",
    "UnsupportedImageFormatError",
    "ImageCorruptedError",
    "ImageTooLargeError",
    "DimensionLimitExceededError",
    "DecompressionBombError",
    "OutputValidationError",
    "ImageTenantConfinementError",
    # Core Components
    "PillowImageAdapter",
    "ImageCacheManager",
    "PROCESSOR_VERSION",
    "build_cache_key",
    "ImageProcessingService",
    "get_image_processing_service",
    # Security & Validation
    "ALLOWED_FORMATS",
    "MIN_DIMENSION",
    "MAX_DIMENSION",
    "MAX_TOTAL_PIXELS",
    "MAX_FILE_BYTES",
    "DEFAULT_PROCESSING_TIMEOUT_SECONDS",
    "detect_image_format_from_magic",
    "safe_open_image",
    "validate_dimensions",
    "validate_image_payload_size",
    "validate_storage_key_confinement",
    "validate_image_output",
]
