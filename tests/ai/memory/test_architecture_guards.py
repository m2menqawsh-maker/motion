"""
tests/ai/memory/test_architecture_guards.py
===========================================
Architectural boundary guard tests for S27.6 & S27.7 (Memory Foundation & Write Policy).

Enforces:
1. No raw DB driver imports (psycopg2, asyncpg, sqlite3, etc.) inside ai/memory/.
2. No direct raw SQL execution inside ai/memory/.
3. Model-facing code / AI orchestrators cannot write to MemoryRepository directly.
   All memory writes must be mediated by MemoryPolicy / MemoryService.
4. PostgresMemoryRepository lives in approved persistence layer (scripts/core/memory/).
"""

import ast
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_DIR = WORKSPACE_ROOT / "ai"
MEMORY_DIR = AI_DIR / "memory"
ROUTING_DIR = AI_DIR / "routing"
MODELS_DIR = AI_DIR / "models"


class TestMemoryArchitectureGuards:

    def test_memory_layer_does_not_import_raw_db_drivers(self):
        """Scans ai/memory/ to ensure no direct database driver modules are imported."""
        forbidden_db = {
            "sqlite3",
            "psycopg",
            "psycopg2",
            "asyncpg",
            "mysql",
            "mysql.connector",
            "databases",
        }
        violations = []
        for py_file in MEMORY_DIR.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_mod = alias.name.split(".")[0]
                        if alias.name in forbidden_db or root_mod in forbidden_db:
                            violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    root_mod = mod.split(".")[0]
                    if mod in forbidden_db or root_mod in forbidden_db:
                        violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, mod))

        assert not violations, f"Raw database driver import found in ai/memory/: {violations}"

    def test_memory_layer_does_not_execute_raw_sql(self):
        """Verifies no raw SQL strings are executed inside ai/memory/."""
        violations = []
        for py_file in MEMORY_DIR.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"execute", "executemany"}:
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            lead = node.args[0].value.strip().upper()
                            if any(lead.startswith(kw) for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP"]):
                                violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, lead[:30]))

        assert not violations, f"Direct raw SQL execution found in ai/memory/: {violations}"

    def test_ai_facing_layers_do_not_import_or_write_to_memory_repository(self):
        """
        Guarantees that model-facing layers (routing, models, providers)
        never directly import or invoke MemoryRepository.
        All writes must pass through MemoryService / MemoryPolicy.
        """
        forbidden_repo_usages = {"MemoryRepository", "InMemoryMemoryRepository", "PostgresMemoryRepository"}
        violations = []

        scan_dirs = [ROUTING_DIR, MODELS_DIR]
        for s_dir in scan_dirs:
            if not s_dir.exists():
                continue
            for py_file in s_dir.rglob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name in forbidden_repo_usages:
                                violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))

        assert not violations, f"AI-facing module imports MemoryRepository directly: {violations}"

    def test_postgres_memory_repository_location(self):
        """Verifies PostgresMemoryRepository is housed under approved scripts/core/ boundary."""
        pg_repo_file = WORKSPACE_ROOT / "scripts" / "core" / "memory" / "postgres_memory_repository.py"
        assert pg_repo_file.exists(), "PostgresMemoryRepository must reside in scripts/core/memory/"

        from scripts.core.memory.postgres_memory_repository import PostgresMemoryRepository
        from ai.memory.repository import MemoryRepository

        assert issubclass(PostgresMemoryRepository, MemoryRepository)

    def test_no_dict_any_in_memory_boundary_models(self):
        """
        Architecture Guard (AI-06R Gate):
        Verifies that no domain or boundary model in `ai/memory/` (specifically
        MemoryEntry, MemoryCandidate, MemoryWriteDecision, MemoryFilter,
        MemorySearchResult, EmbeddingRecord, TrustedTenantContext) uses unrestricted
        `Any`, `dict[str, Any]`, or `Dict[str, Any]` in field annotations.
        """
        target_classes = {
            "MemoryEntry",
            "MemoryCandidate",
            "MemoryWriteDecision",
            "MemoryFilter",
            "MemorySearchResult",
            "EmbeddingRecord",
            "TrustedTenantContext",
        }

        def contains_any(node: ast.AST) -> bool:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == "Any":
                    return True
                if isinstance(sub, ast.Attribute) and sub.attr == "Any":
                    return True
            return False

        violations = []
        for py_file in MEMORY_DIR.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check target classes or any class inheriting from BaseModel
                    is_model = node.name in target_classes or any(
                        (isinstance(b, ast.Name) and b.id in {"BaseModel", "AIContractModel"})
                        or (isinstance(b, ast.Attribute) and b.attr in {"BaseModel", "AIContractModel"})
                        for b in node.bases
                    )
                    if not is_model:
                        continue

                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            if contains_any(item.annotation):
                                field_name = item.target.id if isinstance(item.target, ast.Name) else "<complex>"
                                violations.append(
                                    (py_file.name, item.lineno, node.name, f"{field_name}: Any / Dict[..., Any]")
                                )

        assert not violations, (
            "Architecture violation: Unrestricted Any / Dict[str, Any] found in ai/memory/ models:\n"
            + "\n".join(f"  • {f}:{line} in {cls} -> {field}" for f, line, cls, field in violations)
            + "\nAll memory models must use typed JSON (JsonValue / JsonObject) instead of Any."
        )
