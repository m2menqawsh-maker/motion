"""
tests/ai/orchestration/test_state_machines.py
==============================================
Unit tests for AIRun and AIStep lifecycle state machines (S27.11).

Invariants verified:
- Valid lifecycle progressions are accepted.
- Illegal transitions raise typed InvalidRunTransitionError / InvalidStepTransitionError.
- Terminal states (SUCCEEDED, FAILED, CANCELLED) are strictly immutable (TerminalStateError).
- Idempotent self-transitions (status -> same status) are safe no-ops.
"""

import pytest
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.orchestration.errors import (
    InvalidRunTransitionError,
    InvalidStepTransitionError,
    TerminalStateError,
)
from ai.orchestration.state import AIRunStateMachine, AIStepStateMachine


# -----------------------------------------------------------------------------
# AIRun State Machine Tests
# -----------------------------------------------------------------------------

def test_airun_valid_transitions():
    # PENDING -> RUNNING
    AIRunStateMachine.validate_transition(AIRunStatus.PENDING, AIRunStatus.RUNNING)
    # PENDING -> CANCELLED
    AIRunStateMachine.validate_transition(AIRunStatus.PENDING, AIRunStatus.CANCELLED)
    # RUNNING -> WAITING
    AIRunStateMachine.validate_transition(AIRunStatus.RUNNING, AIRunStatus.WAITING)
    # RUNNING -> SUCCEEDED
    AIRunStateMachine.validate_transition(AIRunStatus.RUNNING, AIRunStatus.SUCCEEDED)
    # RUNNING -> FAILED
    AIRunStateMachine.validate_transition(AIRunStatus.RUNNING, AIRunStatus.FAILED)
    # RUNNING -> CANCELLED
    AIRunStateMachine.validate_transition(AIRunStatus.RUNNING, AIRunStatus.CANCELLED)
    # WAITING -> RUNNING
    AIRunStateMachine.validate_transition(AIRunStatus.WAITING, AIRunStatus.RUNNING)
    # WAITING -> FAILED
    AIRunStateMachine.validate_transition(AIRunStatus.WAITING, AIRunStatus.FAILED)
    # WAITING -> CANCELLED
    AIRunStateMachine.validate_transition(AIRunStatus.WAITING, AIRunStatus.CANCELLED)


def test_airun_self_transition_idempotent():
    for status in AIRunStatus:
        AIRunStateMachine.validate_transition(status, status)


def test_airun_illegal_transitions():
    # Cannot jump PENDING directly to SUCCEEDED
    with pytest.raises(InvalidRunTransitionError):
        AIRunStateMachine.validate_transition(AIRunStatus.PENDING, AIRunStatus.SUCCEEDED)

    # Cannot jump PENDING directly to WAITING
    with pytest.raises(InvalidRunTransitionError):
        AIRunStateMachine.validate_transition(AIRunStatus.PENDING, AIRunStatus.WAITING)

    # Cannot jump WAITING directly to SUCCEEDED
    with pytest.raises(InvalidRunTransitionError):
        AIRunStateMachine.validate_transition(AIRunStatus.WAITING, AIRunStatus.SUCCEEDED)


def test_airun_terminal_state_protection():
    terminal_states = [AIRunStatus.SUCCEEDED, AIRunStatus.FAILED, AIRunStatus.CANCELLED]
    all_states = list(AIRunStatus)

    for term in terminal_states:
        for target in all_states:
            if term == target:
                continue  # Self-transition is allowed idempotent no-op
            with pytest.raises(TerminalStateError) as exc_info:
                AIRunStateMachine.validate_transition(term, target)
            assert f"Cannot transition terminal AIRun from '{term.value}'" in str(exc_info.value)


# -----------------------------------------------------------------------------
# AIStep State Machine Tests
# -----------------------------------------------------------------------------

def test_aistep_valid_transitions():
    # WAITING -> PENDING
    AIStepStateMachine.validate_transition(AIStepStatus.WAITING, AIStepStatus.PENDING)
    # WAITING -> CANCELLED
    AIStepStateMachine.validate_transition(AIStepStatus.WAITING, AIStepStatus.CANCELLED)
    # WAITING -> FAILED (dependency failure cascade)
    AIStepStateMachine.validate_transition(AIStepStatus.WAITING, AIStepStatus.FAILED)

    # PENDING -> RUNNING
    AIStepStateMachine.validate_transition(AIStepStatus.PENDING, AIStepStatus.RUNNING)
    # PENDING -> CANCELLED
    AIStepStateMachine.validate_transition(AIStepStatus.PENDING, AIStepStatus.CANCELLED)

    # RUNNING -> SUCCEEDED
    AIStepStateMachine.validate_transition(AIStepStatus.RUNNING, AIStepStatus.SUCCEEDED)
    # RUNNING -> FAILED
    AIStepStateMachine.validate_transition(AIStepStatus.RUNNING, AIStepStatus.FAILED)
    # RUNNING -> CANCELLED
    AIStepStateMachine.validate_transition(AIStepStatus.RUNNING, AIStepStatus.CANCELLED)
    # RUNNING -> PENDING (retry or lease reclamation reset)
    AIStepStateMachine.validate_transition(AIStepStatus.RUNNING, AIStepStatus.PENDING)


def test_aistep_self_transition_idempotent():
    for status in AIStepStatus:
        AIStepStateMachine.validate_transition(status, status)


def test_aistep_illegal_transitions():
    # Cannot jump WAITING directly to RUNNING without becoming PENDING
    with pytest.raises(InvalidStepTransitionError):
        AIStepStateMachine.validate_transition(AIStepStatus.WAITING, AIStepStatus.RUNNING)

    # Cannot jump PENDING directly to SUCCEEDED
    with pytest.raises(InvalidStepTransitionError):
        AIStepStateMachine.validate_transition(AIStepStatus.PENDING, AIStepStatus.SUCCEEDED)


def test_aistep_terminal_state_protection():
    terminal_states = [AIStepStatus.SUCCEEDED, AIStepStatus.FAILED, AIStepStatus.CANCELLED]
    all_states = list(AIStepStatus)

    for term in terminal_states:
        for target in all_states:
            if term == target:
                continue
            with pytest.raises(TerminalStateError) as exc_info:
                AIStepStateMachine.validate_transition(term, target)
            assert f"Cannot transition terminal AIStep from '{term.value}'" in str(exc_info.value)
