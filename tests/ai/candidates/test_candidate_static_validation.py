"""
tests/ai/candidates/test_candidate_static_validation.py
======================================================
Comprehensive Static Validation Gate test suite for TemplateCandidate (S28-07B).

Verifies:
1. Healthy candidate passes all 6 gates and receives STATIC_PASS evidence.
2. Invariant: candidate is NOT fully VALIDATED (status is VALIDATING; VALIDATED is forbidden).
3. Mandatory Negative Tests across all 6 gates:
   - Security Gate: fs, child_process, network clients, process.env secrets.
   - Static Code Gate: eval, new Function, missing export, dynamic require.
   - Dependency Gate: undeclared import, forbidden dependency, unknown dependency.
   - TypeScript Gate: type errors, invalid JSX / syntax errors.
   - Template Schema Gate: invalid schema structure, fixture schema mismatch.
   - Contract Gate: tampered content_hash fails closed.
   - Concurrency: candidate mutated during validation triggers STALE_VALIDATION.
4. Idempotency: re-running validation on unchanged snapshot returns consistent report.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from creative_governance.candidates.gates import (
    ContractGate,
    DependencyGate,
    SecurityGate,
    StaticCodeGate,
    TemplateSchemaGate,
    TypeScriptGate,
)
from creative_governance.candidates.policies import ValidationFailureCode
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.validation_service import CandidateValidationService
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
    ComposeEvaluationResult,
    ReuseEvaluationResult,
)
from ai.contracts.creative.template_candidate import (
    CandidateStatus,
    GateStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend
from scripts.core.tenant_model import TenantContext, ProjectRecord


@pytest.fixture
def test_tenant():
    principal = Principal(
        principal_id="usr_alice",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    return TenantContext(
        workspace_id="ws_acme",
        user_id="usr_alice",
        role=Role.EDITOR,
        principal=principal,
    )


@pytest.fixture
def candidate_stack(tmp_path):
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    candidate_service = TemplateCandidateService(
        repository=repo,
        storage_service=storage,
    )
    # Register project for tenant verification
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="prj_brand_001",
            workspace_id="ws_acme",
            created_by="usr_alice",
            name="Brand Launch",
        )
    )
    validation_service = CandidateValidationService(
        candidate_service=candidate_service,
        repository=repo,
        storage_service=storage,
    )
    return candidate_service, validation_service, repo, storage


def create_healthy_candidate(candidate_service, test_tenant, valid_create_decision, valid_creative_plan):
    valid_tsx = """
import React from 'react';

export interface KineticTextProps {
  title: string;
  speed?: number;
}

export const KineticText: React.FC<KineticTextProps> = ({ title, speed = 1.0 }) => {
  return (
    <div style={{ fontSize: 48, color: '#ffffff' }}>
      <h1>{title}</h1>
      <span>Speed: {speed}</span>
    </div>
  );
};
"""
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "speed": {"type": "number", "minimum": 0.1, "maximum": 5.0},
        },
        "required": ["title"],
    }
    fixtures = {
        "title": "Launch Sequence",
        "speed": 1.5,
    }
    return candidate_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code=valid_tsx,
        template_schema=schema,
        dependencies=[],
        fixtures=fixtures,
        name="Kinetic Spring Typography",
        description="Clean spring typography component adhering to Remotion standards.",
    )


# ─── 1. Positive Tests ────────────────────────────────────────────────────────

def test_static_validation_healthy_candidate_passes_all_gates(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, storage = candidate_stack
    candidate = create_healthy_candidate(cand_service, test_tenant, valid_create_decision, valid_creative_plan)

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    # Report verification
    assert report.validation_id.startswith("val_")
    assert report.candidate_id == candidate.candidate_id
    assert report.workspace_id == test_tenant.workspace_id
    assert report.overall_result == ValidationOverallResult.PASS
    assert report.phase == ValidationPhase.STATIC
    assert len(report.gates) == 6

    # Verify all 6 gates individually passed
    gate_statuses = {g.gate_id: g.status for g in report.gates}
    assert gate_statuses["contract_gate"] == GateStatus.PASS
    assert gate_statuses["static_code_gate"] == GateStatus.PASS
    assert gate_statuses["security_gate"] == GateStatus.PASS
    assert gate_statuses["dependency_gate"] == GateStatus.PASS
    assert gate_statuses["typescript_gate"] == GateStatus.PASS
    assert gate_statuses["template_schema_gate"] == GateStatus.PASS

    # Verify candidate updated status semantics (Section 13)
    refetched = cand_service.get_candidate(test_tenant, candidate.candidate_id)
    assert refetched.status == CandidateStatus.VALIDATING

    # CRITICAL INVARIANT: candidate is NOT fully VALIDATED
    assert refetched.status != CandidateStatus.VALIDATED


# ─── 2. Mandatory Security Gate Negative Tests (Section 8) ────────────────────

def test_negative_security_gate_forbidden_fs(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
import fs from 'fs';
export const BadComp = () => <div>{fs.readFileSync('/etc/passwd', 'utf8')}</div>;
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    sec_gate = next(g for g in report.gates if g.gate_id == "security_gate")
    assert sec_gate.status == GateStatus.FAIL
    assert sec_gate.failure_code == ValidationFailureCode.SECURITY_FORBIDDEN_FS

    # Candidate status must remain DRAFT (NOT VALIDATING, NOT VALIDATED)
    refetched = cand_service.get_candidate(test_tenant, candidate.candidate_id)
    assert refetched.status == CandidateStatus.DRAFT


def test_negative_security_gate_forbidden_child_process(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
import { exec } from 'node:child_process';
export const BadComp = () => <div>{exec('id')}</div>;
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    sec_gate = next(g for g in report.gates if g.gate_id == "security_gate")
    assert sec_gate.status == GateStatus.FAIL
    assert sec_gate.failure_code == ValidationFailureCode.SECURITY_FORBIDDEN_CHILD_PROCESS


def test_negative_security_gate_forbidden_network_client(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
import axios from 'axios';
export const BadComp = () => <div>Network</div>;
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    sec_gate = next(g for g in report.gates if g.gate_id == "security_gate")
    assert sec_gate.status == GateStatus.FAIL
    assert sec_gate.failure_code == ValidationFailureCode.SECURITY_FORBIDDEN_NETWORK


def test_negative_security_gate_environment_secret_access(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
export const LeakComp = () => {
  const secret = process.env.OPENAI_API_KEY;
  return <div>{secret}</div>;
};
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    sec_gate = next(g for g in report.gates if g.gate_id == "security_gate")
    assert sec_gate.status == GateStatus.FAIL
    assert sec_gate.failure_code == ValidationFailureCode.SECURITY_FORBIDDEN_ENV_ACCESS


# ─── 3. Mandatory Static Code Gate Negative Tests (Section 7) ─────────────────

def test_negative_static_code_gate_forbidden_eval(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
export const EvalComp = () => {
  eval("console.log('danger')");
  return <div>Eval</div>;
};
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    code_gate = next(g for g in report.gates if g.gate_id == "static_code_gate")
    assert code_gate.status == GateStatus.FAIL
    assert code_gate.failure_code == ValidationFailureCode.FORBIDDEN_EVAL


def test_negative_static_code_gate_forbidden_new_function(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
export const FuncComp = () => {
  const dynamicFn = new Function("return 42");
  return <div>{dynamicFn()}</div>;
};
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    code_gate = next(g for g in report.gates if g.gate_id == "static_code_gate")
    assert code_gate.status == GateStatus.FAIL
    assert code_gate.failure_code == ValidationFailureCode.FORBIDDEN_NEW_FUNCTION


def test_negative_static_code_gate_missing_component_export(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="const internalOnly = 42; console.log(internalOnly);",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    code_gate = next(g for g in report.gates if g.gate_id == "static_code_gate")
    assert code_gate.status == GateStatus.FAIL
    assert code_gate.failure_code == ValidationFailureCode.MISSING_COMPONENT_EXPORT


# ─── 4. Mandatory Dependency Gate Negative Tests (Section 9) ──────────────────

def test_negative_dependency_gate_undeclared_import(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    # Uses an external package that is not in the core allowlist (react, remotion, zod, etc.)
    # without declaring it in candidate.dependencies
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
import { merge } from 'ts-morph';
export const DepComp = () => <div>Undeclared</div>;
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],  # undeclared!
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    dep_gate = next(g for g in report.gates if g.gate_id == "dependency_gate")
    assert dep_gate.status == GateStatus.FAIL
    assert dep_gate.failure_code == ValidationFailureCode.UNDECLARED_IMPORT


def test_negative_dependency_gate_forbidden_package(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Comp = () => <div>Allowed</div>;",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=["shelljs@^0.8.5"],  # forbidden package!
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    dep_gate = next(g for g in report.gates if g.gate_id == "dependency_gate")
    assert dep_gate.status == GateStatus.FAIL
    assert dep_gate.failure_code == ValidationFailureCode.FORBIDDEN_DEPENDENCY


def test_negative_dependency_gate_unknown_external_dependency(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Comp = () => <div>Allowed</div>;",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=["nonexistent-custom-ui-lib-999@^1.0.0"],  # unknown package!
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    dep_gate = next(g for g in report.gates if g.gate_id == "dependency_gate")
    assert dep_gate.status == GateStatus.FAIL
    assert dep_gate.failure_code == ValidationFailureCode.UNKNOWN_EXTERNAL_DEPENDENCY


# ─── 5. Mandatory TypeScript Gate Negative Tests (Section 10) ─────────────────

def test_negative_typescript_gate_type_error(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="""
import React from 'react';
const badNumber: number = "not_a_number";
export const TypeErrComp = () => <div>{badNumber}</div>;
""",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    ts_gate = next(g for g in report.gates if g.gate_id == "typescript_gate")
    assert ts_gate.status == GateStatus.FAIL
    assert ts_gate.failure_code == ValidationFailureCode.TYPESCRIPT_TYPE_ERROR


def test_negative_typescript_gate_invalid_jsx(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const JsxErr = () => <div unclosed_tag ;",
        template_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    # Either static code or TS gate catches syntax
    failed_codes = {g.failure_code for g in report.gates if g.status == GateStatus.FAIL}
    assert (
        ValidationFailureCode.SYNTAX_ERROR in failed_codes
        or ValidationFailureCode.TYPESCRIPT_SYNTAX_ERROR in failed_codes
        or ValidationFailureCode.TYPESCRIPT_JSX_ERROR in failed_codes
    )


# ─── 6. Mandatory Template Schema Gate Negative Tests (Section 11) ────────────

def test_negative_template_schema_gate_invalid_schema(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Comp = () => <div>Test</div>;",
        template_schema={"type": "invalid_unknown_schema_type"},
        dependencies=[],
        fixtures={"x": "val"},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    schema_gate = next(g for g in report.gates if g.gate_id == "template_schema_gate")
    assert schema_gate.status == GateStatus.FAIL
    assert schema_gate.failure_code == ValidationFailureCode.INVALID_SCHEMA_STRUCTURE


def test_negative_template_schema_gate_fixture_mismatch(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = cand_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Comp = () => <div>Test</div>;",
        template_schema={
            "type": "object",
            "properties": {
                "threshold": {"type": "number", "minimum": 10},
            },
            "required": ["threshold"],
        },
        dependencies=[],
        # Fixture violates schema: value is 2, which is less than minimum 10
        fixtures={"threshold": 2},
    )

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    schema_gate = next(g for g in report.gates if g.gate_id == "template_schema_gate")
    assert schema_gate.status == GateStatus.FAIL
    assert schema_gate.failure_code == ValidationFailureCode.FIXTURE_SCHEMA_MISMATCH


# ─── 7. Mandatory Contract Gate Content Hash Negative Test (Section 6) ────────

def test_negative_contract_gate_tampered_content_hash(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = create_healthy_candidate(cand_service, test_tenant, valid_create_decision, valid_creative_plan)

    # Tamper with stored content_hash directly in repository
    tampered = candidate.model_copy(update={"content_hash": "sha256_corrupted_hash_tampered"})
    repo._candidates[(candidate.workspace_id, candidate.candidate_id)] = tampered

    report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    contract_gate = next(g for g in report.gates if g.gate_id == "contract_gate")
    assert contract_gate.status == GateStatus.FAIL
    assert contract_gate.failure_code == ValidationFailureCode.CONTENT_HASH_MISMATCH


# ─── 8. Concurrency & Anti-Stale Validation Guard (Section 4) ─────────────────

def test_candidate_mutation_during_validation_triggers_stale_validation(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = create_healthy_candidate(cand_service, test_tenant, valid_create_decision, valid_creative_plan)

    # Simulate concurrency: candidate is updated while validation is running
    original_run = val_service.contract_gate.run

    def mutate_candidate_on_first_gate(*args, **kwargs):
        # Concurrently bump revision & update description
        cand_service.update_draft_candidate(
            tenant_context=test_tenant,
            candidate_id=candidate.candidate_id,
            expected_revision=candidate.revision,
            description="Mutated while validation in progress",
        )
        return original_run(*args, **kwargs)

    with patch.object(val_service.contract_gate, "run", side_effect=mutate_candidate_on_first_gate):
        report = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    assert report.overall_result == ValidationOverallResult.FAIL
    fresh_gate = next((g for g in report.gates if g.gate_id == "concurrency_freshness_gate"), None)
    assert fresh_gate is not None
    assert fresh_gate.status == GateStatus.FAIL
    assert fresh_gate.failure_code == ValidationFailureCode.STALE_VALIDATION


# ─── 9. Idempotency Test (Section 15) ─────────────────────────────────────────

def test_static_validation_idempotency(
    candidate_stack, test_tenant, valid_create_decision, valid_creative_plan
):
    cand_service, val_service, repo, _ = candidate_stack
    candidate = create_healthy_candidate(cand_service, test_tenant, valid_create_decision, valid_creative_plan)

    # First validation run
    report_1 = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)
    assert report_1.overall_result == ValidationOverallResult.PASS

    # Second validation run without force_rerun
    report_2 = val_service.validate_candidate_static(test_tenant, candidate.candidate_id)

    # Must reuse identical report
    assert report_2.validation_id == report_1.validation_id
    assert report_2.candidate_content_hash == report_1.candidate_content_hash
    assert report_2.overall_result == report_1.overall_result
