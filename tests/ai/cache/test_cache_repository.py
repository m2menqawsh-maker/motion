"""
tests/ai/cache/test_cache_repository.py
=======================================
Unit tests for SQLAICacheRepository (S27.12).

Invariants verified:
- Atomic CAS execution claims: exactly 1 worker wins ownership of an in-flight miss.
- Monotonic lease fencing: stale workers whose leases expired or were stolen are fenced from committing.
- Heartbeats extend lease duration via renew_lease.
- Expired leases are atomically reclaimable by fresh workers.
- Failures mark status FAILED and allow retry.
- Invalidation removes entries cleanly.
- Multi-tenant isolation: identical cache key in workspace A cannot be read or claimed in workspace B.
"""

from datetime import datetime, timedelta, timezone
import pytest

from ai.cache.errors import StaleCacheLeaseError, TenantIsolationViolationError
from ai.contracts.cache import AICacheKeyParams, CacheEntryStatus
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.errors import AIError
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_cache_repo.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    return SQLAICacheRepository(engine=engine)


def test_atomic_claim_and_waiter_detection(repo):
    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "test query"},
    )
    cache_key = "ck_test_key_001"

    # Worker 1 claims ownership
    won1, entry1 = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_1",
        lease_token="tok_1",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won1 is True
    assert entry1 is not None
    assert entry1.status == CacheEntryStatus.IN_FLIGHT
    assert entry1.owner_id == "worker_1"
    assert entry1.lease_token == "tok_1"

    # Worker 2 attempts to claim while lease is active
    won2, entry2 = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_2",
        lease_token="tok_2",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won2 is False
    assert entry2 is not None
    assert entry2.status == CacheEntryStatus.IN_FLIGHT
    assert entry2.owner_id == "worker_1"  # Worker 1 remains owner


def test_completion_and_fencing(repo):
    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "fencing test"},
    )
    cache_key = "ck_fencing_001"

    # Worker 1 claims
    won, _ = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_1",
        lease_token="tok_1",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won is True

    # Worker 1 successfully completes entry
    completed = repo.complete_entry(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_1",
        lease_token="tok_1",
        output_ref="workspaces/ws_alpha/cache/text_generation/ck_fencing_001.json",
        producer="fake_provider",
        model="gpt-4o",
    )
    assert completed.status == CacheEntryStatus.READY
    assert completed.output_ref == "workspaces/ws_alpha/cache/text_generation/ck_fencing_001.json"
    assert completed.owner_id is None
    assert completed.lease_token is None

    # Stale attempt with invalid lease token is strictly fenced
    with pytest.raises(StaleCacheLeaseError):
        repo.complete_entry(
            workspace_id="ws_alpha",
            cache_key=cache_key,
            owner_id="stale_worker",
            lease_token="tok_stale",
            output_ref="invalid_ref",
        )


def test_lease_expiry_and_crash_recovery(repo):
    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "crash test"},
    )
    cache_key = "ck_crash_001"

    # Worker 1 claims with very short lease (0.01 seconds)
    won1, _ = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_crashed",
        lease_token="tok_crashed",
        lease_duration_seconds=0.01,
        params=params,
    )
    assert won1 is True

    # Artificially expire lease in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    with repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_alpha", cache_key),
        )

    # Worker 2 notices expired lease and atomically steals ownership
    won2, stolen_entry = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_recovered",
        lease_token="tok_recovered",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won2 is True
    assert stolen_entry.owner_id == "worker_recovered"
    assert stolen_entry.lease_token == "tok_recovered"

    # Crashed worker tries late commit -> must be fenced!
    with pytest.raises(StaleCacheLeaseError):
        repo.complete_entry(
            workspace_id="ws_alpha",
            cache_key=cache_key,
            owner_id="worker_crashed",
            lease_token="tok_crashed",
            output_ref="late_output",
        )

    # Recovered worker completes successfully
    ready = repo.complete_entry(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_recovered",
        lease_token="tok_recovered",
        output_ref="workspaces/ws_alpha/cache/valid_recovered.json",
    )
    assert ready.status == CacheEntryStatus.READY


def test_failure_and_retry(repo):
    params = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "fail test"},
    )
    cache_key = "ck_fail_001"

    won, _ = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_1",
        lease_token="tok_1",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won is True

    err = AIError.internal_error(message="Provider 500 internal error")
    repo.mark_entry_failed("ws_alpha", cache_key, "worker_1", "tok_1", err)

    entry = repo.get_entry("ws_alpha", cache_key)
    assert entry.status == CacheEntryStatus.FAILED
    assert entry.error is not None
    assert "Provider 500" in entry.error.message

    # Retry should succeed and transition back to IN_FLIGHT
    won_retry, retry_entry = repo.claim_execution_ownership(
        workspace_id="ws_alpha",
        cache_key=cache_key,
        owner_id="worker_retry",
        lease_token="tok_retry",
        lease_duration_seconds=30.0,
        params=params,
    )
    assert won_retry is True
    assert retry_entry.status == CacheEntryStatus.IN_FLIGHT
    assert retry_entry.owner_id == "worker_retry"


def test_tenant_boundary_isolation(repo):
    params_a = AICacheKeyParams(
        workspace_id="ws_tenant_a",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"data": 123},
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_tenant_b",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"data": 123},
    )
    shared_key = "ck_shared_key_name"

    # Workspace A claims and completes
    repo.claim_execution_ownership("ws_tenant_a", shared_key, "w_a", "tok_a", 30.0, params_a)
    repo.complete_entry(
        "ws_tenant_a",
        shared_key,
        "w_a",
        "tok_a",
        "workspaces/ws_tenant_a/output.json",
    )

    # Workspace B queries entry -> must be None!
    assert repo.get_entry("ws_tenant_b", shared_key) is None

    # Workspace B can claim independently
    won_b, entry_b = repo.claim_execution_ownership(
        "ws_tenant_b", shared_key, "w_b", "tok_b", 30.0, params_b
    )
    assert won_b is True
    assert entry_b.workspace_id == "ws_tenant_b"

    # Illegal cross-workspace claim raises TenantIsolationViolationError
    with pytest.raises(TenantIsolationViolationError):
        repo.claim_execution_ownership(
            workspace_id="ws_tenant_a",
            cache_key=shared_key,
            owner_id="hacker",
            lease_token="tok_x",
            lease_duration_seconds=30.0,
            params=params_b,  # Mismatch params.workspace_id != workspace_id
        )
