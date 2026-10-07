"""
ai/specialized/interfaces.py
============================
Provider-neutral abstract interfaces for Specialized Media AI (S27.17 / AI-13).

Covers all 10 specialized capabilities:
1. TEXT_TO_SPEECH
2. IMAGE_GENERATION
3. VIDEO_GENERATION
4. PERSON_SEGMENTATION
5. BACKGROUND_REMOVAL
6. LIP_SYNC
7. UPSCALE
8. AUDIO_DENOISE
9. AUDIO_ENHANCE
10. VOCAL_ISOLATION

Invariants:
- Zero vendor SDK coupling in interface signatures.
- Abstract StorageService keys for all media inputs/outputs.
- Strict Pydantic contracts across all boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai.contracts.specialized import (
    AudioDenoiseRequest,
    AudioDenoiseResult,
    AudioEnhanceRequest,
    AudioEnhanceResult,
    BackgroundRemovalRequest,
    BackgroundRemovalResult,
    ImageGenerationRequest,
    ImageGenerationResult,
    LipSyncRequest,
    LipSyncResult,
    PersonSegmentationRequest,
    PersonSegmentationResult,
    TTSRequest,
    TTSResult,
    UpscaleRequest,
    UpscaleResult,
    VideoGenerationRequest,
    VideoGenerationResult,
    VocalIsolationRequest,
    VocalIsolationResult,
)
from ai.providers.base import AIProvider


class TTSProviderInterface(ABC):
    @abstractmethod
    async def synthesize(self, request: TTSRequest, workspace_id: str) -> TTSResult:
        ...


class ImageGenProviderInterface(ABC):
    @abstractmethod
    async def generate_image(self, request: ImageGenerationRequest, workspace_id: str) -> ImageGenerationResult:
        ...


class VideoGenProviderInterface(ABC):
    @abstractmethod
    async def generate_video(self, request: VideoGenerationRequest, workspace_id: str) -> VideoGenerationResult:
        ...


class PersonSegmentationProviderInterface(ABC):
    @abstractmethod
    async def segment_person(self, request: PersonSegmentationRequest, workspace_id: str) -> PersonSegmentationResult:
        ...


class BackgroundRemovalProviderInterface(ABC):
    @abstractmethod
    async def remove_background(self, request: BackgroundRemovalRequest, workspace_id: str) -> BackgroundRemovalResult:
        ...


class LipSyncProviderInterface(ABC):
    @abstractmethod
    async def sync_lips(self, request: LipSyncRequest, workspace_id: str) -> LipSyncResult:
        ...


class UpscaleProviderInterface(ABC):
    @abstractmethod
    async def upscale(self, request: UpscaleRequest, workspace_id: str) -> UpscaleResult:
        ...


class AudioDenoiseProviderInterface(ABC):
    @abstractmethod
    async def denoise(self, request: AudioDenoiseRequest, workspace_id: str) -> AudioDenoiseResult:
        ...


class AudioEnhanceProviderInterface(ABC):
    @abstractmethod
    async def enhance(self, request: AudioEnhanceRequest, workspace_id: str) -> AudioEnhanceResult:
        ...


class VocalIsolationProviderInterface(ABC):
    @abstractmethod
    async def isolate_vocals(self, request: VocalIsolationRequest, workspace_id: str) -> VocalIsolationResult:
        ...
