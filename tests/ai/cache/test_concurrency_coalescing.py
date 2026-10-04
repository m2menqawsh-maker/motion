"""
tests/ai/cache/test_concurrency_coalescing.py
=============================================
Real concurrency, request coalescing, and cross-process proof (S27.12).

Invariants verified:
- 100 concurrent identical cacheable requests -> exactly 1 provider execution, 100 successful consumers.
- 100 requests with 50 input A and 50 input B -> exactly 2 provider executions (1 for A, 1 for B).
- Non-cacheable capability (CachePolicy.NEVER) obeys policy without forced coalescing.
- Multi-repository / cross-process proof: distinct instances sharing the same DB file coordinate ownership.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading
import time
import pytest

from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def test_setup(tmp_path):
    db_file = tmp_path / "test_coalescing.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    service = AICacheService(repository=repo, storage_service=storage)
    return service, engine, storage, db_file


def test_100_concurrent_identical_requests_single_execution(test_setup):
    service, _, _, _ = test_setup

    provider_lock = threading.Lock()
    provider_executions = 0

    def slow_authoritative_provider():
        nonlocal provider_executions
        with provider_lock:
            provider_executions += 1

        # Simulate provider latency
        time.sleep(0.08)

        now = datetime.now(timezone.utc)
        result = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"answer": "42: universal answer"},
            provenance=ProvenanceRecord(
                source="fake_coalesced_provider",
                timestamp=now,
            ),
        )
        return result, result.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_heavy_load",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"question": "What is the meaning of life?"},
    )

    def worker_task(worker_idx: int):
        res, hit = service.get_or_compute(
            params,
            slow_authoritative_provider,
            wait_timeout_seconds=20.0,
            poll_interval_seconds=0.02,
            worker_id=f"w_{worker_idx}",
        )
        return res, hit

    num_concurrent_requests = 100
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(worker_task, i) for i in range(num_concurrent_requests)]
        results = [f.result() for f in futures]

    # Verify: Exactly 1 provider execution occurred
    assert provider_executions == 1, f"Expected exactly 1 execution, got {provider_executions}"

    # Verify: 100 successful consumers with identical output
    assert len(results) == 100
    for res, hit in results:
        assert res.output_data == {"answer": "42: universal answer"}

    # At least 90 of them should be cache hits / coalesced waiters
    hits = sum(1 for _, hit in results if hit is True)
    assert hits >= 95, f"Expected at least 95 waiters to register as hits, got {hits}"


def test_different_inputs_produce_distinct_coalesced_groups(test_setup):
    service, _, _, _ = test_setup

    provider_lock = threading.Lock()
    execution_counts = {"A": 0, "B": 0}

    def provider_for(input_type: str):
        def _exec():
            with provider_lock:
                execution_counts[input_type] += 1
            time.sleep(0.05)
            now = datetime.now(timezone.utc)
            res = CapabilityResult(
                capability=CapabilityTypeEnum.SUMMARIZATION,
                status=CapabilityStatus.SUCCESS,
                output_data={"group": input_type},
                provenance=ProvenanceRecord(source="test_provider", timestamp=now),
            )
            return res, res.model_dump_json().encode("utf-8")
        return _exec

    params_a = AICacheKeyParams(
        workspace_id="ws_multi",
        capability=CapabilityTypeEnum.SUMMARIZATION,
        input_data={"group": "A"},
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_multi",
        capability=CapabilityTypeEnum.SUMMARIZATION,
        input_data={"group": "B"},
    )

    def task(group: str, idx: int):
        params = params_a if group == "A" else params_b
        res, hit = service.get_or_compute(
            params,
            provider_for(group),
            wait_timeout_seconds=20.0,
            poll_interval_seconds=0.02,
            worker_id=f"w_{group}_{idx}",
        )
        return res

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures_a = [executor.submit(task, "A", i) for i in range(50)]
        futures_b = [executor.submit(task, "B", i) for i in range(50)]
        results_a = [f.result() for f in futures_a]
        results_b = [f.result() for f in futures_b]

    # Exactly 1 provider execution for A, exactly 1 for B -> Total 2!
    assert execution_counts["A"] == 1
    assert execution_counts["B"] == 1
    assert len(results_a) == 50
    assert len(results_b) == 50
    assert all(r.output_data == {"group": "A"} for r in results_a)
    assert all(r.output_data == {"group": "B"} for r in results_b)


def test_non_cacheable_concurrency_no_forced_coalescing(test_setup):
    service, _, _, _ = test_setup

    provider_lock = threading.Lock()
    executions = 0

    def fake_video_gen():
        nonlocal executions
        with provider_lock:
            executions += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.VIDEO_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"frame": "generated"},
            provenance=ProvenanceRecord(source="test_video", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_video",
        capability=CapabilityTypeEnum.VIDEO_GENERATION,  # CachePolicy.NEVER
        input_data={"prompt": "render 3D cube"},
    )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(lambda: service.get_or_compute(params, fake_video_gen)) for _ in range(15)]
        for f in futures:
            res, hit = f.result()
            assert hit is False

    # All 15 requests executed independently because capability is non-cacheable
    assert executions == 15


def test_cross_instance_coalescing_proof(test_setup):
    """
    Proves that request coalescing is NOT just an in-memory lock or dict.
    Two completely distinct AICacheService instances with separate repositories
    connected to the same SQLite database coordinate ownership via DB CAS.
    """
    _, _, storage, db_file = test_setup

    # Instance A
    engine_a = DatabaseEngine(f"sqlite:///{db_file}")
    repo_a = SQLAICacheRepository(engine=engine_a)
    service_a = AICacheService(repository=repo_a, storage_service=storage)

    # Instance B
    engine_b = DatabaseEngine(f"sqlite:///{db_file}")
    repo_b = SQLAICacheRepository(engine=engine_b)
    service_b = AICacheService(repository=repo_b, storage_service=storage)

    provider_calls = 0
    lock = threading.Lock()

    def slow_provider():
        nonlocal provider_calls
        with lock:
            provider_calls += 1
        time.sleep(0.08)
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"msg": "cross-process result"},
            provenance=ProvenanceRecord(source="cross_provider", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    params = AICacheKeyParams(
        workspace_id="ws_cross_proc",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"seed": "same_seed_42"},
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(lambda: service_a.get_or_compute(params, slow_provider, worker_id="instance_a"))
        future_b = executor.submit(lambda: service_b.get_or_compute(params, slow_provider, worker_id="instance_b"))
        res_a, hit_a = future_a.result()
        res_b, hit_b = future_b.result()

    # Across distinct instances, provider executed exactly once!
    assert provider_calls == 1
    assert res_a.output_data == {"msg": "cross-process result"}
    assert res_b.output_data == {"msg": "cross-process result"}
    assert (hit_a or hit_b) is True
