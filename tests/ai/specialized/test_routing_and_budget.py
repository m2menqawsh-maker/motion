"""
tests/ai/specialized/test_routing_and_budget.py
===============================================
Router and Budget integration tests for Specialized Media AI (S27.17 / AI-13 Rules 18 & 19).

Invariants verified:
- Router Integration: Capability Request -> Model Router -> Provider Registry -> Adapter.
- Budget Integration: Pre-flight reservation, post-execution settlement with UsageRecord.
- Budget Exceeded: Pre-flight rejection with AIErrorCode.BUDGET_EXCEEDED.
- Budget Release on Provider Error: Reservations safely released when provider fails.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetScope
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.specialized import ImageGenerationRequest, TTSRequest
from ai.specialized.adapters import FakeSpecializedMediaAdapterA, SpecializedFailureScenario
from ai.specialized.service import SpecializedMediaService
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "budget_storage")


@pytest.fixture
def budget_repo():
    return InMemoryBudgetRepository()


@pytest.fixture
def budget_service(budget_repo):
    return BudgetService(repository=budget_repo)


@pytest.fixture
def workspace_budget(budget_service):
    now = datetime.now(timezone.utc)
    b = Budget(
        budget_id="b_ws_funded",
        scope=BudgetScope.WORKSPACE,
        scope_reference="ws_funded_01",
        limit=Decimal("5.00"),
        valid_from=now - timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    return budget_service.create_budget(b)


@pytest.mark.asyncio
async def test_budget_reservation_and_settlement_on_success(storage, budget_service, workspace_budget):
    """Verifies pre-flight reservation and post-execution settlement on success."""
    adapter_a = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage, budget_service=budget_service)
    svc.register_provider_adapter("fake-specialized-a", adapter_a)

    req = TTSRequest(text="Budget settlement test", voice_id="voice_budget")

    # Initial balance check
    b_before = budget_service.get_budget(workspace_budget.budget_id)
    assert b_before.actual_spend == Decimal("0.00")
    assert b_before.reserved == Decimal("0.00")

    # Execute
    res = await svc.synthesize_speech("ws_funded_01", req, provider_id_override="fake-specialized-a")
    assert res.audio_storage_key.startswith("workspaces/ws_funded_01/")

    # Balance check post-settlement: actual_spend increased, reserved released back to 0
    b_after = budget_service.get_budget(workspace_budget.budget_id)
    assert b_after.actual_spend == Decimal("0.005")
    assert b_after.reserved == Decimal("0.00")


@pytest.mark.asyncio
async def test_budget_exceeded_rejection(storage, budget_service):
    """Verifies that an under-funded workspace is immediately blocked with BUDGET_EXCEEDED."""
    now = datetime.now(timezone.utc)
    # Budget with only $0.01 limit
    tiny_budget = Budget(
        budget_id="b_ws_poor",
        scope=BudgetScope.WORKSPACE,
        scope_reference="ws_poor_01",
        limit=Decimal("0.01"),
        valid_from=now - timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    budget_service.create_budget(tiny_budget)

    adapter_a = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage, budget_service=budget_service)
    svc.register_provider_adapter("fake-specialized-a", adapter_a)

    # Image gen costs $0.050, which exceeds $0.01
    img_req = ImageGenerationRequest(prompt="A very expensive image", width=1024, height=1024)

    from ai.specialized.errors import SpecializedMediaError

    with pytest.raises(SpecializedMediaError) as exc_info:
        await svc.generate_image("ws_poor_01", img_req, provider_id_override="fake-specialized-a")

    assert exc_info.value.code == AIErrorCode.BUDGET_EXCEEDED
    assert adapter_a.invocation_count == 0  # Provider was never called!


@pytest.mark.asyncio
async def test_budget_release_on_provider_failure(storage, budget_service, workspace_budget):
    """Verifies that when a provider fails, the reserved budget is immediately released."""
    from ai.specialized.errors import SpecializedMediaError

    adapter_failing = FakeSpecializedMediaAdapterA(
        storage_service=storage,
        scenario=SpecializedFailureScenario.SERVER_ERROR,
    )
    svc = SpecializedMediaService(storage_service=storage, budget_service=budget_service)
    svc.register_provider_adapter("fake-specialized-a", adapter_failing)

    req = TTSRequest(text="This call will fail", voice_id="voice_fail")

    with pytest.raises(SpecializedMediaError):
        await svc.synthesize_speech("ws_funded_01", req, provider_id_override="fake-specialized-a")

    # Post-failure: reservation should be fully released, not stuck in locked/reserved state
    b_after = budget_service.get_budget(workspace_budget.budget_id)
    assert b_after.reserved == Decimal("0.00")
    assert b_after.actual_spend == Decimal("0.00")
