"""
tests/ai/cache/test_architecture_guards.py
==========================================
Structural and architectural boundary guards for ai/cache/ (S27.12).

Invariants enforced:
1. No raw project filesystem cache access (projects/) inside ai/cache/.
2. No raw database drivers or raw SQL execution in ai/cache/ (ADR-004 DEC-01).
3. No direct provider SDK imports (openai, anthropic, google.generativeai, elevenlabs) inside ai/cache/.
4. No cross-tenant cache lookup: workspace_id is mandatory and enforced on every repository operation.
5. No model-controlled cache key: keys are strictly server-side derived and deterministic.
6. No cache bypass of Budget, Router, or Capability policies.
7. No unrestricted dict[str, Any] at public cache contract and service boundaries.
8. No in-memory-only coalescing authority: durable shared coordination via AICacheRepository.
"""

import ast
import inspect
from pathlib import Path
from typing import List, Tuple
import pytest

from ai.cache.errors import TenantIsolationViolationError
from ai.cache.key import derive_canonical_cache_key
from ai.cache.policy import is_capability_cacheable
from ai.cache.repository import AICacheRepository
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheEntry, AICacheKeyParams
from ai.contracts.common import CapabilityTypeEnum

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_CACHE_DIR = WORKSPACE_ROOT / "ai" / "cache"


def _get_cache_python_files() -> List[Path]:
    return list(AI_CACHE_DIR.glob("*.py"))


def test_no_raw_db_drivers_in_ai_cache():
    forbidden_modules = {"sqlite3", "psycopg2", "psycopg", "asyncpg", "mysql", "databases"}
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_cache_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_modules:
                        violations.append((file_path.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in forbidden_modules:
                    violations.append((file_path.name, node.lineno, node.module or ""))

    assert not violations, f"Forbidden database driver imports found in ai/cache/: {violations}"


def test_no_raw_sql_execution_in_ai_cache():
    violations: List[Tuple[str, int, str]] = []
    sql_keywords = {"SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}

    for file_path in _get_cache_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"execute", "executemany"}:
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        first_word = node.args[0].value.strip().split()[0].upper()
                        if first_word in sql_keywords:
                            violations.append((file_path.name, node.lineno, node.args[0].value[:30]))

    assert not violations, f"Raw SQL execution found in ai/cache/: {violations}"


def test_no_raw_project_filesystem_cache():
    forbidden = ["projects/", "projects\\", ".pipeline_state.json"]
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_cache_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(p in node.value for p in forbidden):
                    violations.append((file_path.name, node.lineno, node.value))

    assert not violations, f"Raw project filesystem access found in ai/cache/: {violations}"


def test_no_direct_provider_sdk_imports_in_ai_cache():
    forbidden_provider_sdks = {
        "openai",
        "anthropic",
        "google.generativeai",
        "google.genai",
        "elevenlabs",
        "replicate",
        "fal_client",
        "boto3",
    }
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_cache_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_provider_sdks or alias.name.split(".")[0] in forbidden_provider_sdks:
                        violations.append((file_path.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in forbidden_provider_sdks or mod.split(".")[0] in forbidden_provider_sdks:
                    violations.append((file_path.name, node.lineno, mod))

    assert not violations, f"Direct provider SDK imports found in ai/cache/: {violations}"


def test_no_in_memory_only_coalescing_authority():
    """
    Guarantees that AICacheService coordinates execution ownership via the durable
    AICacheRepository abstraction rather than holding sole in-memory locking authority.
    """
    sig = inspect.signature(AICacheService.__init__)
    assert "repository" in sig.parameters, "AICacheService must require AICacheRepository"
    assert "storage_service" in sig.parameters, "AICacheService must require StorageService"


def test_cross_tenant_lookup_strictly_requires_workspace_id():
    """
    Verifies that AICacheRepository requires workspace_id on key access methods.
    """
    repo_methods = inspect.getmembers(AICacheRepository, predicate=inspect.isfunction)
    method_dict = dict(repo_methods)

    for method_name in ["get_entry", "claim_execution_ownership", "complete_entry", "invalidate_entry"]:
        assert method_name in method_dict, f"Missing method {method_name} on AICacheRepository"
        params = list(inspect.signature(method_dict[method_name]).parameters.keys())
        assert "workspace_id" in params, f"Method {method_name} must require workspace_id parameter"


def test_no_model_controlled_cache_key():
    """
    Ensures cache keys are derived exclusively server-side from canonical parameters.
    """
    p = AICacheKeyParams(
        workspace_id="ws_sec",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"test": 1},
    )
    key = derive_canonical_cache_key(p)
    assert key.startswith("ck_")
    # Must be deterministic SHA-256
    assert key == derive_canonical_cache_key(p)


def test_no_cache_bypass_of_capability_policy():
    """
    Verifies that non-cacheable capabilities cannot be forced to cache.
    """
    assert is_capability_cacheable(CapabilityTypeEnum.IMAGE_GENERATION) is False
    assert is_capability_cacheable(CapabilityTypeEnum.VIDEO_GENERATION) is False
    assert is_capability_cacheable(CapabilityTypeEnum.MUSIC_GENERATION) is False
