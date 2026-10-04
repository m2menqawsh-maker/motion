"""
tests/ai/cache/test_crash_recovery.py
=====================================
Crash recovery, lease expiration, and worker fencing tests (S27.12).

Invariants verified:
- Worker A acquires ownership, starts execution, and crashes.
- In-flight entry does not remain permanently IN_FLIGHT.
- Worker B detects expired lease, takes over ownership, and successfully completes.
- Worker A (if revived late) is fenced by lease token and cannot poison the entry.
"""

from datetime import datetime, timedelta, timezone
import pytest

from ai.cache.errors import StaleCacheLeaseError
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams, CacheEntryStatus
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def test_setup(tmp_path):
    db_file = tmp_path / "test_crash.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    service = AICacheService(
        repository=repo,
        storage_service=storage,
        default_lease_duration_seconds=0.1,  # Short lease for crash test
    )
    return service, repo, storage


def test_owner_crash_and_waiter_takeover(test_setup):
    service, repo, storage = test_setup

    params = AICacheKeyParams(
        workspace_id="ws_crash_test",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Recoverable task"},
    )
    cache_key = derive_canonical_cache_key(params)

    # 1. Worker A claims ownership
    won_a, entry_a = repo.claim_execution_ownership(
        workspace_id="ws_crash_test",
        cache_key=cache_key,
        owner_id="worker_crashed",
        lease_token="lease_crashed_token",
        lease_duration_seconds=0.05,
        params=params,
    )
    assert won_a is True
    assert entry_a.status == CacheEntryStatus.IN_FLIGHT

    # Simulate Worker A crashing (stops responding, doesn't complete, doesn't heartbeat)
    # Artificially expire lease in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    with repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_crash_test", cache_key),
        )

    # 2. Worker B runs get_or_compute -> detects expired lease, takes over, and succeeds
    provider_b_calls = 0

    def provider_b():
        nonlocal provider_b_calls
        provider_b_calls += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"text": "Successfully computed by Worker B after crash"},
            provenance=ProvenanceRecord(source="worker_b", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    result, hit = service.get_or_compute(
        params,
        provider_b,
        wait_timeout_seconds=5.0,
        worker_id="worker_b",
    )

    assert result.output_data == {"text": "Successfully computed by Worker B after crash"}
    assert provider_b_calls == 1

    # Verify cache entry is now READY and not stuck in IN_FLIGHT
    final_entry = repo.get_entry("ws_crash_test", cache_key)
    assert final_entry.status == CacheEntryStatus.READY
    assert storage.exists(final_entry.output_ref)

    # 3. If Worker A wakes up late and tries to complete, it must be fenced!
    with pytest.raises(StaleCacheLeaseError):
        repo.complete_entry(
            workspace_id="ws_crash_test",
            cache_key=cache_key,
            owner_id="worker_crashed",
            lease_token="lease_crashed_token",
            output_ref="late_bad_output.json",
        )
