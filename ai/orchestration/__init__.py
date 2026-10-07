"""
ai/orchestration/__init__.py
============================
Durable AI Orchestration subsystem (S27.11).

Exports the canonical interfaces, state machines, DAG validation, and services
for asynchronous, resilient AI workflow execution.
"""

from ai.orchestration.dag import DAGSpecification, DAGValidator, StepDefinition
from ai.orchestration.activity import DurableActivityExecutor, settle_activity_cost
from ai.orchestration.activity_classification import (
    ACTIVITY_CLASSIFICATIONS,
    ActivityBoundaryType,
    ActivityClassification,
    FalseIdempotencyClaimError,
    get_activity_classification,
    validate_activity_semantics,
)
from ai.orchestration.errors import (
    ActivityNotFoundError,
    DAGCycleError,
    DAGError,
    DuplicateStepIdError,
    InvalidRunTransitionError,
    InvalidStepTransitionError,
    InvalidTransitionError,
    LeaseError,
    LeaseExpiredError,
    NonIdempotentRetryError,
    OrchestrationError,
    RunAlreadyTerminalError,
    RunNotFoundError,
    SelfDependencyError,
    StaleWorkerLeaseError,
    StepNotFoundError,
    TenantAccessDeniedError,
    TerminalStateError,
    UnknownDependencyError,
)
from ai.orchestration.lease import LeaseRecord, generate_lease_token
from ai.orchestration.recovery import AIRecoveryService, RecoveryReport
from ai.orchestration.repository import AIRunRepository
from ai.orchestration.retry import RetryPolicy
from ai.orchestration.service import AIRunService
from ai.orchestration.state import (
    AIRunStateMachine,
    AIStepStateMachine,
    TERMINAL_RUN_STATES,
    TERMINAL_STEP_STATES,
)
from ai.orchestration.worker import AIDurableWorker

__all__ = [
    # State machines & constants
    "AIRunStateMachine",
    "AIStepStateMachine",
    "TERMINAL_RUN_STATES",
    "TERMINAL_STEP_STATES",
    # DAG
    "DAGSpecification",
    "DAGValidator",
    "StepDefinition",
    # Lease
    "LeaseRecord",
    "generate_lease_token",
    # Retry
    "RetryPolicy",
    # Repository & Service
    "AIRunRepository",
    "AIRunService",
    "AIDurableWorker",
    "DurableActivityExecutor",
    "settle_activity_cost",
    "AIRecoveryService",
    "RecoveryReport",
    # Activity Classification (AI-10BR)
    "ActivityBoundaryType",
    "ActivityClassification",
    "ACTIVITY_CLASSIFICATIONS",
    "FalseIdempotencyClaimError",
    "get_activity_classification",
    "validate_activity_semantics",
    # Errors
    "OrchestrationError",
    "InvalidTransitionError",
    "InvalidRunTransitionError",
    "InvalidStepTransitionError",
    "TerminalStateError",
    "DAGError",
    "DAGCycleError",
    "DuplicateStepIdError",
    "SelfDependencyError",
    "UnknownDependencyError",
    "LeaseError",
    "StaleWorkerLeaseError",
    "LeaseExpiredError",
    "TenantAccessDeniedError",
    "RunNotFoundError",
    "StepNotFoundError",
    "RunAlreadyTerminalError",
    "ActivityNotFoundError",
    "NonIdempotentRetryError",
]
