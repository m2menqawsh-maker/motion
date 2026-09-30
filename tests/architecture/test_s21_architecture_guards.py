"""
tests/architecture/test_s21_architecture_guards.py — S21 Architecture Guards:
Enforces architectural boundaries for durable runs, worker execution, and cross-process locks.
"""

import ast
from pathlib import Path
import pytest
from api.schemas.run import RunCreateRequest


ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_no_background_tasks_for_pipeline_execution():
    """
    Architecture Guard:
    FastAPI BackgroundTasks must NOT be used to execute the video pipeline.
    """
    render_router_path = ROOT / "api" / "routers" / "render.py"
    runs_router_path = ROOT / "api" / "routers" / "runs.py"

    for path in (render_router_path, runs_router_path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "fastapi":
                names = [n.name for n in node.names]
                assert "BackgroundTasks" not in names, (
                    f"Architecture violation: {path} must not import or use BackgroundTasks"
                )


def test_guard_pipeline_enforces_project_execution_lock():
    """
    Architecture Guard:
    scripts/pipeline.py must enforce ProjectExecutionLock to protect CLI and workers.
    """
    pipeline_path = ROOT / "scripts" / "pipeline.py"
    code = pipeline_path.read_text(encoding="utf-8")
    assert "ProjectExecutionLock" in code, "scripts/pipeline.py must use ProjectExecutionLock"
    assert "execution_lock.acquire()" in code, "scripts/pipeline.py must acquire execution lock"


def test_guard_runs_router_delegates_to_run_service():
    """
    Architecture Guard:
    api/routers/runs.py must delegate business logic to RunService,
    without executing raw SQL or touching repositories directly.
    """
    runs_router_path = ROOT / "api" / "routers" / "runs.py"
    tree = ast.parse(runs_router_path.read_text(encoding="utf-8"))

    # Must import RunService
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert "api.services.run_service" in imported_modules
    assert "scripts.core.run_repository" not in imported_modules, (
        "Routers must interact with RunService, not directly with RunRepository"
    )


def test_guard_worker_invokes_canonical_pipeline():
    """
    Architecture Guard:
    PipelineWorker must invoke scripts/pipeline.py via safe_subprocess
    and must not manually mutate ProjectState lifecycle.
    """
    worker_path = ROOT / "scripts" / "core" / "worker.py"
    code = worker_path.read_text(encoding="utf-8")
    assert "scripts/pipeline.py" in code, "Worker must execute canonical scripts/pipeline.py"
    assert "safe_subprocess" in code, "Worker must use safe_subprocess"
    assert "LifecycleService.transition" not in code, (
        "Worker must not directly mutate lifecycle; pipeline.py is the canonical orchestrator"
    )


def test_guard_no_client_override_of_server_owned_fields():
    """
    Architecture Guard:
    Clients cannot control worker_id, status, lease_expires_at, or failure_code.
    """
    allowed_client_fields = {"idempotency_key"}
    request_fields = set(RunCreateRequest.model_fields.keys())
    assert request_fields.issubset(allowed_client_fields), (
        f"RunCreateRequest contains server-owned fields: {request_fields - allowed_client_fields}"
    )
