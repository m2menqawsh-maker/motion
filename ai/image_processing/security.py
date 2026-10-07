"""
ai/image_processing/security.py
===============================
Security controls, resource bounds, and decompression bomb protection for ImageProcessingService (S28-M08).

Invariants:
- Centralized bounds: MIN_DIMENSION=1, MAX_DIMENSION=8192, MAX_TOTAL_PIXELS=33_554_432 (~32MP), MAX_FILE_BYTES=50MB.
- Strict format allowlist: PNG, JPEG, WEBP, GIF.
- Configures PIL.Image.MAX_IMAGE_PIXELS to fail-closed against decompression bombs.
- Enforces strict tenant confinement and prevents path traversal.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Set, Tuple
from PIL import Image

from ai.image_processing.errors import (
    DecompressionBombError,
    DimensionLimitExceededError,
    ImageCorruptedError,
    ImageTenantConfinementError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)

# Centralized canonical resource limits
MIN_DIMENSION: int = 1
MAX_DIMENSION: int = 8192
MAX_TOTAL_PIXELS: int = 33_554_432  # 32 Megapixels
MAX_FILE_BYTES: int = 50 * 1024 * 1024  # 50 MB
DEFAULT_PROCESSING_TIMEOUT_SECONDS: float = 30.0

# Canonical format allowlist
ALLOWED_FORMATS: Set[str] = {"PNG", "JPEG", "JPG", "WEBP", "GIF"}

# Magic byte signatures
MAGIC_BYTES = {
    "PNG": b"\x89PNG\r\n\x1a\n",
    "JPEG": b"\xff\xd8\xff",
    "WEBP": b"RIFF",  # with WEBP at offset 8
    "GIF": b"GIF8",
}

# Configure PIL decompression bomb ceiling
Image.MAX_IMAGE_PIXELS = MAX_TOTAL_PIXELS


def validate_image_payload_size(data_len: int) -> None:
    """Validates that raw image payload does not exceed MAX_FILE_BYTES."""
    if data_len <= 0:
        raise ImageCorruptedError("Image payload is zero-byte or empty.")
    if data_len > MAX_FILE_BYTES:
        raise ImageTooLargeError(size_bytes=data_len, max_bytes=MAX_FILE_BYTES)


def detect_image_format_from_magic(data: bytes) -> str:
    """Detects image format from magic byte signatures."""
    if len(data) < 12:
        raise ImageCorruptedError("Image payload is too small to contain valid headers.")

    if data.startswith(MAGIC_BYTES["PNG"]):
        return "PNG"
    if data.startswith(MAGIC_BYTES["JPEG"]):
        return "JPEG"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WEBP"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "GIF"

    raise UnsupportedImageFormatError("UNKNOWN", list(ALLOWED_FORMATS))


def validate_dimensions(width: int, height: int) -> None:
    """Validates that dimensions fall within strict canonical limits."""
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise DimensionLimitExceededError(width, height, MAX_DIMENSION, MAX_TOTAL_PIXELS)
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise DimensionLimitExceededError(width, height, MAX_DIMENSION, MAX_TOTAL_PIXELS)
    pixels = width * height
    if pixels > MAX_TOTAL_PIXELS:
        raise DimensionLimitExceededError(width, height, MAX_DIMENSION, MAX_TOTAL_PIXELS)


def safe_open_image(data: bytes) -> Image.Image:
    """
    Safely opens and verifies an image from in-memory bytes with decompression bomb protection.
    Returns the opened Image instance.
    """
    validate_image_payload_size(len(data))
    
    # Pre-check magic bytes
    fmt = detect_image_format_from_magic(data)
    if fmt not in ALLOWED_FORMATS:
        raise UnsupportedImageFormatError(fmt, list(ALLOWED_FORMATS))

    try:
        bio = io.BytesIO(data)
        img = Image.open(bio)
        # Check dimensions before decoding pixels
        w, h = img.size
        validate_dimensions(w, h)
        # Verify integrity
        img.verify()
        # Re-open after verify() because verify() invalidates the image handle for subsequent reads
        bio.seek(0)
        img = Image.open(bio)
        # Load pixels within safe limits
        img.load()
        return img
    except Image.DecompressionBombError:
        raise DecompressionBombError()
    except (DimensionLimitExceededError, UnsupportedImageFormatError, ImageTooLargeError):
        raise
    except Exception as e:
        raise ImageCorruptedError(f"Failed to decode image: {e}")


def validate_storage_key_confinement(project_id: str, storage_key: str) -> str:
    """
    Validates that a storage key is strictly confined to the authorized project prefix.
    Prevents directory traversal, absolute paths, and cross-project leakage.
    """
    if not project_id or not isinstance(project_id, str):
        raise ImageTenantConfinementError("Missing or invalid project_id.")
    if not storage_key or not isinstance(storage_key, str):
        raise ImageTenantConfinementError("Missing or invalid storage_key.")

    clean_key = storage_key.strip().replace("\\", "/").lstrip("/")
    parts = clean_key.split("/")

    # Check for traversal tokens
    for part in parts:
        if part in ("..", ".", "~") or "\x00" in part:
            raise ImageTenantConfinementError(f"Path traversal detected in storage key: '{storage_key}'")

    projects_token = "projects"
    if len(parts) >= 2 and parts[0] == projects_token:
        key_proj = parts[1]
        if key_proj != project_id:
            raise ImageTenantConfinementError(
                f"Tenant confinement violation: storage key belongs to '{key_proj}', not '{project_id}'."
            )
    elif len(parts) >= 3 and parts[0] == "workspaces":
        if len(parts) >= 4 and parts[2] == projects_token:
            key_proj = parts[3]
        else:
            key_proj = parts[2]
        if key_proj != project_id:
            raise ImageTenantConfinementError(
                f"Tenant confinement violation: storage key belongs to '{key_proj}', not '{project_id}'."
            )

    return clean_key
