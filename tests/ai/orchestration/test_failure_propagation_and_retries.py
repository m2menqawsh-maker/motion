"""
tests/ai/orchestration/test_failure_propagation_and_retries.py
==============================================================
Tests for typed bounded retries, non-retryable errors, and failure cascade propagation (S27.11).

Invariants verified:
- Retryable errors back off and reset status to PENDING with attempt incremented.
- Retries are strictly bounded by max_attempts (no infinite retry).
- Non-retryable errors fail terminally on the first attempt.
- Terminal failure in an upstream step cascades down the DAG, marking dependent children
  as FAILED (DEPENDENCY_FAILED) and terminating the parent AIRun.
"""

from datetime import datetime, timezone
import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.retry import RetryPolicy
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def service(tmp_path):
    db_file = tmp_path / "test_retry.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    policy = RetryPolicy(max_attempts=3, backoff_base_seconds=0.0, backoff_factor=1.0)
    return AIRunService(repository=repo, retry_policy=policy)


def test_retryable_error_bounded_and_terminal_failure(service):
    """
    Step fails with RATE_LIMITED:
    Attempt 1 fails -> rescheduled as PENDING (attempt 1).
    Attempt 2 claims (attempt becomes 2) and fails -> rescheduled as PENDING.
    Attempt 3 claims (attempt becomes 3) and fails -> reached max_attempts (3) -> terminal FAILED!
    """
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_retry", capability=CapabilityTypeEnum.PLANNING, max_attempts=3),
        ]
    )
    run = service.create_run(workspace_id="ws_retry", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    rate_limit_err = AIError.rate_limited(message="Upstream provider throttled request.")

    # Attempt 1
    c1 = service.claim_next_runnable_step("w1", "ws_retry")
    assert c1 is not None
    assert c1.attempt == 1

    f1 = service.fail_step(c1.step_id, "w1", c1.lease_token, rate_limit_err)
    assert f1.status == AIStepStatus.PENDING
    assert f1.next_retry_at is not None

    # Attempt 2
    c2 = service.claim_next_runnable_step("w1", "ws_retry")
    assert c2 is not None
    assert c2.attempt == 2

    f2 = service.fail_step(c2.step_id, "w1", c2.lease_token, rate_limit_err)
    assert f2.status == AIStepStatus.PENDING

    # Attempt 3 (reaches max_attempts=3)
    c3 = service.claim_next_runnable_step("w1", "ws_retry")
    assert c3 is not None
    assert c3.attempt == 3

    f3 = service.fail_step(c3.step_id, "w1", c3.lease_token, rate_limit_err)
    assert f3.status == AIStepStatus.FAILED
    assert f3.completed_at is not None

    # Parent AIRun must be marked FAILED
    parent_run = service.get_run(run.run_id, workspace_id="ws_retry")
    assert parent_run.status == AIRunStatus.FAILED


def test_non_retryable_error_fails_immediately(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_auth", capability=CapabilityTypeEnum.PLANNING, max_attempts=5),
        ]
    )
    run = service.create_run(workspace_id="ws_auth", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    policy_err = AIError.policy_denied(message="Operation denied by governance guard.")

    c1 = service.claim_next_runnable_step("w1", "ws_auth")
    assert c1 is not None

    f1 = service.fail_step(c1.step_id, "w1", c1.lease_token, policy_err)
    assert f1.status == AIStepStatus.FAILED, "Non-retryable error must fail terminally on attempt 1"

    parent_run = service.get_run(run.run_id, workspace_id="ws_auth")
    assert parent_run.status == AIRunStatus.FAILED


def test_terminal_failure_cascades_down_dag(service):
    r"""
    DAG:
        A
       / \
      B   C
       \ /
        D

    If A succeeds, B fails terminally, and C succeeds:
    - Step D depends on B and C.
    - D cannot execute and must be marked FAILED (DEPENDENCY_FAILED).
    - D must NOT remain WAITING forever!
    - Parent AIRun is marked FAILED.
    """
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="A", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="B", capability=CapabilityTypeEnum.VOICE_ANALYSIS, dependencies=["A"]),
            StepDefinition(step_id="C", capability=CapabilityTypeEnum.SHOT_DETECTION, dependencies=["A"]),
            StepDefinition(step_id="D", capability=CapabilityTypeEnum.VIDEO_UNDERSTANDING, dependencies=["B", "C"]),
        ]
    )

    run = service.create_run(workspace_id="ws_cascade", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # 1. Complete A
    cA = service.claim_next_runnable_step("w1", "ws_cascade")
    service.complete_step(cA.step_id, "w1", cA.lease_token)

    # B and C are now PENDING
    cB = service.claim_next_runnable_step("w2", "ws_cascade")
    assert cB.step_id.endswith("_B")

    # Fail B terminally
    err = AIError.policy_denied(message="Audio content rejected by moderation.")
    service.fail_step(cB.step_id, "w2", cB.lease_token, err)

    # Verify D was cascaded to FAILED with DEPENDENCY_FAILED
    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}

    assert step_map["B"].status == AIStepStatus.FAILED
    assert step_map["D"].status == AIStepStatus.FAILED
    assert step_map["D"].error is not None
    assert step_map["D"].error.code == AIErrorCode.DEPENDENCY_FAILED

    # Verify parent run is FAILED
    parent = service.get_run(run.run_id, workspace_id="ws_cascade")
    assert parent.status == AIRunStatus.FAILED
