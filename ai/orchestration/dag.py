"""
ai/orchestration/dag.py
========================
DAG execution foundation, cycle validation, and dependency scheduling (S27.11).

Invariants:
- All step IDs must be strictly unique within the DAG.
- Cycles, self-dependencies, unknown dependencies, and cross-run dependencies are rejected.
- Dependency resolution guarantees that a child step becomes runnable exactly once
  when all parent prerequisites have succeeded.
- Terminal failure in a parent propagates deterministically to downstream descendants.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from pydantic import Field
from ai.contracts.base import AIContractModel
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIStepStatus
from ai.orchestration.errors import (
    DAGCycleError,
    DuplicateStepIdError,
    SelfDependencyError,
    UnknownDependencyError,
)


class StepDefinition(AIContractModel):
    """Declarative specification of a single step within a DAG workflow."""
    step_id: str = Field(min_length=1, description="Unique identifier for the step in the workflow")
    capability: CapabilityTypeEnum = Field(description="Capability required to execute this step")
    dependencies: list[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    input_ref: Optional[str] = Field(default=None, description="Input artifact storage key or reference")
    provider: Optional[str] = Field(default=None, description="Optional pinned provider identifier")
    model: Optional[str] = Field(default=None, description="Optional pinned model identifier")
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts on failure")
    idempotency_key: Optional[str] = Field(default=None, description="Logical idempotency deduplication key")
    prompt_id: Optional[str] = Field(default=None, description="Canonical prompt identifier for this step")
    prompt_version: Optional[str] = Field(default=None, description="Approved version of prompt for this step")
    prompt_hash: Optional[str] = Field(default=None, description="Content hash of prompt for this step")


class DAGSpecification(AIContractModel):
    """Declarative specification of a complete multi-step AI workflow DAG."""
    workflow_ref: Optional[str] = Field(default=None, description="Reference template or recipe ID")
    steps: list[StepDefinition] = Field(min_length=1, description="List of discrete step definitions")


class DAGValidator:
    """
    Validates DAG structural integrity, cycle freeness, and computes topological ordering.
    """

    def __init__(self, spec: DAGSpecification):
        self.spec = spec
        self._step_map: Dict[str, StepDefinition] = {}
        self._children_map: Dict[str, List[str]] = {}
        self._parents_map: Dict[str, List[str]] = {}
        self._validate_and_build()

    def _validate_and_build(self) -> None:
        step_ids: List[str] = []
        for step in self.spec.steps:
            if step.step_id in self._step_map:
                raise DuplicateStepIdError(
                    f"Duplicate step_id '{step.step_id}' found in DAG specification."
                )
            self._step_map[step.step_id] = step
            step_ids.append(step.step_id)
            self._children_map[step.step_id] = []
            self._parents_map[step.step_id] = list(step.dependencies)

        all_ids = set(step_ids)

        # Check self-dependencies and unknown dependencies
        for step_id, step in self._step_map.items():
            for dep in step.dependencies:
                if dep == step_id:
                    raise SelfDependencyError(
                        f"Step '{step_id}' declares a self-dependency."
                    )
                if dep not in all_ids:
                    raise UnknownDependencyError(
                        f"Step '{step_id}' depends on unknown step '{dep}'."
                    )
                self._children_map[dep].append(step_id)

        # Detect cycles using 3-state DFS (0: unvisited, 1: visiting, 2: visited)
        visited: Dict[str, int] = {sid: 0 for sid in all_ids}

        def dfs(node: str, path: List[str]) -> None:
            visited[node] = 1
            for child in self._children_map[node]:
                if visited[child] == 1:
                    cycle = path + [child]
                    raise DAGCycleError(
                        f"Cyclic dependency detected in DAG: {' -> '.join(cycle)}"
                    )
                if visited[child] == 0:
                    dfs(child, path + [child])
            visited[node] = 2

        for sid in step_ids:
            if visited[sid] == 0:
                dfs(sid, [sid])

    @property
    def step_count(self) -> int:
        return len(self._step_map)

    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        return self._step_map.get(step_id)

    def get_root_steps(self) -> List[str]:
        """Returns step IDs that have zero parent dependencies."""
        return [sid for sid, parents in self._parents_map.items() if not parents]

    def get_children(self, step_id: str) -> List[str]:
        """Returns direct downstream children of the specified step."""
        return list(self._children_map.get(step_id, []))

    def get_parents(self, step_id: str) -> List[str]:
        """Returns direct upstream prerequisites of the specified step."""
        return list(self._parents_map.get(step_id, []))

    def get_all_descendants(self, step_id: str) -> Set[str]:
        """Computes all transitive downstream descendants of a step."""
        descendants: Set[str] = set()
        queue = list(self._children_map.get(step_id, []))
        while queue:
            curr = queue.pop(0)
            if curr not in descendants:
                descendants.add(curr)
                queue.extend(self._children_map.get(curr, []))
        return descendants

    def get_topological_order(self) -> List[str]:
        """Computes a deterministic topological ordering of all steps."""
        in_degree = {sid: len(parents) for sid, parents in self._parents_map.items()}
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        queue.sort()  # Deterministic tie-breaking
        order: List[str] = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for child in sorted(self._children_map[curr]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return order

    def resolve_newly_runnable_children(
        self,
        completed_step_id: str,
        all_step_statuses: Dict[str, AIStepStatus],
    ) -> List[str]:
        """
        Determines which direct children of completed_step_id have become newly runnable.
        A child is newly runnable iff:
        - Its current status is WAITING.
        - ALL its declared parent dependencies have status SUCCEEDED.
        """
        newly_runnable: List[str] = []
        for child_id in self.get_children(completed_step_id):
            child_status = all_step_statuses.get(child_id)
            if child_status != AIStepStatus.WAITING:
                continue

            parents = self.get_parents(child_id)
            all_parents_succeeded = all(
                all_step_statuses.get(p) == AIStepStatus.SUCCEEDED for p in parents
            )
            if all_parents_succeeded:
                newly_runnable.append(child_id)

        return newly_runnable
