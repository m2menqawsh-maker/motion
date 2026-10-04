"""
tests/ai/cache/test_cache_service.py
====================================
Functional and behavioral tests for AICacheService (S27.12).

Invariants verified:
- First request: cache miss -> provider executed -> artifact saved in StorageService -> READY.
- Second identical request: cache hit -> provider not executed -> zero provider cost.
- Non-cacheable capabilities (CachePolicy.NEVER) strictly execute every time without caching.
- Explicit bypass_cache=True forces provider execution and bypasses cache lookup.
- Artifact is durably persisted in StorageService with validated canonical storage key.
"""

from datetime import datetime, timezone
import pytest

from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from ai.contracts.usage import CostEstimate, UsageRecord
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def cache_service(tmp_path):
    db_file = tmp_path / "test_cache_service.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    return AICacheService(repository=repo, storage_service=storage)


def test_cache_miss_then_hit(cache_service):
    provider_call_count = 0

    def fake_provider():
        nonlocal provider_call_count
        provider_call_count += 1
        now = datetime.now(timezone.utc)
        result = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"generated_text": "Video script overview"},
            provenance=ProvenanceRecord(
                source="fake_provider",
                model_id="gpt-4o",
                provider_id="fake_provider",
                timestamp=now,
                latency_ms=120,
            ),
            usage=UsageRecord(input_tokens=10, output_tokens=20, total_tokens=30),
        )
        return result, result.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Write video script"},
        model="gpt-4o",
    )

    # 1. First invocation: Cache MISS
    res1, hit1 = cache_service.get_or_compute(params, fake_provider)
    assert hit1 is False
    assert provider_call_count == 1
    assert res1.output_data == {"generated_text": "Video script overview"}

    # Verify artifact exists in storage
    entry = cache_service.repository.get_entry(params.workspace_id, "ck_" + cache_service.repository.get_entry(params.workspace_id, "dummy") if False else "")
    # Query via service's repo
    from ai.cache.key import derive_canonical_cache_key
    ck = derive_canonical_cache_key(params)
    stored_entry = cache_service.repository.get_entry(params.workspace_id, ck)
    assert stored_entry is not None
    assert cache_service.storage_service.exists(stored_entry.output_ref)

    # 2. Second invocation: Cache HIT
    res2, hit2 = cache_service.get_or_compute(params, fake_provider)
    assert hit2 is True
    assert provider_call_count == 1  # ZERO provider invocations
    assert res2.output_data == {"generated_text": "Video script overview"}


def test_non_cacheable_capability_obeys_policy(cache_service):
    provider_calls = 0

    def fake_video_gen():
        nonlocal provider_calls
        provider_calls += 1
        now = datetime.now(timezone.utc)
        result = CapabilityResult(
            capability=CapabilityTypeEnum.VIDEO_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"video_asset_id": f"asset_vid_{provider_calls}"},
            provenance=ProvenanceRecord(
                source="fake_video_provider",
                timestamp=now,
            ),
        )
        return result, result.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.VIDEO_GENERATION,  # Policy is NEVER
        input_data={"prompt": "generate intro animation"},
    )

    # Invocation 1
    res1, hit1 = cache_service.get_or_compute(params, fake_video_gen)
    assert hit1 is False
    assert provider_calls == 1

    # Invocation 2: MUST NOT be a cache hit
    res2, hit2 = cache_service.get_or_compute(params, fake_video_gen)
    assert hit2 is False
    assert provider_calls == 2

    # Nothing should be stored in the cache table for this key
    from ai.cache.key import derive_canonical_cache_key
    ck = derive_canonical_cache_key(params)
    assert cache_service.repository.get_entry(params.workspace_id, ck) is None


def test_bypass_cache_flag(cache_service):
    provider_calls = 0

    def fake_summarizer():
        nonlocal provider_calls
        provider_calls += 1
        now = datetime.now(timezone.utc)
        result = CapabilityResult(
            capability=CapabilityTypeEnum.SUMMARIZATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"summary": f"Summary attempt {provider_calls}"},
            provenance=ProvenanceRecord(
                source="fake_provider",
                timestamp=now,
            ),
        )
        return result, result.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.SUMMARIZATION,
        input_data={"transcript": "long video transcript..."},
    )

    # 1. Normal call -> caches result
    res1, hit1 = cache_service.get_or_compute(params, fake_summarizer, bypass_cache=False)
    assert hit1 is False
    assert provider_calls == 1

    # 2. Normal call -> cache HIT
    res2, hit2 = cache_service.get_or_compute(params, fake_summarizer, bypass_cache=False)
    assert hit2 is True
    assert provider_calls == 1

    # 3. Explicit bypass -> re-executes provider!
    res3, hit3 = cache_service.get_or_compute(params, fake_summarizer, bypass_cache=True)
    assert hit3 is False
    assert provider_calls == 2
    assert res3.output_data == {"summary": "Summary attempt 2"}
