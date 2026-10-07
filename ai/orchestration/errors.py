"""
ai/orchestration/errors.py
===========================
Typed exceptions for Durable AI Orchestration (S27.11).

Invariants:
- Strict error taxonomy; no unclassified generic strings.
- Distinct error types for state transitions, DAG validation, and lease fencing.
"""

from __future__ import annotations


class OrchestrationError(Exception):
    """Base exception for all AI orchestration failures."""
    pass


class InvalidTransitionError(OrchestrationError):
    """Raised when an illegal state machine transition is attempted."""
    pass


class InvalidRunTransitionError(InvalidTransitionError):
    """Raised when an invalid AIRun lifecycle transition is requested."""
    pass


class InvalidStepTransitionError(InvalidTransitionError):
    """Raised when an invalid AIStep lifecycle transition is requested."""
    pass


class TerminalStateError(InvalidTransitionError):
    """Raised when attempting to transition an entity out of a terminal state."""
    pass


class DAGError(OrchestrationError):
    """Base exception for workflow DAG structural or validation errors."""
    pass


class DAGCycleError(DAGError):
    """Raised when a cyclic dependency is detected in the DAG."""
    pass


class DuplicateStepIdError(DAGError):
    """Raised when a DAG contains duplicate step identifiers."""
    pass


class SelfDependencyError(DAGError):
    """Raised when a step declares a dependency upon itself."""
    pass


class UnknownDependencyError(DAGError):
    """Raised when a step depends on an identifier not present in the DAG."""
    pass


class LeaseError(OrchestrationError):
    """Base exception for worker lease and fencing violations."""
    pass


class StaleWorkerLeaseError(LeaseError):
    """Raised when a worker attempts an operation with an expired or superseded lease token."""
    pass


class LeaseExpiredError(LeaseError):
    """Raised when an operation is attempted after lease expiration."""
    pass


class TenantAccessDeniedError(OrchestrationError):
    """Raised when an actor attempts cross-tenant access to an AIRun or AIStep."""
    pass


class RunNotFoundError(OrchestrationError):
    """Raised when a requested AIRun does not exist."""
    pass


class StepNotFoundError(OrchestrationError):
    """Raised when a requested AIStep does not exist."""
    pass


class RunAlreadyTerminalError(OrchestrationError):
    """Raised when attempting to execute operations on an already terminal run."""
    pass


class ActivityNotFoundError(OrchestrationError):
    """Raised when a requested AIActivityRecord does not exist."""
    pass


class NonIdempotentRetryError(OrchestrationError):
    """Raised when attempting an automatic retry of a non-idempotent activity."""
    pass

