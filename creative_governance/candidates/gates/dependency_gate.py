"""
creative_governance/candidates/gates/dependency_gate.py
======================================
Dependency Gate for TemplateCandidate Static Validation (S28-07B).

Enforces hermetic package verification without performing network package
resolution or dynamic package installation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from creative_governance.candidates.gates.ast_runner import run_candidate_ast_worker
from creative_governance.candidates.gates.base import StaticGate
from creative_governance.candidates.policies import (
    APPROVED_CORE_PACKAGES,
    FORBIDDEN_DEPENDENCY_PACKAGES,
    ValidationFailureCode,
)
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_JSON_PATH = WORKSPACE_ROOT / "package.json"


def _normalize_package_name(specifier: str) -> str:
    """
    Extracts the root package name from an import path or dependency specifier.
    e.g. 'lodash/fp' -> 'lodash', '@remotion/transitions' -> '@remotion/transitions'
    'three@^0.160.0' -> 'three', '@types/react@^19' -> '@types/react'
    """
    spec = specifier.strip()
    if "@" in spec and not spec.startswith("@"):
        spec = spec.split("@")[0].strip()
    elif spec.startswith("@"):
        # Scoped package: '@scope/pkg@version' or '@scope/pkg/subpath'
        parts = spec.split("/")
        if len(parts) >= 2:
            scope = parts[0]
            rest = parts[1]
            if "@" in rest:
                pkg_name = rest.split("@")[0]
            else:
                pkg_name = rest
            return f"{scope}/{pkg_name}"
        return spec

    parts = spec.split("/")
    return parts[0]


def get_installed_runtime_packages() -> Set[str]:
    """Reads project package.json to get approved installed dependencies."""
    installed: Set[str] = set()
    if PACKAGE_JSON_PATH.exists():
        try:
            with open(PACKAGE_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in data.get("dependencies", {}).keys():
                    installed.add(k)
                for k in data.get("devDependencies", {}).keys():
                    installed.add(k)
        except Exception:
            pass
    return installed


class DependencyGate(StaticGate):
    """
    Validates declared candidate dependencies against runtime availability,
    verifies that all imported modules are declared, and rejects forbidden packages.
    """

    @property
    def gate_id(self) -> str:
        return "dependency_gate"

    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> CandidateGateResult:
        analysis = ast_analysis
        if analysis is None:
            analysis = run_candidate_ast_worker(
                source_code=candidate.source_code,
                dependencies=candidate.dependencies,
                template_schema=candidate.template_schema,
                skip_tsc=True,
            )

        if not analysis.get("success", False):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                failure_code=ValidationFailureCode.VALIDATOR_EXECUTION_ERROR,
                summary=f"Dependency AST analyzer execution error: {analysis.get('error', 'unknown error')}",
                machine_details={"error": analysis.get("error")},
            )

        installed_packages = get_installed_runtime_packages()

        # 1. Inspect Declared Dependencies
        declared_pkgs: Set[str] = set()
        for dep in candidate.dependencies:
            pkg_name = _normalize_package_name(dep)
            declared_pkgs.add(pkg_name)

            # Check if declared dependency is forbidden
            if pkg_name in FORBIDDEN_DEPENDENCY_PACKAGES:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_DEPENDENCY,
                    summary=f"Declared dependency '{dep}' is in the forbidden packages list.",
                    machine_details={"forbidden_dependency": dep, "normalized_pkg": pkg_name},
                )

            # Check if declared dependency is installed/available in runtime
            if pkg_name not in APPROVED_CORE_PACKAGES and pkg_name not in installed_packages:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.UNKNOWN_EXTERNAL_DEPENDENCY,
                    summary=(
                        f"Declared dependency '{dep}' is not installed or available in the approved "
                        f"hermetic runtime environment. Candidate validation cannot perform network installs."
                    ),
                    machine_details={"unknown_dependency": dep, "normalized_pkg": pkg_name},
                )

        # 2. Inspect Imports Actually Used in Source Code
        used_imports = analysis.get("dependencies", {}).get("used_imports", [])
        for imp in used_imports:
            # Skip relative local imports (e.g. './Component', '../primitives')
            if imp.startswith(".") or imp.startswith("/"):
                continue

            pkg_name = _normalize_package_name(imp)

            # If it's a forbidden package imported in code
            if pkg_name in FORBIDDEN_DEPENDENCY_PACKAGES:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_DEPENDENCY,
                    summary=f"Imported package '{imp}' is forbidden by security policy.",
                    machine_details={"forbidden_import": imp, "normalized_pkg": pkg_name},
                )

            # If in core allowlist, always permitted
            if pkg_name in APPROVED_CORE_PACKAGES:
                continue

            # Otherwise it must be explicitly declared in candidate.dependencies
            if pkg_name not in declared_pkgs:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.UNDECLARED_IMPORT,
                    summary=(
                        f"Import '{imp}' is used in candidate source code but is NOT declared in "
                        f"candidate.dependencies."
                    ),
                    machine_details={
                        "undeclared_import": imp,
                        "normalized_pkg": pkg_name,
                        "declared_dependencies": candidate.dependencies,
                    },
                )

            # If declared, must also be installed
            if pkg_name not in installed_packages:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.UNKNOWN_EXTERNAL_DEPENDENCY,
                    summary=f"Imported package '{imp}' is not installed in the hermetic environment.",
                    machine_details={"import": imp, "normalized_pkg": pkg_name},
                )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="All imported modules are declared, approved, and hermetically available in runtime.",
            machine_details={
                "declared_dependencies_count": len(candidate.dependencies),
                "used_imports_count": len(used_imports),
            },
        )
