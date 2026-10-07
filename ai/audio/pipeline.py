"""
ai/audio/pipeline.py
====================
Authoritative Audio Intelligence Pipeline (S27.16 / AI-13).

Invariants:
- Native DSP First: Silence, loudness, peak, clipping, noise estimation, and beat tracking
  are processed via deterministic NativeAudioDSP without invoking external AI providers.
- Provider calls counter: ai_provider_invocations == 0 for all deterministic acoustic analysis.
- Clear boundary: analysis is decoupled from audio transforms (denoise, enhance, vocal isolation).
- Integrates directly with AI-11 AICacheService and StorageService.
- Strict multi-tenant isolation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from ai.cache.errors import TenantIsolationViolationError
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.audio import (
    AudioBeatTrack,
    AudioIntelligence,
    AudioLoudnessMetrics,
    AudioNoiseEstimate,
    AudioQualityObservation,
    TimeRange,
)
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityType
from ai.contracts.media import AnalysisProvenance, TechnicalMetadata
from ai.audio.dsp import NativeAudioDSP
from scripts.core.storage.storage_service import StorageService

logger = logging.getLogger("ai.audio.pipeline")


class AudioIntelligencePipeline:
    """
    Authoritative coordinator executing native deterministic DSP acoustic analysis.
    """

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        cache_service: Optional[AICacheService] = None,
        dsp_engine: Optional[NativeAudioDSP] = None,
    ):
        self.storage_service = storage_service
        self.cache_service = cache_service
        self.dsp_engine = dsp_engine or NativeAudioDSP()
        self.ai_provider_invocations = 0  # Crucial audit counter: must remain 0 for DSP analysis

    async def analyze_audio(
        self,
        workspace_id: str,
        asset_id: str,
        audio_bytes: bytes,
        technical_metadata: Optional[TechnicalMetadata] = None,
        analysis_version: str = "1.0.0",
        bypass_cache: bool = False,
    ) -> AudioIntelligence:
        """
        Executes native DSP acoustic analysis.
        Guarantees: Zero external AI model calls.
        """
        content_hash = hashlib.sha256(audio_bytes).hexdigest()
        now_utc = datetime.now(timezone.utc)

        # 1. AI-11 Cache Check
        cache_key_str: Optional[str] = None
        if self.cache_service and not bypass_cache:
            cache_params = AICacheKeyParams(
                workspace_id=workspace_id,
                capability=CapabilityType.VOICE_ANALYSIS,
                content_hash=content_hash,
                model="native-dsp-v1",
                model_version=analysis_version,
                settings={"dsp": "standard"},
            )
            cache_key_str = derive_canonical_cache_key(cache_params)
            cached_entry = self.cache_service.get(workspace_id=workspace_id, cache_key=cache_key_str)

            if cached_entry and cached_entry.output_ref and self.storage_service:
                try:
                    cached_bytes = self.storage_service.get(cached_entry.output_ref)
                    cached_data = json.loads(cached_bytes.decode("utf-8"))
                    cached_intel = AudioIntelligence.model_validate(cached_data)
                    logger.info("AudioIntelligence Cache HIT for asset '%s' (key: %s)", asset_id, cache_key_str[:12])
                    return cached_intel
                except Exception as exc:
                    logger.warning("Failed to load cached audio payload: %s", exc)

        logger.info("AudioIntelligence Cache MISS for asset '%s'. Running Native DSP First.", asset_id)

        # 2. Native DSP Measurements (Zero AI spend)
        loudness = self.dsp_engine.measure_loudness_and_clipping(audio_bytes)
        speech_ranges, silence_ranges = self.dsp_engine.detect_speech_and_silence_ranges(audio_bytes)
        noise = self.dsp_engine.estimate_noise_profile(audio_bytes)
        beats = self.dsp_engine.detect_beats_and_tempo(audio_bytes)

        # Quality observations
        quality_obs: List[AudioQualityObservation] = [
            AudioQualityObservation(
                metric_name="clipping",
                score=0.0 if loudness.clipping_detected else 1.0,
                details=f"Clipping events: {loudness.clipping_events_count}",
                provenance=loudness.provenance,
            ),
            AudioQualityObservation(
                metric_name="noise_floor",
                score=1.0 if noise.noise_profile_label == "clean" else (0.7 if noise.noise_profile_label == "low_hiss" else 0.4),
                details=f"Estimated SNR: {noise.snr_db} dB, Profile: {noise.noise_profile_label}",
                provenance=noise.provenance,
            ),
        ]

        # 3. Assemble Canonical AudioIntelligence Contract
        top_provenance = AnalysisProvenance(
            producer="audio_intelligence_pipeline",
            provider="local",
            model="native_dsp_v1",
            version="1.0.0",
            confidence=0.98,
            timestamp=now_utc,
            analysis_version=analysis_version,
            contract_version="1.0.0",
        )

        audio_intel = AudioIntelligence(
            status="READY",
            has_audio_analysis=True,
            speech_ranges=speech_ranges,
            silence_ranges=silence_ranges,
            loudness=loudness,
            noise_estimate=noise,
            beats=beats,
            music_ranges=[],
            quality_observations=quality_obs,
            noise_profile=noise.noise_profile_label,
            tempo_bpm=beats.tempo_bpm,
            beat_timestamps=beats.beat_timestamps,
            vocal_isolation_ref=None,
            provenance=top_provenance,
        )

        # 4. AI-11 Cache Publish
        if self.cache_service and self.storage_service and cache_key_str and not bypass_cache:
            try:
                storage_key = f"workspaces/{workspace_id}/cache/audio/{cache_key_str}.json"
                payload_bytes = audio_intel.model_dump_json(indent=2).encode("utf-8")
                self.storage_service.put(
                    key=storage_key,
                    data=payload_bytes,
                    content_type="application/json",
                )
                self.cache_service.publish(
                    workspace_id=workspace_id,
                    cache_key=cache_key_str,
                    output_ref=storage_key,
                    content_hash=hashlib.sha256(payload_bytes).hexdigest(),
                    confidence=0.98,
                )
                logger.info("Published audio analysis to AI-11 cache (key: %s)", cache_key_str[:12])
            except Exception as exc:
                logger.warning("Failed to publish audio analysis to cache: %s", exc)

        return audio_intel
