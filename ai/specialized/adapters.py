"""
ai/specialized/adapters.py
==========================
Reference and Fake Provider Adapters for Specialized Media AI (S27.17 / AI-13).

Provides:
- FakeSpecializedMediaAdapterA (Alpha implementation)
- FakeSpecializedMediaAdapterB (Beta implementation for swap tests)
Both adapters strictly conform to canonical contracts and integrate with StorageService.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import JsonValue

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, PrivacyRequirement, ProvenanceRecord
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.media import AnalysisProvenance
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
from ai.contracts.usage import UsageRecord
from ai.providers.base import AIProvider, ProviderDefinition
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
from scripts.core.storage.storage_service import StorageService


class SpecializedFailureScenario(str, Enum):
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"


class BaseSpecializedFakeAdapter(
    AIProvider,
    TTSProviderInterface,
    ImageGenProviderInterface,
    VideoGenProviderInterface,
    PersonSegmentationProviderInterface,
    BackgroundRemovalProviderInterface,
    LipSyncProviderInterface,
    UpscaleProviderInterface,
    AudioDenoiseProviderInterface,
    AudioEnhanceProviderInterface,
    VocalIsolationProviderInterface,
):
    """
    Base implementation for offline testing and provider swap proofs.
    """

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        storage_service: StorageService,
        scenario: SpecializedFailureScenario = SpecializedFailureScenario.NONE,
    ):
        definition = ProviderDefinition(
            provider_id=provider_id,
            display_name=display_name,
            supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
            enabled=True,
            description="Offline specialized media provider adapter",
        )
        super().__init__(definition)
        self.storage_service = storage_service
        self.scenario = scenario
        self.invocation_count = 0

    def set_scenario(self, scenario: SpecializedFailureScenario) -> None:
        self.scenario = scenario

    def _check_failure(self) -> None:
        from ai.specialized.errors import SpecializedMediaError
        if self.scenario == SpecializedFailureScenario.TIMEOUT:
            raise SpecializedMediaError(
                code=AIErrorCode.TIMEOUT,
                message=f"Specialized provider '{self.provider_id}' timed out after 30000ms",
                retryable=True,
                dependency_reference=self.provider_id,
            )
        if self.scenario == SpecializedFailureScenario.RATE_LIMITED:
            raise SpecializedMediaError(
                code=AIErrorCode.RATE_LIMITED,
                message=f"Rate limit exceeded on provider '{self.provider_id}'",
                retryable=True,
                details={"retry_after_seconds": 15},
                dependency_reference=self.provider_id,
            )
        if self.scenario == SpecializedFailureScenario.SERVER_ERROR:
            raise SpecializedMediaError(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Upstream provider '{self.provider_id}' internal server error (HTTP 500)",
                retryable=True,
                dependency_reference=self.provider_id,
            )

    def _make_provenance(self, model_name: str) -> AnalysisProvenance:
        return AnalysisProvenance(
            producer=f"{self.provider_id}_adapter",
            provider=self.provider_id,
            model=model_name,
            version="1.0.0",
            confidence=0.98,
            timestamp=datetime.now(timezone.utc),
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

    # 1. TTS
    async def synthesize(self, request: TTSRequest, workspace_id: str) -> TTSResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("neural-tts-v1")
        payload = f"SYNTHESIZED_AUDIO:{self.provider_id}:{request.text}:{request.voice_id}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/tts/{h}.wav"
        self.storage_service.put(key, payload, "audio/wav")

        return TTSResult(
            audio_storage_key=key,
            audio_hash=h,
            duration_seconds=3.5,
            sample_rate=44100,
            format=request.format,
            provenance=prov,
        )

    # 2. Image Gen
    async def generate_image(self, request: ImageGenerationRequest, workspace_id: str) -> ImageGenerationResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("diffusion-image-v1")
        payload = f"IMAGE:{self.provider_id}:{request.prompt}:{request.width}x{request.height}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/images/{h}.png"
        self.storage_service.put(key, payload, "image/png")

        return ImageGenerationResult(
            image_storage_key=key,
            image_hash=h,
            width=request.width,
            height=request.height,
            format="png",
            provenance=prov,
        )

    # 3. Video Gen
    async def generate_video(self, request: VideoGenerationRequest, workspace_id: str) -> VideoGenerationResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("diffusion-video-v1")
        payload = f"VIDEO:{self.provider_id}:{request.prompt}:{request.duration_seconds}s".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/videos/{h}.mp4"
        self.storage_service.put(key, payload, "video/mp4")

        return VideoGenerationResult(
            video_storage_key=key,
            video_hash=h,
            duration_seconds=request.duration_seconds,
            fps=float(request.fps),
            width=request.width,
            height=request.height,
            format="mp4",
            provenance=prov,
        )

    # 4. Person Segmentation
    async def segment_person(self, request: PersonSegmentationRequest, workspace_id: str) -> PersonSegmentationResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("matte-segmenter-v1")
        payload = f"MASK:{self.provider_id}:{request.content_hash}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/masks/{h}.png"
        self.storage_service.put(key, payload, "image/png")

        return PersonSegmentationResult(
            mask_storage_key=key,
            mask_hash=h,
            person_count=1,
            confidence=0.97,
            provenance=prov,
        )

    # 5. Background Removal
    async def remove_background(self, request: BackgroundRemovalRequest, workspace_id: str) -> BackgroundRemovalResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("bg-removal-v1")
        payload = f"TRANSPARENT_IMAGE:{self.provider_id}:{request.content_hash}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/nobg/{h}.png"
        self.storage_service.put(key, payload, "image/png")

        return BackgroundRemovalResult(
            output_storage_key=key,
            output_hash=h,
            format=request.output_format,
            provenance=prov,
        )

    # 6. Lip Sync
    async def sync_lips(self, request: LipSyncRequest, workspace_id: str) -> LipSyncResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("wav2lip-v1")
        payload = f"LIPSYNC_VIDEO:{self.provider_id}:{request.content_hash}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/lipsync/{h}.mp4"
        self.storage_service.put(key, payload, "video/mp4")

        return LipSyncResult(
            output_video_storage_key=key,
            output_video_hash=h,
            duration_seconds=5.0,
            sync_confidence=0.96,
            provenance=prov,
        )

    # 7. Upscale
    async def upscale(self, request: UpscaleRequest, workspace_id: str) -> UpscaleResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("esrgan-upscale-v1")
        payload = f"UPSCALED_MEDIA:{self.provider_id}:{request.content_hash}:{request.scale_factor}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/upscaled/{h}.png"
        self.storage_service.put(key, payload, "image/png")

        w = request.target_width or int(1920 * request.scale_factor)
        ht = request.target_height or int(1080 * request.scale_factor)

        return UpscaleResult(
            output_storage_key=key,
            output_hash=h,
            width=w,
            height=ht,
            provenance=prov,
        )

    # 8. Audio Denoise
    async def denoise(self, request: AudioDenoiseRequest, workspace_id: str) -> AudioDenoiseResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("demucs-denoise-v1")
        payload = f"DENOISED_AUDIO:{self.provider_id}:{request.content_hash}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/denoised/{h}.wav"
        self.storage_service.put(key, payload, "audio/wav")

        return AudioDenoiseResult(
            output_audio_storage_key=key,
            output_audio_hash=h,
            noise_reduction_db=14.5,
            provenance=prov,
        )

    # 9. Audio Enhance
    async def enhance(self, request: AudioEnhanceRequest, workspace_id: str) -> AudioEnhanceResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("neural-audio-enhance-v1")
        payload = f"ENHANCED_AUDIO:{self.provider_id}:{request.content_hash}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        key = f"workspaces/{workspace_id}/specialized/enhanced/{h}.wav"
        self.storage_service.put(key, payload, "audio/wav")

        return AudioEnhanceResult(
            output_audio_storage_key=key,
            output_audio_hash=h,
            applied_lufs=request.target_lufs,
            provenance=prov,
        )

    # 10. Vocal Isolation
    async def isolate_vocals(self, request: VocalIsolationRequest, workspace_id: str) -> VocalIsolationResult:
        self.invocation_count += 1
        self._check_failure()

        prov = self._make_provenance("demucs-stem-sep-v1")
        v_payload = f"VOCALS:{self.provider_id}:{request.content_hash}".encode("utf-8")
        v_h = hashlib.sha256(v_payload).hexdigest()
        v_key = f"workspaces/{workspace_id}/specialized/stems/vocals_{v_h}.wav"
        self.storage_service.put(v_key, v_payload, "audio/wav")

        i_key = None
        i_h = None
        if request.extract_instrumental:
            i_payload = f"INSTRUMENTAL:{self.provider_id}:{request.content_hash}".encode("utf-8")
            i_h = hashlib.sha256(i_payload).hexdigest()
            i_key = f"workspaces/{workspace_id}/specialized/stems/instr_{i_h}.wav"
            self.storage_service.put(i_key, i_payload, "audio/wav")

        return VocalIsolationResult(
            vocals_storage_key=v_key,
            vocals_hash=v_h,
            instrumental_storage_key=i_key,
            instrumental_hash=i_h,
            provenance=prov,
        )

    # Unified Capability execution dispatcher
    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self._check_failure()
        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source=f"{self.provider_id}_adapter",
            model_id=f"{self.provider_id}-model",
            provider_id=self.provider_id,
            timestamp=now,
            latency_ms=25,
        )
        return CapabilityResult(
            capability=request.capability,
            status=CapabilityStatus.SUCCESS,
            output_data={"result": f"Executed on {self.provider_id}", "status": "completed"},
            confidence=0.98,
            provenance=provenance,
            usage=UsageRecord(input_tokens=10, output_tokens=20),
        )


class FakeSpecializedMediaAdapterA(BaseSpecializedFakeAdapter):
    def __init__(
        self,
        storage_service: StorageService,
        scenario: SpecializedFailureScenario = SpecializedFailureScenario.NONE,
    ):
        super().__init__(
            provider_id="fake-specialized-a",
            display_name="Fake Specialized Engine Alpha",
            storage_service=storage_service,
            scenario=scenario,
        )


class FakeSpecializedMediaAdapterB(BaseSpecializedFakeAdapter):
    def __init__(
        self,
        storage_service: StorageService,
        scenario: SpecializedFailureScenario = SpecializedFailureScenario.NONE,
    ):
        super().__init__(
            provider_id="fake-specialized-b",
            display_name="Fake Specialized Engine Beta",
            storage_service=storage_service,
            scenario=scenario,
        )
