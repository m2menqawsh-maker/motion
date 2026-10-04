"""
tests/ai/cache/test_poisoning_and_invalidation.py
=================================================
Cache poisoning protection, failure handling, missing artifacts, and invalidation tests (S27.12).

Invariants verified:
- Malformed model output (missing output_data): rejected, never committed as READY.
- Provider failure: marked as FAILED in cache; never committed as READY.
- Missing or corrupted artifact in StorageService: detected, stale entry invalidated, recomputed cleanly.
- Natural invalidations:
  - Input content change -> cache MISS.
  - Content hash change -> cache MISS.
  - Settings change -> cache MISS.
  - Model change -> cache MISS.
  - Model version change -> cache MISS.
  - Prompt version change -> cache MISS.
  - Analysis version change -> cache MISS.
- TTL expiration: expired entry is not returned as fresh; recomputed and updated.
"""

from datetime import datetime, timedelta, timezone
import pytest

from ai.cache.errors import CacheError, CachePoisoningError
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams, CacheEntryStatus
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from ai.contracts.errors import AIError
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def cache_service(tmp_path):
    db_file = tmp_path / "test_poison.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    return AICacheService(repository=repo, storage_service=storage)


def test_malformed_model_output_does_not_poison_cache(cache_service):
    def malformed_provider():
        now = datetime.now(timezone.utc)
        # Attempt to create result with empty output_data
        result = CapabilityResult.model_construct(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data=None,  # Missing output data!
            provenance=ProvenanceRecord(source="bad_model", timestamp=now),
        )
        return result, b"{}"

    params = AICacheKeyParams(
        workspace_id="ws_poison",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Generate something"},
    )

    with pytest.raises(CachePoisoningError):
        cache_service.get_or_compute(params, malformed_provider)

    # Verify cache entry was NOT committed as READY
    cache_key = derive_canonical_cache_key(params)
    entry = cache_service.repository.get_entry("ws_poison", cache_key)
    assert entry is not None
    assert entry.status == CacheEntryStatus.FAILED


def test_provider_failure_does_not_create_successful_cache_entry(cache_service):
    def failing_provider():
        raise RuntimeError("Provider is down with 503")

    params = AICacheKeyParams(
        workspace_id="ws_fail",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Will fail"},
    )

    with pytest.raises(RuntimeError) as exc_info:
        cache_service.get_or_compute(params, failing_provider)

    assert "Provider is down" in str(exc_info.value)

    cache_key = derive_canonical_cache_key(params)
    entry = cache_service.repository.get_entry("ws_fail", cache_key)
    assert entry is not None
    assert entry.status == CacheEntryStatus.FAILED
    assert "Provider is down" in entry.error.message



def test_missing_or_corrupt_artifact_recovers_and_recomputes(cache_service):
    provider_calls = 0

    def valid_provider():
        nonlocal provider_calls
        provider_calls += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.SUMMARIZATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"summary": f"Computed content v{provider_calls}"},
            provenance=ProvenanceRecord(source="provider", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_corrupt",
        capability=CapabilityTypeEnum.SUMMARIZATION,
        input_data={"doc": "important document"},
    )
    cache_key = derive_canonical_cache_key(params)

    # 1. First execution -> populates cache and saves artifact
    res1, hit1 = cache_service.get_or_compute(params, valid_provider)
    assert hit1 is False
    assert provider_calls == 1

    entry = cache_service.repository.get_entry("ws_corrupt", cache_key)
    assert entry.status == CacheEntryStatus.READY
    assert cache_service.storage_service.exists(entry.output_ref)

    # 2. Corrupt or delete the artifact behind the cache's back
    cache_service.storage_service.delete(entry.output_ref)
    assert not cache_service.storage_service.exists(entry.output_ref)

    # 3. Next request queries cache: detects missing artifact, invalidates DB entry, recomputes!
    res2, hit2 = cache_service.get_or_compute(params, valid_provider)
    assert hit2 is False  # Cache miss recompute
    assert provider_calls == 2
    assert res2.output_data == {"summary": "Computed content v2"}

    # Verify fresh artifact is restored
    entry2 = cache_service.repository.get_entry("ws_corrupt", cache_key)
    assert entry2.status == CacheEntryStatus.READY
    assert cache_service.storage_service.exists(entry2.output_ref)


def test_natural_invalidation_matrix(cache_service):
    provider_calls = 0

    def provider():
        nonlocal provider_calls
        provider_calls += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"seq": provider_calls},
            provenance=ProvenanceRecord(source="provider", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    base = AICacheKeyParams(
        workspace_id="ws_matrix",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"text": "hello"},
        content_hash="hash_v1",
        settings={"temperature": 0.5},
        model="gpt-4o",
        model_version="1.0.0",
        contract_version="1.0.0",
        prompt_version="1.0.0",
        analysis_version="1.0.0",
    )

    # Initial call
    cache_service.get_or_compute(base, provider)
    assert provider_calls == 1

    # Exact same parameters -> HIT (calls remains 1)
    cache_service.get_or_compute(base, provider)
    assert provider_calls == 1

    # 1. Change input data -> MISS
    p_input = base.model_copy(update={"input_data": {"text": "hello world"}})
    cache_service.get_or_compute(p_input, provider)
    assert provider_calls == 2

    # 2. Change content hash -> MISS
    p_content = base.model_copy(update={"content_hash": "hash_v2"})
    cache_service.get_or_compute(p_content, provider)
    assert provider_calls == 3

    # 3. Change settings -> MISS
    p_settings = base.model_copy(update={"settings": {"temperature": 0.9}})
    cache_service.get_or_compute(p_settings, provider)
    assert provider_calls == 4

    # 4. Change model -> MISS
    p_model = base.model_copy(update={"model": "claude-3-5"})
    cache_service.get_or_compute(p_model, provider)
    assert provider_calls == 5

    # 5. Change model version -> MISS
    p_model_v = base.model_copy(update={"model_version": "2.0.0"})
    cache_service.get_or_compute(p_model_v, provider)
    assert provider_calls == 6

    # 6. Change prompt version -> MISS
    p_prompt_v = base.model_copy(update={"prompt_version": "2.0.0"})
    cache_service.get_or_compute(p_prompt_v, provider)
    assert provider_calls == 7

    # 7. Change analysis version -> MISS
    p_analysis_v = base.model_copy(update={"analysis_version": "2.0.0"})
    cache_service.get_or_compute(p_analysis_v, provider)
    assert provider_calls == 8


def test_ttl_expiration_recomputes(cache_service):
    provider_calls = 0

    def provider():
        nonlocal provider_calls
        provider_calls += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"call": provider_calls},
            provenance=ProvenanceRecord(source="provider", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_ttl",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "TTL test"},
    )
    cache_key = derive_canonical_cache_key(params)

    # Populate with TTL = 1 second
    cache_service.get_or_compute(params, provider, ttl_seconds=1)
    assert provider_calls == 1

    # Artificially expire TTL in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with cache_service.repository.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_ttl", cache_key),
        )

    # Query again -> must detect expired TTL, recompute, and update
    res, hit = cache_service.get_or_compute(params, provider, ttl_seconds=60)
    assert hit is False
    assert provider_calls == 2
    assert res.output_data == {"call": 2}
