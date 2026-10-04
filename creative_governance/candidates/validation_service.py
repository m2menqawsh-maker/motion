"""
creative_governance/candidates/validation_service.py
===================================
Authoritative Domain Service for TemplateCandidate Static Validation (S28-07B).

Orchestrates:
1. Candidate loading and tenant isolation enforcement.
2. Freezing an immutable ValidationSnapshot bound to content_hash and revision.
3. Deterministic sequential execution of the 6 static validation gates:
   - Contract Gate
   - Static Code Gate
   - Security Gate
   - Dependency Gate
   - TypeScript Gate
   - Template Schema Gate
4. Concurrency freshness / anti-stale validation guard.
5. Durable report and evidence persistence (metadata repository and StorageService).
6. Lifecycle status semantics (DRAFT -> VALIDATING upon STATIC_PASS; NOT VALIDATED).
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
    CandidateTenantMismatchError,
)
from creative_governance.candidates.gates import (
    AspectGate,
    CandidateQCGate,
    ContractGate,
    DependencyGate,
    ProbeGate,
    RenderSmokeGate,
    RuntimeContractGate,
    SecurityGate,
    StaticCodeGate,
    TemplateSchemaGate,
    TypeScriptGate,
)
from creative_governance.candidates.gates.ast_runner import run_candidate_ast_worker
from creative_governance.candidates.policies import (
    RUNTIME_VALIDATION_POLICY_VERSION,
    VALIDATION_POLICY_VERSION,
    ValidationFailureCode,
)
from creative_governance.candidates.repository import TemplateCandidateRepository
from creative_governance.candidates.runtime_runner import IsolatedCandidateRunner
from creative_governance.candidates.service import TemplateCandidateService
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
    ValidationSnapshot,
)
from scripts.core.storage import StorageService, build_storage_key
from scripts.core.tenant_model import TenantContext


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateValidationService:
    """
    Sole authority governing static validation for TemplateCandidates.
    """

    def __init__(
        self,
        candidate_service: TemplateCandidateService,
        repository: TemplateCandidateRepository,
        storage_service: StorageService,
    ) -> None:
        self.candidate_service = candidate_service
        self.repository = repository
        self.storage_service = storage_service

        # Initialize static gates in deterministic order
        self.contract_gate = ContractGate()
        self.static_code_gate = StaticCodeGate()
        self.security_gate = SecurityGate()
        self.dependency_gate = DependencyGate()
        self.typescript_gate = TypeScriptGate()
        self.template_schema_gate = TemplateSchemaGate()

        # Initialize S28-07C runtime gates and runner
        self.render_smoke_gate = RenderSmokeGate()
        self.runtime_contract_gate = RuntimeContractGate()
        self.aspect_gate = AspectGate()
        self.probe_gate = ProbeGate()
        self.qc_gate = CandidateQCGate()
        self.runtime_runner = IsolatedCandidateRunner()

    def validate_candidate_static(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        force_rerun: bool = False,
    ) -> CandidateValidationReport:
        """
        Executes the static validation suite on the specified candidate within
        the caller's tenant boundary.

        If all gates pass: awards STATIC_PASS evidence and updates status to VALIDATING.
        Does NOT mark candidate as VALIDATED (reserved for S28-07C runtime tests).
        """
        workspace_id = tenant_context.workspace_id

        # 1. Load tenant-scoped candidate
        candidate = self.candidate_service.get_candidate(tenant_context, candidate_id)

        # Status guard: only DRAFT or VALIDATING candidates can undergo static validation
        if candidate.status not in (CandidateStatus.DRAFT, CandidateStatus.VALIDATING):
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status}'. "
                f"Static validation can only be run on DRAFT or VALIDATING candidates."
            )

        # 2. Freeze validation snapshot
        started_at = _now_utc()
        snapshot = ValidationSnapshot(
            candidate_id=candidate.candidate_id,
            workspace_id=candidate.workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            phase=ValidationPhase.STATIC,
            policy_version=VALIDATION_POLICY_VERSION,
            started_at=started_at,
        )

        # 3. Idempotency Check: reuse identical snapshot report if not force_rerun
        if not force_rerun:
            existing_reports = self.repository.list_validation_reports(candidate_id, workspace_id)
            for prev_rep in existing_reports:
                if (
                    prev_rep.candidate_content_hash == snapshot.candidate_content_hash
                    and prev_rep.candidate_revision == snapshot.candidate_revision
                    and prev_rep.policy_version == VALIDATION_POLICY_VERSION
                    and prev_rep.phase == ValidationPhase.STATIC
                ):
                    return prev_rep

        validation_id = f"val_{uuid.uuid4().hex[:12]}"

        # 4. Run AST & TypeScript analyzer hermetically
        ast_analysis = run_candidate_ast_worker(
            source_code=candidate.source_code,
            dependencies=candidate.dependencies,
            template_schema=candidate.template_schema,
            skip_tsc=False,
            timeout_seconds=25,
        )

        # 5. Deterministic gate execution sequence
        gate_results: List[CandidateGateResult] = []

        # Gate 1: Contract Gate
        gate_results.append(
            self.contract_gate.run(candidate, tenant_context, ast_analysis)
        )

        # Gate 2: Static Code Gate
        gate_results.append(
            self.static_code_gate.run(candidate, tenant_context, ast_analysis)
        )

        # Gate 3: Security Gate
        gate_results.append(
            self.security_gate.run(candidate, tenant_context, ast_analysis)
        )

        # Gate 4: Dependency Gate
        gate_results.append(
            self.dependency_gate.run(candidate, tenant_context, ast_analysis)
        )

        # Gate 5: TypeScript Gate
        gate_results.append(
            self.typescript_gate.run(candidate, tenant_context, ast_analysis)
        )

        # Gate 6: Template Schema Gate
        gate_results.append(
            self.template_schema_gate.run(candidate, tenant_context, ast_analysis)
        )

        # 6. Anti-Stale Validation Concurrency Guard (Section 4)
        fresh_candidate = self.candidate_service.get_candidate(tenant_context, candidate_id)
        is_stale = (
            fresh_candidate.content_hash != snapshot.candidate_content_hash
            or fresh_candidate.revision != snapshot.candidate_revision
        )

        if is_stale:
            stale_gate = CandidateGateResult(
                gate_id="concurrency_freshness_gate",
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.STALE_VALIDATION,
                summary=(
                    f"Candidate '{candidate_id}' mutated during validation. "
                    f"Snapshot revision {snapshot.candidate_revision} (hash {snapshot.candidate_content_hash[:8]}...) "
                    f"drifted to revision {fresh_candidate.revision} (hash {fresh_candidate.content_hash[:8]}...). "
                    f"STATIC_PASS cannot be awarded to a stale snapshot."
                ),
                machine_details={
                    "snapshot_revision": snapshot.candidate_revision,
                    "fresh_revision": fresh_candidate.revision,
                    "snapshot_hash": snapshot.candidate_content_hash,
                    "fresh_hash": fresh_candidate.content_hash,
                },
            )
            gate_results.append(stale_gate)

        # 7. Overall Result Calculation
        if any(g.status == GateStatus.ERROR for g in gate_results):
            overall_result = ValidationOverallResult.ERROR
        elif any(g.status == GateStatus.FAIL for g in gate_results):
            overall_result = ValidationOverallResult.FAIL
        else:
            overall_result = ValidationOverallResult.PASS

        completed_at = _now_utc()

        # Findings summary
        findings = [
            f"[{g.gate_id}] {g.failure_code or 'FAILED'}: {g.summary}"
            for g in gate_results
            if g.status != GateStatus.PASS
        ]

        # 8. Durable Evidence Storage Key Generation (Section 14)
        evidence_refs: Dict[str, str] = {}
        report_storage_key = build_storage_key(
            workspace_id,
            candidate.source_project_id,
            "candidates",
            candidate_id,
            f"validation_{validation_id}_report.json",
        )

        # 9. Construct Canonical Report Contract
        report = CandidateValidationReport(
            validation_id=validation_id,
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            candidate_content_hash=snapshot.candidate_content_hash,
            candidate_revision=snapshot.candidate_revision,
            phase=ValidationPhase.STATIC,
            policy_version=VALIDATION_POLICY_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            gates=gate_results,
            overall_result=overall_result,
            evidence_refs=evidence_refs,
            findings=findings,
            report_id=validation_id,
            passed=(overall_result == ValidationOverallResult.PASS),
            evaluated_at=completed_at,
        )

        # Store report JSON in StorageService
        try:
            self.storage_service.put(
                report_storage_key,
                report.model_dump_json().encode("utf-8"),
                content_type="application/json",
            )
            evidence_refs["report_json"] = report_storage_key
            report = report.model_copy(update={"evidence_refs": evidence_refs})
        except Exception:
            pass

        # Persist report in repository
        persisted_report = self.repository.save_validation_report(report)

        # 10. Update Candidate Status Semantics (Section 13)
        # If STATIC PASS: update status to VALIDATING (NOT VALIDATED)
        if overall_result == ValidationOverallResult.PASS and not is_stale:
            try:
                self.candidate_service.transition_to_validating(
                    tenant_context=tenant_context,
                    candidate_id=candidate.candidate_id,
                    expected_revision=snapshot.candidate_revision,
                )
            except CandidateConflictError:
                # Concurrent update collided at the very end
                pass

        return persisted_report

    def get_validation_report(
        self,
        tenant_context: TenantContext,
        validation_id: str,
    ) -> Optional[CandidateValidationReport]:
        """
        Retrieves a validation report scoped strictly to the caller's workspace.
        """
        return self.repository.get_validation_report(
            validation_id=validation_id,
            workspace_id=tenant_context.workspace_id,
        )

    def list_validation_reports(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
    ) -> List[CandidateValidationReport]:
        """
        Lists all validation reports for a candidate scoped to caller's workspace.
        """
        # Verify candidate exists in caller workspace
        self.candidate_service.get_candidate(tenant_context, candidate_id)
        return self.repository.list_validation_reports(
            candidate_id=candidate_id,
            workspace_id=tenant_context.workspace_id,
        )

    def _find_active_static_pass(
        self,
        candidate_id: str,
        workspace_id: str,
        current_hash: str,
        current_revision: int,
    ) -> Tuple[Optional[CandidateValidationReport], Optional[str]]:
        """
        Finds the active STATIC_PASS report for a candidate and verifies freshness.
        Returns (report, error_reason).
        """
        existing_reports = self.repository.list_validation_reports(candidate_id, workspace_id)
        static_passes = [
            r for r in existing_reports
            if r.phase == ValidationPhase.STATIC and r.overall_result == ValidationOverallResult.PASS
        ]
        if not static_passes:
            return None, ValidationFailureCode.NO_STATIC_PASS_FOUND

        latest_pass = static_passes[-1]
        if (
            latest_pass.candidate_content_hash != current_hash
            or latest_pass.candidate_revision != current_revision
        ):
            return latest_pass, ValidationFailureCode.STALE_STATIC_PASS

        return latest_pass, None

    def validate_candidate_runtime(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        force_rerun: bool = False,
        runner_override: Optional[IsolatedCandidateRunner] = None,
    ) -> CandidateValidationReport:
        """
        Executes the runtime and visual validation suite on the specified candidate
        within the caller's tenant boundary (S28-07C).

        Preconditions:
        - candidate.status == VALIDATING
        - STATIC_PASS report exists and matches current hash/revision

        Runs 5 runtime gates in an ephemeral, isolated temporary workspace:
        1. Render Smoke Gate
        2. Runtime Contract Gate
        3. Aspect Gate
        4. Probe Gate
        5. Candidate QC Gate

        If all gates pass: transitions candidate status to VALIDATED via CAS.
        """
        workspace_id = tenant_context.workspace_id

        # 1. Load tenant-scoped candidate
        candidate = self.candidate_service.get_candidate(tenant_context, candidate_id)

        # 2. Precondition: Candidate status must be VALIDATING (or already validated for idempotent retry)
        if candidate.status != CandidateStatus.VALIDATING and candidate.status.value != "VALIDATED":
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status}'. "
                f"Runtime validation can only be run on candidates in VALIDATING status."
            )
        if candidate.status.value == "VALIDATED" and force_rerun:
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status}'. "
                f"Cannot force rerun runtime validation on already VALIDATED candidate."
            )

        # 3. Precondition: Static validation report check (fail-closed if missing or stale)
        static_report, err_code = self._find_active_static_pass(
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            current_hash=candidate.content_hash,
            current_revision=candidate.revision,
        )

        if err_code == ValidationFailureCode.NO_STATIC_PASS_FOUND or static_report is None:
            raise CandidateEligibilityError(
                f"Runtime validation denied: candidate '{candidate_id}' has no valid STATIC_PASS report. "
                f"Static validation must pass before runtime validation can begin."
            )

        if err_code == ValidationFailureCode.STALE_STATIC_PASS:
            raise CandidateConflictError(
                f"Runtime validation denied: static validation report for candidate '{candidate_id}' is stale. "
                f"Static snapshot ({static_report.candidate_content_hash[:8]}... rev {static_report.candidate_revision}) "
                f"does not match current candidate ({candidate.content_hash[:8]}... rev {candidate.revision})."
            )

        # 4. Freeze Runtime Validation Snapshot
        runtime_validation_id = f"rval_{uuid.uuid4().hex[:12]}"
        started_at = _now_utc()
        static_report_json = static_report.model_dump_json()
        static_report_hash = hashlib.sha256(static_report_json.encode("utf-8")).hexdigest()

        snapshot = ValidationSnapshot(
            candidate_id=candidate.candidate_id,
            workspace_id=candidate.workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            phase=ValidationPhase.RUNTIME,
            policy_version=RUNTIME_VALIDATION_POLICY_VERSION,
            started_at=started_at,
            static_validation_id=static_report.validation_id,
            static_validation_report_hash=static_report_hash,
            runtime_validation_id=runtime_validation_id,
        )

        # 5. Idempotency Check
        if not force_rerun:
            existing_reports = self.repository.list_validation_reports(candidate_id, workspace_id)
            for prev_rep in existing_reports:
                if (
                    prev_rep.phase == ValidationPhase.RUNTIME
                    and prev_rep.candidate_content_hash == snapshot.candidate_content_hash
                    and prev_rep.candidate_revision == snapshot.candidate_revision
                    and prev_rep.static_validation_id == static_report.validation_id
                    and prev_rep.policy_version == RUNTIME_VALIDATION_POLICY_VERSION
                ):
                    return prev_rep

        runner = runner_override or self.runtime_runner

        # 6. Isolated Runtime Preparation & Execution
        workspace_dir = runner.create_workspace(candidate.candidate_id, runtime_validation_id)
        runtime_context: Dict[str, Any] = {}
        gate_results: List[CandidateGateResult] = []
        evidence_refs: Dict[str, str] = {}

        try:
            harness_file, props_file = runner.prepare_workspace(
                workspace_dir=workspace_dir,
                source_code=candidate.source_code,
                fixtures=candidate.fixtures,
                component_name=candidate.name or "CandidateComponent",
            )

            # Gate 1: Render Smoke Gate
            smoke_res = self.render_smoke_gate.run(
                candidate, tenant_context, runner, workspace_dir, harness_file, props_file, runtime_context
            )
            gate_results.append(smoke_res)

            # Gate 2: Runtime Contract Gate
            contract_res = self.runtime_contract_gate.run(
                candidate, tenant_context, runner, workspace_dir, harness_file, props_file, runtime_context
            )
            gate_results.append(contract_res)

            # Gate 3: Aspect Gate
            aspect_res = self.aspect_gate.run(
                candidate, tenant_context, runner, workspace_dir, harness_file, props_file, runtime_context
            )
            gate_results.append(aspect_res)

            # Gate 4: Probe Gate
            probe_res = self.probe_gate.run(
                candidate, tenant_context, runner, workspace_dir, harness_file, props_file, runtime_context
            )
            gate_results.append(probe_res)

            # Gate 5: Candidate QC Gate
            qc_res = self.qc_gate.run(
                candidate, tenant_context, runner, workspace_dir, harness_file, props_file, runtime_context
            )
            gate_results.append(qc_res)

            # Persist visual artifacts permanently into StorageService
            # A. Smoke frame
            smoke_render = runtime_context.get("smoke_render")
            if smoke_render and smoke_render.output_path and Path(smoke_render.output_path).exists():
                smoke_bytes = Path(smoke_render.output_path).read_bytes()
                smoke_key = build_storage_key(
                    workspace_id, candidate.source_project_id, "candidates", candidate_id, f"runtime_{runtime_validation_id}_smoke.png"
                )
                try:
                    self.storage_service.put(smoke_key, smoke_bytes, content_type="image/png")
                    evidence_refs["smoke_frame"] = smoke_key
                except Exception:
                    pass

            # B. Representative frames
            rep_frames = runtime_context.get("representative_frames", [])
            for rf in rep_frames:
                if rf.output_path and Path(rf.output_path).exists():
                    f_bytes = Path(rf.output_path).read_bytes()
                    f_key = build_storage_key(
                        workspace_id, candidate.source_project_id, "candidates", candidate_id, f"runtime_{runtime_validation_id}_frame_{rf.frame_number}.png"
                    )
                    try:
                        self.storage_service.put(f_key, f_bytes, content_type="image/png")
                        evidence_refs[f"frame_{rf.frame_number}"] = f_key
                    except Exception:
                        pass

            # C. Probe report JSON
            probe_records = runtime_context.get("probe_records")
            if probe_records:
                probe_key = build_storage_key(
                    workspace_id, candidate.source_project_id, "candidates", candidate_id, f"runtime_{runtime_validation_id}_probe.json"
                )
                try:
                    self.storage_service.put(probe_key, json.dumps(probe_records).encode("utf-8"), content_type="application/json")
                    evidence_refs["probe_report"] = probe_key
                except Exception:
                    pass

            # D. QC report JSON
            qc_report = runtime_context.get("qc_report")
            if qc_report:
                qc_key = build_storage_key(
                    workspace_id, candidate.source_project_id, "candidates", candidate_id, f"runtime_{runtime_validation_id}_qc.json"
                )
                try:
                    self.storage_service.put(qc_key, json.dumps(qc_report).encode("utf-8"), content_type="application/json")
                    evidence_refs["qc_report"] = qc_key
                except Exception:
                    pass

        finally:
            # Ephemeral workspace cleanup
            runner.cleanup_workspace(workspace_dir)

        # 7. Anti-Stale Concurrency Guard (Section 4)
        fresh_candidate = self.candidate_service.get_candidate(tenant_context, candidate_id)
        is_stale = (
            fresh_candidate.content_hash != snapshot.candidate_content_hash
            or fresh_candidate.revision != snapshot.candidate_revision
        )
        if is_stale:
            stale_gate = CandidateGateResult(
                gate_id="runtime_concurrency_freshness_gate",
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.STALE_RUNTIME_VALIDATION,
                summary=(
                    f"Candidate '{candidate_id}' mutated during runtime validation. "
                    f"Snapshot revision {snapshot.candidate_revision} drifted to {fresh_candidate.revision}. "
                    f"VALIDATED status cannot be awarded to a stale snapshot."
                ),
                machine_details={
                    "snapshot_revision": snapshot.candidate_revision,
                    "fresh_revision": fresh_candidate.revision,
                    "snapshot_hash": snapshot.candidate_content_hash,
                    "fresh_hash": fresh_candidate.content_hash,
                },
            )
            gate_results.append(stale_gate)

        # 8. Overall Result Calculation
        if any(g.status == GateStatus.ERROR for g in gate_results):
            overall_result = ValidationOverallResult.ERROR
        elif any(g.status == GateStatus.FAIL for g in gate_results):
            overall_result = ValidationOverallResult.FAIL
        else:
            overall_result = ValidationOverallResult.PASS

        completed_at = _now_utc()
        findings = [
            f"[{g.gate_id}] {g.failure_code or 'FAILED'}: {g.summary}"
            for g in gate_results
            if g.status != GateStatus.PASS
        ]

        report_storage_key = build_storage_key(
            workspace_id,
            candidate.source_project_id,
            "candidates",
            candidate_id,
            f"runtime_{runtime_validation_id}_report.json",
        )

        # 9. Construct Canonical Report Contract
        report = CandidateValidationReport(
            validation_id=runtime_validation_id,
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            candidate_content_hash=snapshot.candidate_content_hash,
            candidate_revision=snapshot.candidate_revision,
            phase=ValidationPhase.RUNTIME,
            policy_version=RUNTIME_VALIDATION_POLICY_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            gates=gate_results,
            overall_result=overall_result,
            evidence_refs=evidence_refs,
            findings=findings,
            report_id=runtime_validation_id,
            passed=(overall_result == ValidationOverallResult.PASS),
            evaluated_at=completed_at,
            static_validation_id=static_report.validation_id,
            static_validation_report_hash=static_report_hash,
        )

        # Store report JSON in StorageService
        try:
            self.storage_service.put(
                report_storage_key,
                report.model_dump_json().encode("utf-8"),
                content_type="application/json",
            )
            evidence_refs["report_json"] = report_storage_key
            report = report.model_copy(update={"evidence_refs": evidence_refs})
        except Exception:
            pass

        # Persist report in repository
        persisted_report = self.repository.save_validation_report(report)

        # 10. Update Candidate Status Semantics: VALIDATING -> VALIDATED (Section 16)
        if overall_result == ValidationOverallResult.PASS and not is_stale:
            try:
                self.candidate_service.transition_to_validated(
                    tenant_context=tenant_context,
                    candidate_id=candidate.candidate_id,
                    expected_revision=snapshot.candidate_revision,
                    runtime_validation_report_id=runtime_validation_id,
                )
            except CandidateConflictError:
                # Concurrent update collided at the very end
                pass

        return persisted_report

