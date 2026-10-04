"""
tests/ai/orchestration/test_dag.py
===================================
Unit tests for DAG specification, cycle detection, and dependency validation (S27.11).

Invariants verified:
- Cyclic DAGs are detected and rejected with DAGCycleError.
- Self-dependencies are rejected with SelfDependencyError.
- Unknown dependencies are rejected with UnknownDependencyError.
- Duplicate step IDs are rejected with DuplicateStepIdError.
- Linear and diamond-shaped DAGs compute deterministic topological sort.
- Dependency resolution resolves newly runnable children exactly once.
"""

import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIStepStatus
from ai.orchestration.dag import DAGSpecification, DAGValidator, StepDefinition
from ai.orchestration.errors import (
    DAGCycleError,
    DuplicateStepIdError,
    SelfDependencyError,
    UnknownDependencyError,
)


def _step(sid: str, deps: list[str] = None) -> StepDefinition:
    return StepDefinition(
        step_id=sid,
        capability=CapabilityTypeEnum.PLANNING,
        dependencies=deps or [],
    )


# -----------------------------------------------------------------------------
# DAG Validation Tests
# -----------------------------------------------------------------------------

def test_dag_duplicate_step_id_rejected():
    spec = DAGSpecification(
        steps=[
            _step("step_1"),
            _step("step_1"),
        ]
    )
    with pytest.raises(DuplicateStepIdError) as exc_info:
        DAGValidator(spec)
    assert "Duplicate step_id 'step_1'" in str(exc_info.value)


def test_dag_self_dependency_rejected():
    spec = DAGSpecification(
        steps=[
            _step("step_1", deps=["step_1"]),
        ]
    )
    with pytest.raises(SelfDependencyError) as exc_info:
        DAGValidator(spec)
    assert "declares a self-dependency" in str(exc_info.value)


def test_dag_unknown_dependency_rejected():
    spec = DAGSpecification(
        steps=[
            _step("step_1", deps=["non_existent_step"]),
        ]
    )
    with pytest.raises(UnknownDependencyError) as exc_info:
        DAGValidator(spec)
    assert "depends on unknown step 'non_existent_step'" in str(exc_info.value)


def test_dag_simple_cycle_rejected():
    # A -> B -> A
    spec = DAGSpecification(
        steps=[
            _step("A", deps=["B"]),
            _step("B", deps=["A"]),
        ]
    )
    with pytest.raises(DAGCycleError) as exc_info:
        DAGValidator(spec)
    assert "Cyclic dependency detected" in str(exc_info.value)


def test_dag_three_node_cycle_rejected():
    # A -> B -> C -> A
    spec = DAGSpecification(
        steps=[
            _step("A", deps=["C"]),
            _step("B", deps=["A"]),
            _step("C", deps=["B"]),
        ]
    )
    with pytest.raises(DAGCycleError) as exc_info:
        DAGValidator(spec)
    assert "Cyclic dependency detected" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Topological Sort & Parallel Fan-out / Fan-in
# -----------------------------------------------------------------------------

def test_diamond_dag_topological_order():
    r"""
    DAG:
          A
        / | \
       B  C  D
        \ | /
          E
    """
    spec = DAGSpecification(
        steps=[
            _step("A"),
            _step("B", deps=["A"]),
            _step("C", deps=["A"]),
            _step("D", deps=["A"]),
            _step("E", deps=["B", "C", "D"]),
        ]
    )
    validator = DAGValidator(spec)
    assert validator.step_count == 5
    assert validator.get_root_steps() == ["A"]

    children_of_a = sorted(validator.get_children("A"))
    assert children_of_a == ["B", "C", "D"]

    parents_of_e = sorted(validator.get_parents("E"))
    assert parents_of_e == ["B", "C", "D"]

    order = validator.get_topological_order()
    assert order[0] == "A"
    assert order[-1] == "E"
    assert set(order[1:4]) == {"B", "C", "D"}

    descendants_of_a = validator.get_all_descendants("A")
    assert descendants_of_a == {"B", "C", "D", "E"}


def test_resolve_newly_runnable_children():
    """
    Step A finishes: B, C, D become newly runnable.
    Step B finishes: E should NOT be runnable yet (waiting for C and D).
    Step C finishes: E should NOT be runnable yet.
    Step D finishes: E becomes newly runnable!
    """
    spec = DAGSpecification(
        steps=[
            _step("A"),
            _step("B", deps=["A"]),
            _step("C", deps=["A"]),
            _step("D", deps=["A"]),
            _step("E", deps=["B", "C", "D"]),
        ]
    )
    validator = DAGValidator(spec)

    statuses = {
        "A": AIStepStatus.SUCCEEDED,
        "B": AIStepStatus.WAITING,
        "C": AIStepStatus.WAITING,
        "D": AIStepStatus.WAITING,
        "E": AIStepStatus.WAITING,
    }

    # When A finishes:
    newly_runnable = sorted(validator.resolve_newly_runnable_children("A", statuses))
    assert newly_runnable == ["B", "C", "D"]

    # Now simulate B, C running and finishing
    statuses["B"] = AIStepStatus.SUCCEEDED
    statuses["C"] = AIStepStatus.SUCCEEDED
    statuses["D"] = AIStepStatus.RUNNING

    # Checking when B finishes:
    assert validator.resolve_newly_runnable_children("B", statuses) == []

    # Now D finishes:
    statuses["D"] = AIStepStatus.SUCCEEDED
    newly_runnable_e = validator.resolve_newly_runnable_children("D", statuses)
    assert newly_runnable_e == ["E"]
