"""
tests/ai/vision/test_adaptive_resolution.py
===========================================
Tests for Adaptive Resolution Policy (S27.15 / AI-13 Rules 8, 30).
"""

from ai.contracts.common import CapabilityType
from ai.vision.adaptive_resolution import AdaptiveResolutionPolicy, ResolutionTier


def test_scene_classification_uses_low_resolution():
    tier = AdaptiveResolutionPolicy.resolve_tier(CapabilityType.SCENE_CLASSIFICATION)
    assert tier == ResolutionTier.LOW
    dims = AdaptiveResolutionPolicy.get_dimensions(tier)
    assert dims == (640, 360)


def test_ocr_and_ui_use_high_resolution():
    ocr_tier = AdaptiveResolutionPolicy.resolve_tier(CapabilityType.OCR)
    assert ocr_tier == ResolutionTier.HIGH
    dims = AdaptiveResolutionPolicy.get_dimensions(ocr_tier)
    assert dims == (1920, 1080)

    ui_tier = AdaptiveResolutionPolicy.resolve_tier(CapabilityType.VISION, is_ui_screen=True)
    assert ui_tier == ResolutionTier.HIGH


def test_critical_inspection_demands_high_resolution():
    crit_tier = AdaptiveResolutionPolicy.resolve_tier(
        CapabilityType.OBJECT_DETECTION,
        is_critical_inspection=True,
    )
    assert crit_tier == ResolutionTier.HIGH
