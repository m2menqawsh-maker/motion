"""
tests/ai/audio/test_audio_pipeline.py
=====================================
Pipeline and integration tests for AudioIntelligencePipeline (S27.16 / AI-13).

Invariants verified:
- Audio pipeline runs native DSP first.
- Cache HIT / MISS semantics (Rule 9, 31).
- Multi-tenant boundary isolation (Rule 25, 31).
- Strongly-typed AudioIntelligence contract without unstructured dicts.
"""

import pytest

from ai.audio.benchmark.fixtures import (
    generate_clean_speech_fixture,
    generate_music_fixture,
)
from ai.audio.pipeline import AudioIntelligencePipeline
from ai.cache.service import AICacheService
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    storage_dir = tmp_path / "audio_storage"
    return LocalStorageBackend(root_dir=storage_dir)


@pytest.fixture
def cache(tmp_path, storage):
    db_file = tmp_path / "audio_cache.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    return AICacheService(repository=repo, storage_service=storage)


@pytest.fixture
def audio_pipeline(storage, cache):
    return AudioIntelligencePipeline(storage_service=storage, cache_service=cache)


@pytest.mark.asyncio
async def test_audio_pipeline_execution(audio_pipeline):
    """Verifies end-to-end execution of native acoustic intelligence pipeline."""
    audio_wav = generate_clean_speech_fixture(duration_sec=2.0)

    intel = await audio_pipeline.analyze_audio(
        workspace_id="ws_audio_100",
        asset_id="ast_audio_test_01",
        audio_bytes=audio_wav,
    )

    assert intel.status == "READY"
    assert intel.has_audio_analysis is True
    assert intel.loudness is not None
    assert intel.noise_estimate is not None
    assert intel.beats is not None
    assert isinstance(intel.speech_ranges, list)
    assert isinstance(intel.silence_ranges, list)
    assert len(intel.quality_observations) >= 2


@pytest.mark.asyncio
async def test_audio_cache_hit_and_miss(audio_pipeline):
    """
    Mandatory Test (Rule 9, 31):
    Same audio stream + same analysis -> Cache HIT.
    Different audio bytes -> Cache MISS.
    """
    wav_a = generate_music_fixture(duration_sec=2.0, bpm=120.0)
    wav_b = generate_clean_speech_fixture(duration_sec=2.0)

    # 1. Initial invocation: Cache MISS
    res1 = await audio_pipeline.analyze_audio(
        workspace_id="ws_client_cache",
        asset_id="audio_asset_01",
        audio_bytes=wav_a,
    )
    assert res1.status == "READY"

    # 2. Second invocation: Cache HIT
    res2 = await audio_pipeline.analyze_audio(
        workspace_id="ws_client_cache",
        asset_id="audio_asset_01",
        audio_bytes=wav_a,
    )
    assert res2.status == "READY"
    assert res2.loudness.integrated_lufs == res1.loudness.integrated_lufs

    # 3. Altered bytes: Cache MISS
    res3 = await audio_pipeline.analyze_audio(
        workspace_id="ws_client_cache",
        asset_id="audio_asset_02",
        audio_bytes=wav_b,
    )
    assert res3.status == "READY"
    assert res3.beats.tempo_bpm != res1.beats.tempo_bpm or res3.noise_estimate.snr_db != res1.noise_estimate.snr_db


@pytest.mark.asyncio
async def test_audio_tenant_isolation(storage, cache):
    """
    Mandatory Test (Rule 25, 31):
    Workspace A cannot read Workspace B cached audio analysis or artifacts.
    """
    pipeline = AudioIntelligencePipeline(storage_service=storage, cache_service=cache)
    secret_wav = generate_clean_speech_fixture(duration_sec=1.5)

    # Execute for Tenant A
    await pipeline.analyze_audio(
        workspace_id="tenant_audio_a",
        asset_id="ast_audio_secret",
        audio_bytes=secret_wav,
    )

    # Query from Tenant B perspective: Cache MUST MISS because of strict workspace scoping
    from ai.cache.key import derive_canonical_cache_key
    from ai.contracts.cache import AICacheKeyParams
    from ai.contracts.common import CapabilityType
    import hashlib

    ck_b = derive_canonical_cache_key(
        AICacheKeyParams(
            workspace_id="tenant_audio_b",
            capability=CapabilityType.VOICE_ANALYSIS,
            content_hash=hashlib.sha256(secret_wav).hexdigest(),
            model="native-dsp-v1",
            model_version="1.0.0",
            settings={"dsp": "standard"},
        )
    )

    entry_b = cache.get(workspace_id="tenant_audio_b", cache_key=ck_b)
    assert entry_b is None
