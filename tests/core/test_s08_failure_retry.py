"""
S08 Failure Taxonomy, Safe Retry & Resume Semantics — Red Reproduction Tests.

Tests the core requirements of S08:
1. Specific failure classification (no generic GATE_EXECUTION_FAILED blanket)
2. Security violations are NEVER_RETRY
3. Timeout is retryable under explicit bounded policy
4. Deterministic failures do not retry
5. Conditional retry rejects stale state revision
6. Conditional retry rejects changed inputs
7. Invalidated evidence blocks retry
8. Structured errors persist after state reload
9. Retry attempt history is persisted in ProjectState
10. Retry limit is enforced (terminal failure on exhaustion)
11. FAILED lifecycle contract requires recovery / cannot resume blindly
12. S07.5 Preconditions: Evidence resurrection prevention, new generation, no duplicate topology
"""

import pytest
import json
import uuid
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    EvidenceStatus,
    ArtifactRecord,
    ProjectState,
    StateMachine,
)
from scripts.core.state_store import StateStore
from scripts.core.failure_model import (
    FailureCode,
    FailureCategory,
    FailureInfo,
    Severity,
    get_failure_metadata,
)
from scripts.core.retry_policy import (
    IdempotencyClass,
    RetryDecision,
    RetryPolicyEngine,
)


# ==============================================================================
# Group 1: Failure Classification & Non-Generic Gate Errors (Finding A & B)
# ==============================================================================

def test_red_1_validation_failure_is_classified_specifically():
    """
    Test 1 (S08 Finding A & B):
    A failure caused by an invalid blueprint or template validation must be classified
    specifically (e.g. BLUEPRINT_VALIDATION_FAILED), NOT generic GATE_EXECUTION_FAILED.
    Deterministic validation failures must have retry_disposition NEVER / retryable = False.
    """
    from scripts.core.failure_model import FailureClassifier, RetryDisposition

    # Simulate blueprint gate failure output/error
    classifier = FailureClassifier()
    result = classifier.classify(
        script_name="gates/validate_blueprint.py",
        returncode=1,
        stdout="❌ BLUEPRINT FAIL: Missing required scene field 'template'",
        stderr="",
        exception=RuntimeError("validate_blueprint.py exited with code 1"),
        stage="blueprint",
        component="validate_blueprint",
    )

    assert result.code == FailureCode.BLUEPRINT_VALIDATION_FAILED, (
        f"DEFECT PROVEN (Finding A): Specific blueprint validation failure was classified as {result.code.value}!"
    )
    assert result.metadata.category == FailureCategory.VALIDATION_ERROR or result.metadata.category == FailureCategory.GATE_FAILURE
    assert result.retry_disposition == RetryDisposition.NEVER
    assert not result.metadata.retryable


def test_red_2_security_violation_is_never_retry():
    """
    Test 2:
    Security policy rejections (e.g. path traversal, unsafe subprocess command)
    must be classified as SECURITY_POLICY_BLOCKED with retry_disposition NEVER,
    regardless of attempt count or idempotency.
    """
    from scripts.core.failure_model import FailureClassifier, RetryDisposition

    classifier = FailureClassifier()
    failure = classifier.classify(
        script_name="gates/asset_gate.py",
        returncode=1,
        stdout="[GUARDIAN SECURITY ALERT] Path traversal attempted: ../../etc/passwd",
        stderr="SecurityPolicyBlocked",
        exception=PermissionError("Security policy blocked path traversal"),
        stage="assets",
        component="asset_gate",
    )

    assert failure.code == FailureCode.SECURITY_POLICY_BLOCKED
    assert failure.retry_disposition == RetryDisposition.NEVER

    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.SAFE_TO_RETRY, current_attempt=1)
    assert not decision.should_retry, "DEFECT PROVEN: Security violation was allowed to retry!"
    assert "not retryable" in decision.reason or "NEVER" in decision.reason or "Security" in decision.reason


def test_red_3_timeout_is_retryable_bounded():
    """
    Test 3:
    Transient timeouts (e.g. render timeout, network fetch timeout) must be classified
    as TIMEOUT and allowed bounded retry (max 3 attempts).
    """
    from scripts.core.failure_model import FailureClassifier, RetryDisposition

    classifier = FailureClassifier()
    failure = classifier.classify(
        script_name="render_project.py",
        returncode=-9,
        stdout="",
        stderr="Process timed out after 300 seconds",
        exception=TimeoutError("Command timed out after 300 seconds"),
        stage="render",
        component="remotion",
    )

    assert failure.code in (FailureCode.RENDER_TIMEOUT, FailureCode.TIMEOUT)
    assert failure.metadata.category == FailureCategory.TIMEOUT
    assert failure.retry_disposition == RetryDisposition.RETRYABLE

    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, current_attempt=1)
    assert decision.should_retry is True
    assert decision.max_attempts <= 3
    assert decision.delay_seconds > 0


def test_red_4_deterministic_failure_does_not_retry():
    """
    Test 4 (Finding B):
    Deterministic failures (e.g. schema invalidation, unknown template) must NEVER retry.
    Calling RetryPolicyEngine.evaluate() must return should_retry=False even on attempt 1.
    """
    from scripts.core.failure_model import FailureClassifier, RetryDisposition

    classifier = FailureClassifier()
    failure = classifier.classify(
        script_name="gates/code_template_gate.py",
        returncode=1,
        stdout="TemplateValidationError: Template 'UnknownFancyTemplate' not registered",
        stderr="",
        exception=RuntimeError("code_template_gate.py exited with code 1"),
        stage="blueprint",
        component="code_template_gate",
    )

    assert failure.code == FailureCode.TEMPLATE_VALIDATION_FAILED
    assert failure.retry_disposition == RetryDisposition.NEVER

    decision = RetryPolicyEngine.evaluate(failure, IdempotencyClass.SAFE_TO_RETRY, current_attempt=1)
    assert decision.should_retry is False


# ==============================================================================
# Group 2: Conditional Retry & Runtime Validity Checks (Finding C)
# ==============================================================================

def test_red_5_conditional_retry_rejects_stale_revision(tmp_path):
    """
    Test 5 (Finding C):
    When an operation is CONDITIONALLY_RETRYABLE, RetryPolicyEngine must verify that
    the project state revision has NOT diverged. If revision on disk is N+1, retry must fail closed.
    """
    from scripts.core.failure_model import FailureClassifier, RetryDisposition
    from scripts.core.retry_policy import RetryContext

    project_dir = tmp_path / "prj_stale_rev"
    project_dir.mkdir(parents=True)

    state = ProjectState(
        project_id="prj_stale_rev",
        lifecycle_state=LifecycleState.BLUEPRINT_READY,
        revision=5,
    )
    StateStore.save(project_dir, state)

    # RetryContext was created at revision 5
    context = RetryContext(
        project_id="prj_stale_rev",
        stage="blueprint",
        operation="materialize_project",
        attempt=1,
        expected_revision=5,
        idempotency=IdempotencyClass.CONDITIONALLY_RETRYABLE,
    )

    # State diverged on disk (revision advanced to 6)
    state.revision = 6
    StateStore._persist_atomic(project_dir, state)

    # Verification must fail closed due to stale revision
    is_valid, reason = RetryPolicyEngine.validate_retry_preconditions(context, project_dir)
    assert not is_valid, "DEFECT PROVEN (Finding C): Conditional retry accepted a stale state revision!"
    assert "revision" in reason.lower() or "stale" in reason.lower()


def test_red_6_conditional_retry_rejects_changed_inputs(tmp_path):
    """
    Test 6 (Finding C):
    If input files (e.g. 05_blueprint.json) change between attempts, the previous attempt
    cannot be safely retried with the old context.
    """
    from scripts.core.retry_policy import RetryContext

    project_dir = tmp_path / "prj_changed_input"
    project_dir.mkdir(parents=True)

    bp_file = project_dir / "05_blueprint.json"
    bp_file.write_text('{"scenes": [1]}', encoding="utf-8")

    state = ProjectState(
        project_id="prj_changed_input",
        lifecycle_state=LifecycleState.BLUEPRINT_READY,
        revision=4,
    )
    StateStore.save(project_dir, state)

    # Initial fingerprint
    initial_hash = StateStore._compute_sha256(bp_file)

    context = RetryContext(
        project_id="prj_changed_input",
        stage="blueprint",
        operation="materialize_project",
        attempt=1,
        expected_revision=4,
        input_fingerprints={"05_blueprint.json": initial_hash},
        idempotency=IdempotencyClass.CONDITIONALLY_RETRYABLE,
    )

    # Modifying the input file on disk
    bp_file.write_text('{"scenes": [1, 2, 3]}', encoding="utf-8")

    is_valid, reason = RetryPolicyEngine.validate_retry_preconditions(context, project_dir)
    assert not is_valid, "DEFECT PROVEN: Conditional retry accepted modified input files!"
    assert "input" in reason.lower() or "fingerprint" in reason.lower() or "mismatch" in reason.lower()


def test_red_7_invalidated_evidence_blocks_retry(tmp_path):
    """
    Test 7 (S07.5 Precondition & Finding C):
    If evidence required by the operation was INVALIDATED (e.g. by rollback or recovery),
    conditional retry must be rejected.
    """
    from scripts.core.retry_policy import RetryContext

    project_dir = tmp_path / "prj_invalidated_ev"
    project_dir.mkdir(parents=True)

    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    rec = ArtifactRecord(
        path="05_blueprint.json",
        validation=ValidationLevel.SHA256,
        status=EvidenceStatus.INVALIDATED,
        invalidated_reason="Rollback from MATERIALIZED",
    )

    state = ProjectState(
        project_id="prj_invalidated_ev",
        lifecycle_state=LifecycleState.PLAN_READY,
        revision=7,
        artifact_records=[rec],
    )
    StateStore.save(project_dir, state)

    context = RetryContext(
        project_id="prj_invalidated_ev",
        stage="blueprint",
        operation="materialize_project",
        attempt=1,
        expected_revision=7,
        evidence_paths=["05_blueprint.json"],
        idempotency=IdempotencyClass.CONDITIONALLY_RETRYABLE,
    )

    is_valid, reason = RetryPolicyEngine.validate_retry_preconditions(context, project_dir)
    assert not is_valid, "DEFECT PROVEN: Conditional retry allowed operation on INVALIDATED evidence!"
    assert "invalidated" in reason.lower() or "evidence" in reason.lower()


# ==============================================================================
# Group 3: Persistence of Structured Errors & Retry History (Finding D)
# ==============================================================================

def test_red_8_structured_error_persists_after_reload(tmp_path):
    """
    Test 8 (Finding D):
    Failures recorded during execution must be persisted into ProjectState.structured_errors
    and must survive a complete reload from disk.
    """
    from scripts.core.failure_model import FailureInfo, FailureCode, FailureCategory, RetryDisposition

    project_dir = tmp_path / "prj_persist_error"
    project_dir.mkdir(parents=True)

    state = ProjectState(
        project_id="prj_persist_error",
        lifecycle_state=LifecycleState.BLUEPRINT_READY,
        revision=2,
    )
    StateStore.save(project_dir, state)

    failure = FailureInfo(
        code=FailureCode.BLUEPRINT_VALIDATION_FAILED,
        message="Invalid scene structure in 05_blueprint.json",
        stage="blueprint",
        component="validate_blueprint",
    )

    # Record failure into state via authoritative method
    RetryPolicyEngine.record_failure_attempt(
        project_dir=project_dir,
        failure=failure,
        attempt=1,
        will_retry=False,
    )

    # Reload from disk to prove persistence
    loaded = StateStore.load(project_dir)
    assert loaded is not None
    assert len(loaded.structured_errors) > 0, "DEFECT PROVEN (Finding D): structured_errors was empty after reload!"

    err = loaded.structured_errors[-1]
    assert err.get("code") == FailureCode.BLUEPRINT_VALIDATION_FAILED.value
    assert err.get("attempt") == 1
    assert err.get("will_retry") is False


def test_red_9_retry_attempts_themselves_are_persisted(tmp_path):
    """
    Test 9 (Finding D):
    Each retry attempt must be explicitly audited in ProjectState.run_metadata['retry_history']
    with lifecycle events (ATTEMPT_STARTED, ATTEMPT_FAILED, RETRY_SCHEDULED, etc.).
    """
    from scripts.core.failure_model import FailureInfo, FailureCode

    project_dir = tmp_path / "prj_retry_history"
    project_dir.mkdir(parents=True)

    state = ProjectState(
        project_id="prj_retry_history",
        lifecycle_state=LifecycleState.RENDERED,
        revision=5,
    )
    StateStore.save(project_dir, state)

    failure = FailureInfo(
        code=FailureCode.RENDER_TIMEOUT,
        message="Render process timed out",
        stage="render",
        component="remotion",
    )

    # Record Attempt 1 failure with retry scheduled
    RetryPolicyEngine.record_failure_attempt(
        project_dir=project_dir,
        failure=failure,
        attempt=1,
        will_retry=True,
    )

    # Record Attempt 2 failure without retry (exhausted)
    RetryPolicyEngine.record_failure_attempt(
        project_dir=project_dir,
        failure=failure,
        attempt=2,
        will_retry=False,
    )

    loaded = StateStore.load(project_dir)
    history = loaded.run_metadata.get("retry_history", [])
    assert len(history) == 2, f"DEFECT PROVEN: Expected 2 retry history records, got {len(history)}"
    assert history[0]["attempt"] == 1
    assert history[0]["will_retry"] is True
    assert history[1]["attempt"] == 2
    assert history[1]["will_retry"] is False


def test_red_10_retry_limit_is_enforced():
    """
    Test 10:
    Once current_attempt reaches max_attempts, no further attempts are permitted,
    and decision.should_retry must be False.
    """
    from scripts.core.failure_model import FailureInfo, FailureCode

    failure = FailureInfo(
        code=FailureCode.RENDER_TIMEOUT,
        message="Timeout",
    )

    # Attempt 1 -> ok
    d1 = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 1)
    assert d1.should_retry is True

    # Attempt 2 -> ok
    d2 = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 2)
    assert d2.should_retry is True

    # Attempt 3 (Max) -> exhausted!
    d3 = RetryPolicyEngine.evaluate(failure, IdempotencyClass.CONDITIONALLY_RETRYABLE, 3)
    assert d3.should_retry is False
    assert "exhausted" in d3.reason.lower()


# ==============================================================================
# Group 4: FAILED Lifecycle Semantics & Recovery Boundary (Finding E)
# ==============================================================================

def test_red_11_failed_lifecycle_contract_requires_recovery(tmp_path):
    """
    Test 11 (Finding E):
    When a project lifecycle_state is FAILED, it must NOT be resumable directly.
    Resuming requires applying a RecoveryPlan to reconcile the state.
    """
    from scripts.core.recovery_engine import RecoveryEngine

    project_dir = tmp_path / "prj_failed_contract"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
    ]

    state = ProjectState(
        project_id="prj_failed_contract",
        lifecycle_state=LifecycleState.FAILED,
        revision=9,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    decision = RecoveryEngine.evaluate(project_dir)
    assert decision.can_resume is False, "DEFECT PROVEN: Project in FAILED state was treated as directly resumable!"
    assert decision.recommended_action == "apply_recovery_plan"
    assert decision.recovery_plan is not None
    assert decision.recovery_plan.target_state == LifecycleState.PLAN_READY


# ==============================================================================
# Group 5: S07.5 Mandatory Preconditions & Integrity Checks
# ==============================================================================

def test_red_s07_5_retry_does_not_resurrect_invalidated_evidence(tmp_path):
    """
    S07.5 Precondition 1:
    A retry path must NOT resurrect an INVALIDATED evidence record using a stale record.
    """
    from scripts.core.evidence_matrix import EvidenceLedger

    persisted = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=10,
            generation_id="gen-1",
            status=EvidenceStatus.INVALIDATED,
        )
    ]

    stale_retry_record = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=9,
            generation_id="gen-1",
            status=EvidenceStatus.VALID,
        )
    ]

    merged = EvidenceLedger.merge_records(persisted, stale_retry_record)
    assert merged[0].status == EvidenceStatus.INVALIDATED


def test_red_s07_5_retry_after_recovery_uses_new_generation(tmp_path):
    """
    S07.5 Precondition 2:
    A legitimate retry following recovery must generate a new distinct generation_id,
    which EvidenceLedger accepts as VALID while archiving previous lineage.
    """
    from scripts.core.evidence_matrix import EvidenceLedger

    persisted = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=10,
            generation_id="gen-1",
            status=EvidenceStatus.INVALIDATED,
        )
    ]

    new_gen_retry_record = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=6000,
            produced_at_revision=12,
            generation_id="gen-2",
            status=EvidenceStatus.VALID,
        )
    ]

    merged = EvidenceLedger.merge_records(persisted, new_gen_retry_record)
    assert merged[0].status == EvidenceStatus.VALID
    assert merged[0].generation_id == "gen-2"
    assert "superseded_lineage" in merged[0].metadata


def test_red_s07_5_studio_approved_alone_does_not_authorize_failed_render_retry(tmp_path):
    """
    S07.5 Precondition 6:
    .studio_approved marker alone on disk without canonical approved_by in approval_metadata
    must NOT allow retrying a failed render operation.
    """
    from scripts.core.retry_policy import RetryContext

    project_dir = tmp_path / "prj_render_marker_alone"
    project_dir.mkdir(parents=True)

    # Forged marker on disk
    (project_dir / ".studio_approved").write_text("", encoding="utf-8")

    state = ProjectState(
        project_id="prj_render_marker_alone",
        lifecycle_state=LifecycleState.REVIEW_APPROVED,
        revision=10,
        approval_metadata={},  # No approved_by!
    )
    StateStore.save(project_dir, state)

    context = RetryContext(
        project_id="prj_render_marker_alone",
        stage="render",
        operation="render_project",
        attempt=1,
        expected_revision=10,
        idempotency=IdempotencyClass.CONDITIONALLY_RETRYABLE,
    )

    is_valid, reason = RetryPolicyEngine.validate_retry_preconditions(context, project_dir)
    assert not is_valid, "DEFECT PROVEN: .studio_approved alone falsely authorized render retry!"
    assert "approval" in reason.lower() or "authoriz" in reason.lower()


def test_red_s07_5_retry_engine_uses_statemachine_topology():
    """
    S07.5 Precondition 5:
    Retry Engine must NOT declare an independent or parallel lifecycle topology.
    It must query StateMachine.get_topological_order().
    """
    import scripts.core.retry_policy as retry_mod
    # Verify that retry module does NOT hardcode an independent LIFECYCLE_ORDER
    if hasattr(retry_mod, "LIFECYCLE_ORDER"):
        assert retry_mod.LIFECYCLE_ORDER == StateMachine.get_topological_order()
