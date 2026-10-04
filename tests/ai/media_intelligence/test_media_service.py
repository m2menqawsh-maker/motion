"""
tests/ai/media_intelligence/test_media_service.py
=================================================
End-to-end tests for MediaIntelligenceService, cache hit/miss,
byte-level invalidation, tenant isolation, and cache poisoning prevention (S27.13 / S27.14).
"""

import io
import math
import struct
import wave
import pytest

from ai.cache.errors import TenantIsolationViolationError
from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import ProvenanceRecord
from ai.contracts.media import MediaIntelligence
from ai.media.service import MalformedProviderOutputError, MediaIntelligenceService
from ai.media.technical_probe import TechnicalMediaProbe
from ai.speech.adapter import FakeSpeechProviderA
from scripts.core.media_intelligence_repository import InMemoryMediaIntelligenceRepository
from scripts.core.storage.storage_service import LocalStorageBackend


def create_test_wave_bytes(duration_sec: float = 5.0, freq: float = 440.0, is_silent: bool = False) -> bytes:
    """Creates a deterministic in-memory WAVE audio buffer."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        num_samples = int(duration_sec * 44100)
        frames = bytearray()
        for i in range(num_samples):
            val = 0 if is_silent else int(12000 * math.sin(2 * math.pi * freq * (i / 44100)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


@pytest.fixture
def storage(tmp_path):
    backend = LocalStorageBackend(root_dir=tmp_path / "storage_root")
    return backend


@pytest.fixture
def repository():
    return InMemoryMediaIntelligenceRepository()


@pytest.fixture
def service(storage, repository):
    return MediaIntelligenceService(
        storage_service=storage,
        repository=repository,
        technical_probe=TechnicalMediaProbe(),
    )


@pytest.mark.asyncio
async def test_media_analysis_standard_flow(service, storage, repository):
    audio_bytes = create_test_wave_bytes(duration_sec=5.0)
    provider = FakeSpeechProviderA()

    report = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_01",
        media_bytes=audio_bytes,
        provider_override=provider,
    )

    assert isinstance(report, MediaIntelligence)
    assert report.workspace_id == "ws_alpha"
    assert report.asset_id == "ast_promo_01"
    assert report.speech is not None
    assert "الموبايل" in report.speech.transcript
    assert report.technical.format == "wav"
    assert report.audio.status == "TYPED_FOUNDATION_AI13"

    # Verify StorageService persistence
    storage_key = service._build_storage_key("ws_alpha", "ast_promo_01", "1.0.0", report.content_hash)
    stored_bytes = storage.get(storage_key)
    assert stored_bytes is not None

    # Verify repository index
    index = repository.get_index("ws_alpha", "ast_promo_01", report.content_hash, "1.0.0")
    assert index is not None
    assert index.storage_key == storage_key
    assert provider.invocation_count == 1


@pytest.mark.asyncio
async def test_cache_hit_on_identical_asset(service):
    """
    Mandatory Test:
    analyze Asset A -> analyze Asset A again unchanged -> Cache HIT -> no second expensive provider call.
    """
    audio_bytes = create_test_wave_bytes(duration_sec=5.0)
    provider = FakeSpeechProviderA()

    # Call 1: Cache MISS
    report_1 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_02",
        media_bytes=audio_bytes,
        provider_override=provider,
    )
    assert provider.invocation_count == 1

    # Call 2: Unchanged Asset -> Cache HIT
    report_2 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_02",
        media_bytes=audio_bytes,
        provider_override=provider,
    )

    # Provider must NOT have been called a second time
    assert provider.invocation_count == 1
    assert report_1.content_hash == report_2.content_hash
    assert report_1.speech.transcript == report_2.speech.transcript


@pytest.mark.asyncio
async def test_byte_change_invalidates_cache(service):
    """
    Mandatory Test:
    Asset bytes V1 -> analyze, change 1 byte -> Asset bytes V2 -> new content hash -> cache MISS -> new analysis.
    """
    audio_bytes_v1 = bytearray(create_test_wave_bytes(duration_sec=5.0, freq=440.0))
    provider = FakeSpeechProviderA()

    # Call 1: Analysis V1
    report_v1 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_03",
        media_bytes=bytes(audio_bytes_v1),
        provider_override=provider,
    )
    assert provider.invocation_count == 1

    # Modify exactly ONE audio sample byte
    audio_bytes_v2 = bytearray(audio_bytes_v1)
    audio_bytes_v2[100] = (audio_bytes_v2[100] + 1) % 256

    assert bytes(audio_bytes_v1) != bytes(audio_bytes_v2)

    # Call 2: Analysis V2 -> Must trigger cache MISS and re-invoke provider
    report_v2 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_03",
        media_bytes=bytes(audio_bytes_v2),
        provider_override=provider,
    )

    assert provider.invocation_count == 2
    assert report_v1.content_hash != report_v2.content_hash


@pytest.mark.asyncio
async def test_analysis_version_change_invalidation(service):
    audio_bytes = create_test_wave_bytes(duration_sec=5.0)
    provider = FakeSpeechProviderA()

    # Call 1 with analysis_version="1.0.0"
    report_v1 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_04",
        media_bytes=audio_bytes,
        analysis_version="1.0.0",
        provider_override=provider,
    )
    assert provider.invocation_count == 1

    # Call 2 with analysis_version="2.0.0" -> Cache MISS
    report_v2 = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_promo_04",
        media_bytes=audio_bytes,
        analysis_version="2.0.0",
        provider_override=provider,
    )

    assert provider.invocation_count == 2
    assert report_v1.analysis_version == "1.0.0"
    assert report_v2.analysis_version == "2.0.0"


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(service):
    """
    Mandatory Test:
    Workspace A cannot read or leak reports of Workspace B.
    """
    audio_bytes = create_test_wave_bytes(duration_sec=5.0)
    provider = FakeSpeechProviderA()

    report_a = await service.analyze_media(
        workspace_id="ws_tenant_a",
        asset_id="ast_secret_doc",
        media_bytes=audio_bytes,
        provider_override=provider,
    )

    # Workspace B queries the same asset_id and content_hash
    report_b = service.get_analysis_report(
        workspace_id="ws_tenant_b",
        asset_id="ast_secret_doc",
        content_hash=report_a.content_hash,
    )

    # Must return None, zero cross-tenant leakage
    assert report_b is None


@pytest.mark.asyncio
async def test_silent_audio_skips_expensive_speech_call(service):
    """Deterministic local probe discovers silence and skips speech AI call."""
    silent_audio = create_test_wave_bytes(duration_sec=2.0, is_silent=True)
    provider = FakeSpeechProviderA()

    report = await service.analyze_media(
        workspace_id="ws_alpha",
        asset_id="ast_silent",
        media_bytes=silent_audio,
        provider_override=provider,
    )

    # Provider should never have been invoked for pure silence
    assert provider.invocation_count == 0
    assert report.speech is None
    assert report.technical.has_audio is True


@pytest.mark.asyncio
async def test_malformed_provider_output_not_cached_as_ready(service, repository, storage):
    """
    Mandatory Test:
    Malformed provider output -> structured failure -> NOT cached as READY (no cache poisoning).
    """
    audio_bytes = create_test_wave_bytes(duration_sec=2.0)

    # Provider returns corrupt inverted timestamps
    corrupt_payload = {
        "text": "corrupt output",
        "segments": [
            {"start": 5.0, "end": 2.0, "text": "inverted timestamps"}  # end < start violates invariant
        ],
    }
    bad_provider = FakeSpeechProviderA(custom_payload=corrupt_payload)

    with pytest.raises(MalformedProviderOutputError):
        await service.analyze_media(
            workspace_id="ws_alpha",
            asset_id="ast_bad",
            media_bytes=audio_bytes,
            provider_override=bad_provider,
        )

    # Verify no corrupted report entered repository or storage
    indices = repository.list_indices("ws_alpha", "ast_bad")
    assert len(indices) == 0
