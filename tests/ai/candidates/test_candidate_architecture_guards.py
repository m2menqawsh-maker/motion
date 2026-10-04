"""
tests/ai/candidates/test_candidate_architecture_guards.py
==========================================================
Architecture Guard Suite for TemplateCandidate Domain (S28-07A).

Invariants Verified:
1. ai/candidates/ contains ZERO raw SQL statements or direct database driver imports (ADR-004 DEC-01).
2. ai/candidates/ contains ZERO raw filesystem mutations bypassing StorageService (write_text, write_bytes, open(..., 'w')).
3. Candidate subsystem contains ZERO writes or mutations targeting the Canonical Template Registry
   ('registry/', 'template-registry-data.json', 'template_catalog.json', 'templates/').
4. CandidateService never invokes registry generators or promotion mutations.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CANDIDATES_ROOT = WORKSPACE_ROOT / "creative_governance" / "candidates"
AI_CANDIDATES_ROOT = WORKSPACE_ROOT / "ai" / "candidates"
CANDIDATES_REPO = WORKSPACE_ROOT / "scripts" / "core" / "template_candidate_repository.py"


def test_no_raw_sql_in_candidates_domain():
    """Ensures ai/candidates/ has zero SQL queries or DB driver imports."""
    if not CANDIDATES_ROOT.exists():
        pytest.skip("ai/candidates not yet created")

    forbidden_drivers = {"sqlite3", "psycopg2", "mysql", "asyncpg", "pymysql"}
    sql_patterns = [
        re.compile(r"\bSELECT\b\s+.*\s+\bFROM\b", re.IGNORECASE),
        re.compile(r"\bINSERT\b\s+\bINTO\b", re.IGNORECASE),
        re.compile(r"\bUPDATE\b\s+.*\s+\bSET\b", re.IGNORECASE),
        re.compile(r"\bDELETE\b\s+\bFROM\b", re.IGNORECASE),
    ]

    violations: List[str] = []
    for py_file in CANDIDATES_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", None)
                names = [alias.name for alias in node.names]
                if mod in forbidden_drivers or any(n in forbidden_drivers for n in names):
                    violations.append(f"{py_file.name}:{node.lineno}: Forbidden DB driver import")

        for i, line in enumerate(text.splitlines(), start=1):
            for pat in sql_patterns:
                if pat.search(line):
                    violations.append(f"{py_file.name}:{i}: Raw SQL query pattern '{line.strip()}'")

    assert len(violations) == 0, "SQL violations in ai/candidates:\n" + "\n".join(violations)


def test_no_raw_filesystem_writes_in_candidates_domain():
    """Ensures ai/candidates/ delegates all file mutations to StorageService."""
    if not CANDIDATES_ROOT.exists():
        pytest.skip("ai/candidates not yet created")

    violations: List[str] = []
    for py_file in CANDIDATES_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    for arg in node.args[1:]:
                        if isinstance(arg, ast.Constant) and any(m in str(arg.value) for m in ["w", "a", "x"]):
                            violations.append(f"{py_file.name}:{node.lineno}: Raw open('{arg.value}')")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
                    violations.append(f"{py_file.name}:{node.lineno}: Raw Path.{node.func.attr}()")

    assert len(violations) == 0, "Raw FS write violations in ai/candidates:\n" + "\n".join(violations)


def test_candidate_subsystem_has_no_registry_mutation_rights():
    """Ensures CandidateService and candidate repos have NO code mutating canonical registry."""
    files_to_check = []
    if CANDIDATES_ROOT.exists():
        files_to_check.extend(list(CANDIDATES_ROOT.rglob("*.py")))
    if CANDIDATES_REPO.exists():
        files_to_check.append(CANDIDATES_REPO)

    forbidden_patterns = [
        "template-registry-data.json",
        "template-registry.tsx",
        "template-runtime-contract.json",
        "generate_registry",
        "ground-truth/template_catalog.json",
    ]

    violations: List[str] = []
    for py_file in files_to_check:
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if any(p in line for p in forbidden_patterns) and not line.strip().startswith("#"):
                violations.append(f"{py_file.name}:{i}: Forbidden registry reference '{line.strip()}'")

    assert len(violations) == 0, "Forbidden registry references found:\n" + "\n".join(violations)


def test_validation_layer_has_no_promotion_or_approval_authority():
    """
    Ensures CandidateValidationService, gates, and runner have ZERO imports
    or calls to promotion/approval services or approved/promoted status.
    Transition to VALIDATED is restricted exclusively to TemplateCandidateService.transition_to_validated.
    """
    validation_files = [
        f for f in CANDIDATES_ROOT.rglob("*.py")
        if f.name not in ("review_service.py", "promotion_service.py", "__init__.py")
    ]
    
    # Strictly forbidden across candidate validation domain
    universal_forbidden = [
        "PromotionService",
        "promote_candidate",
        "ApprovalService",
        "approve_candidate",
        "CandidateStatus.APPROVED",
        "CandidateStatus.PROMOTED",
    ]

    violations: List[str] = []
    for py_file in validation_files:
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for term in universal_forbidden:
                if term in line:
                    violations.append(f"{py_file.name}:{i}: Forbidden promotion/approval reference '{term}'")

            # CandidateStatus.VALIDATED is forbidden in gates and validators;
            # permitted ONLY within TemplateCandidateService.transition_to_validated authority
            if "CandidateStatus.VALIDATED" in line and py_file.name != "service.py":
                violations.append(f"{py_file.name}:{i}: Direct reference to CandidateStatus.VALIDATED outside service.py")

    assert len(violations) == 0, "Validation layer authority violations:\n" + "\n".join(violations)


def test_review_service_has_no_promotion_or_registry_authority():
    """
    Ensures CandidateReviewService has ZERO authority or code to promote candidates
    or mutate the Canonical Template Registry (S28-07D Non-Negotiable Invariants).
    APPROVED ≠ PROMOTED.
    """
    review_service_file = CANDIDATES_ROOT / "review_service.py"
    if not review_service_file.exists():
        pytest.skip("review_service.py not yet present")

    forbidden_in_review = [
        "PromotionService",
        "promote_candidate",
        "CandidateStatus.PROMOTED",
        "template-registry-data.json",
        "template-registry.tsx",
        "template_catalog.json",
        "registry/",
    ]

    text = review_service_file.read_text(encoding="utf-8")
    violations: List[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for term in forbidden_in_review:
            if term in line:
                violations.append(f"review_service.py:{i}: Forbidden promotion/registry reference '{term}'")

    assert len(violations) == 0, "Review service authority violations:\n" + "\n".join(violations)


def test_router_has_no_direct_candidate_status_assignment():
    """
    Ensures candidate_reviews API router is transport-only:
    it never mutates candidate status or calls repository status assignment directly.
    """
    router_file = WORKSPACE_ROOT / "api" / "routers" / "candidate_reviews.py"
    if not router_file.exists():
        pytest.skip("candidate_reviews.py router not yet present")

    text = router_file.read_text(encoding="utf-8")
    forbidden_router_patterns = [
        "status =",
        "status=",
        "update_candidate_status_cas",
        "save_candidate",
        "CandidateStatus.APPROVED",
        "CandidateStatus.REJECTED",
        "CandidateStatus.AWAITING_APPROVAL",
    ]

    violations: List[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for term in forbidden_router_patterns:
            if term in line:
                violations.append(f"candidate_reviews.py:{i}: Direct router mutation attempt '{term}'")

    assert len(violations) == 0, "Router direct mutation violations:\n" + "\n".join(violations)


def test_ai_layer_has_no_direct_candidate_approval():
    """
    Ensures AI agents, planners, and skills have ZERO references to CandidateReviewService.approve
    or recording CandidateStatus.APPROVED (S28-07D Non-Negotiable Invariants).
    AI creator ≠ Reviewer.
    """
    ai_dirs = [WORKSPACE_ROOT / "ai" / "taste", WORKSPACE_ROOT / "ai" / "skills"]
    planner_file = WORKSPACE_ROOT / "ai" / "creative_planner.py"
    
    files_to_check: List[Path] = []
    if planner_file.exists():
        files_to_check.append(planner_file)
    for d in ai_dirs:
        if d.exists():
            files_to_check.extend(list(d.rglob("*.py")))

    forbidden_approval_terms = [
        "CandidateReviewService",
        "CandidateReviewDecision",
        ".approve(",
        "CandidateStatus.APPROVED",
    ]

    violations: List[str] = []
    for py_file in files_to_check:
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for term in forbidden_approval_terms:
                if term in line:
                    violations.append(f"{py_file.name}:{i}: AI layer approval violation '{term}'")

    assert len(violations) == 0, "AI layer approval violations:\n" + "\n".join(violations)



def test_validation_layer_has_no_package_manager_execution():
    """Ensures static validation never executes npm install, pnpm add, yarn add, pip install."""
    validation_files = list(CANDIDATES_ROOT.rglob("*.py"))
    worker_script = WORKSPACE_ROOT / "scripts" / "validators" / "candidate_ast_worker.cjs"
    if worker_script.exists():
        validation_files.append(worker_script)

    forbidden_commands = [
        "npm install",
        "npm i ",
        "pnpm add",
        "pnpm install",
        "yarn add",
        "yarn install",
        "pip install",
    ]

    violations: List[str] = []
    for file_path in validation_files:
        text = file_path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("#"):
                continue
            for cmd in forbidden_commands:
                if cmd in line:
                    violations.append(f"{file_path.name}:{i}: Forbidden package manager execution '{cmd}'")

    assert len(violations) == 0, "Package manager execution violations in validation layer:\n" + "\n".join(violations)


def test_ai_layer_has_no_promotion_authority():
    """
    Ensures AI agents, planners, and skills have ZERO references to PromotionService.promote_candidate
    or recording CandidateStatus.PROMOTED (S28-07E Non-Negotiable Invariants).
    AI ≠ Promotion Authority.
    """
    ai_dirs = [WORKSPACE_ROOT / "ai" / "taste", WORKSPACE_ROOT / "ai" / "skills"]
    planner_file = WORKSPACE_ROOT / "ai" / "creative_planner.py"

    files_to_check: List[Path] = []
    if planner_file.exists():
        files_to_check.append(planner_file)
    for d in ai_dirs:
        if d.exists():
            files_to_check.extend(list(d.rglob("*.py")))

    forbidden_promotion_terms = [
        "PromotionService",
        "TemplateRegistryPublisher",
        ".promote_candidate(",
        "CandidateStatus.PROMOTED",
        "PromotionManifest",
    ]

    violations: List[str] = []
    for py_file in files_to_check:
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for term in forbidden_promotion_terms:
                if term in line:
                    violations.append(f"{py_file.name}:{i}: AI layer promotion violation '{term}'")

    assert len(violations) == 0, "AI layer promotion violations:\n" + "\n".join(violations)


def test_router_has_no_direct_candidate_promotion_mutation():
    """
    Ensures candidate_promotions API router is transport-only:
    it never mutates candidate status or calls repository status assignment directly,
    nor mutates the filesystem/registry directly.
    """
    router_file = WORKSPACE_ROOT / "api" / "routers" / "candidate_promotions.py"
    if not router_file.exists():
        pytest.skip("candidate_promotions.py router not yet present")

    text = router_file.read_text(encoding="utf-8")
    forbidden_router_patterns = [
        "status =",
        "status=",
        "update_candidate_status_cas",
        "save_candidate",
        "CandidateStatus.PROMOTED",
        "template-registry-data.json",
        "template-registry.tsx",
        "template_catalog.json",
        "templates/",
    ]

    violations: List[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for term in forbidden_router_patterns:
            if term in line:
                violations.append(f"candidate_promotions.py:{i}: Direct router mutation attempt '{term}'")

    assert len(violations) == 0, "Router direct promotion mutation violations:\n" + "\n".join(violations)


def test_promotion_service_is_sole_promoted_status_authority():
    """
    Ensures that within the candidate subsystem, transition to CandidateStatus.PROMOTED is
    referenced exclusively by PromotionService (and the enum definition itself).
    Validation ≠ Promotion, Reviewer ≠ Promotion, Router ≠ Promotion.
    """
    files_to_check = []
    if CANDIDATES_ROOT.exists():
        files_to_check.extend(list(CANDIDATES_ROOT.rglob("*.py")))

    violations: List[str] = []
    for py_file in files_to_check:
        if py_file.name in ("promotion_service.py", "__init__.py"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "CandidateStatus.PROMOTED" in line:
                violations.append(f"{py_file.name}:{i}: Unauthorized CandidateStatus.PROMOTED reference '{line.strip()}'")

    assert len(violations) == 0, "Unauthorized CandidateStatus.PROMOTED references:\n" + "\n".join(violations)

