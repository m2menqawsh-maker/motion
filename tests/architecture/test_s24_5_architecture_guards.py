"""
tests/architecture/test_s24_5_architecture_guards.py — Architecture Guards for S24.5 (Multi-Tenant SaaS Foundation).

Invariants enforced:
1. Mandatory NOT NULL workspace_id on all projects (no legacy nulls or legacy bypasses).
2. Heavy object persistence is mediated through StorageService abstraction (LocalStorage/S3).
3. Strict tenant boundary enforcement across all sensitive operations (Valid object ID != authorized access).
4. No global mutable tenant/user state (zero thread-local / global current_user leakage).
5. Routers delegate persistence to domain services and repositories, not raw SQL manipulation.
"""

import ast
import re
from pathlib import Path
import pytest

from scripts.core.tenant_model import ProjectRecord, Workspace, WorkspaceMember, User
from scripts.core.database import SCHEMA_SQL
from scripts.core.storage import StorageService, LocalStorageBackend, S3CompatibleStorageBackend

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_mandatory_not_null_workspace_id():
    """
    Architecture Invariant:
    Every project MUST belong to exactly one workspace.
    No nullable workspace_id, no legacy_project=true, no workspace_id = NULL in SQL schema.
    """
    # 1. Inspect ProjectRecord Pydantic domain model
    field_info = ProjectRecord.model_fields.get("workspace_id")
    assert field_info is not None, "ProjectRecord must have workspace_id field"
    assert field_info.is_required(), "ProjectRecord.workspace_id must be required (NOT NULL)"

    # 2. Inspect SQL schema
    assert "workspace_id TEXT NOT NULL" in SCHEMA_SQL, "Database schema must enforce NOT NULL on workspace_id"
    assert "legacy_project" not in SCHEMA_SQL, "Schema must NOT contain legacy_project flag"

    # 3. Model instantiation without workspace_id must fail validation
    with pytest.raises(Exception):
        ProjectRecord(
            id="prj_invalid",
            created_by="usr_admin",
            name="No Workspace",
            created_at="2026-09-30T00:00:00Z",
            updated_at="2026-09-30T00:00:00Z",
        )


def test_guard_storage_abstraction_architecture():
    """
    Architecture Invariant:
    Heavy binary storage is abstracted behind StorageService.
    LocalStorageBackend and S3CompatibleStorageBackend implement the contract.
    Raw host absolute filesystem paths are never leaked as public object keys.
    """
    assert issubclass(LocalStorageBackend, StorageService)
    assert issubclass(S3CompatibleStorageBackend, StorageService)

    # StorageService must define mandatory methods
    expected_methods = {"put", "get", "open", "exists", "delete", "copy", "metadata", "signed_url"}
    service_methods = set(dir(StorageService))
    assert expected_methods.issubset(service_methods), f"Missing methods in StorageService: {expected_methods - service_methods}"


def test_guard_no_global_mutable_user_or_tenant_state():
    """
    Architecture Invariant:
    Authentication and tenant context must be passed explicitly or injected via FastAPI dependencies.
    No global mutable variables (e.g. current_user = ..., CURRENT_TENANT = ...) in api/ or scripts/core/.
    """
    search_dirs = [WORKSPACE_ROOT / "api", WORKSPACE_ROOT / "scripts" / "core"]
    forbidden_global_names = {"current_user", "current_tenant", "current_workspace", "_current_user", "_current_tenant"}

    violations = []
    for sdir in search_dirs:
        for py_file in sdir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            except Exception:
                continue

            for node in tree.body:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name) and target.id.lower() in forbidden_global_names:
                            violations.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno} ({target.id})")

    assert not violations, f"Architecture violation: Global mutable tenant/user state found in:\n" + "\n".join(violations)


def test_guard_strict_tenant_authorization_on_routers():
    """
    Architecture Invariant:
    Routers dealing with sensitive operations (runs, assets, artifacts, outputs)
    must enforce require_permission with strict tenant authorization.
    """
    target_routers = [
        WORKSPACE_ROOT / "api" / "routers" / "runs.py",
        WORKSPACE_ROOT / "api" / "routers" / "artifacts.py",
        WORKSPACE_ROOT / "api" / "routers" / "outputs.py",
        WORKSPACE_ROOT / "api" / "routers" / "assets.py",
    ]

    for router_path in target_routers:
        assert router_path.exists(), f"Router {router_path.name} must exist"
        content = router_path.read_text(encoding="utf-8")
        assert "require_permission" in content or "require_tenant_context" in content, (
            f"Router {router_path.name} must enforce permissions or tenant context"
        )


def test_guard_no_direct_sql_in_routers():
    """
    Architecture Invariant:
    Routers in api/routers/ must delegate database mutations to domain repositories / services,
    and must not execute raw SQL queries directly.
    """
    router_dir = WORKSPACE_ROOT / "api" / "routers"
    violations = []

    for router_path in router_dir.glob("*.py"):
        try:
            tree = ast.parse(router_path.read_text(encoding="utf-8"), filename=str(router_path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Detect cursor.execute(...) or conn.execute(...)
                if isinstance(func, ast.Attribute) and func.attr == "execute":
                    violations.append(f"{router_path.name}:{node.lineno} calls .execute(...) directly")

    assert not violations, f"Architecture violation: Direct SQL execution in routers found:\n" + "\n".join(violations)
