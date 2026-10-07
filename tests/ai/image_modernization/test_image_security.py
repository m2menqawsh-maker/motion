"""
tests/ai/image_modernization/test_image_security.py
===================================================
Security, bounds, decompression bomb, and tenant isolation tests (S28-M08).

Invariants:
- Decompression bombs fail closed prior to unbounded memory allocation.
- Corrupted, zero-byte, or truncated images fail closed with typed errors.
- Path traversal (.., /, \\, \x00) and cross-tenant access are strictly blocked.
- Arbitrary host paths and unrestricted formats fail closed.
"""

from __future__ import annotations

import io
import pytest
from PIL import Image

from ai.image_processing.contracts import ProbeImageRequest, ResizeImageRequest
from ai.image_processing.errors import (
    DecompressionBombError,
    DimensionLimitExceededError,
    ImageCorruptedError,
    ImageTenantConfinementError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from ai.image_processing.security import (
    MAX_FILE_BYTES,
    MAX_TOTAL_PIXELS,
    detect_image_format_from_magic,
    safe_open_image,
    validate_dimensions,
    validate_image_payload_size,
    validate_storage_key_confinement,
)
from ai.image_processing.service import ImageProcessingService


def test_zero_byte_image_fails_closed():
    with pytest.raises(ImageCorruptedError):
        validate_image_payload_size(0)


def test_payload_exceeding_max_file_size_fails_closed():
    with pytest.raises(ImageTooLargeError):
        validate_image_payload_size(MAX_FILE_BYTES + 1)


def test_malformed_random_bytes_fails_closed():
    random_junk = b"NOT_AN_IMAGE_RANDOM_GARBAGE_PAYLOAD_12345"
    with pytest.raises(UnsupportedImageFormatError):
        detect_image_format_from_magic(random_junk)

    with pytest.raises(UnsupportedImageFormatError):
        safe_open_image(random_junk)


def test_truncated_png_fails_closed():
    # Valid PNG header but truncated immediately
    truncated = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    with pytest.raises(ImageCorruptedError):
        safe_open_image(truncated)


def test_decompression_bomb_extreme_dimensions_fails_closed():
    # Dimensions exceeding MAX_TOTAL_PIXELS (e.g. 10000 x 10000 = 100M pixels > 33M limit)
    with pytest.raises(DimensionLimitExceededError):
        validate_dimensions(10000, 10000)

    with pytest.raises(DimensionLimitExceededError):
        validate_dimensions(9000, 100)


def test_storage_key_traversal_blocked():
    # Parent traversal ..
    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "../../../etc/passwd")

    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "projects/proj_alpha/../../secret.png")

    # Null byte injection
    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "images/safe\x00exploit.png")

    # Backslash traversal
    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "..\\..\\windows\\system32")


def test_cross_tenant_project_access_blocked():
    # Request for project alpha trying to access project beta's storage key
    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "projects/proj_beta/assets/ready/secret.png")

    with pytest.raises(ImageTenantConfinementError):
        validate_storage_key_confinement("proj_alpha", "workspaces/ws_other/proj_beta/image.png")


def test_service_level_confinement_enforcement(image_service: ImageProcessingService, mock_storage):
    # Setup image in proj_beta
    img = Image.new("RGB", (50, 50), color="green")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    mock_storage.put("projects/proj_beta/assets/ready/beta.png", bio.getvalue())

    # Proj_alpha attempts to read proj_beta's image
    req = ProbeImageRequest(project_id="proj_alpha", image_storage_key="projects/proj_beta/assets/ready/beta.png")
    with pytest.raises(ImageTenantConfinementError):
        image_service.probe_image(req)
