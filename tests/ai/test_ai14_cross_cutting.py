"""
tests/ai/test_ai14_cross_cutting.py
====================================
Cross-Cutting Integration & Tenant Isolation Suite for AI-14 (S27.18 - S27.21).

Invariants verified:
1. Prompt Tenant Isolation: Workspace A cannot view, mutate, or render Workspace B's prompts.
2. Observability Tenant Isolation: Workspace A cannot query or view Workspace B's traces/spans.
3. Batch Tenant Isolation: Workspace A's batch cache is invisible to Workspace B.
4. Architecture Integrity: Zero raw SQL driver imports, zero direct SQL executions, and zero architectural boundary bypasses across all AI-14 components.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from ai.batch.service import BatchAIService
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetScope
from ai.cache.service import AICacheService
from ai.contracts.common import CapabilityType, ExecutionClass
from ai.contracts.observability import SpanType
from ai.contracts.prompt import PromptNotFoundError, PromptRenderRequest, PromptStatus, PromptVersionNotFoundError
from ai.observability.tracer import AITracer
from ai.orchestration.service import AIRunService
from ai.prompts.service import PromptService
from ai.routing.router import ModelRouter
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_prompt_repository import SQLPromptRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend
from tests.ai.test_ai_architecture_guards import AIArchitectureAnalyzer, AI_ROOT


@pytest.fixture
def env(tmp_path):
    db_file = tmp_path / "test_cross_cutting.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")

    prompt_repo = SQLPromptRepository(engine=engine)
    trace_repo = SQLTraceRepository(engine=engine)
    run_repo = SQLAIRunRepository(engine=engine)
    cache_repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)

    prompt_service = PromptService(repository=prompt_repo)
    run_service = AIRunService(repository=run_repo)
    cache_service = AICacheService(repository=cache_repo, storage_service=storage)

    budget_repo = InMemoryBudgetRepository()
    budget_service = BudgetService(repository=budget_repo)
    now = datetime.now(timezone.utc)
    for ws in ["ws_tenant_a", "ws_tenant_b"]:
        budget_service.create_budget(
            Budget(
                budget_id=f"bgt_{ws}",
                scope=BudgetScope.WORKSPACE,
                scope_reference=ws,
                limit=Decimal("50.00"),
                valid_from=now,
                created_at=now,
                updated_at=now,
            )
        )

    batch_service = BatchAIService(
        run_service=run_service,
        budget_service=budget_service,
        cache_service=cache_service,
        router=ModelRouter(),
    )

    return {
        "engine": engine,
        "prompt_service": prompt_service,
        "trace_repo": trace_repo,
        "run_repo": run_repo,
        "cache_service": cache_service,
        "budget_service": budget_service,
        "batch_service": batch_service,
    }


def test_prompt_tenant_isolation(env):
    prompt_service: PromptService = env["prompt_service"]

    # Tenant A creates and promotes a proprietary prompt
    prompt_service.create_prompt(
        prompt_id="secret_prompt",
        template="Tenant A secret recipe with {ingredient}.",
        workspace_id="ws_tenant_a",
        variables=["ingredient"],
    )
    prompt_service.promote_prompt("secret_prompt", 1, PromptStatus.TESTING, workspace_id="ws_tenant_a")
    prompt_service.promote_prompt("secret_prompt", 1, PromptStatus.PRODUCTION, workspace_id="ws_tenant_a", eval_gate_id="gate_a")

    # Tenant B tries to query Tenant A's prompt
    tenant_b_prompt = prompt_service._repository.get_prompt("secret_prompt", 1, workspace_id="ws_tenant_b")
    assert tenant_b_prompt is None

    # Tenant B tries to render Tenant A's prompt -> raises PromptNotFoundError
    with pytest.raises(PromptNotFoundError):
        prompt_service.render_prompt(
            PromptRenderRequest(
                prompt_id="secret_prompt",
                workspace_id="ws_tenant_b",
                variables={"ingredient": "sugar"},
            )
        )

    # Tenant B cannot mutate Tenant A's prompt
    with pytest.raises(PromptVersionNotFoundError):
        prompt_service.promote_prompt("secret_prompt", 1, PromptStatus.RETIRED, workspace_id="ws_tenant_b")


def test_observability_trace_tenant_isolation(env):
    trace_repo: SQLTraceRepository = env["trace_repo"]

    # Tracer for Tenant A
    tracer_a = AITracer(
        run_id="run_tenant_a_001",
        workspace_id="ws_tenant_a",
        repository=trace_repo,
    )
    with tracer_a.start_span("tenant_a_op", SpanType.AI_RUN) as span:
        span.set_capability("VIDEO_PLANNING")
        span.set_attribute("tenant_secret", "alpha_confidential")

    # Verify Tenant A can retrieve the trace
    trace_a = trace_repo.get_trace_for_run("run_tenant_a_001", workspace_id="ws_tenant_a")
    assert trace_a is not None
    assert len(trace_a.spans) == 1

    # Verify Tenant B CANNOT retrieve Tenant A's trace
    trace_b_access = trace_repo.get_trace_for_run("run_tenant_a_001", workspace_id="ws_tenant_b")
    assert trace_b_access is None

    # Verify spans query for Tenant B returns empty list
    spans_b = trace_repo.list_spans_for_run("run_tenant_a_001", workspace_id="ws_tenant_b")
    assert spans_b == []


def test_batch_cache_tenant_isolation(env):
    batch_service: BatchAIService = env["batch_service"]

    worker_a_calls = []
    worker_b_calls = []

    def worker_a(inp):
        worker_a_calls.append(inp)
        return {"result": f"processed_for_a_{inp['id']}"}

    def worker_b(inp):
        worker_b_calls.append(inp)
        return {"result": f"processed_for_b_{inp['id']}"}

    tasks = [{"id": "item_42"}]

    # Tenant A executes batch
    res_a = batch_service.execute_batch(
        workspace_id="ws_tenant_a",
        capability=CapabilityType.REASONING,
        tasks=tasks,
        worker_fn=worker_a,
    )
    assert res_a.executed_count == 1
    assert res_a.cached_count == 0
    assert len(worker_a_calls) == 1

    # Tenant B executes IDENTICAL task payload
    res_b = batch_service.execute_batch(
        workspace_id="ws_tenant_b",
        capability=CapabilityType.REASONING,
        tasks=tasks,
        worker_fn=worker_b,
    )

    # Invariant: Tenant B MUST NOT get Tenant A's cached artifact
    assert res_b.executed_count == 1
    assert res_b.cached_count == 0
    assert len(worker_b_calls) == 1
    assert res_b.results[0]["result"]["result"] == "processed_for_b_item_42"


def test_ai14_architecture_conformance():
    """
    Mandatory Architecture Check:
    Scans all new AI-14 modules under ai/ for architectural violations.
    """
    analyzer = AIArchitectureAnalyzer()
    ai14_dirs = ["prompts", "observability", "evals", "batch"]

    all_violations = []
    for d in ai14_dirs:
        dir_path = AI_ROOT / d
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                violations = analyzer.analyze_file(py_file)
                all_violations.extend(violations)

    assert all_violations == [], f"Architecture violations detected in AI-14: {all_violations}"
