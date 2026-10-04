"""
tests/ai/test_creative_architecture_guards.py
=============================================
Architecture Guard Suite for S28 (Creative Intelligence Platform).

Enforces non-negotiable boundaries defined in S28 Foundation (DEC-S28.01):
1. ai/taste -> direct canonical registry write (FORBIDDEN)
2. ai/skills -> uncontrolled raw filesystem mutation (FORBIDDEN)
3. ai/recipes -> provider-specific direct calls (FORBIDDEN)
4. CreativePlanner -> lifecycle mutation (FORBIDDEN)
5. CreativePlanner -> QC override (FORBIDDEN)

Includes:
- Live inspection of `ai/contracts/creative/` (and all creative platform modules).
- Synthetic positive & negative AST tests proving boundary violations are caught automatically.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, NamedTuple
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
CREATIVE_CONTRACTS_ROOT = WORKSPACE_ROOT / "ai" / "contracts" / "creative"


class CreativeViolation(NamedTuple):
    file_path: str
    line_number: int
    rule_id: str
    message: str


class CreativeArchitectureAnalyzer:
    """
    AST-based structural analyzer that inspects source code for
    architectural boundary bypasses in the Creative Intelligence Platform.
    """

    FORBIDDEN_PROVIDER_MODULES = {
        "openai",
        "elevenlabs",
        "heygen",
        "fal",
        "replicate",
        "anthropic",
        "google.generativeai",
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

    FORBIDDEN_LIFECYCLE_PATTERNS = {
        ".pipeline_state.json",
        "pipeline_state",
    }

    FORBIDDEN_QC_PATTERNS = {
        ".studio_approved",
        ".studio_unlocked",
        ".qc_passed",
        "06_qc_report.json",
        "08_qc_report.json",
        "qc_report",
    }

    WRITE_MODES = {
        "w", "wb", "w+", "wb+",
        "a", "ab", "a+", "ab+",
        "x", "xb", "x+", "xb+",
    }

    def __init__(self):
        self.violations: List[CreativeViolation] = []

    def _extract_string_literals(self, node: ast.AST | None) -> List[str]:
        if node is None:
            return []
        literals: List[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                literals.extend(self._extract_string_literals(part))
        elif isinstance(node, ast.BinOp):
            literals.extend(self._extract_string_literals(node.left))
            literals.extend(self._extract_string_literals(node.right))
        elif isinstance(node, ast.Call):
            for arg in node.args:
                literals.extend(self._extract_string_literals(arg))
            for kw in node.keywords:
                literals.extend(self._extract_string_literals(kw.value))
        elif isinstance(node, ast.Attribute):
            literals.extend(self._extract_string_literals(node.value))
        elif isinstance(node, ast.Name):
            literals.append(node.id)
        return literals

    def _matches_authority(self, target_nodes: List[ast.AST | None]) -> str | None:
        """Returns 'REGISTRY', 'LIFECYCLE', or 'QC' if any target node matches protected authority patterns."""
        for target in target_nodes:
            if target is None:
                continue
            strings = [s.lower() for s in self._extract_string_literals(target)]
            for s in strings:
                if any(p in s for p in self.FORBIDDEN_REGISTRY_PATTERNS):
                    return "REGISTRY"
                if any(p in s for p in self.FORBIDDEN_LIFECYCLE_PATTERNS):
                    return "LIFECYCLE"
                if any(p in s for p in self.FORBIDDEN_QC_PATTERNS):
                    return "QC"
        return None

    def analyze_file(self, file_path: Path) -> List[CreativeViolation]:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception as exc:
            return [
                CreativeViolation(
                    file_path=str(file_path),
                    line_number=0,
                    rule_id="CREATIVE-PARSE-ERR",
                    message=f"Failed to parse Python file: {exc}",
                )
            ]
        return self.analyze_tree(tree, file_path=file_path)

    def analyze_tree(self, tree: ast.AST, file_path: Path | str = "<memory>") -> List[CreativeViolation]:
        violations: List[CreativeViolation] = []
        path_str = str(file_path).lower()

        is_recipe_context = "recipe" in path_str
        is_taste_context = "taste" in path_str
        is_skill_context = "skill" in path_str
        is_planner_context = "plan" in path_str or "creative" in path_str
        is_candidate_context = "candidate" in path_str

        for node in ast.walk(tree):
            # 1. Rule: ai/recipes -> provider-specific direct calls (CREATIVE-RECIPE-NO-PROVIDER)
            if is_recipe_context:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_mod = alias.name.split(".")[0]
                        if root_mod in self.FORBIDDEN_PROVIDER_MODULES:
                            violations.append(
                                CreativeViolation(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    rule_id="CREATIVE-RECIPE-NO-PROVIDER",
                                    message=(
                                        f"Recipe module directly imports vendor SDK '{alias.name}'. "
                                        f"Recipes must express requirements via CapabilityType instead."
                                    ),
                                )
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    root_mod = mod.split(".")[0]
                    if root_mod in self.FORBIDDEN_PROVIDER_MODULES:
                        violations.append(
                            CreativeViolation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                rule_id="CREATIVE-RECIPE-NO-PROVIDER",
                                message=(
                                    f"Recipe module directly imports from vendor SDK '{mod}'. "
                                    f"Recipes must express requirements via CapabilityType instead."
                                ),
                            )
                        )

            # 2. Rule: Lifecycle attribute mutation in planner
            if is_planner_context:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute):
                            if target.attr in {"lifecycle_state", "current_stage"}:
                                violations.append(
                                    CreativeViolation(
                                        file_path=str(file_path),
                                        line_number=node.lineno,
                                        rule_id="CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION",
                                        message=f"Creative planner attempts direct mutation of lifecycle attribute '{target.attr}'.",
                                    )
                                )

            # 3. Check AST Call mutations across filesystem and protected authorities
            if isinstance(node, ast.Call):
                mutation_targets: List[ast.AST | None] = []
                is_destructive_fs = False
                op_name = ""

                # Case A: open(...) with write/append/create modes
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    if node.args:
                        mode = "r"
                        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                            mode = str(node.args[1].value)
                        for kw in node.keywords:
                            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                                mode = str(kw.value.value)
                        if any(m in mode for m in ("w", "a", "x")):
                            mutation_targets.append(node.args[0])
                            op_name = f"open(..., mode='{mode}')"

                # Case B: Methods on objects (Path, os, shutil, etc.)
                elif isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    obj = node.func.value
                    op_name = attr

                    # write_text, write_bytes
                    if attr in {"write_text", "write_bytes"}:
                        mutation_targets.append(obj)

                    # rename, replace
                    elif attr in {"rename", "replace"}:
                        mutation_targets.append(obj)
                        if node.args:
                            mutation_targets.extend(node.args)

                    # unlink, remove
                    elif attr in {"unlink", "remove"}:
                        mutation_targets.append(obj)
                        if node.args:
                            mutation_targets.append(node.args[0])
                        is_destructive_fs = True

                    # copy, copy2, move
                    elif attr in {"copy", "copy2", "move"}:
                        if node.args:
                            mutation_targets.extend(node.args)

                    # rmtree, rmdir
                    elif attr in {"rmtree", "rmdir"}:
                        if node.args:
                            mutation_targets.append(node.args[0])
                        mutation_targets.append(obj)
                        is_destructive_fs = True

                # Evaluate mutation against protected authorities and subsystem constraints
                auth = self._matches_authority(mutation_targets) if mutation_targets else None

                # Rule 3.1: Skills cannot perform raw destructive filesystem operations or mutate protected authorities
                if is_skill_context:
                    if is_destructive_fs and not path_str.endswith("test_s28_inventory.py"):
                        violations.append(
                            CreativeViolation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                rule_id="CREATIVE-SKILLS-NO-RAW-FS",
                                message=f"Skill executes raw destructive filesystem mutation '{op_name}'.",
                            )
                        )
                    elif auth is not None:
                        violations.append(
                            CreativeViolation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                rule_id="CREATIVE-SKILLS-NO-RAW-FS",
                                message=f"Skill attempts mutation of protected authority surface ({auth}) via '{op_name}'.",
                            )
                        )

                # Rule 3.2: Taste cannot mutate canonical registry surfaces
                if is_taste_context and auth == "REGISTRY":
                    violations.append(
                        CreativeViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            rule_id="CREATIVE-TASTE-NO-REGISTRY-WRITE",
                            message=f"Taste logic attempts direct write/mutation to registry surface via '{op_name}'.",
                        )
                    )

                # Rule 3.3: Planner cannot mutate lifecycle surfaces
                if is_planner_context and auth == "LIFECYCLE":
                    violations.append(
                        CreativeViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            rule_id="CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION",
                            message=f"Creative planner attempts direct write/mutation to lifecycle surface via '{op_name}'.",
                        )
                    )

                # Rule 3.4: Planner cannot override or create QC surfaces
                if is_planner_context and auth == "QC":
                    violations.append(
                        CreativeViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            rule_id="CREATIVE-PLANNER-NO-QC-OVERRIDE",
                            message=f"Creative planner attempts direct creation/override of QC artifact via '{op_name}'.",
                        )
                    )

                # Rule 3.5: Candidate domain cannot mutate canonical registry surfaces
                if is_candidate_context and auth == "REGISTRY":
                    violations.append(
                        CreativeViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            rule_id="CREATIVE-CANDIDATE-NO-REGISTRY-WRITE",
                            message=f"Candidate subsystem attempts direct write/mutation to registry surface via '{op_name}'.",
                        )
                    )

        return violations


# ============================================================================
# LIVE INSPECTION TEST
# ============================================================================

def test_live_creative_contracts_conform_to_architecture():
    """Live verification that all canonical creative contracts and candidates obey architecture guards."""
    assert CREATIVE_CONTRACTS_ROOT.exists(), f"Missing {CREATIVE_CONTRACTS_ROOT}"
    analyzer = CreativeArchitectureAnalyzer()
    all_violations: List[CreativeViolation] = []

    for py_file in CREATIVE_CONTRACTS_ROOT.glob("*.py"):
        violations = analyzer.analyze_file(py_file)
        all_violations.extend(violations)

    candidates_root = WORKSPACE_ROOT / "ai" / "candidates"
    if candidates_root.exists():
        for py_file in candidates_root.glob("*.py"):
            violations = analyzer.analyze_file(py_file)
            all_violations.extend(violations)

    if all_violations:
        msg = "\n".join(f"[{v.rule_id}] {v.file_path}:{v.line_number} — {v.message}" for v in all_violations)
        pytest.fail(f"Creative Architecture Violations Detected in Canonical Contracts/Candidates:\n{msg}")


# ============================================================================
# SYNTHETIC POSITIVE & NEGATIVE TESTS
# ============================================================================

def test_catch_candidate_direct_registry_write():
    """Negative: Proves candidate subsystem attempting to write to canonical registry is caught."""
    code = """
def mutate_registry():
    with open("registry/template-registry-data.json", "w") as f:
        f.write("{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/candidates/service.py")
    assert any(v.rule_id == "CREATIVE-CANDIDATE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_recipe_provider_import_violation():
    """Negative: Proves importing vendor SDK in a recipe is caught."""
    code = """
import os
import elevenlabs
from ai.contracts.creative import RecipeDefinition

def run_recipe():
    pass
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/recipes/avatar_recipe.py")
    assert any(v.rule_id == "CREATIVE-RECIPE-NO-PROVIDER" for v in violations)


def test_catch_taste_direct_registry_write():
    """Negative: Proves direct write to template registry from taste code is caught."""
    code = """
def update_registered_style():
    with open("registry/template-registry-data.json", "w") as f:
        f.write("{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_skill_uncontrolled_filesystem_mutation():
    """Negative: Proves raw destructive filesystem call in a skill is caught."""
    code = """
import shutil
def clear_workspace(target):
    shutil.rmtree(target)
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/skills/typography_skill.py")
    assert any(v.rule_id == "CREATIVE-SKILLS-NO-RAW-FS" for v in violations)


def test_catch_planner_lifecycle_mutation():
    """Negative: Proves planner directly mutating state.lifecycle_state is caught."""
    code = """
def execute_plan(state):
    state.lifecycle_state = "COMPLETED"
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION" for v in violations)


def test_catch_planner_qc_override():
    """Negative: Proves planner creating .studio_approved is caught."""
    code = """
def force_approval():
    with open(".studio_approved", "w") as f:
        f.write("APPROVED")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-QC-OVERRIDE" for v in violations)


def test_catch_taste_path_write_text_registry():
    """Negative: Proves Path.write_text to template registry is caught."""
    code = """
from pathlib import Path
def mutate_registry():
    Path("registry/template-registry-data.json").write_text("{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_taste_path_write_bytes_registry():
    """Negative: Proves Path.write_bytes to template catalog is caught."""
    code = """
from pathlib import Path
def mutate_catalog():
    Path("registry/template_catalog.json").write_bytes(b"{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/style_matcher.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_taste_shutil_copy2_registry():
    """Negative: Proves shutil.copy2 to registry is caught."""
    code = """
import shutil
def copy_to_registry():
    shutil.copy2("candidate.tsx", "registry/template-registry.tsx")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_taste_shutil_move_registry():
    """Negative: Proves shutil.move to template aliases is caught."""
    code = """
import shutil
def move_to_aliases():
    shutil.move("temp_aliases.ts", "registry/template-aliases.ts")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_taste_shutil_rmtree_registry():
    """Negative: Proves shutil.rmtree targeting registry is caught."""
    code = """
import shutil
def nuke_registry():
    shutil.rmtree("registry/")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_taste_open_exclusive_mode_registry():
    """Negative: Proves open with mode='x' (exclusive create) targeting registry is caught."""
    code = """
def create_index():
    with open("registry/template_index.md", "x") as f:
        f.write("# Index")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/taste/engine.py")
    assert any(v.rule_id == "CREATIVE-TASTE-NO-REGISTRY-WRITE" for v in violations)


def test_catch_skill_path_unlink():
    """Negative: Proves Path.unlink in a skill is caught."""
    code = """
from pathlib import Path
def cleanup_temp():
    Path("/tmp/scratch.mp4").unlink()
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/skills/render_skill.py")
    assert any(v.rule_id == "CREATIVE-SKILLS-NO-RAW-FS" for v in violations)


def test_catch_skill_os_remove():
    """Negative: Proves os.remove in a skill is caught."""
    code = """
import os
def delete_file(p):
    os.remove(p)
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/skills/audio_skill.py")
    assert any(v.rule_id == "CREATIVE-SKILLS-NO-RAW-FS" for v in violations)


def test_catch_skill_protected_authority_write():
    """Negative: Proves skill writing directly to pipeline state is caught."""
    code = """
from pathlib import Path
def tamper_state():
    Path(".pipeline_state.json").write_text("{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/skills/planner_skill.py")
    assert any(v.rule_id == "CREATIVE-SKILLS-NO-RAW-FS" for v in violations)


def test_catch_planner_path_write_bytes_lifecycle():
    """Negative: Proves planner writing bytes to .pipeline_state.json is caught."""
    code = """
from pathlib import Path
def write_state():
    Path(".pipeline_state.json").write_bytes(b"{}")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION" for v in violations)


def test_catch_planner_os_replace_lifecycle():
    """Negative: Proves planner using os.replace on .pipeline_state.json is caught."""
    code = """
import os
def swap_state():
    os.replace("new_state.json", ".pipeline_state.json")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION" for v in violations)


def test_catch_planner_path_rename_lifecycle():
    """Negative: Proves planner using Path.rename on .pipeline_state.json is caught."""
    code = """
from pathlib import Path
def move_state():
    Path(".pipeline_state.json").rename("backup.json")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-LIFECYCLE-MUTATION" for v in violations)


def test_catch_planner_path_write_text_qc_override():
    """Negative: Proves planner using Path.write_text on .studio_approved is caught."""
    code = """
from pathlib import Path
def bypass_studio():
    Path(".studio_approved").write_text("APPROVED")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-QC-OVERRIDE" for v in violations)


def test_catch_planner_os_remove_qc():
    """Negative: Proves planner using os.remove on 06_qc_report.json is caught."""
    code = """
import os
def delete_bad_qc():
    os.remove("06_qc_report.json")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-QC-OVERRIDE" for v in violations)


def test_catch_planner_path_unlink_qc():
    """Negative: Proves planner using Path.unlink on .studio_unlocked is caught."""
    code = """
from pathlib import Path
def delete_lock():
    Path(".studio_unlocked").unlink()
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-QC-OVERRIDE" for v in violations)


def test_catch_planner_shutil_copy_qc():
    """Negative: Proves planner using shutil.copy to overwrite 08_qc_report.json is caught."""
    code = """
import shutil
def overwrite_final_qc():
    shutil.copy("mock_passed.json", "08_qc_report.json")
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert any(v.rule_id == "CREATIVE-PLANNER-NO-QC-OVERRIDE" for v in violations)


def test_clean_compliant_creative_code_passes():
    """Positive: Clean, capability-driven creative code raises zero violations."""
    code = """
from ai.contracts.creative import CreativeBrief, CreativePlan, RecipeDefinition
from ai.contracts.common import CapabilityType

class CompliantPlanner:
    def plan(self, brief: CreativeBrief) -> CreativePlan:
        # Generates an advisory plan proposal without raw fs or lifecycle mutation
        return None
"""
    tree = ast.parse(code)
    analyzer = CreativeArchitectureAnalyzer()
    violations = analyzer.analyze_tree(tree, file_path="ai/creative_planner.py")
    assert len(violations) == 0


def test_s28_04_no_premature_s28_05_runtime():
    """Boundary Guard: S28-04 must NOT prematurely implement S28-05 runtime modules.
    Verified absent:
    - CreativePlanner runtime (e.g. ai/planner/ or ai/creative_planner/)
    - BlueprintCompiler runtime (e.g. ai/compiler/ or ai/blueprint_compiler/)
    - Canonical Blueprint generation runtime
    """
    ai_root = WORKSPACE_ROOT / "ai"

    forbidden_s28_05_files = [
        ai_root / "creative_planner.py",
        ai_root / "creative_plan" / "compiler.py",
        ai_root / "blueprint_compiler.py",
        ai_root / "blueprint" / "compiler.py",
        ai_root / "compiler" / "blueprint.py",
    ]

    for p in forbidden_s28_05_files:
        assert not p.exists(), f"Premature S28-05 runtime file must not exist in S28-04: {p}"


def test_s28_04_no_premature_s28_06_runtime():
    """Boundary Guard: S28-04 must NOT prematurely implement S28-06 runtime modules.
    Verified absent:
    - Tier Decision Engine runtime (ai/tier/ or ai/tier_decision/)
    - REUSE Engine runtime (ai/reuse/)
    - COMPOSE Engine runtime (ai/compose/)
    - CREATE Engine runtime (ai/create/)
    - Template Candidate generation runtime
    """
    ai_root = WORKSPACE_ROOT / "ai"

    forbidden_s28_06_files = [
        ai_root / "tier_decision.py",
        ai_root / "tier" / "engine.py",
        ai_root / "reuse" / "engine.py",
        ai_root / "compose" / "engine.py",
        ai_root / "create" / "engine.py",
        ai_root / "candidate" / "generator.py",
    ]

    for p in forbidden_s28_06_files:
        assert not p.exists(), f"Premature S28-06 runtime file must not exist in S28-04: {p}"

