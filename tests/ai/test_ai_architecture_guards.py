"""
tests/ai/test_ai_architecture_guards.py
========================================
Architecture Guard Suite for S27 (AI & Media Intelligence Platform).

Enforces strict architectural boundaries defined in ADR-004:
1. AI is not Source of Truth (no raw database bypass / raw SQL).
2. AI is not lifecycle authority (no direct mutation of state.lifecycle_state).
3. AI is not filesystem authority (no raw project filesystem access).
4. AI is not QC / approval authority (no direct .studio_approved or ReviewDecision forging).
5. AI is not template registry authority (no direct mutation of templates/ or registry/).
6. Business mutations must pass through controlled Tool Layer / Domain Services.

Includes both:
- Live inspection of all files under `ai/` (fails CI if any violation is introduced).
- Synthetic positive & negative tests proving the analyzer catches violations without false positives.
"""

import ast
from pathlib import Path
from typing import List, NamedTuple
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
AI_ROOT = WORKSPACE_ROOT / "ai"


class ArchitectureViolation(NamedTuple):
    file_path: str
    line_number: int
    rule_id: str
    message: str


class AIArchitectureAnalyzer:
    """
    AST-based structural analyzer that inspects Python source code for
    direct architectural boundary bypasses in the AI subsystem.
    """

    FORBIDDEN_DB_MODULES = {
        "sqlite3",
        "psycopg2",
        "asyncpg",
        "mysql",
        "mysql.connector",
        "databases",
    }

    FORBIDDEN_FILESYSTEM_PATTERNS = [
        "projects/",
        "projects\\",
        ".pipeline_state.json",
    ]

    FORBIDDEN_QC_FILES = {
        ".studio_approved",
        ".studio_unlocked",
        ".qc_passed",
        "06_qc_report.json",
    }

    FORBIDDEN_REGISTRY_PATTERNS = [
        "templates/",
        "templates\\",
        "registry/",
        "registry\\",
    ]

    WRITE_MODES = {"w", "wb", "w+", "wb+", "a", "ab", "a+", "ab+"}

    def __init__(self):
        self.violations: List[ArchitectureViolation] = []

    def analyze_file(self, file_path: Path) -> List[ArchitectureViolation]:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception as exc:
            return [
                ArchitectureViolation(
                    file_path=str(file_path),
                    line_number=0,
                    rule_id="AI-PARSE-ERR",
                    message=f"Failed to parse Python file: {exc}",
                )
            ]
        return self.analyze_tree(tree, file_path=file_path)

    def analyze_tree(self, tree: ast.AST, file_path: Path | str = "<memory>") -> List[ArchitectureViolation]:
        violations: List[ArchitectureViolation] = []
        path_str = str(file_path)

        for node in ast.walk(tree):
            # 1. Check forbidden database driver imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if alias.name in self.FORBIDDEN_DB_MODULES or root_mod in self.FORBIDDEN_DB_MODULES:
                        violations.append(
                            ArchitectureViolation(
                                file_path=path_str,
                                line_number=node.lineno,
                                rule_id="AI-ARCH-001-RAW-DB",
                                message=(
                                    f"Direct database driver import '{alias.name}' is forbidden in ai/*. "
                                    f"Database access must be mediated via approved repositories (e.g., RunRepository)."
                                ),
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                root_mod = mod.split(".")[0]
                if mod in self.FORBIDDEN_DB_MODULES or root_mod in self.FORBIDDEN_DB_MODULES:
                    violations.append(
                        ArchitectureViolation(
                            file_path=path_str,
                            line_number=node.lineno,
                            rule_id="AI-ARCH-001-RAW-DB",
                            message=(
                                f"Direct database driver import from '{mod}' is forbidden in ai/*. "
                                f"Database access must be mediated via approved repositories."
                            ),
                        )
                    )

            # 2. Check direct SQL execution (.execute on cursor/connection)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"execute", "executemany"}:
                    # Check if first arg looks like raw SQL string
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        sql_lead = node.args[0].value.strip().upper()
                        if any(sql_lead.startswith(kw) for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER"]):
                            violations.append(
                                ArchitectureViolation(
                                    file_path=path_str,
                                    line_number=node.lineno,
                                    rule_id="AI-ARCH-002-RAW-SQL",
                                    message=(
                                        f"Direct SQL execution is forbidden in ai/*. "
                                        f"Use domain repositories or services instead of executing raw SQL."
                                    ),
                                )
                            )

            # 3. Check direct mutation of lifecycle_state
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                        violations.append(
                            ArchitectureViolation(
                                file_path=path_str,
                                line_number=node.lineno,
                                rule_id="AI-ARCH-003-LIFECYCLE-MUTATION",
                                message=(
                                    f"Direct assignment to 'lifecycle_state' is strictly forbidden in ai/*. "
                                    f"Lifecycle transitions must be executed exclusively by LifecycleService.transition()."
                                ),
                            )
                        )

            # 4. Check raw project filesystem access
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                # Check for project path literals used in file system contexts
                if any(val.startswith(pat) or f"/{pat}" in val or f"\\{pat}" in val or val == pat for pat in self.FORBIDDEN_FILESYSTEM_PATTERNS):
                    violations.append(
                        ArchitectureViolation(
                            file_path=path_str,
                            line_number=node.lineno,
                            rule_id="AI-ARCH-004-PROJECT-FS-BYPASS",
                            message=(
                                f"Direct project filesystem reference '{val}' found in ai/*. "
                                f"Direct access to projects/ is forbidden. Access must be mediated via "
                                f"Domain Services (ProjectService, AssetService, StorageService)."
                            ),
                        )
                    )

                # 5. Check QC and review authority bypass (.studio_approved, .qc_passed, etc.)
                if any(qc_file in val for qc_file in self.FORBIDDEN_QC_FILES):
                    violations.append(
                        ArchitectureViolation(
                            file_path=path_str,
                            line_number=node.lineno,
                            rule_id="AI-ARCH-005-QC-AUTHORITY-BYPASS",
                            message=(
                                f"Direct QC/approval token reference '{val}' is forbidden in ai/*. "
                                f"AI cannot approve gates or declare QC passed. Authority belongs solely "
                                f"to SmartQC, ProbePlanner, and ReviewService."
                            ),
                        )
                    )

            # 6. Check template registry direct write/mutation
            if isinstance(node, ast.Call):
                func = node.func
                is_write_call = False
                target_nodes = []

                if isinstance(func, ast.Attribute) and func.attr in {"write_text", "write_bytes"}:
                    is_write_call = True
                    target_nodes.append(func.value)
                elif isinstance(func, ast.Name) and func.id == "open":
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value in self.WRITE_MODES:
                        is_write_call = True
                        target_nodes.append(node.args[0])

                if is_write_call:
                    for target_node in target_nodes:
                        for subnode in ast.walk(target_node):
                            if isinstance(subnode, ast.Constant) and isinstance(subnode.value, str):
                                if any(pat in subnode.value for pat in self.FORBIDDEN_REGISTRY_PATTERNS):
                                    violations.append(
                                        ArchitectureViolation(
                                            file_path=path_str,
                                            line_number=node.lineno,
                                            rule_id="AI-ARCH-006-REGISTRY-MUTATION",
                                            message=(
                                                f"Direct mutation of template registry '{subnode.value}' is forbidden in ai/*. "
                                                f"Templates are immutable system assets."
                                            ),
                                        )
                                    )

            # 7. Check direct approval authorization forging (ReviewDecisionType.APPROVED)
            if isinstance(node, ast.Attribute) and node.attr == "APPROVED":
                val_node = node.value
                is_review_decision_enum = False
                if isinstance(val_node, ast.Name) and val_node.id == "ReviewDecisionType":
                    is_review_decision_enum = True
                elif isinstance(val_node, ast.Attribute) and val_node.attr == "ReviewDecisionType":
                    is_review_decision_enum = True

                if is_review_decision_enum:
                    violations.append(
                        ArchitectureViolation(
                            file_path=path_str,
                            line_number=node.lineno,
                            rule_id="AI-ARCH-007-APPROVAL-AUTHORITY-BYPASS",
                            message=(
                                "Direct approval authorization forging ('ReviewDecisionType.APPROVED') is forbidden in ai/*. "
                                "Approvals must be granted exclusively by server-verified human reviewers through ReviewService."
                            ),
                        )
                    )

        return violations


# ============================================================================
# LIVE CI ARCHITECTURE GUARD (Runs against real ai/ codebase)
# ============================================================================

def test_ai_subsystem_architecture_conformance():
    """
    Mandatory CI Architecture Gate for S27.0+:
    Scans every Python file in `ai/` and asserts zero architectural violations.
    Fails immediately if any file in `ai/` bypasses domain services, touches raw
    project filesystem, mutates lifecycle state, executes raw SQL, or attempts QC bypass.
    """
    assert AI_ROOT.exists(), f"Subsystem root {AI_ROOT} must exist"

    py_files = list(AI_ROOT.rglob("*.py"))
    assert len(py_files) >= 1, "ai/ must contain at least one package file"

    analyzer = AIArchitectureAnalyzer()
    all_violations: List[ArchitectureViolation] = []

    for py_file in py_files:
        violations = analyzer.analyze_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        formatted = "\n".join(
            f"[{v.rule_id}] {v.file_path}:{v.line_number} -> {v.message}"
            for v in all_violations
        )
        pytest.fail(
            f"\n🚨 S27 AI Architecture Guard detected {len(all_violations)} violation(s):\n{formatted}\n"
            f"Review ADR-004 for allowed integration boundaries."
        )


# ============================================================================
# SYNTHETIC UNIT TESTS (Verify Guard Effectiveness & Absence of False Positives)
# ============================================================================

def test_guard_detects_forbidden_db_imports():
    """Negative test: Guard must catch forbidden database driver imports."""
    forbidden_code = """
import sqlite3
import psycopg2
from asyncpg import connect

def get_data():
    pass
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_db.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-001-RAW-DB" in rule_ids
    assert len(violations) == 3


def test_guard_detects_direct_sql_execution():
    """Negative test: Guard must catch direct raw SQL execution."""
    forbidden_code = """
def update_something(cursor):
    cursor.execute("UPDATE projects SET status = 'active' WHERE id = 'prj_1'")
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_sql.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-002-RAW-SQL" in rule_ids


def test_guard_detects_direct_lifecycle_mutation():
    """Negative test: Guard must catch direct assignment to lifecycle_state."""
    forbidden_code = """
def advance_project(state):
    state.lifecycle_state = "COMPLETE"
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_lifecycle.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-003-LIFECYCLE-MUTATION" in rule_ids


def test_guard_detects_raw_project_filesystem_access():
    """Negative test: Guard must catch raw project path references."""
    forbidden_code = """
def read_blueprint(project_id):
    path = f"projects/{project_id}/05_blueprint.json"
    with open(path, "r") as f:
        return f.read()
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_fs.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-004-PROJECT-FS-BYPASS" in rule_ids


def test_guard_detects_qc_authority_bypass():
    """Negative test: Guard must catch attempts to create or reference .studio_approved directly."""
    forbidden_code = """
def approve_studio(project_dir):
    with open(project_dir + "/.studio_approved", "w") as f:
        f.write("approved")
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_qc.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-005-QC-AUTHORITY-BYPASS" in rule_ids


def test_guard_detects_registry_mutation():
    """Negative test: Guard must catch direct writes to template registry."""
    forbidden_code = """
def inject_template():
    Path("templates/elements/NewComp.tsx").write_text("export default null;")
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_registry.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-006-REGISTRY-MUTATION" in rule_ids


def test_guard_allows_internal_package_file_access():
    """
    Positive test: Guard must NOT produce false positives when ai/* accesses
    its own internal package configs, schema contracts, or local resources.
    """
    valid_code = """
from pathlib import Path
from pydantic import BaseModel

class AIConfig(BaseModel):
    model_name: str

def load_internal_schema():
    contract_dir = Path(__file__).parent / "contracts" / "schemas"
    config_file = Path(__file__).resolve().parent / "config.json"
    return contract_dir.exists()
"""
    tree = ast.parse(valid_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "ai/contracts/loader.py")
    assert violations == [], f"Expected 0 violations for valid internal code, got: {violations}"


def test_guard_allows_domain_service_usage():
    """
    Positive test: Guard must allow proper usage of Domain Services and typed contracts.
    """
    valid_code = """
from pydantic import BaseModel
from api.services.project_service import ProjectService
from api.services.asset_service import AssetService
from scripts.core.security.principal import Principal

async def get_project_info(project_id: str, principal: Principal):
    return ProjectService.list_projects(principal)
"""
    tree = ast.parse(valid_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "ai/tools/project_tool.py")
    assert violations == [], f"Expected 0 violations for domain service usage, got: {violations}"


def test_guard_detects_approval_authority_bypass():
    """Negative test: Guard must catch attempts to forge ReviewDecisionType.APPROVED."""
    forbidden_code = """
from scripts.core.state_model import ReviewDecisionType

def forge_approval():
    return ReviewDecisionType.APPROVED
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_approval.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-007-APPROVAL-AUTHORITY-BYPASS" in rule_ids


def test_guard_detects_pipeline_state_bypass():
    """Negative test: Guard must catch direct references to .pipeline_state.json."""
    forbidden_code = """
import json

def read_raw_state():
    with open(".pipeline_state.json", "r") as f:
        return json.load(f)
"""
    tree = ast.parse(forbidden_code)
    violations = AIArchitectureAnalyzer().analyze_tree(tree, "synthetic_state.py")
    rule_ids = [v.rule_id for v in violations]
    assert "AI-ARCH-004-PROJECT-FS-BYPASS" in rule_ids

