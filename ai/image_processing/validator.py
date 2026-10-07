"""
ai/image_processing/validator.py
================================
Validation logic for image inputs and outputs (S28-M08).

Invariants:
- Validates output non-empty, valid magic bytes, valid decodability.
- Validates that dimensions and format match expected operation semantics.
- Fails closed if output cannot be decoded or exceeds resource bounds.
"""

from __future__ import annotations

import io
from typing import Optional, Set
from PIL import Image

from ai.image_processing.errors import OutputValidationError
from ai.image_processing.security import (
    ALLOWED_FORMATS,
    MAX_DIMENSION,
    MAX_TOTAL_PIXELS,
    MIN_DIMENSION,
    detect_image_format_from_magic,
    safe_open_image,
    validate_dimensions,
)


def validate_image_output(
    data: bytes,
    expected_format: Optional[str] = None,
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
    tolerance: int = 2,
) -> Tuple[str, int, int]:
    """
    Validates processed image output before publication to StorageService.
    
    Checks:
    1. Output is non-empty.
    2. Magic bytes match expected format (or an allowed format).
    3. Payload can be safely decoded without memory explosion.
    4. Decoded dimensions match expected bounds within optional tolerance.
    
    Returns:
        (format, width, height)
    """
    if not data or len(data) == 0:
        raise OutputValidationError("Output image byte payload is empty.")

    # 1. Magic byte verification
    try:
        detected_fmt = detect_image_format_from_magic(data)
    except Exception as e:
        raise OutputValidationError(f"Invalid image output header/magic: {e}")

    if expected_format:
        clean_expected = expected_format.strip().upper()
        if clean_expected == "JPG":
            clean_expected = "JPEG"
        if detected_fmt != clean_expected:
            raise OutputValidationError(
                f"Output format mismatch: detected '{detected_fmt}', expected '{clean_expected}'."
            )

    # 2. Safe decode verification
    try:
        img = safe_open_image(data)
    except Exception as e:
        raise OutputValidationError(f"Output image decode failed: {e}")

    w, h = img.size
    validate_dimensions(w, h)

    # 3. Dimension semantic verification
    if expected_width is not None and abs(w - expected_width) > tolerance:
        raise OutputValidationError(
            f"Output width {w} deviates from expected {expected_width} (tolerance {tolerance})."
        )
    if expected_height is not None and abs(h - expected_height) > tolerance:
        raise OutputValidationError(
            f"Output height {h} deviates from expected {expected_height} (tolerance {tolerance})."
        )

    return detected_fmt, w, h
