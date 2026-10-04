"""
creative_governance/candidates/gates/static_code_gate.py
=======================================
Static Code Gate for TemplateCandidate Static Validation (S28-07B).

Performs structural and syntactic AST inspection without executing candidate code.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from creative_governance.candidates.gates.ast_runner import run_candidate_ast_worker
from creative_governance.candidates.gates.base import StaticGate
from creative_governance.candidates.policies import ValidationFailureCode
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class StaticCodeGate(StaticGate):
    """
    Validates syntax parseability, ES module format, component exports,
    and absence of forbidden dynamic code patterns or raw filesystem paths.
    """

    @property
    def gate_id(self) -> str:
        return "static_code_gate"

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
                summary=f"Static code AST analyzer execution error: {analysis.get('error', 'unknown error')}",
                machine_details={"error": analysis.get("error")},
            )

        static_info = analysis.get("static_code", {})

        # 1. Syntax parseability
        if not static_info.get("syntax_valid", True):
            errors = static_info.get("syntax_errors", [])
            err_msg = errors[0]["message"] if errors and isinstance(errors[0], dict) else str(errors)
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.SYNTAX_ERROR,
                summary=f"TypeScript/TSX syntax error: {err_msg}",
                machine_details={"syntax_errors": errors},
            )

        # 2. Module format (ESM vs CommonJS)
        if static_info.get("module_format") == "CommonJS":
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.COMMONJS_FORBIDDEN,
                summary="CommonJS module patterns ('module.exports' / 'exports.') are forbidden. Use ESM export.",
                machine_details={"module_format": "CommonJS"},
            )

        # 3. Expected Component Export
        if not static_info.get("has_component_export", False):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_COMPONENT_EXPORT,
                summary="Candidate does not export any component or function. Expected an exported React component.",
                machine_details={"exported_names": static_info.get("exported_names", [])},
            )

        # 4. Forbidden Dynamic Code Construction
        forbidden_dynamic = static_info.get("forbidden_dynamic_code", [])
        for item in forbidden_dynamic:
            kind = item.get("kind")
            detail = item.get("detail", "")
            line = item.get("line", 1)

            if kind == "eval":
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_EVAL,
                    summary=f"Forbidden 'eval()' call detected at line {line}: {detail}",
                    machine_details=item,
                )
            elif kind == "new_Function" or kind == "Function":
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_NEW_FUNCTION,
                    summary=f"Forbidden dynamic function constructor detected at line {line}: {detail}",
                    machine_details=item,
                )
            elif kind == "dynamic_require":
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_DYNAMIC_REQUIRE,
                    summary=f"Forbidden dynamic 'require()' call detected at line {line}: {detail}",
                    machine_details=item,
                )
            elif kind == "dynamic_import":
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_DYNAMIC_IMPORT,
                    summary=f"Forbidden dynamic 'import()' call detected at line {line}: {detail}",
                    machine_details=item,
                )
            elif kind == "eval_timer_string":
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FORBIDDEN_DYNAMIC_CODE,
                    summary=f"Forbidden timer with string evaluation detected at line {line}: {detail}",
                    machine_details=item,
                )

        # 5. Unexpected Node-specific APIs
        unexpected_apis = static_info.get("unexpected_node_apis", [])
        if unexpected_apis:
            first_api = unexpected_apis[0]
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.NODE_SPECIFIC_API_FORBIDDEN,
                summary=f"Unexpected Node-specific runtime API '{first_api.get('api')}' at line {first_api.get('line')}.",
                machine_details={"unexpected_apis": unexpected_apis},
            )

        # 6. Direct Raw Filesystem Assumptions
        raw_fs = static_info.get("raw_fs_patterns", [])
        if raw_fs:
            first_fs = raw_fs[0]
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.RAW_FILESYSTEM_ASSUMPTION,
                summary=f"Direct raw filesystem path reference '{first_fs.get('pattern')}' at line {first_fs.get('line')}.",
                machine_details={"raw_fs_patterns": raw_fs},
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="Candidate source code passed static AST structure, export, and syntax checks.",
            machine_details={
                "exported_names": static_info.get("exported_names", []),
                "module_format": static_info.get("module_format", "ESM"),
            },
        )
