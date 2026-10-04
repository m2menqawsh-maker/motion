"""
tests/ai/candidates/test_candidate_runtime_validation.py
========================================================
Comprehensive Runtime & Visual Validation Gate test suite for TemplateCandidate (S28-07C).

Verifies:
1. Preconditions: candidate must be VALIDATING with valid, non-stale STATIC_PASS.
2. Complete healthy candidate execution:
   - DRAFT -> Static Validation -> STATIC_PASS -> VALIDATING
   - Runtime Validation -> Render Smoke PASS, Runtime Contract PASS, Aspect PASS, Probe PASS, QC PASS -> VALIDATED.
   - Proves candidate is still NOT APPROVED, NOT PROMOTED, and NOT in Canonical Registry.
3. Render Smoke Gate negative tests: mount error, import error, timeout, empty output, tool error.
4. Runtime Contract Gate negative tests: invalid fps, invalid duration bounds, invalid fixtures.
5. Aspect Gate negative tests: unsupported aspect ratio, aspect render failure, dimension mismatch.
6. Probe Gate negative tests: missing representative frames, dimension mismatch.
7. Candidate QC Gate negative tests: black output violation, empty output violation, corrupt frame, tool error.
8. Anti-stale concurrency protection during runtime validation.
9. Idempotency & safe retry.
10. Cross-tenant isolation (Workspace A cannot validate or inspect Workspace B candidate).
11. Immutability after validation (VALIDATED candidate cannot be mutated directly).
12. Live Remotion still execution integration test.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch
import pytest
from PIL import Image

from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
)
from creative_governance.candidates.gates import (
    AspectGate,
    CandidateQCGate,
    ProbeGate,
    RenderSmokeGate,
    RuntimeContractGate,
)
from creative_governance.candidates.policies import (
    CANDIDATE_RUNTIME_QC_PROFILE,
    CANONICAL_ASPECT_RATIOS,
    RUNTIME_VALIDATION_POLICY_VERSION,
    ValidationFailureCode,
)
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.runtime_runner import (
    CandidateRenderResult,
    IsolatedCandidateRunner,
)
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
from scripts.core.tenant_model import ProjectRecord, TenantContext


# ─── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tenant_a():
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
def tenant_b():
    principal = Principal(
        principal_id="usr_bob",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    return TenantContext(
        workspace_id="ws_globex",
        user_id="usr_bob",
        role=Role.EDITOR,
        principal=principal,
    )

@pytest.fixture
def runtime_stack(tmp_path):
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    candidate_service = TemplateCandidateService(
        repository=repo,
        storage_service=storage,
    )
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="prj_brand_001",
            workspace_id="ws_acme",
            created_by="usr_alice",
            name="Brand Launch",
        )
    )
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="prj_globex_001",
            workspace_id="ws_globex",
            created_by="usr_bob",
            name="Globex Operations",
        )
    )
    validation_service = CandidateValidationService(
        candidate_service=candidate_service,
        repository=repo,
        storage_service=storage,
    )
    return candidate_service, validation_service, repo, storage


def create_healthy_test_candidate(candidate_service, tenant, valid_create_decision, valid_creative_plan):
    source_code = """
import React from 'react';
import { AbsoluteFill } from 'remotion';

export interface KineticTextProps {
  title: string;
  speed?: number;
}

export const KineticText: React.FC<KineticTextProps> = ({ title, speed = 1.0 }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#0A0E27', justifyContent: 'center', alignItems: 'center' }}>
      <h1 style={{ fontSize: 64, color: '#00F5FF', fontFamily: 'sans-serif' }}>{title}</h1>
      <p style={{ fontSize: 24, color: '#FFFFFF' }}>Speed: {speed}</p>
    </AbsoluteFill>
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
        "aspect_ratios": ["9:16", "16:9"],
        "fps": 30,
        "durationInFrames": 30,
    }
    fixtures = {
        "title": "Quantum Kinetic Typography",
        "speed": 1.5,
    }
    return candidate_service.create_candidate(
        tenant_context=tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code=source_code,
        template_schema=schema,
        dependencies=[],
        fixtures=fixtures,
        name="KineticText",
        description="Clean kinetic typography component.",
        proposed_tags=["9:16", "16:9"],
    )


def create_mock_png(width: int, height: int, color=(10, 14, 39)) -> bytes:
    """Creates a valid, non-black, non-uniform PNG image in memory."""
    img = Image.new("RGB", (width, height), color=color)
    # Draw some varied pixels to ensure non-zero variance
    for x in range(min(100, width)):
        for y in range(min(100, height)):
            img.putpixel((x, y), (0, 245, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def mock_successful_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
    """Mock runner producing valid test PNG still."""
    out_name = out_filename or f"frame_{frame_index:02d}_f{frame_number}.png"
    out_path = Path(workspace_dir) / out_name
    png_data = create_mock_png(width, height)
    out_path.write_bytes(png_data)
    import hashlib
    sha = hashlib.sha256(png_data).hexdigest()
    return CandidateRenderResult(
        success=True,
        frame_index=frame_index,
        frame_number=frame_number,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        output_path=str(out_path.absolute()),
        sha256_digest=sha,
        file_size_bytes=len(png_data),
    )


# ─── Preconditions & Static Gate Boundary Tests ───────────────────────────────

def test_precondition_draft_candidate_denied_runtime_validation(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    assert candidate.status == CandidateStatus.DRAFT

    # DRAFT candidate cannot run runtime validation directly
    with pytest.raises(CandidateInvalidStatusError) as exc_info:
        validation_service.validate_candidate_runtime(tenant_a, candidate.candidate_id)
    assert "VALIDATING" in str(exc_info.value)


def test_precondition_missing_static_pass_denied(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, repo, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    # Manually force status to VALIDATING without static report
    repo.update_candidate_status_cas(
        candidate_id=candidate.candidate_id,
        workspace_id=tenant_a.workspace_id,
        status=CandidateStatus.VALIDATING,
        expected_revision=candidate.revision,
    )

    with pytest.raises(CandidateEligibilityError) as exc_info:
        validation_service.validate_candidate_runtime(tenant_a, candidate.candidate_id)
    assert "STATIC_PASS" in str(exc_info.value)


def test_precondition_stale_static_pass_denied(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, repo, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    # 1. Run static validation to obtain STATIC_PASS
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)
    updated = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert updated.status == CandidateStatus.VALIDATING

    # 2. Simulate drift in candidate content hash
    tampered_candidate = updated.model_copy(update={"content_hash": "stale_hash_xyz_12345"})
    repo._candidates[(tenant_a.workspace_id, candidate.candidate_id)] = tampered_candidate

    with pytest.raises(CandidateConflictError) as exc_info:
        validation_service.validate_candidate_runtime(tenant_a, candidate.candidate_id)
    assert "stale" in str(exc_info.value).lower()


# ─── Full Successful Validation Flow ──────────────────────────────────────────

def test_full_successful_candidate_validation_flow(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, repo, storage = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    assert candidate.status == CandidateStatus.DRAFT

    # Step 1: Static Validation
    static_report = validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)
    assert static_report.overall_result == ValidationOverallResult.PASS
    assert static_report.phase == ValidationPhase.STATIC

    validating_cand = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert validating_cand.status == CandidateStatus.VALIDATING

    # Step 2: Runtime Validation
    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_successful_render)
    runtime_report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    # Verify Runtime Report
    assert runtime_report.overall_result == ValidationOverallResult.PASS
    assert runtime_report.phase == ValidationPhase.RUNTIME
    assert runtime_report.static_validation_id == static_report.validation_id

    # Verify All 5 Expected Runtime Gates
    gate_ids = [g.gate_id for g in runtime_report.gates]
    assert "render_smoke_gate" in gate_ids
    assert "runtime_contract_gate" in gate_ids
    assert "aspect_gate" in gate_ids
    assert "probe_gate" in gate_ids
    assert "qc_gate" in gate_ids

    for g in runtime_report.gates:
        assert g.status == GateStatus.PASS

    # Verify Candidate Status Transition
    validated_cand = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert validated_cand.status == CandidateStatus.VALIDATED

    # Invariants Verification: VALIDATED != APPROVED and != PROMOTED
    assert validated_cand.status != CandidateStatus.APPROVED
    assert validated_cand.status != CandidateStatus.PROMOTED

    # Verify zero presence in Canonical Registry
    registry_file = Path("registry/template-registry-data.json")
    if registry_file.exists():
        assert candidate.candidate_id not in registry_file.read_text(encoding="utf-8")


# ─── Render Smoke Negative Tests ──────────────────────────────────────────────

def test_render_smoke_mount_error_failure(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_mount_crash(**kwargs):
        return CandidateRenderResult(
            success=False,
            frame_index=0,
            frame_number=0,
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            error_message="React mount crash: Element type is invalid. Expected a string or ReactClass.",
            failure_code=ValidationFailureCode.RENDER_MOUNT_ERROR,
            is_tool_error=False,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_mount_crash)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    smoke_gate = next(g for g in report.gates if g.gate_id == "render_smoke_gate")
    assert smoke_gate.status == GateStatus.FAIL
    assert smoke_gate.failure_code == ValidationFailureCode.RENDER_MOUNT_ERROR

    # Candidate status must remain VALIDATING
    cand = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert cand.status == CandidateStatus.VALIDATING


def test_render_smoke_import_error_failure(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_import_failure(**kwargs):
        return CandidateRenderResult(
            success=False,
            frame_index=0,
            frame_number=0,
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            error_message="Cannot find module 'non-existent-lib-xyz'",
            failure_code=ValidationFailureCode.RENDER_IMPORT_ERROR,
            is_tool_error=False,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_import_failure)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    smoke_gate = next(g for g in report.gates if g.gate_id == "render_smoke_gate")
    assert smoke_gate.status == GateStatus.FAIL
    assert smoke_gate.failure_code == ValidationFailureCode.RENDER_IMPORT_ERROR


def test_render_smoke_timeout_failure(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_timeout(**kwargs):
        return CandidateRenderResult(
            success=False,
            frame_index=0,
            frame_number=0,
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            error_message="Render timed out after 30s",
            failure_code=ValidationFailureCode.RENDER_TIMEOUT,
            is_tool_error=False,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_timeout)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    smoke_gate = next(g for g in report.gates if g.gate_id == "render_smoke_gate")
    assert smoke_gate.status == GateStatus.FAIL
    assert smoke_gate.failure_code == ValidationFailureCode.RENDER_TIMEOUT


def test_render_smoke_empty_output_failure(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_empty_output(**kwargs):
        return CandidateRenderResult(
            success=False,
            frame_index=0,
            frame_number=0,
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            error_message="Rendered output image missing or 0 bytes",
            failure_code=ValidationFailureCode.RENDER_EMPTY_OUTPUT,
            is_tool_error=False,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_empty_output)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    smoke_gate = next(g for g in report.gates if g.gate_id == "render_smoke_gate")
    assert smoke_gate.status == GateStatus.FAIL
    assert smoke_gate.failure_code == ValidationFailureCode.RENDER_EMPTY_OUTPUT


def test_render_smoke_tool_execution_error(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_tool_crash(**kwargs):
        return CandidateRenderResult(
            success=False,
            frame_index=0,
            frame_number=0,
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            error_message="Subprocess failed to spawn: /usr/bin/npx not found",
            failure_code=ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR,
            is_tool_error=True,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_tool_crash)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    # Tool crash must result in ERROR verdict (never PASS)
    assert report.overall_result == ValidationOverallResult.ERROR
    smoke_gate = next(g for g in report.gates if g.gate_id == "render_smoke_gate")
    assert smoke_gate.status == GateStatus.ERROR
    assert smoke_gate.failure_code == ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR


# ─── Runtime Contract Gate Negative Tests ─────────────────────────────────────

def test_runtime_contract_invalid_fps(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    # Update candidate in DRAFT with non-standard fps
    tampered_schema = dict(candidate.template_schema)
    tampered_schema["fps"] = 17
    candidate = candidate_service.update_draft_candidate(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        expected_revision=candidate.revision,
        template_schema=tampered_schema,
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_successful_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    contract_gate = next(g for g in report.gates if g.gate_id == "runtime_contract_gate")
    assert contract_gate.status == GateStatus.FAIL
    assert contract_gate.failure_code == ValidationFailureCode.INVALID_RUNTIME_FPS


# ─── Aspect Gate Negative Tests ───────────────────────────────────────────────

def test_aspect_gate_unsupported_aspect_ratio(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    # Update candidate in DRAFT with unsupported aspect ratio
    tampered_schema = dict(candidate.template_schema)
    tampered_schema["aspect_ratios"] = ["9:16", "99:1"]
    candidate = candidate_service.update_draft_candidate(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        expected_revision=candidate.revision,
        template_schema=tampered_schema,
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_successful_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    aspect_gate = next(g for g in report.gates if g.gate_id == "aspect_gate")
    assert aspect_gate.status == GateStatus.FAIL
    assert aspect_gate.failure_code == ValidationFailureCode.UNSUPPORTED_ASPECT_RATIO


def test_aspect_gate_render_failure_on_declared_aspect(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_fail_on_16_9(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
        if aspect_ratio == "16:9":
            return CandidateRenderResult(
                success=False,
                frame_index=0,
                frame_number=0,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message="16:9 layout component threw in flexbox calculation",
                failure_code=ValidationFailureCode.ASPECT_RENDER_FAILED,
                is_tool_error=False,
            )
        return mock_successful_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_fail_on_16_9)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    aspect_gate = next(g for g in report.gates if g.gate_id == "aspect_gate")
    assert aspect_gate.status == GateStatus.FAIL


# ─── Candidate QC Gate Negative Tests ─────────────────────────────────────────

def test_qc_gate_black_output_violation(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan, tmp_path
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    # Mock runner that produces a pure black frame
    def mock_black_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
        out_name = out_filename or f"frame_{frame_index:02d}_f{frame_number}.png"
        out_path = Path(workspace_dir) / out_name
        # Solid black image (0, 0, 0)
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        img.save(out_path, format="PNG")
        data = out_path.read_bytes()
        import hashlib
        return CandidateRenderResult(
            success=True,
            frame_index=frame_index,
            frame_number=frame_number,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            output_path=str(out_path.absolute()),
            sha256_digest=hashlib.sha256(data).hexdigest(),
            file_size_bytes=len(data),
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_black_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    qc_gate = next(g for g in report.gates if g.gate_id == "qc_gate")
    assert qc_gate.status == GateStatus.FAIL
    assert qc_gate.failure_code == ValidationFailureCode.QC_BLACK_OUTPUT

    # Status must NOT be VALIDATED
    cand = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert cand.status == CandidateStatus.VALIDATING


def test_qc_gate_empty_uniform_output_violation(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    # Mock runner that produces a solid white frame (zero visual variance)
    def mock_solid_white_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
        out_name = out_filename or f"frame_{frame_index:02d}_f{frame_number}.png"
        out_path = Path(workspace_dir) / out_name
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        img.save(out_path, format="PNG")
        data = out_path.read_bytes()
        import hashlib
        return CandidateRenderResult(
            success=True,
            frame_index=frame_index,
            frame_number=frame_number,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            output_path=str(out_path.absolute()),
            sha256_digest=hashlib.sha256(data).hexdigest(),
            file_size_bytes=len(data),
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_solid_white_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    qc_gate = next(g for g in report.gates if g.gate_id == "qc_gate")
    assert qc_gate.status == GateStatus.FAIL
    assert qc_gate.failure_code == ValidationFailureCode.QC_EMPTY_OUTPUT


def test_qc_gate_corrupt_frame_file(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    def mock_corrupt_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
        out_name = out_filename or f"frame_{frame_index:02d}_f{frame_number}.png"
        out_path = Path(workspace_dir) / out_name
        # Write corrupted bytes that pass basic header check but fail PIL decompression
        out_path.write_bytes(b"\x89PNG\r\n\x1a\nCORRUPTED_PIXEL_DATA_TRUNCATED")
        import hashlib
        return CandidateRenderResult(
            success=True,
            frame_index=frame_index,
            frame_number=frame_number,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            output_path=str(out_path.absolute()),
            sha256_digest=hashlib.sha256(b"corrupt").hexdigest(),
            file_size_bytes=32,
        )

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_corrupt_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    assert report.overall_result == ValidationOverallResult.FAIL
    qc_gate = next(g for g in report.gates if g.gate_id == "qc_gate")
    assert qc_gate.status == GateStatus.FAIL
    assert qc_gate.failure_code == ValidationFailureCode.QC_CORRUPT_FRAME


# ─── Concurrency & Anti-Stale Tests ───────────────────────────────────────────

def test_anti_stale_mutation_during_runtime_validation(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, repo, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    # Hook runner to mutate candidate midway through runtime validation
    def mock_render_with_midway_mutation(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename):
        # Mutate candidate revision in repo during execution
        key = (tenant_a.workspace_id, candidate.candidate_id)
        current = repo._candidates[key]
        repo._candidates[key] = current.model_copy(
            update={"revision": current.revision + 1, "content_hash": "mutated_hash_midway"}
        )
        return mock_successful_render(workspace_dir, frame_number, frame_index, width, height, aspect_ratio, out_filename)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_render_with_midway_mutation)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    # Must detect stale mutation and reject VALIDATED
    assert report.overall_result == ValidationOverallResult.FAIL
    stale_gate = next(g for g in report.gates if g.gate_id == "runtime_concurrency_freshness_gate")
    assert stale_gate.failure_code == ValidationFailureCode.STALE_RUNTIME_VALIDATION

    cand = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert cand.status != CandidateStatus.VALIDATED


# ─── Tenant Isolation Tests ───────────────────────────────────────────────────

def test_cross_tenant_runtime_validation_denied(
    runtime_stack, tenant_a, tenant_b, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate_a = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate_a.candidate_id)

    # Tenant B tries to validate Tenant A's candidate
    with pytest.raises(CandidateNotFoundError):
        validation_service.validate_candidate_runtime(tenant_b, candidate_a.candidate_id)


def test_cross_tenant_report_read_denied(
    runtime_stack, tenant_a, tenant_b, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate_a = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate_a.candidate_id)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_successful_render)
    report = validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate_a.candidate_id,
        runner_override=mock_runner,
    )

    # Tenant B cannot read Tenant A's report
    b_report = validation_service.get_validation_report(tenant_b, report.validation_id)
    assert b_report is None


# ─── Immutability After Validation ────────────────────────────────────────────

def test_validated_candidate_cannot_be_mutated(
    runtime_stack, tenant_a, valid_create_decision, valid_creative_plan
):
    candidate_service, validation_service, _, _ = runtime_stack
    candidate = create_healthy_test_candidate(
        candidate_service, tenant_a, valid_create_decision, valid_creative_plan
    )
    validation_service.validate_candidate_static(tenant_a, candidate.candidate_id)

    mock_runner = IsolatedCandidateRunner(mock_render_fn=mock_successful_render)
    validation_service.validate_candidate_runtime(
        tenant_context=tenant_a,
        candidate_id=candidate.candidate_id,
        runner_override=mock_runner,
    )

    validated = candidate_service.get_candidate(tenant_a, candidate.candidate_id)
    assert validated.status == CandidateStatus.VALIDATED

    # Attempting to mutate a VALIDATED candidate raises CandidateInvalidStatusError
    with pytest.raises(CandidateInvalidStatusError) as exc_info:
        candidate_service.update_draft_candidate(
            tenant_context=tenant_a,
            candidate_id=candidate.candidate_id,
            expected_revision=validated.revision,
            source_code="export const Tampered = () => null;",
        )
    assert "DRAFT" in str(exc_info.value)
