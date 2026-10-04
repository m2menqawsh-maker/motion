"""
ai/orchestration/state.py
==========================
State machines and transition validators for AIRun and AIStep (S27.11).

Invariants:
- Terminal states (SUCCEEDED, FAILED, CANCELLED) are strictly immutable.
- Attempting illegal transitions raises typed InvalidTransitionError subclasses.
- Idempotent self-transitions (CURRENT -> CURRENT) are allowed as no-ops.
"""

from __future__ import annotations

from typing import Set
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.orchestration.errors import (
    InvalidRunTransitionError,
    InvalidStepTransitionError,
    TerminalStateError,
)

TERMINAL_RUN_STATES: Set[AIRunStatus] = {
    AIRunStatus.SUCCEEDED,
    AIRunStatus.FAILED,
    AIRunStatus.CANCELLED,
}

TERMINAL_STEP_STATES: Set[AIStepStatus] = {
    AIStepStatus.SUCCEEDED,
    AIStepStatus.FAILED,
    AIStepStatus.CANCELLED,
}

VALID_RUN_TRANSITIONS: dict[AIRunStatus, Set[AIRunStatus]] = {
    AIRunStatus.PENDING: {AIRunStatus.RUNNING, AIRunStatus.CANCELLED},
    AIRunStatus.RUNNING: {
        AIRunStatus.WAITING,
        AIRunStatus.SUCCEEDED,
        AIRunStatus.FAILED,
        AIRunStatus.CANCELLED,
    },
    AIRunStatus.WAITING: {
        AIRunStatus.RUNNING,
        AIRunStatus.FAILED,
        AIRunStatus.CANCELLED,
    },
    AIRunStatus.SUCCEEDED: set(),
    AIRunStatus.FAILED: set(),
    AIRunStatus.CANCELLED: set(),
}

VALID_STEP_TRANSITIONS: dict[AIStepStatus, Set[AIStepStatus]] = {
    AIStepStatus.WAITING: {
        AIStepStatus.PENDING,
        AIStepStatus.FAILED,
        AIStepStatus.CANCELLED,
    },
    AIStepStatus.PENDING: {
        AIStepStatus.RUNNING,
        AIStepStatus.CANCELLED,
    },
    AIStepStatus.RUNNING: {
        AIStepStatus.SUCCEEDED,
        AIStepStatus.FAILED,
        AIStepStatus.CANCELLED,
        AIStepStatus.PENDING,  # Permitted on retry or lease reclamation reset
    },
    AIStepStatus.SUCCEEDED: set(),
    AIStepStatus.FAILED: set(),
    AIStepStatus.CANCELLED: set(),
}


class AIRunStateMachine:
    """Validator and lifecycle authority for AIRun state transitions."""

    @classmethod
    def is_terminal(cls, status: AIRunStatus) -> bool:
        return status in TERMINAL_RUN_STATES

    @classmethod
    def validate_transition(cls, current: AIRunStatus, target: AIRunStatus) -> None:
        """
        Validates transition legality from current to target.
        Raises TerminalStateError if current is terminal.
        Raises InvalidRunTransitionError if transition is illegal.
        """
        if current == target:
            return  # Idempotent no-op

        if current in TERMINAL_RUN_STATES:
            raise TerminalStateError(
                f"Cannot transition terminal AIRun from '{current.value}' to '{target.value}'."
            )

        allowed = VALID_RUN_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidRunTransitionError(
                f"Illegal AIRun transition from '{current.value}' to '{target.value}'. Allowed: {[s.value for s in allowed]}"
            )


class AIStepStateMachine:
    """Validator and lifecycle authority for AIStep state transitions."""

    @classmethod
    def is_terminal(cls, status: AIStepStatus) -> bool:
        return status in TERMINAL_STEP_STATES

    @classmethod
    def validate_transition(cls, current: AIStepStatus, target: AIStepStatus) -> None:
        """
        Validates transition legality from current to target.
        Raises TerminalStateError if current is terminal.
        Raises InvalidStepTransitionError if transition is illegal.
        """
        if current == target:
            return  # Idempotent no-op

        if current in TERMINAL_STEP_STATES:
            raise TerminalStateError(
                f"Cannot transition terminal AIStep from '{current.value}' to '{target.value}'."
            )

        allowed = VALID_STEP_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStepTransitionError(
                f"Illegal AIStep transition from '{current.value}' to '{target.value}'. Allowed: {[s.value for s in allowed]}"
            )
