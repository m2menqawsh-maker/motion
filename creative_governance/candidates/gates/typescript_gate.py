"""
creative_governance/candidates/gates/typescript_gate.py
======================================
TypeScript Gate for TemplateCandidate Static Validation (S28-07B).

Executes isolated type-check verification without polluting canonical directories,
enforcing TypeScript purity, valid JSX syntax, and prop contract typing.
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


class TypeScriptGate(StaticGate):
    """
    Validates that the candidate source code, combined with project type definitions
    and approved dependencies, compiles cleanly with zero TypeScript errors.
    """

    @property
    def gate_id(self) -> str:
        return "typescript_gate"

    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> CandidateGateResult:
        analysis = ast_analysis
        if analysis is None or "typescript" not in analysis or not analysis.get("typescript"):
            # Run full AST analysis with TypeScript compiler diagnostics enabled
            analysis = run_candidate_ast_worker(
                source_code=candidate.source_code,
                dependencies=candidate.dependencies,
                template_schema=candidate.template_schema,
                skip_tsc=False,
                timeout_seconds=25,
            )

        if not analysis.get("success", False):
            # Validator itself crashed or timed out -> ERROR
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                failure_code=ValidationFailureCode.VALIDATOR_EXECUTION_ERROR,
                summary=f"TypeScript compiler tool execution error: {analysis.get('error', 'unknown error')}",
                machine_details={"error": analysis.get("error")},
            )

        ts_info = analysis.get("typescript", {})
        compiles = ts_info.get("compiles", False)
        errors = ts_info.get("errors", [])

        if not compiles or errors:
            first_err = errors[0] if errors else {"message": "Unknown type compilation failure", "line": 1, "code": 0}
            msg = first_err.get("message", "")
            code = first_err.get("code", 0)
            line = first_err.get("line", 1)

            # Classify JSX vs syntax vs type error
            if "JSX" in msg or code in (17004, 17002, 17008, 17009):
                failure_code = ValidationFailureCode.TYPESCRIPT_JSX_ERROR
                summary = f"JSX typing or syntax error at line {line}: {msg}"
            elif code >= 1000 and code < 2000:
                failure_code = ValidationFailureCode.TYPESCRIPT_SYNTAX_ERROR
                summary = f"TypeScript syntax parse error at line {line}: {msg}"
            else:
                failure_code = ValidationFailureCode.TYPESCRIPT_TYPE_ERROR
                summary = f"TypeScript type check error at line {line} (TS{code}): {msg}"

            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=failure_code,
                summary=summary,
                machine_details={
                    "errors_count": len(errors),
                    "first_error": first_err,
                    "errors": errors[:10],
                },
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="Candidate component passed isolated TypeScript type checking with zero errors.",
            machine_details={"diagnostics_count": 0},
        )
