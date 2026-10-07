"""
tests/architecture/test_s28_r14_architecture_guards.py
Pytest Architecture Enforcement for S28-R14: Production Integration Boundaries.

Enforces Section 23 invariants:
  1. API router directly mutating VideoDocument -> forbidden (must use AuthoringService)
  2. Renderer adapter importing/writing project repository directly -> forbidden
  3. Renderer adapter bypassing StorageService for persistent artifacts -> forbidden
  4. Renderer code changing lifecycle directly -> forbidden
  5. Authoring layer selecting concrete render engine -> forbidden
  6. AI authoring importing Remotion/FFmpeg renderer code -> forbidden
  7. Production code relying on process-local lock for document CAS -> forbidden
  8. Production idempotency implemented only with in-memory cache -> forbidden
  9. Worker using local workspace as persistent project truth -> forbidden
  10. Cross-layer direct provider calls that bypass approved adapter boundaries -> forbidden
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_api_router_does_not_directly_mutate_document():
    """R14-AG-01: API routers must delegate to AuthoringService; no direct document/SQL mutation."""
    authoring_router = REPO_ROOT / "api" / "routers" / "authoring.py"
    assert authoring_router.exists()
    content = authoring_router.read_text(encoding="utf-8")

    # Must call AuthoringService
    assert "AuthoringService" in content
    # Must NOT directly write raw SQL updates or bypass service
    assert "UPDATE project_artifact_versions" not in content
    assert "UPDATE project_states" not in content
    assert "CanonicalDocumentRepository" not in content  # router delegates to AuthoringService


def test_renderer_adapters_do_not_import_or_write_project_repo():
    """R14-AG-02: Renderer adapters must NOT import or write to project repository directly."""
    forbidden = ["ProjectRepository", "TenantRepository", "project_artifact_versions", "project_states"]
    adapter_files = [
        REPO_ROOT / "contracts" / "renderer.ts",
        REPO_ROOT / "contracts" / "remotion-renderer-adapter.ts",
        REPO_ROOT / "contracts" / "canvas-renderer-adapter.ts",
    ]

    for f in adapter_files:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for term in forbidden:
                assert term not in content, f"{f.name} must not reference {term}"


def test_renderer_adapters_do_not_bypass_storage_service():
    """R14-AG-03: Renderers produce local intermediate files; persistent publication uses StorageService."""
    executor_file = REPO_ROOT / "planner" / "production-render-graph-executor.ts"
    assert executor_file.exists()
    content = executor_file.read_text(encoding="utf-8")

    assert "IStorageService" in content or "LocalStorageService" in content
    assert "this.storage.put" in content
    # No direct raw database storage insertion of artifact blobs
    assert "INSERT INTO" not in content


def test_renderer_code_does_not_change_lifecycle_directly():
    """R14-AG-04: Renderer code must NOT import or call LifecycleService directly."""
    render_dirs = [REPO_ROOT / "planner", REPO_ROOT / "compositor"]
    for d in render_dirs:
        for f in d.glob("*.ts"):
            content = f.read_text(encoding="utf-8")
            assert "LifecycleService" not in content, f"{f.name} must not reference LifecycleService"
            assert "transition_to" not in content, f"{f.name} must not call transition_to"


def test_authoring_layer_does_not_select_concrete_renderer():
    """R14-AG-05: Authoring layer must remain engine-neutral and not select concrete renderers."""
    authoring_dir = REPO_ROOT / "authoring"
    for f in authoring_dir.glob("*.ts"):
        content = f.read_text(encoding="utf-8")
        assert "CANONICAL_RENDERER_REGISTRY" not in content, f"{f.name} must not reference renderer registry"
        assert "RemotionRendererAdapter" not in content, f"{f.name} must not reference Remotion adapter"
        assert "selectRenderer" not in content, f"{f.name} must not call selectRenderer"


def test_ai_authoring_has_zero_renderer_imports():
    """R14-AG-06: AI authoring must NOT import Remotion or FFmpeg."""
    ai_dir = REPO_ROOT / "ai"
    for py_file in ai_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        # Ensure no imports of remotion or fluent-ffmpeg
        assert not re.search(r"\bimport\s+remotion\b", content, re.IGNORECASE)
        assert not re.search(r"\bfrom\s+remotion\b", content, re.IGNORECASE)
        assert not re.search(r"\bimport\s+ffmpeg\b", content, re.IGNORECASE)


def test_document_cas_does_not_rely_on_process_local_lock():
    """R14-AG-07: CanonicalDocumentRepository must use DB transactional CAS, not process-local lock."""
    doc_repo_file = REPO_ROOT / "scripts" / "core" / "canonical_document_repository.py"
    assert doc_repo_file.exists()
    content = doc_repo_file.read_text(encoding="utf-8")

    # Must NOT rely on threading.Lock or asyncio.Lock for persistence CAS
    assert "threading.Lock" not in content
    assert "asyncio.Lock" not in content
    # Must use transactional DB commit
    assert "transaction(" in content
    assert "UPDATE project_states" in content
    assert "WHERE project_id = ? AND revision = ?" in content


def test_production_idempotency_does_not_rely_only_on_in_memory_cache():
    """R14-AG-08: Authoring idempotency repository persists to database table across process restarts."""
    idemp_repo_file = REPO_ROOT / "scripts" / "core" / "authoring_idempotency_repository.py"
    assert idemp_repo_file.exists()
    content = idemp_repo_file.read_text(encoding="utf-8")

    assert "authoring_idempotency_records" in content
    assert "INSERT INTO authoring_idempotency_records" in content
    assert "UPDATE authoring_idempotency_records" in content


def test_worker_does_not_use_local_workspace_as_persistent_project_truth():
    """R14-AG-09: Worker sandboxes are ephemeral temporary directories cleaned up automatically."""
    executor_file = REPO_ROOT / "planner" / "production-render-graph-executor.ts"
    assert executor_file.exists()
    content = executor_file.read_text(encoding="utf-8")

    assert "render_sandbox_" in content
    assert "fs.rmSync(workDir, { recursive: true, force: true })" in content


def test_api_routers_have_zero_direct_renderer_subprocess_spawns():
    """R14-AG-10: API routers do not execute raw renderer commands directly."""
    routers_dir = REPO_ROOT / "api" / "routers"
    for f in routers_dir.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        assert "subprocess.run" not in content, f"{f.name} must not spawn subprocesses"
        assert "subprocess.Popen" not in content, f"{f.name} must not spawn subprocesses"
        assert "npx remotion" not in content, f"{f.name} must not call remotion directly"
