"""
tests/ai/mcp/test_mcp_contracts.py
==================================
Tests for MCP typed operational contracts (S27.10).

Invariants:
- Unexpected fields forbidden (extra="forbid").
- Strict type enforcement (no loose coercion).
- Immutability (frozen=True).
- No dict[str, Any] at operational boundaries.
"""

import pytest
from pydantic import ValidationError

from ai.mcp.contracts import (
    AutoCropInput,
    AutoCropOutput,
    CropRatioInput,
    CropRatioOutput,
    DetectBlackFramesInput,
    DetectBlackFramesOutput,
    ExtendAudioInput,
    ExtendAudioOutput,
    ExtendVideoInput,
    ExtendVideoOutput,
    NormalizeLoudnessInput,
    NormalizeLoudnessOutput,
    ResizeVideoInput,
    ResizeVideoOutput,
    TrimAudioInput,
    TrimAudioOutput,
    TrimSilenceInput,
    TrimSilenceOutput,
    TrimVideoInput,
    TrimVideoOutput,
    UpscaleImageInput,
    UpscaleImageOutput,
)


def test_extra_fields_forbidden():
    """All MCP contract models must reject unrecognized extra fields."""
    with pytest.raises(ValidationError):
        TrimAudioInput(file_path="audio.mp3", target_duration=5.0, unexpected_field="malicious")

    with pytest.raises(ValidationError):
        ResizeVideoInput(file_path="video.mp4", target_width=1920, target_height=1080, extra="bad")

    with pytest.raises(ValidationError):
        UpscaleImageInput(file_path="image.png", extra_arg=123)


def test_strict_types_enforced():
    """Mismatched primitive types must fail validation rather than silently coercing."""
    with pytest.raises(ValidationError):
        # target_duration must be float/number, not string
        TrimAudioInput(file_path="audio.mp3", target_duration="not_a_number")

    with pytest.raises(ValidationError):
        # target_width must be int, not string
        ResizeVideoInput(file_path="video.mp4", target_width="1920", target_height=1080)


def test_immutability_enforced():
    """Contract instances must be immutable frozen value objects."""
    inp = TrimAudioInput(file_path="audio.mp3", target_duration=5.0)
    with pytest.raises(ValidationError):
        inp.file_path = "changed.mp3"


def test_range_validations():
    """Values out of allowed physical ranges must be rejected."""
    with pytest.raises(ValidationError):
        # Duration must be > 0
        TrimAudioInput(file_path="audio.mp3", target_duration=0.0)

    with pytest.raises(ValidationError):
        # Target LUFS cannot be positive
        NormalizeLoudnessInput(file_path="audio.mp3", target_lufs=5.0)

    with pytest.raises(ValidationError):
        # Dimensions must be positive
        ResizeVideoInput(file_path="video.mp4", target_width=-100, target_height=1080)


def test_crop_ratio_pattern_validation():
    """Crop ratio must match regex pattern like 9:16 or 16:9."""
    valid = CropRatioInput(file_path="image.png", target_ratio="16:9")
    assert valid.target_ratio == "16:9"

    with pytest.raises(ValidationError):
        CropRatioInput(file_path="image.png", target_ratio="invalid_ratio")
