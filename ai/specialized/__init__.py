"""
ai/specialized/__init__.py
==========================
Specialized Media AI package for S27.17 (AI-13).
"""

from ai.specialized.adapters import (
    BaseSpecializedFakeAdapter,
    FakeSpecializedMediaAdapterA,
    FakeSpecializedMediaAdapterB,
    SpecializedFailureScenario,
)
from ai.specialized.interfaces import (
    AudioDenoiseProviderInterface,
    AudioEnhanceProviderInterface,
    BackgroundRemovalProviderInterface,
    ImageGenProviderInterface,
    LipSyncProviderInterface,
    PersonSegmentationProviderInterface,
    TTSProviderInterface,
    UpscaleProviderInterface,
    VideoGenProviderInterface,
    VocalIsolationProviderInterface,
)
from ai.specialized.service import (
    SpecializedMediaService,
)

__all__ = [
    "SpecializedFailureScenario",
    "BaseSpecializedFakeAdapter",
    "FakeSpecializedMediaAdapterA",
    "FakeSpecializedMediaAdapterB",
    "TTSProviderInterface",
    "ImageGenProviderInterface",
    "VideoGenProviderInterface",
    "PersonSegmentationProviderInterface",
    "BackgroundRemovalProviderInterface",
    "LipSyncProviderInterface",
    "UpscaleProviderInterface",
    "AudioDenoiseProviderInterface",
    "AudioEnhanceProviderInterface",
    "VocalIsolationProviderInterface",
    "SpecializedMediaService",
]
