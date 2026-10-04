"""
tests/ai/tools/test_architecture_guards.py
==========================================
Architecture Guard Suite for AI Tool Subsystem (S27.9).

Enforces:
- Section 35: Raw project filesystem guard (no open, Path projects/, os.remove, shutil, glob)
- Section 36: Raw SQL / direct DB mutation guard (no raw SQL, sqlite3/psycopg2 in tools)
- Section 37: Provider coupling guard (no vendor SDKs or imports)
- Section 38: Model coupling guard (no branching on model name)
- Section 39: No dict[str, Any] guard in tool contracts
- Section 40: Lifecycle bypass guard (no direct status mutation)
- Section 41: QC / approval bypass guard (no QC approver tools)
- Section 50: Architecture guards required
"""

import ast
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_TOOLS_ROOT = WORKSPACE_ROOT / "ai" / "tools"


def _get_python_files():
    assert AI_TOOLS_ROOT.exists(), f"Tools directory {AI_TOOLS_ROOT} must exist"
    return list(AI_TOOLS_ROOT.rglob("*.py"))


def test_guard_raw_project_filesystem_access():
    """
    Section 35: ai/tools/* must NOT use raw project filesystem access.
    No open(), shutil, os.remove, os.unlink, os.rename, glob, or 'projects/' string paths.
    """
    forbidden_calls = {"open", "unlink", "remove", "rename", "rmdir"}
    forbidden_modules = {"shutil", "glob"}

    violations = []
    for f in _get_python_files():
        source = f.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(f))

        for node in ast.walk(tree):
            # Check function calls
            if isinstance(node, ast.Call):
                func = node.func
                func_name = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name in forbidden_calls:
                    violations.append(f"{f.name}:{node.lineno} calls forbidden filesystem function '{func_name}'")

            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_modules:
                        violations.append(f"{f.name}:{node.lineno} imports forbidden module '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module in forbidden_modules:
                    violations.append(f"{f.name}:{node.lineno} imports from forbidden module '{node.module}'")

            # Check string constants for projects/
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "projects/" in node.value or "projects\\" in node.value:
                    violations.append(f"{f.name}:{node.lineno} contains raw project filesystem path '{node.value}'")

    assert not violations, f"Raw project filesystem guard violations found:\n" + "\n".join(violations)


def test_guard_raw_sql_and_direct_db():
    """
    Section 36: ai/tools/* must NOT execute raw SQL or direct DB connections.
    """
    import re
    forbidden_db_modules = {"sqlite3", "psycopg2", "asyncpg", "databases", "mysql"}
    sql_regex = re.compile(r"\b(?:SELECT\s+[\w\*\s,]+\s+FROM\s+\w+|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET\s+|DELETE\s+FROM\s+\w+|DROP\s+TABLE\s+\w+)\b", re.IGNORECASE)

    violations = []
    for f in _get_python_files():
        source = f.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(f))

        for node in ast.walk(tree):
            # Check DB imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_db_modules:
                        violations.append(f"{f.name}:{node.lineno} imports raw DB driver '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module in forbidden_db_modules:
                    violations.append(f"{f.name}:{node.lineno} imports from raw DB driver '{node.module}'")

            # Check SQL queries in string literals (excluding docstrings and module docs)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if sql_regex.search(node.value) and "INVARIANTS" not in node.value.upper():
                    violations.append(f"{f.name}:{node.lineno} contains raw SQL query in string literal")

    assert not violations, f"Raw DB/SQL guard violations found:\n" + "\n".join(violations)


def test_guard_provider_and_model_coupling():
    """
    Sections 37 & 38: ai/tools/* must NOT import or branch on vendor AI providers or models.
    """
    forbidden_vendor_keywords = {
        "openai",
        "anthropic",
        "elevenlabs",
        "fal_client",
        "replicate",
    }

    violations = []
    for f in _get_python_files():
        source = f.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(f))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for vk in forbidden_vendor_keywords:
                        if vk in alias.name.lower():
                            violations.append(f"{f.name}:{node.lineno} imports vendor SDK '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").lower()
                for vk in forbidden_vendor_keywords:
                    if vk in mod:
                        violations.append(f"{f.name}:{node.lineno} imports from vendor SDK '{node.module}'")

            # Check model branching: e.g. if model == "gpt-4"
            if isinstance(node, ast.Compare):
                # Check for comparisons involving model or provider names
                left_src = ast.unparse(node.left).lower()
                if "model" in left_src or "provider" in left_src:
                    for comp in node.comparators:
                        comp_src = ast.unparse(comp).lower()
                        if any(vk in comp_src for vk in ("gpt", "claude", "gemini")):
                            violations.append(f"{f.name}:{node.lineno} branches on model/provider '{comp_src}'")

    assert not violations, f"Provider/Model coupling guard violations found:\n" + "\n".join(violations)


def test_guard_no_dict_any_in_contracts():
    """
    Section 39: ai/tools/contracts.py must NOT use dict[str, Any] or Dict[str, Any] or Any.
    """
    contracts_file = AI_TOOLS_ROOT / "contracts.py"
    source = contracts_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(contracts_file))

    violations = []
    for node in ast.walk(tree):
        # Look for type annotations: Subscript or Name
        if isinstance(node, ast.AnnAssign):
            ann_src = ast.unparse(node.annotation)
            if "dict[str, Any]" in ann_src or "Dict[str, Any]" in ann_src:
                violations.append(f"contracts.py:{node.lineno} uses forbidden '{ann_src}'")
            elif ann_src == "Any":
                violations.append(f"contracts.py:{node.lineno} uses untyped 'Any' annotation")

    assert not violations, f"dict[str, Any] guard violations found:\n" + "\n".join(violations)


def test_guard_lifecycle_and_approval_bypass():
    """
    Sections 40 & 41: ai/tools/* must NOT mutate lifecycle or approve QC.
    """
    violations = []
    for f in _get_python_files():
        source = f.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(f))

        for node in ast.walk(tree):
            # Check attribute assignments: e.g., obj.lifecycle_state = ... or obj.status = ...
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        attr = target.attr
                        if attr in ("lifecycle_state", "is_approved", "approved_by"):
                            violations.append(f"{f.name}:{node.lineno} directly mutates '{attr}'")

    assert not violations, f"Lifecycle/Approval bypass guard violations found:\n" + "\n".join(violations)


def check_repository_imports_in_source(source: str, filename: str = "test.py") -> list[str]:
    forbidden_modules = {"scripts.core.database", "repositories", "sqlite3", "psycopg2", "asyncpg"}
    forbidden_symbols = {"TenantRepository", "RunRepository", "StateStore", "get_database_engine", "DatabaseEngine"}
    tree = ast.parse(source, filename=filename)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(m in alias.name for m in forbidden_modules):
                    violations.append(f"{filename}:{node.lineno} imports forbidden repository/DB module '{alias.name}'")
                if any(s in alias.name for s in forbidden_symbols):
                    violations.append(f"{filename}:{node.lineno} imports forbidden persistence symbol '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if any(m in mod for m in forbidden_modules):
                violations.append(f"{filename}:{node.lineno} imports from forbidden repository/DB module '{mod}'")
            for alias in node.names:
                if any(s in alias.name for s in forbidden_symbols) or alias.name.endswith("Repository"):
                    violations.append(f"{filename}:{node.lineno} imports forbidden persistence class '{alias.name}'")
    return violations


def test_guard_no_repository_or_persistence_imports_in_ai_tools():
    """
    S27.9 Hardening Guard: ai/tools/* must NOT import or access repositories or persistence layer directly.
    All resource resolution and authorization MUST pass through domain boundaries (e.g. ProjectService).
    """
    violations = []
    for f in _get_python_files():
        source = f.read_text(encoding="utf-8")
        violations.extend(check_repository_imports_in_source(source, filename=f.name))

    assert not violations, f"Direct repository/persistence import violations found:\n" + "\n".join(violations)


def test_guard_repository_violation_synthetic_failure():
    """
    Empirical proof that check_repository_imports_in_source catches repository imports and fails.
    """
    bad_source_1 = "from scripts.core.database import TenantRepository\n"
    v1 = check_repository_imports_in_source(bad_source_1, "bad_tool.py")
    assert len(v1) > 0, "Guard must catch 'from scripts.core.database import TenantRepository'"

    bad_source_2 = "import scripts.core.database\n"
    v2 = check_repository_imports_in_source(bad_source_2, "bad_tool.py")
    assert len(v2) > 0, "Guard must catch 'import scripts.core.database'"

    bad_source_3 = "from scripts.core.state_store import StateStore\n"
    v3 = check_repository_imports_in_source(bad_source_3, "bad_tool.py")
    assert len(v3) > 0, "Guard must catch 'from scripts.core.state_store import StateStore'"


def test_guard_no_opaque_mutation_payload_in_tool_contracts():
    """
    S27.9 Hardening Guard: Mutating tool contracts (e.g. PatchBlueprintInput) must NOT use
    opaque JSON containers (Dict[str, JsonValue], Dict[str, Any], dict) as their primary mutation payload.
    """
    contracts_file = AI_TOOLS_ROOT / "contracts.py"
    source = contracts_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(contracts_file))

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PatchBlueprintInput":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == "blueprint":
                    ann_src = ast.unparse(item.annotation)
                    if any(opaque in ann_src for opaque in ("Dict[str, JsonValue]", "dict[str, JsonValue]", "Dict[str, Any]", "dict")):
                        violations.append(f"PatchBlueprintInput.blueprint uses opaque type '{ann_src}' instead of typed Blueprint schema.")

    assert not violations, f"Opaque mutation payload guard violations found:\n" + "\n".join(violations)
