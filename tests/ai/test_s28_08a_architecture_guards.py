"""
tests/ai/test_s28_08a_architecture_guards.py
=============================================
Architecture Guard Suite for S28-08A (User Personalization & Creative Feedback Learning).

Guards and Invariants:
1. Rule S28-08A-01: No Secondary Memory Subsystems or DBs (ai/style & ai/feedback must use S27 MemoryService).
2. Rule S28-08A-02: Zero Canonical Registry Writes from Style or Feedback subsystems.
3. Rule S28-08A-03: Zero Lifecycle or QC State Mutations (UserStyle/Feedback cannot mutate pipeline state or QC).
4. Rule S28-08A-04: Contract Boundary & Immutability (UserStyleProfile & EffectiveUserStyle frozen/forbid extras).
5. Rule S28-08A-05: AI Authority Clamping (Domain controls confidence & epistemic status; client confidence=1.0 ignored).
6. Rule S28-08A-06: Deterministic Precedence Ranking (Current explicit request strictly outranks remembered preferences).
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import List, NamedTuple
import pytest

from ai.contracts.creative.feedback import (
    EffectiveUserStyle,
    FeedbackClassification,
    StyleDecisionTrace,
    UserStyleProfile,
    WinningSource,
)
from ai.style.resolver import UserStyleResolver

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AI_ROOT = WORKSPACE_ROOT / "ai"
STYLE_ROOT = AI_ROOT / "style"
FEEDBACK_ROOT = AI_ROOT / "feedback"


class ArchitectureViolation(NamedTuple):
    file_path: str
    line_number: int
    rule_id: str
    message: str


class S28_08A_ArchitectureAnalyzer:
    """AST analyzer enforcing S28-08A architectural invariants across style and feedback subsystems."""

    FORBIDDEN_DB_DRIVERS = {
        "sqlite3",
        "psycopg2",
        "asyncpg",
        "mysql",
        "pymysql",
        "duckdb",
        "tinydb",
        "shelve",
        "redis",
    }

    FORBIDDEN_REGISTRY_PATTERNS = {
        "template-registry-data.json",
        "template-registry.tsx",
        "template_catalog.json",
        "template-aliases.ts",
        "template_index.md",
        "registry/",
        "registry\\",
    }

    FORBIDDEN_LIFECYCLE_STRINGS = {
        ".pipeline_state.json",
        "pipeline_state",
        ".qc_passed",
        "qc_passed",
        "studio_approved",
        "STATIC_PASS",
        "RUNTIME_PASS",
    }

    @classmethod
    def check_no_secondary_memory_subsystems(cls, search_dir: Path) -> List[ArchitectureViolation]:
        violations: List[ArchitectureViolation] = []
        if not search_dir.exists():
            return violations

        for py_file in search_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mod = getattr(node, "module", None) or ""
                    imported_names = [alias.name for alias in node.names]
                    for forbidden in cls.FORBIDDEN_DB_DRIVERS:
                        if forbidden in mod or any(forbidden in n for n in imported_names):
                            violations.append(
                                ArchitectureViolation(
                                    file_path=str(py_file.relative_to(WORKSPACE_ROOT)),
                                    line_number=node.lineno,
                                    rule_id="S28-08A-01",
                                    message=f"Forbidden secondary DB driver import '{forbidden}'. Must use S27 MemoryService.",
                                )
                            )

            # Check for raw SQL statements
            sql_patterns = [
                re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE),
                re.compile(r"\bSELECT\s+.*\s+FROM\b", re.IGNORECASE),
                re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
            ]
            for idx, line in enumerate(text.splitlines(), start=1):
                for pat in sql_patterns:
                    if pat.search(line):
                        violations.append(
                            ArchitectureViolation(
                                file_path=str(py_file.relative_to(WORKSPACE_ROOT)),
                                line_number=idx,
                                rule_id="S28-08A-01",
                                message=f"Raw SQL statement detected: '{line.strip()}'.",
                            )
                        )
        return violations

    @classmethod
    def check_zero_registry_writes(cls, search_dir: Path) -> List[ArchitectureViolation]:
        violations: List[ArchitectureViolation] = []
        if not search_dir.exists():
            return violations

        for py_file in search_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for idx, line in enumerate(text.splitlines(), start=1):
                for pat in cls.FORBIDDEN_REGISTRY_PATTERNS:
                    if pat in line:
                        violations.append(
                            ArchitectureViolation(
                                file_path=str(py_file.relative_to(WORKSPACE_ROOT)),
                                line_number=idx,
                                rule_id="S28-08A-02",
                                message=f"Forbidden Canonical Template Registry pattern '{pat}' in line: '{line.strip()}'.",
                            )
                        )
        return violations

    @classmethod
    def check_zero_lifecycle_mutations(cls, search_dir: Path) -> List[ArchitectureViolation]:
        violations: List[ArchitectureViolation] = []
        if not search_dir.exists():
            return violations

        for py_file in search_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for idx, line in enumerate(text.splitlines(), start=1):
                # Ignore comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for l_str in cls.FORBIDDEN_LIFECYCLE_STRINGS:
                    if l_str in line and "test" not in py_file.name:
                        violations.append(
                            ArchitectureViolation(
                                file_path=str(py_file.relative_to(WORKSPACE_ROOT)),
                                line_number=idx,
                                rule_id="S28-08A-03",
                                message=f"Forbidden lifecycle/QC mutation string '{l_str}' in line: '{line.strip()}'.",
                            )
                        )
        return violations


class TestS2808AArchitectureGuards:
    """Verifies all structural boundaries and non-negotiable rules for S28-08A."""

    def test_rule_s28_08a_01_no_secondary_memory_in_style(self):
        """ai/style contains zero secondary database drivers or raw SQL."""
        violations = S28_08A_ArchitectureAnalyzer.check_no_secondary_memory_subsystems(STYLE_ROOT)
        assert len(violations) == 0, "\n".join(str(v) for v in violations)

    def test_rule_s28_08a_01_no_secondary_memory_in_feedback(self):
        """ai/feedback contains zero secondary database drivers or raw SQL."""
        violations = S28_08A_ArchitectureAnalyzer.check_no_secondary_memory_subsystems(FEEDBACK_ROOT)
        assert len(violations) == 0, "\n".join(str(v) for v in violations)

    def test_rule_s28_08a_02_zero_registry_writes(self):
        """Neither style nor feedback subsystems touch the Canonical Template Registry."""
        violations_style = S28_08A_ArchitectureAnalyzer.check_zero_registry_writes(STYLE_ROOT)
        violations_fb = S28_08A_ArchitectureAnalyzer.check_zero_registry_writes(FEEDBACK_ROOT)
        all_violations = violations_style + violations_fb
        assert len(all_violations) == 0, "\n".join(str(v) for v in all_violations)

    def test_rule_s28_08a_03_zero_lifecycle_mutations(self):
        """Neither style nor feedback subsystems mutate pipeline lifecycle state or QC."""
        violations_style = S28_08A_ArchitectureAnalyzer.check_zero_lifecycle_mutations(STYLE_ROOT)
        violations_fb = S28_08A_ArchitectureAnalyzer.check_zero_lifecycle_mutations(FEEDBACK_ROOT)
        all_violations = violations_style + violations_fb
        assert len(all_violations) == 0, "\n".join(str(v) for v in all_violations)

    def test_rule_s28_08a_04_contracts_immutability(self):
        """UserStyleProfile and EffectiveUserStyle forbid extra fields and protect immutability."""
        assert UserStyleProfile.model_config.get("extra") == "forbid"
        assert UserStyleProfile.model_config.get("frozen") is True

        assert EffectiveUserStyle.model_config.get("extra") == "forbid"
        assert EffectiveUserStyle.model_config.get("frozen") is True

        assert FeedbackClassification.model_config.get("extra") == "forbid"
        assert FeedbackClassification.model_config.get("frozen") is True

        assert StyleDecisionTrace.model_config.get("extra") == "forbid"
        assert StyleDecisionTrace.model_config.get("frozen") is True

    def test_rule_s28_08a_06_precedence_hierarchy_ranking(self):
        """WinningSource must have CURRENT_REQUEST strictly at highest priority."""
        sources = [s.value for s in WinningSource]
        assert sources == [
            "CURRENT_REQUEST",
            "BRAND_CONSTRAINT",
            "CONFIRMED_USER_PREFERENCE",
            "INFERRED_PREFERENCE",
            "GLOBAL_DEFAULT",
        ]
