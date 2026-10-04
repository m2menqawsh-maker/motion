"""
tests/ai/cache/test_tenant_isolation.py
=======================================
Multi-tenant isolation and zero cross-tenant leakage tests (S27.12).

Invariants verified:
- Workspace A caches a result.
- Workspace B sends identical input, settings, and capability.
- Workspace B receives a cache MISS and executes its own provider call.
- Workspace B cannot read, see, or reuse Workspace A's cache metadata or stored artifacts.
- Workspace A cache invalidation does not purge or affect Workspace B.
- Zero cross-tenant data leakage.
"""

from datetime import datetime, timezone
import pytest

from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def cache_service(tmp_path):
    db_file = tmp_path / "test_tenant_isolation.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    return AICacheService(repository=repo, storage_service=storage)


def test_zero_cross_tenant_leakage(cache_service):
    provider_calls = {"ws_alpha": 0, "ws_beta": 0}

    def provider_for(ws: str):
        def _exec():
            provider_calls[ws] += 1
            now = datetime.now(timezone.utc)
            res = CapabilityResult(
                capability=CapabilityTypeEnum.TEXT_GENERATION,
                status=CapabilityStatus.SUCCESS,
                output_data={"tenant_secret": f"secret_data_for_{ws}"},
                provenance=ProvenanceRecord(source="tenant_provider", timestamp=now),
            )
            return res, res.model_dump_json().encode("utf-8")
        return _exec

    # Identical input payload
    shared_input = {"prompt": "Confidential customer inquiry"}

    params_a = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data=shared_input,
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_beta",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data=shared_input,
    )

    # 1. Workspace A executes and populates cache
    res_a, hit_a = cache_service.get_or_compute(params_a, provider_for("ws_alpha"))
    assert hit_a is False
    assert provider_calls["ws_alpha"] == 1
    assert res_a.output_data == {"tenant_secret": "secret_data_for_ws_alpha"}

    # 2. Workspace B executes with IDENTICAL input -> MUST be a cache MISS!
    res_b, hit_b = cache_service.get_or_compute(params_b, provider_for("ws_beta"))
    assert hit_b is False
    assert provider_calls["ws_beta"] == 1
    assert res_b.output_data == {"tenant_secret": "secret_data_for_ws_beta"}

    # 3. Workspace B queries its own cache -> HIT
    res_b_2, hit_b_2 = cache_service.get_or_compute(params_b, provider_for("ws_beta"))
    assert hit_b_2 is True
    assert provider_calls["ws_beta"] == 1  # No duplicate execution
    assert res_b_2.output_data == {"tenant_secret": "secret_data_for_ws_beta"}

    # Verify keys are completely distinct
    key_a = derive_canonical_cache_key(params_a)
    key_b = derive_canonical_cache_key(params_b)
    assert key_a != key_b

    # Verify Workspace B cannot access Workspace A's DB entry
    entry_a = cache_service.repository.get_entry("ws_alpha", key_a)
    entry_b_lookup_a = cache_service.repository.get_entry("ws_beta", key_a)
    assert entry_a is not None
    assert entry_b_lookup_a is None

    # Verify storage isolation: artifact paths reside in isolated tenant prefixes
    assert "workspaces/ws_alpha/" in entry_a.output_ref
    entry_b = cache_service.repository.get_entry("ws_beta", key_b)
    assert "workspaces/ws_beta/" in entry_b.output_ref


def test_tenant_invalidation_isolation(cache_service):
    params_a = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"data": "test"},
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_beta",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"data": "test"},
    )

    def dummy_provider(ws):
        def _fn():
            now = datetime.now(timezone.utc)
            res = CapabilityResult(
                capability=CapabilityTypeEnum.TEXT_GENERATION,
                status=CapabilityStatus.SUCCESS,
                output_data={"ws": ws},
                provenance=ProvenanceRecord(source="test", timestamp=now),
            )
            return res, res.model_dump_json().encode("utf-8")
        return _fn

    cache_service.get_or_compute(params_a, dummy_provider("ws_alpha"))
    cache_service.get_or_compute(params_b, dummy_provider("ws_beta"))

    # Invalidate all entries in Workspace A
    purged = cache_service.repository.invalidate_workspace("ws_alpha")
    assert purged == 1

    # Workspace A is purged
    key_a = derive_canonical_cache_key(params_a)
    assert cache_service.repository.get_entry("ws_alpha", key_a) is None

    # Workspace B is untouched!
    key_b = derive_canonical_cache_key(params_b)
    assert cache_service.repository.get_entry("ws_beta", key_b) is not None
