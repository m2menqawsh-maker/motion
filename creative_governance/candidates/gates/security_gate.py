"""
creative_governance/candidates/gates/security_gate.py
====================================
Security Gate for TemplateCandidate Static Validation (S28-07B).

Enforces non-negotiable security boundaries preventing templates from acquiring
general-purpose Node.js host capabilities, system process access, or leaking secrets.
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


class SecurityGate(StaticGate):
    """
    Validates that candidate code cannot execute arbitrary shell commands,
    access host filesystem, open raw network sockets, or read environment secrets.
    """

    @property
    def gate_id(self) -> str:
        return "security_gate"

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
                summary=f"Security AST analyzer execution error: {analysis.get('error', 'unknown error')}",
                machine_details={"error": analysis.get("error")},
            )

        sec_info = analysis.get("security", {})
        violations = sec_info.get("violations", [])

        if violations:
            first_v = violations[0]
            v_type = first_v.get("type")
            mod = first_v.get("module", "")
            detail = first_v.get("detail", "")
            line = first_v.get("line", 1)

            # Classify specific security failure code
            failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_RUNTIME
            if v_type == "SENSITIVE_ENV_ACCESS":
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_ENV_ACCESS
                summary = f"Unauthorized access to environment secret/key '{mod}' at line {line}."
            elif "fs" in mod:
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_FS
                summary = f"Forbidden host filesystem module '{mod}' at line {line}: {detail}."
            elif "child_process" in mod or mod in ("exec", "spawn", "fork"):
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_CHILD_PROCESS
                summary = f"Forbidden process execution module '{mod}' at line {line}: {detail}."
            elif mod in ("net", "node:net", "tls", "node:tls", "http", "node:http", "https", "node:https", "dgram", "dns", "axios", "node-fetch", "got", "ws", "socket.io"):
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_NETWORK
                summary = f"Forbidden raw network / HTTP client module '{mod}' at line {line}: {detail}."
            elif "worker_threads" in mod:
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_THREADS
                summary = f"Forbidden worker_threads module at line {line}: {detail}."
            elif "cluster" in mod:
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_CLUSTER
                summary = f"Forbidden cluster module at line {line}: {detail}."
            elif "vm" in mod:
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_VM
                summary = f"Forbidden vm sandbox execution module at line {line}: {detail}."
            elif "os" in mod:
                failure_code = ValidationFailureCode.SECURITY_FORBIDDEN_OS
                summary = f"Forbidden os host inspection module at line {line}: {detail}."
            else:
                summary = f"Security violation detected: {detail or mod} at line {line}."

            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=failure_code,
                summary=summary,
                machine_details={
                    "violations": violations,
                    "env_accesses": sec_info.get("env_accesses", []),
                },
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="Candidate code contains no unauthorized host capabilities, process execution, or secret leaks.",
            machine_details={"violations_count": 0},
        )
