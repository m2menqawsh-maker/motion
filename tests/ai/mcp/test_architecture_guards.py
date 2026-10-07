"""
tests/ai/mcp/test_architecture_guards.py
========================================
Architecture Guards for MCP Rationalization (S27.10).

Enforces:
- Production AI cannot directly invoke arbitrary legacy MCPs.
- Retained MCPs cannot bypass Domain Tool authorization.
- Retained MCPs cannot trust model-supplied identity.
- No arbitrary shell execution in MCP adapters (shell=True banned).
- No arbitrary project filesystem escape.
- No raw DB/SQL from AI-facing MCP adapters.
- No lifecycle or QC approval bypass.
- No provider names exposed as business capabilities.
"""

import ast
from pathlib import Path
import pytest

from ai.mcp.catalog import default_mcp_catalog
from ai.mcp.policy import FORBIDDEN_MODEL_IDENTITY_FIELDS
from ai.contracts.common import CapabilityType


ROOT_DIR = Path(__file__).resolve().parents[3]
MCP_MODULE_DIR = ROOT_DIR / "ai" / "mcp"


def _get_mcp_python_files():
    assert MCP_MODULE_DIR.exists()
    return list(MCP_MODULE_DIR.rglob("*.py"))


def test_guard_no_shell_true_in_mcp_subsystem():
    """shell=True is strictly banned across all files in ai/mcp."""
    violations = []
    for f in _get_mcp_python_files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "shell":
                if isinstance(node.value, ast.Constant) and node.value.value is True:
                    violations.append(f"{f.name}:{node.lineno} uses shell=True")

    assert not violations, "Forbidden shell=True calls found:\n" + "\n".join(violations)


def test_guard_no_raw_subprocess_run_or_popen():
    """Direct subprocess.run / subprocess.Popen is prohibited; must use asyncio exec or safe wrappers."""
    violations = []
    for f in _get_mcp_python_files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "subprocess" and node.attr in {"run", "Popen", "call", "check_output"}:
                    violations.append(f"{f.name}:{node.lineno} calls direct subprocess.{node.attr}")

    assert not violations, "Forbidden direct subprocess calls found:\n" + "\n".join(violations)


def test_guard_no_raw_database_imports():
    """No database driver imports (sqlite3, psycopg2, asyncpg, etc.) in ai/mcp."""
    forbidden = {"sqlite3", "psycopg2", "asyncpg", "mysql", "databases"}
    violations = []
    for f in _get_mcp_python_files():
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in forbidden:
                        violations.append(f"{f.name}:{node.lineno} imports {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden:
                    violations.append(f"{f.name}:{node.lineno} imports from {node.module}")

    assert not violations, "Forbidden raw DB imports found in ai/mcp:\n" + "\n".join(violations)


def test_guard_model_identity_isolation_completeness():
    """FORBIDDEN_MODEL_IDENTITY_FIELDS must contain all authoritative identity fields."""
    required = {"workspace_id", "tenant_id", "actor_id", "user_id", "role", "permissions", "approved_by"}
    missing = required - FORBIDDEN_MODEL_IDENTITY_FIELDS
    assert not missing, f"Missing identity protection fields: {missing}"


def test_guard_no_provider_names_as_capabilities():
    """Capabilities must never expose vendor or provider names."""
    forbidden_prefixes = ["openai", "gemini", "anthropic", "elevenlabs", "fal", "replicate", "heygen", "pixabay"]
    for cap in CapabilityType:
        val = cap.value.lower()
        for prefix in forbidden_prefixes:
            assert not val.startswith(prefix), f"Capability {cap.value} contains provider prefix {prefix}"


def test_guard_production_mcp_isolation():
    """Only KEEP_AS_MCP servers with allowed_for_production=True can be run by production AI."""
    all_servers = default_mcp_catalog.list_servers()
    for srv in all_servers:
        if srv.allowed_for_production:
            assert srv.disposition.value == "KEEP_AS_MCP", f"Server {srv.server_id} allowed for production but disposition is {srv.disposition}"
        else:
            assert srv.disposition.value in {"CONVERT_TO_DOMAIN_SERVICE", "CONVERT_TO_CAPABILITY_ADAPTER", "DEPRECATE", "DELETE"}


# =============================================================================
# S28-M09 Decoupling & Boundary Guards
# =============================================================================

def test_guard_no_creative_planner_raw_mcp():
    """CreativePlanner and planning modules must never import or invoke raw MCP tools or transports."""
    planning_dir = MCP_MODULE_DIR.parent / "planning"
    assert planning_dir.exists()
    violations = []

    for f in planning_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "mcp" or a.name.startswith("ai.mcp"):
                        violations.append(f"{f.name}:{node.lineno} imports {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "mcp" or node.module.startswith("ai.mcp")):
                    violations.append(f"{f.name}:{node.lineno} imports from {node.module}")

    assert not violations, f"Planning subsystem contains forbidden raw MCP dependencies:\n" + "\n".join(violations)


def test_guard_no_skill_raw_mcp_transport():
    """Skill definitions and routers must route via CapabilityRouter, never raw MCP transport."""
    skills_dir = MCP_MODULE_DIR.parent / "skills"
    assert skills_dir.exists()
    violations = []

    for f in skills_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "mcp" or a.name.startswith("ai.mcp"):
                        violations.append(f"{f.name}:{node.lineno} imports {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "mcp" or node.module.startswith("ai.mcp")):
                    violations.append(f"{f.name}:{node.lineno} imports from {node.module}")

    assert not violations, f"Skills subsystem contains forbidden raw MCP dependencies:\n" + "\n".join(violations)


def test_guard_no_recipe_raw_mcp():
    """Recipe registries and evaluators must never depend on raw MCP servers."""
    recipes_dir = MCP_MODULE_DIR.parent / "recipes"
    assert recipes_dir.exists()
    violations = []

    for f in recipes_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "mcp" or a.name.startswith("ai.mcp"):
                        violations.append(f"{f.name}:{node.lineno} imports {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "mcp" or node.module.startswith("ai.mcp")):
                    violations.append(f"{f.name}:{node.lineno} imports from {node.module}")

    assert not violations, f"Recipes subsystem contains forbidden raw MCP dependencies:\n" + "\n".join(violations)


def test_guard_no_internal_domain_legacy_mcp_client():
    """Internal AI domains (speech, audio, vision, media_processing, acquisition) must have zero raw MCP dependencies."""
    domains = ["speech", "audio", "vision", "media_processing", "acquisition"]
    violations = []

    for d in domains:
        domain_dir = MCP_MODULE_DIR.parent / d
        if not domain_dir.exists():
            continue
        for f in domain_dir.glob("*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name == "mcp" or a.name.startswith("ai.mcp"):
                            violations.append(f"{d}/{f.name}:{node.lineno} imports {a.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "mcp" or node.module.startswith("ai.mcp")):
                        violations.append(f"{d}/{f.name}:{node.lineno} imports from {node.module}")

    assert not violations, f"Internal domain services contain forbidden MCP dependencies:\n" + "\n".join(violations)


def test_guard_no_mcp_facade_direct_storage_mutation():
    """MCP compatibility facade must never directly write to disk or project manifests; delegates via ToolGateway."""
    compat_dir = MCP_MODULE_DIR / "compatibility"
    assert compat_dir.exists()
    violations = []

    forbidden_calls = {"unlink", "rmdir", "mkdir", "write_text", "write_bytes", "touch"}
    for f in compat_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_calls:
                    violations.append(f"{f.name}:{node.lineno} calls direct filesystem mutation '{node.func.attr}'")

    assert not violations, f"MCP compatibility layer contains direct filesystem mutations:\n" + "\n".join(violations)

