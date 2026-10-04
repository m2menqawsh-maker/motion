"""
ai/speech/cache.py
==================
Canonical cache identity and storage manager for Speech-to-Text (S28-M04).

Invariants:
- Cache identity is deterministic, provider-neutral, and strictly tenant-isolated.
- Key dimensions: workspace_id + capability + content_hash + model_id + model_version + config_hash.
- Never uses filename or path as identity.
- Clean separation between tenant project storage and shared cache entries.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional, Tuple

from ai.contracts.cache import AICacheEntry, AICacheKeyParams, CacheEntryStatus
from ai.contracts.common import CapabilityType
from ai.contracts.media import SpeechIntelligence, TranscriptArtifact
from ai.cache.key import derive_canonical_cache_key
from ai.speech.stt_provider import STTConfig

logger = logging.getLogger("clean_video.ai.speech.cache")


class STTCacheManager:
    """
    Manager governing canonical cache lookup and persistence for Speech Intelligence.
    Ensures that identical audio and hyperparameters yield cache hits while invalidations
    (bytes, model version, or config) result in clean misses.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, TranscriptArtifact] = {}

    def derive_cache_key(
        self,
        workspace_id: str,
        project_id: str,
        source_content_hash: str,
        config: STTConfig,
        model_id: str = "faster-whisper-base",
        model_version: str = "1.2.1",
    ) -> str:
        """Computes deterministic canonical cache key using standard AICacheKeyParams."""
        config_hash = config.compute_config_hash()
        settings = {
            "config_hash": config_hash,
            "model_size": config.model_size,
            "language": config.language,
            "beam_size": config.beam_size,
            "temperature": config.temperature,
            "vad_filter": config.vad_filter,
            "word_timestamps": config.word_timestamps,
        }

        params = AICacheKeyParams(
            workspace_id=workspace_id,
            capability=CapabilityType.SPEECH_TO_TEXT,
            input_data={"project_id": project_id},
            content_hash=source_content_hash,
            settings=settings,
            model=model_id,
            model_version=model_version,
            contract_version="1.0.0",
            prompt_version="1.0.0",
            analysis_version="1.0.0",
        )
        return derive_canonical_cache_key(params)

    def get(self, cache_key: str) -> Optional[TranscriptArtifact]:
        """Retrieves cached TranscriptArtifact if present."""
        return self._cache.get(cache_key)

    def put(self, cache_key: str, artifact: TranscriptArtifact) -> None:
        """Stores TranscriptArtifact under canonical cache key."""
        self._cache[cache_key] = artifact
        logger.info("Persisted TranscriptArtifact to STTCacheManager (key=%s)", cache_key[:16])

    def clear(self) -> None:
        """Clears all cached entries (used in test isolation)."""
        self._cache.clear()


_default_stt_cache_manager: Optional[STTCacheManager] = None


def get_stt_cache_manager() -> STTCacheManager:
    global _default_stt_cache_manager
    if _default_stt_cache_manager is None:
        _default_stt_cache_manager = STTCacheManager()
    return _default_stt_cache_manager
