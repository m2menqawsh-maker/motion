"""
ai/vision/__init__.py
=====================
Vision Intelligence package for S27.15 (AI-13).
"""

from ai.vision.adaptive_resolution import (
    AdaptiveResolutionPolicy,
    ResolutionTier,
    RESOLUTION_DIMENSIONS,
)
from ai.vision.keyframe_extractor import (
    KeyframeExtractionPolicy,
    KeyframeExtractor,
)
from ai.vision.object_person import (
    VisualClassificationEngine,
)
from ai.vision.ocr import (
    OCREngine,
)
from ai.vision.pipeline import (
    VisionPipeline,
)
from ai.vision.shot_detection import (
    NativeShotDetector,
)

__all__ = [
    "AdaptiveResolutionPolicy",
    "ResolutionTier",
    "RESOLUTION_DIMENSIONS",
    "KeyframeExtractionPolicy",
    "KeyframeExtractor",
    "VisualClassificationEngine",
    "OCREngine",
    "VisionPipeline",
    "NativeShotDetector",
]
