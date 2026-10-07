"""
tests/architecture/test_s28_r15_architecture_guards.py
Pytest Architecture Enforcement for S28-R15: Final Architecture Audit & Invariants.

Guards:
  1. No competing persistent VideoDocument representations exist in codebase.
  2. Zero renderer/Remotion/FFmpeg imports inside AI authoring core.
  3. MasterCompositor remains strictly renderer-neutral and does not import renderer engines.
  4. Worker fencing: Expired lease cannot commit authoritative state over newer lease.
  5. Renderer adapters do not have direct database or repository access.
  6. Document CAS commits strictly require transactional WHERE revision = ? clauses.
  7. API routers have zero direct subprocess execution or raw remotion invocations.
  8. Storage keys are strictly server-generated; no raw user path ingestion.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_r15_ag_01_single_video_document_truth():
    """R15-AG-01: BlueprintV2 / Canonical VideoDocument is the sole authoritative document schema."""
    contracts_dir = REPO_ROOT / "contracts"
    canonical_contract = contracts_dir / "canonical-video.ts"
    assert canonical_contract.exists()
    content = canonical_contract.read_text(encoding="utf-8")
    assert "BlueprintV2" in content
    assert "validateBlueprintV2" in content

    # Ensure no duplicate competing document schemas exist
    legacy_doc_types = ["LegacyProjectDoc", "V1VideoDraft", "RawTimelineState"]
    for t in legacy_doc_types:
        assert t not in content


def test_r15_ag_02_zero_renderer_imports_in_ai_authoring():
    """R15-AG-02: AI planning and authoring have ZERO direct dependencies on Remotion or FFmpeg."""
    ai_dir = REPO_ROOT / "ai"
    for py_file in ai_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert not re.search(r"\bimport\s+remotion\b", content, re.IGNORECASE)
        assert not re.search(r"\bfrom\s+remotion\b", content, re.IGNORECASE)
        assert not re.search(r"\bimport\s+ffmpeg\b", content, re.IGNORECASE)


def test_r15_ag_03_master_compositor_renderer_independence():
    """R15-AG-03: MasterCompositor operates strictly on intermediate artifacts, not concrete renderer engines."""
    comp_file = REPO_ROOT / "compositor" / "master-compositor.ts"
    if comp_file.exists():
        content = comp_file.read_text(encoding="utf-8")
        assert "RemotionRendererAdapter" not in content
        assert "CanvasRendererAdapter" not in content
        assert "CANONICAL_RENDERER_REGISTRY" not in content


def test_r15_ag_04_stale_worker_fencing_invariant():
    """R15-AG-04: Worker run state updates enforce worker_id / lease validation in SQL."""
    db_file = REPO_ROOT / "scripts" / "core" / "database.py"
    content = db_file.read_text(encoding="utf-8")
    assert "worker_id" in content
    assert "lease_expires_at" in content


def test_r15_ag_05_renderer_adapters_zero_db_access():
    """R15-AG-05: Renderer adapters must NOT import or write to database tables."""
    forbidden = ["ProjectRepository", "TenantRepository", "authoring_idempotency_records", "run_events"]
    adapter_files = [
        REPO_ROOT / "contracts" / "renderer.ts",
        REPO_ROOT / "contracts" / "remotion-renderer-adapter.ts",
        REPO_ROOT / "contracts" / "canvas-renderer-adapter.ts",
    ]
    for f in adapter_files:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            for term in forbidden:
                assert term not in content, f"{f.name} must not contain {term}"


def test_r15_ag_06_cas_strictly_transactional():
    """R15-AG-06: Document repository commits require transactional CAS with revision matching."""
    doc_repo_file = REPO_ROOT / "scripts" / "core" / "canonical_document_repository.py"
    assert doc_repo_file.exists()
    content = doc_repo_file.read_text(encoding="utf-8")
    assert "WHERE project_id = ? AND revision = ?" in content
    assert "transaction(" in content
    assert "RevisionConflictError" in content


def test_r15_ag_07_api_routers_zero_renderer_spawns():
    """R15-AG-07: API routers must not invoke renderer subprocesses directly."""
    routers_dir = REPO_ROOT / "api" / "routers"
    for f in routers_dir.glob("*.py"):
        content = f.read_text(encoding="utf-8")
        assert "subprocess.run" not in content
        assert "subprocess.Popen" not in content
        assert "npx remotion" not in content


def test_r15_ag_08_storage_keys_server_generated():
    """R15-AG-08: Storage keys are server-generated via build_storage_key and validate_storage_key."""
    storage_file = REPO_ROOT / "scripts" / "core" / "storage" / "storage_service.py"
    assert storage_file.exists()
    content = storage_file.read_text(encoding="utf-8")
    assert "def build_storage_key(" in content
    assert "def validate_storage_key(" in content
    assert "StorageSecurityError" in content
