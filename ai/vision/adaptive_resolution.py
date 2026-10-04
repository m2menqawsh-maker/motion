"""
ai/vision/adaptive_resolution.py
================================
Adaptive Resolution Policy for Vision Intelligence (S27.15 / AI-13).

Invariants:
- High resolution is NEVER unconditionally forced on all visual analysis.
- Scene classification operates at LOW / MEDIUM resolution.
- OCR and UI/Screen text inspection operate at HIGH resolution.
- Critical / detailed inspection operates at HIGH resolution.
- Object & Person detection operates at MEDIUM / HIGH resolution based on scene density.
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple
from ai.contracts.common import CapabilityType


class ResolutionTier(str, Enum):
    """Normalized spatial resolution tiers for vision processing."""
    LOW = "LOW"        # 640x360 (Fast scene classification, global motion, color grading)
    MEDIUM = "MEDIUM"  # 1280x720 (Object detection, person detection, general b-roll)
    HIGH = "HIGH"      # 1920x1080 (OCR, UI inspection, dense text, fine detail)
    ULTRA = "ULTRA"    # 3840x2160 (Forensic inspection, 4K master validation)


RESOLUTION_DIMENSIONS = {
    ResolutionTier.LOW: (640, 360),
    ResolutionTier.MEDIUM: (1280, 720),
    ResolutionTier.HIGH: (1920, 1080),
    ResolutionTier.ULTRA: (3840, 2160),
}


class AdaptiveResolutionPolicy:
    """
    Authoritative resolution selection policy engine.
    Controls frame extraction and scaling budget to minimize token/compute spend.
    """

    @staticmethod
    def resolve_tier(
        capability: CapabilityType,
        is_ui_screen: bool = False,
        is_critical_inspection: bool = False,
        prefer_speed: bool = False,
    ) -> ResolutionTier:
        """
        Determines the optimal resolution tier for a visual processing task.
        """
        # 1. Critical inspection or UI screen text always demands HIGH
        if is_critical_inspection or is_ui_screen:
            return ResolutionTier.HIGH

        # 2. OCR requires high spatial fidelity for character clarity
        if capability == CapabilityType.OCR:
            return ResolutionTier.HIGH

        # 3. Scene classification only needs coarse macro visual features
        if capability == CapabilityType.SCENE_CLASSIFICATION:
            return ResolutionTier.LOW

        # 4. Object & Person detection
        if capability in (CapabilityType.OBJECT_DETECTION, CapabilityType.PERSON_DETECTION):
            return ResolutionTier.LOW if prefer_speed else ResolutionTier.MEDIUM

        # 5. Video understanding / temporal summarization
        if capability == CapabilityType.VIDEO_UNDERSTANDING:
            return ResolutionTier.MEDIUM

        # 6. Default
        return ResolutionTier.MEDIUM

    @staticmethod
    def get_dimensions(tier: ResolutionTier) -> Tuple[int, int]:
        """Returns (width, height) for the chosen resolution tier."""
        return RESOLUTION_DIMENSIONS.get(tier, (1280, 720))
