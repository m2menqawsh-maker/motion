"""
creative_governance/candidates/gates/contract_gate.py
====================================
Contract Gate for TemplateCandidate Static Validation (S28-07B).

Verifies Candidate internal consistency, provenance integrity, tenant ownership,
and cryptographic content hash binding prior to code analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from creative_governance.candidates.gates.base import StaticGate
from creative_governance.candidates.hashing import compute_candidate_content_hash
from creative_governance.candidates.policies import ValidationFailureCode
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class ContractGate(StaticGate):
    """
    Validates structural completeness, provenance lineage, tenant isolation,
    and server-side content hash fidelity.
    """

    @property
    def gate_id(self) -> str:
        return "contract_gate"

    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> CandidateGateResult:
        # 1. Provenance presence & validity
        if not candidate.required_provenance or not candidate.required_provenance.source or not candidate.required_provenance.source.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_PROVENANCE,
                summary="Candidate is missing required provenance record or source is empty.",
                machine_details={"field": "required_provenance"},
            )

        # 2. Tenant Workspace Isolation check
        if candidate.workspace_id != tenant_context.workspace_id:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.TENANT_WORKSPACE_MISMATCH,
                summary=(
                    f"Candidate workspace_id '{candidate.workspace_id}' does not match "
                    f"caller workspace_id '{tenant_context.workspace_id}'."
                ),
                machine_details={
                    "candidate_workspace_id": candidate.workspace_id,
                    "caller_workspace_id": tenant_context.workspace_id,
                },
            )

        # 3. Source Project Ownership
        if not candidate.source_project_id or not candidate.source_project_id.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.PROJECT_OWNERSHIP_INVALID,
                summary="Candidate source_project_id is missing or empty.",
                machine_details={"field": "source_project_id"},
            )

        # 4. CreativePlan Reference
        if not candidate.creative_plan_reference or not candidate.creative_plan_reference.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_PLAN_REFERENCE,
                summary="Candidate creative_plan_reference is missing or empty.",
                machine_details={"field": "creative_plan_reference"},
            )

        # 5. CreativeTierDecision Reference
        if not candidate.creative_tier_decision_reference or not candidate.creative_tier_decision_reference.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_TIER_DECISION_REFERENCE,
                summary="Candidate creative_tier_decision_reference is missing or empty.",
                machine_details={"field": "creative_tier_decision_reference"},
            )

        # 6. Provenance: why_reuse_failed
        if not candidate.why_reuse_failed or not candidate.why_reuse_failed.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_REUSE_RATIONALE,
                summary="Candidate why_reuse_failed evidence rationale is missing or empty.",
                machine_details={"field": "why_reuse_failed"},
            )

        # 7. Provenance: why_compose_failed
        if not candidate.why_compose_failed or not candidate.why_compose_failed.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_COMPOSE_RATIONALE,
                summary="Candidate why_compose_failed evidence rationale is missing or empty.",
                machine_details={"field": "why_compose_failed"},
            )

        # 8. Source code presence
        if not candidate.source_code or not candidate.source_code.strip():
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_SOURCE_CODE,
                summary="Candidate source_code is missing or empty.",
                machine_details={"field": "source_code"},
            )

        # 9. Template schema presence
        if not isinstance(candidate.template_schema, dict) or len(candidate.template_schema) == 0:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_TEMPLATE_SCHEMA,
                summary="Candidate template_schema is missing or empty dictionary.",
                machine_details={"field": "template_schema"},
            )

        # 10. Fixtures presence
        if not isinstance(candidate.fixtures, dict) or len(candidate.fixtures) == 0:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.MISSING_FIXTURES,
                summary="Candidate fixtures is missing or empty dictionary.",
                machine_details={"field": "fixtures"},
            )

        # 11. Dependencies structure
        if not isinstance(candidate.dependencies, list):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_DEPENDENCIES_FORMAT,
                summary="Candidate dependencies must be a list of strings.",
                machine_details={"dependencies": candidate.dependencies},
            )

        for dep in candidate.dependencies:
            if not isinstance(dep, str) or not dep.strip():
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.INVALID_DEPENDENCIES_FORMAT,
                    summary=f"Candidate dependency entry '{dep}' is not a valid non-empty string.",
                    machine_details={"invalid_entry": dep},
                )

        # 12. Server-side Content Hash Recomputation (FAIL CLOSED on mismatch)
        computed_hash = compute_candidate_content_hash(
            source_code=candidate.source_code,
            template_schema=candidate.template_schema,
            dependencies=candidate.dependencies,
            fixtures=candidate.fixtures,
            why_reuse_failed=candidate.why_reuse_failed,
            why_compose_failed=candidate.why_compose_failed,
            creative_plan_reference=candidate.creative_plan_reference,
            creative_tier_decision_reference=candidate.creative_tier_decision_reference,
        )

        if computed_hash != candidate.content_hash:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.CONTENT_HASH_MISMATCH,
                summary=(
                    f"Candidate content_hash mismatch: expected server recomputation '{computed_hash}' "
                    f"does not match stored hash '{candidate.content_hash}'. FAIL CLOSED."
                ),
                machine_details={
                    "stored_hash": candidate.content_hash,
                    "recomputed_hash": computed_hash,
                },
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="Candidate contract, provenance, tenant bounds, and content hash verified.",
            machine_details={
                "content_hash": candidate.content_hash,
                "revision": candidate.revision,
                "source_project_id": candidate.source_project_id,
            },
        )
