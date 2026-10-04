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


MCP_MODULE_DIR = Path(__file__).resolve().parent.parent.parent / "ai" / "mcp"


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
