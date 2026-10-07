"""
ai/image_processing/errors.py
=============================
Canonical error taxonomy for ImageProcessingService (S28-M08).

Invariants:
- All exceptions derive from ImageProcessingError.
- Error messages are sanitized and safe: no raw host filesystem paths, no credentials, no internal stack leaks.
- Structured details map cleanly to AIError codes for ToolGateway propagation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from ai.contracts.errors import AIError, AIErrorCode


class ImageProcessingError(Exception):
    """Base exception for all image processing failures."""
    def __init__(self, message: str, code: str = "IMAGE_PROCESSING_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_ai_error(self) -> AIError:
        """Converts domain exception to canonical AIError."""
        return AIError(
            code=AIErrorCode.MEDIA_PROCESSING_FAILED,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class InvalidImageRequestError(ImageProcessingError):
    """Raised when an image request contains invalid or contradictory parameters."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="INVALID_IMAGE_REQUEST", details=details)

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.INVALID_PARAMETER,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class UnsupportedImageFormatError(ImageProcessingError):
    """Raised when an image format is not in the canonical allowlist."""
    def __init__(self, format_name: str, allowed: Optional[list] = None):
        msg = f"Image format '{format_name}' is not supported. Allowed formats: {allowed or ['PNG', 'JPEG', 'WEBP']}"
        super().__init__(msg, code="UNSUPPORTED_IMAGE_FORMAT", details={"format": format_name, "allowed": allowed})

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.UNSUPPORTED_MEDIA_TYPE,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class ImageCorruptedError(ImageProcessingError):
    """Raised when image bytes cannot be decoded or image header/payload is corrupt."""
    def __init__(self, message: str = "Image bytes are corrupted or header is invalid", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="IMAGE_CORRUPTED", details=details)

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.MEDIA_DECODE_FAILED,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class ImageTooLargeError(ImageProcessingError):
    """Raised when image file size exceeds allowed byte threshold."""
    def __init__(self, size_bytes: int, max_bytes: int):
        msg = f"Image payload ({size_bytes} bytes) exceeds maximum allowable size ({max_bytes} bytes)."
        super().__init__(msg, code="IMAGE_TOO_LARGE", details={"size_bytes": size_bytes, "max_bytes": max_bytes})

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.RESOURCE_EXHAUSTED,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class DimensionLimitExceededError(ImageProcessingError):
    """Raised when image dimensions exceed bounded limits (decompression bomb protection)."""
    def __init__(self, width: int, height: int, max_dim: int, max_pixels: int):
        msg = f"Image dimensions {width}x{height} ({width * height} pixels) exceed limits (max dimension {max_dim}, max pixels {max_pixels})."
        super().__init__(
            msg,
            code="DIMENSION_LIMIT_EXCEEDED",
            details={"width": width, "height": height, "pixels": width * height, "max_dimension": max_dim, "max_pixels": max_pixels},
        )

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.RESOURCE_EXHAUSTED,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class DecompressionBombError(ImageProcessingError):
    """Raised when a decompression bomb is detected prior to full decode."""
    def __init__(self, message: str = "Decompression bomb risk detected; image decode aborted for safety."):
        super().__init__(message, code="DECOMPRESSION_BOMB_DETECTED")

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.SECURITY_POLICY_VIOLATION,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code},
        )


class OutputValidationError(ImageProcessingError):
    """Raised when processed image output fails post-processing validation."""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Processed image output validation failed: {reason}", code="OUTPUT_VALIDATION_FAILED", details=details)

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.MEDIA_PROCESSING_FAILED,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )


class ImageTenantConfinementError(ImageProcessingError):
    """Raised when an image access or output violates tenant / workspace boundaries."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="TENANT_CONFINEMENT_VIOLATION", details=details)

    def to_ai_error(self) -> AIError:
        return AIError(
            code=AIErrorCode.TENANT_ISOLATION_VIOLATION,
            message=self.message,
            category="IMAGE_PROCESSING",
            retryable=False,
            details={"error_code": self.code, **self.details},
        )
