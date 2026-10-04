"""
tests/ai/speech/test_stt_cache_and_artifacts.py
===============================================
Comprehensive test suite for STT canonical cache identity, TranscriptArtifact,
and deterministic configuration hashing (S28-M04 PART 1).
"""

from __future__ import annotations

import datetime
import pytest

from ai.contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.contracts.media import (
    AnalysisProvenance,
    SpeechIntelligence,
    SpeechSegment,
    SpeechWord,
    TranscriptArtifact,
)
from ai.models.registry import ModelRegistry
from ai.routing.router import ModelRouter
from ai.speech.cache import STTCacheManager, get_stt_cache_manager
from ai.speech.local_provider import LocalSTTProvider
from ai.speech.stt_provider import STTConfig
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def clean_cache():
    cache_mgr = get_stt_cache_manager()
    cache_mgr.clear()
    yield cache_mgr
    cache_mgr.clear()


@pytest.fixture
def sample_speech_intelligence():
    now = datetime.datetime.now(datetime.timezone.utc)
    return SpeechIntelligence(
        language="ar",
        language_confidence=0.98,
        transcript="مرحبا بكم في الفيديو",
        segments=[
            SpeechSegment(
                id="seg_0",
                start=0.0,
                end=1.5,
                text="مرحبا بكم",
                words=[
                    SpeechWord(start=0.0, end=0.6, text="مرحبا", confidence=0.95),
                    SpeechWord(start=0.6, end=1.5, text="بكم", confidence=0.96),
                ],
            ),
            SpeechSegment(
                id="seg_1",
                start=1.6,
                end=2.8,
                text="في الفيديو",
                words=[
                    SpeechWord(start=1.6, end=2.0, text="في", confidence=0.99),
                    SpeechWord(start=2.0, end=2.8, text="الفيديو", confidence=0.97),
                ],
            ),
        ],
        words=[
            SpeechWord(start=0.0, end=0.6, text="مرحبا", confidence=0.95),
            SpeechWord(start=0.6, end=1.5, text="بكم", confidence=0.96),
            SpeechWord(start=1.6, end=2.0, text="في", confidence=0.99),
            SpeechWord(start=2.0, end=2.8, text="الفيديو", confidence=0.97),
        ],
        speakers=[],
        duration_seconds=2.8,
        overall_confidence=0.96,
        provenance=AnalysisProvenance(
            producer="LocalSTTProvider",
            provider="local",
            model="faster-whisper-base",
            version="1.2.1",
            confidence=0.98,
            timestamp=now,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        ),
    )


class TestSTTCacheAndArtifacts:
    def test_transcript_artifact_bidirectional_conversion(self, sample_speech_intelligence):
        """Verifies lossless round-trip conversion between SpeechIntelligence and TranscriptArtifact."""
        artifact = TranscriptArtifact.from_speech_intelligence(
            speech_intel=sample_speech_intelligence,
            source_asset_id="asset_audio_123",
            source_content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            model_id="faster-whisper-base",
            model_version="1.2.1",
            config_hash="a1b2c3d4e5f60718",
        )

        assert artifact.source_asset_id == "asset_audio_123"
        assert artifact.source_content_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert artifact.model_id == "faster-whisper-base"
        assert artifact.transcript == "مرحبا بكم في الفيديو"
        assert len(artifact.segments) == 2
        assert len(artifact.words) == 4

        # Convert back
        restored = artifact.to_speech_intelligence()
        assert restored.transcript == sample_speech_intelligence.transcript
        assert restored.language == sample_speech_intelligence.language
        assert len(restored.segments) == len(sample_speech_intelligence.segments)
        assert len(restored.words) == len(sample_speech_intelligence.words)
        assert restored.duration_seconds == sample_speech_intelligence.duration_seconds

        # Test JSON serialization round-trip
        json_str = artifact.model_dump_json()
        deserialized = TranscriptArtifact.model_validate_json(json_str)
        assert deserialized.transcript_id == artifact.transcript_id
        assert deserialized.transcript == artifact.transcript

    def test_deterministic_config_hashing(self):
        """Verifies that config hashing is order-invariant, deterministic, and sensitive to parameter changes."""
        config1 = STTConfig(
            model_size="base",
            language="ar",
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            word_timestamps=True,
        )
        config2 = STTConfig(
            word_timestamps=True,
            vad_filter=True,
            temperature=0.0,
            beam_size=5,
            language="ar",
            model_size="base",
        )
        assert config1.compute_config_hash() == config2.compute_config_hash()

        # Changing any parameter must alter hash
        config_vad_false = STTConfig(
            model_size="base",
            language="ar",
            beam_size=5,
            temperature=0.0,
            vad_filter=False,
            word_timestamps=True,
        )
        assert config1.compute_config_hash() != config_vad_false.compute_config_hash()

        config_beam = STTConfig(
            model_size="base",
            language="ar",
            beam_size=2,
            temperature=0.0,
            vad_filter=True,
            word_timestamps=True,
        )
        assert config1.compute_config_hash() != config_beam.compute_config_hash()

    def test_canonical_cache_key_generation_and_miss_dimensions(self, clean_cache):
        """Verifies that cache keys strictly differentiate across all required dimensions."""
        base_config = STTConfig(model_size="base", language="ar")
        key_base = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_alpha_1",
            source_content_hash="hash_aaa",
            config=base_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )

        # 1. Same parameters produce identical key
        key_same = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_alpha_1",
            source_content_hash="hash_aaa",
            config=base_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )
        assert key_base == key_same

        # 2. Different workspace ID -> Miss
        key_diff_ws = clean_cache.derive_cache_key(
            workspace_id="ws_02",
            project_id="prj_alpha_1",
            source_content_hash="hash_aaa",
            config=base_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )
        assert key_base != key_diff_ws

        # 3. Different project ID -> Miss
        key_diff_prj = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_beta_2",
            source_content_hash="hash_aaa",
            config=base_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )
        assert key_base != key_diff_prj

        # 4. Different source content hash -> Miss
        key_diff_content = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_alpha_1",
            source_content_hash="hash_bbb",
            config=base_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )
        assert key_base != key_diff_content

        # 5. Different model ID -> Miss
        key_diff_model = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_alpha_1",
            source_content_hash="hash_aaa",
            config=base_config,
            model_id="faster-whisper-tiny",
            model_version="1.2.1",
        )
        assert key_base != key_diff_model

        # 6. Different config -> Miss
        alt_config = STTConfig(model_size="base", language="ar", vad_filter=False)
        key_diff_config = clean_cache.derive_cache_key(
            workspace_id="ws_01",
            project_id="prj_alpha_1",
            source_content_hash="hash_aaa",
            config=alt_config,
            model_id="faster-whisper-base",
            model_version="1.2.1",
        )
        assert key_base != key_diff_config

    @pytest.mark.asyncio
    async def test_router_cache_hit_and_miss_flow(self, clean_cache):
        """Tests that ModelRouter properly retrieves cached results and avoids redundant model inference."""
        router = ModelRouter()
        local_stt = LocalSTTProvider()
        router.register_stt_provider("faster-whisper", local_stt)

        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        req1 = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/voiceover.wav",
                "language": "ar",
            },
        )

        # 1st Call: Cache miss, performs actual inference
        res1 = await router.execute_stt(req1, ctx)
        assert res1.status == CapabilityStatus.SUCCESS
        assert res1.execution_metadata["cache_hit"] is False
        assert len(res1.output["transcript"]) > 0

        # 2nd Call: Same parameters, instant cache hit
        res2 = await router.execute_stt(req1, ctx)
        assert res2.status == CapabilityStatus.SUCCESS
        assert res2.execution_metadata["cache_hit"] is True
        assert res2.output["transcript"] == res1.output["transcript"]
        assert res2.duration_ms < 50  # Instantaneous

        # 3rd Call: Different parameters (e.g. model_size="tiny") -> Cache miss
        req3 = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/voiceover.wav",
                "language": "ar",
                "model_size": "tiny",
            },
        )
        res3 = await router.execute_stt(req3, ctx)
        assert res3.status == CapabilityStatus.SUCCESS
        assert res3.execution_metadata["cache_hit"] is False
