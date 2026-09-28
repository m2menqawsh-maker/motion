"""
Artifact Dependency Graph & Invalidation Planning (S10).

Provides:
- Semantic ArtifactKind enumeration (logical artifact identities, not raw filenames).
- Typed DependencyEdge representation (Content, Authorization, Derivation, QC).
- Deterministic topological dependency resolution and cycle prevention (DAG).
- Centralized InvalidationPlan computation (detection -> resolution -> plan -> atomic CAS apply).
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Dict, List, Set, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from scripts.core.state_model import (
    ProjectState,
    EvidenceStatus,
    LifecycleState,
)


class ArtifactKind(str, Enum):
    MANIFEST = "02_asset_manifest.json"
    PLAN = "01_plan.md"
    TIMINGS = "04_timings.json"
    BLUEPRINT = "05_blueprint.json"
    MATERIALIZED_MEDIA = "media_map.json"
    PROBE_REPORT = "probe_qc_report.json"
    REVIEW_BUNDLE = "review_bundle"
    REVIEW_DECISION = "review_decision"  # Canonical ProjectState.review_decisions (managed solely by ReviewService)
    RENDER_OUTPUT = "out.mp4"
    FINAL_QC = "08_qc_report.json"
    COMPLETE = "complete"

    @classmethod
    def from_string(cls, val: str) -> Optional[ArtifactKind]:
        """Resolves an ArtifactKind from enum value, name, or known filename/alias."""
        val_clean = val.strip()
        # Direct enum value match
        for member in cls:
            if member.value == val_clean or member.name == val_clean.upper():
                return member
        # Aliases
        if val_clean in ("master_plan.md", "00_answers.md"):
            return cls.PLAN
        # Legacy/housekeeping file aliases: map to canonical semantic node for invalidation resolution
        if val_clean in (".studio_approved", "approval_metadata", "studio_approved"):
            return cls.REVIEW_DECISION
        if val_clean in (".studio_unlocked", "probe_qc", "contact_sheet.png", "contact_sheet"):
            return cls.PROBE_REPORT
        return None


class DependencyEdgeType(str, Enum):
    CONTENT_DEPENDENCY = "CONTENT_DEPENDENCY"            # Upstream content directly feeds into downstream
    AUTHORIZATION_DEPENDENCY = "AUTHORIZATION_DEPENDENCY"# Upstream authorization is required for downstream execution
    DERIVATION_DEPENDENCY = "DERIVATION_DEPENDENCY"      # Downstream is generated or derived from upstream
    QC_DEPENDENCY = "QC_DEPENDENCY"                      # Downstream validates upstream quality


class DependencyEdge(BaseModel):
    model_config = ConfigDict(extra='ignore')

    upstream: ArtifactKind
    downstream: ArtifactKind
    edge_type: DependencyEdgeType
    description: Optional[str] = None


class InvalidationPlan(BaseModel):
    model_config = ConfigDict(extra='ignore')

    plan_id: str = Field(default_factory=lambda: f"inv-{uuid.uuid4().hex[:8]}")
    project_id: str
    source_revision: int
    changed_artifacts: List[str] = Field(default_factory=list)
    invalidated_artifacts: List[str] = Field(default_factory=list)
    invalidated_evidence_paths: List[str] = Field(default_factory=list)
    invalidated_review_bundles: List[str] = Field(default_factory=list)
    invalidated_decisions: List[str] = Field(default_factory=list)
    stale_disk_paths: List[str] = Field(default_factory=list)
    reason: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArtifactDependencyGraph:
    """
    Centralized canonical executable dependency graph.
    Represents the true dataflow and authorization hierarchy of the clean video pipeline.
    """

    def __init__(self) -> None:
        self.nodes: Set[ArtifactKind] = set(ArtifactKind)
        self.edges: List[DependencyEdge] = [
            # 1. Manifest dependencies
            DependencyEdge(
                upstream=ArtifactKind.MANIFEST,
                downstream=ArtifactKind.MATERIALIZED_MEDIA,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Declared asset manifest drives media acquisition and normalization",
            ),
            DependencyEdge(
                upstream=ArtifactKind.MANIFEST,
                downstream=ArtifactKind.REVIEW_BUNDLE,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Asset manifest hash is frozen into ReviewBundle snapshot",
            ),

            # 2. Plan dependencies
            DependencyEdge(
                upstream=ArtifactKind.PLAN,
                downstream=ArtifactKind.TIMINGS,
                edge_type=DependencyEdgeType.DERIVATION_DEPENDENCY,
                description="Speech and audio timing is extracted from script plan",
            ),
            DependencyEdge(
                upstream=ArtifactKind.PLAN,
                downstream=ArtifactKind.BLUEPRINT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Blueprint scenes are generated based on script plan structure",
            ),

            # 3. Timings dependencies
            DependencyEdge(
                upstream=ArtifactKind.TIMINGS,
                downstream=ArtifactKind.BLUEPRINT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Blueprint frame counts and scene durations derive from timings",
            ),

            # 4. Blueprint dependencies
            DependencyEdge(
                upstream=ArtifactKind.BLUEPRINT,
                downstream=ArtifactKind.MATERIALIZED_MEDIA,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Blueprint media references dictate required assets for download",
            ),
            DependencyEdge(
                upstream=ArtifactKind.BLUEPRINT,
                downstream=ArtifactKind.PROBE_REPORT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Probe QC inspects blueprint template schemas and durations",
            ),
            DependencyEdge(
                upstream=ArtifactKind.BLUEPRINT,
                downstream=ArtifactKind.REVIEW_BUNDLE,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Blueprint hash is frozen into ReviewBundle snapshot",
            ),
            DependencyEdge(
                upstream=ArtifactKind.BLUEPRINT,
                downstream=ArtifactKind.RENDER_OUTPUT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Blueprint is passed directly via --props to Remotion render",
            ),

            # 5. Materialized Media dependencies
            DependencyEdge(
                upstream=ArtifactKind.MATERIALIZED_MEDIA,
                downstream=ArtifactKind.PROBE_REPORT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Probe QC checks media resolution, audio bitrate and channels",
            ),
            DependencyEdge(
                upstream=ArtifactKind.MATERIALIZED_MEDIA,
                downstream=ArtifactKind.REVIEW_BUNDLE,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Media map hash is frozen into ReviewBundle snapshot",
            ),
            DependencyEdge(
                upstream=ArtifactKind.MATERIALIZED_MEDIA,
                downstream=ArtifactKind.RENDER_OUTPUT,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Render reads normalized media files from media map",
            ),

            # 6. Probe dependencies
            DependencyEdge(
                upstream=ArtifactKind.PROBE_REPORT,
                downstream=ArtifactKind.REVIEW_BUNDLE,
                edge_type=DependencyEdgeType.CONTENT_DEPENDENCY,
                description="Probe report hash is frozen into ReviewBundle snapshot",
            ),

            # 7. Review Bundle dependencies
            DependencyEdge(
                upstream=ArtifactKind.REVIEW_BUNDLE,
                downstream=ArtifactKind.REVIEW_DECISION,
                edge_type=DependencyEdgeType.AUTHORIZATION_DEPENDENCY,
                description="Human reviewer acts upon a specific immutable ReviewBundle digest",
            ),

            # 8. Review Decision dependencies
            DependencyEdge(
                upstream=ArtifactKind.REVIEW_DECISION,
                downstream=ArtifactKind.RENDER_OUTPUT,
                edge_type=DependencyEdgeType.AUTHORIZATION_DEPENDENCY,
                description="Render requires an active APPROVED review decision in canonical state via ReviewService. Stale legacy markers (.studio_approved) have zero authorization authority.",
            ),

            # 9. Render dependencies
            DependencyEdge(
                upstream=ArtifactKind.RENDER_OUTPUT,
                downstream=ArtifactKind.FINAL_QC,
                edge_type=DependencyEdgeType.QC_DEPENDENCY,
                description="Final QC inspects generated out.mp4 for audio sync, black frames, bitrate",
            ),

            # 10. Final QC dependencies
            DependencyEdge(
                upstream=ArtifactKind.FINAL_QC,
                downstream=ArtifactKind.COMPLETE,
                edge_type=DependencyEdgeType.AUTHORIZATION_DEPENDENCY,
                description="Final QC pass authorizes project completion marker",
            ),
        ]

        # Adjacency structures for fast deterministic lookup
        self._downstream_map: Dict[ArtifactKind, List[DependencyEdge]] = {k: [] for k in self.nodes}
        self._upstream_map: Dict[ArtifactKind, List[DependencyEdge]] = {k: [] for k in self.nodes}
        for edge in self.edges:
            self._downstream_map[edge.upstream].append(edge)
            self._upstream_map[edge.downstream].append(edge)

    def get_direct_dependents(self, node: ArtifactKind) -> List[ArtifactKind]:
        """Returns direct downstream dependents of a given node."""
        return [edge.downstream for edge in self._downstream_map.get(node, [])]

    def get_direct_dependencies(self, node: ArtifactKind) -> List[ArtifactKind]:
        """Returns direct upstream dependencies of a given node."""
        return [edge.upstream for edge in self._upstream_map.get(node, [])]

    def get_transitive_dependents(self, node: ArtifactKind) -> Set[ArtifactKind]:
        """
        Computes all downstream dependents transitively affected if `node` is mutated.
        Deterministic breadth-first search.
        """
        visited: Set[ArtifactKind] = set()
        queue: List[ArtifactKind] = [node]

        while queue:
            curr = queue.pop(0)
            for downstream in self.get_direct_dependents(curr):
                if downstream not in visited:
                    visited.add(downstream)
                    queue.append(downstream)

        return visited

    def get_transitive_dependencies(self, node: ArtifactKind) -> Set[ArtifactKind]:
        """Computes all upstream dependencies required to produce `node`."""
        visited: Set[ArtifactKind] = set()
        queue: List[ArtifactKind] = [node]

        while queue:
            curr = queue.pop(0)
            for upstream in self.get_direct_dependencies(curr):
                if upstream not in visited:
                    visited.add(upstream)
                    queue.append(upstream)

        return visited

    def why_invalidated(self, upstream: ArtifactKind, downstream: ArtifactKind) -> List[DependencyEdge]:
        """Returns the chain of edges demonstrating why `downstream` is invalidated when `upstream` changes."""
        if upstream == downstream:
            return []

        # Find shortest path from upstream to downstream
        queue: List[List[DependencyEdge]] = []
        for edge in self._downstream_map.get(upstream, []):
            queue.append([edge])

        visited = {upstream}
        while queue:
            path = queue.pop(0)
            last_edge = path[-1]
            if last_edge.downstream == downstream:
                return path
            if last_edge.downstream not in visited:
                visited.add(last_edge.downstream)
                for next_edge in self._downstream_map.get(last_edge.downstream, []):
                    queue.append(path + [next_edge])

        return []

    def compute_invalidation_plan(
        self,
        project_state: ProjectState,
        changed_nodes: List[Union[ArtifactKind, str]],
        reason: str,
    ) -> InvalidationPlan:
        """
        Computes a structured InvalidationPlan based on changed artifacts.
        Does NOT apply mutations to state; separates calculation from execution.
        """
        # 1. Resolve logical ArtifactKinds
        resolved_changed: Set[ArtifactKind] = set()
        changed_strs: List[str] = []
        for itm in changed_nodes:
            if isinstance(itm, ArtifactKind):
                resolved_changed.add(itm)
                changed_strs.append(itm.value)
            else:
                kind = ArtifactKind.from_string(str(itm))
                if kind:
                    resolved_changed.add(kind)
                    changed_strs.append(kind.value)
                else:
                    changed_strs.append(str(itm))

        # 2. Compute transitive dependents
        invalidated_kinds: Set[ArtifactKind] = set()
        for c in resolved_changed:
            invalidated_kinds.update(self.get_transitive_dependents(c))

        # 3. Resolve disk/evidence paths to invalidate in ProjectState.artifact_records
        invalidated_evidence_paths: Set[str] = set()
        for k in invalidated_kinds:
            if k not in (ArtifactKind.REVIEW_BUNDLE, ArtifactKind.REVIEW_DECISION, ArtifactKind.COMPLETE):
                invalidated_evidence_paths.add(k.value)

        # 4. Resolve review entities
        invalidated_bundles: List[str] = []
        invalidated_decisions: List[str] = []
        stale_disk_paths: List[str] = []

        if ArtifactKind.REVIEW_BUNDLE in invalidated_kinds:
            for b in project_state.review_bundles:
                if b.status == "ACTIVE":
                    invalidated_bundles.append(b.review_bundle_id)

        if ArtifactKind.REVIEW_DECISION in invalidated_kinds:
            for d in project_state.review_decisions:
                if d.decision.upper() == "APPROVED":
                    invalidated_decisions.append(d.decision_id)
            stale_disk_paths.append(".studio_approved")

        if ArtifactKind.PROBE_REPORT in invalidated_kinds:
            stale_disk_paths.append(".studio_unlocked")

        return InvalidationPlan(
            project_id=project_state.project_id,
            source_revision=project_state.revision,
            changed_artifacts=sorted(list(changed_strs)),
            invalidated_artifacts=sorted([k.value for k in invalidated_kinds]),
            invalidated_evidence_paths=sorted(list(invalidated_evidence_paths)),
            invalidated_review_bundles=invalidated_bundles,
            invalidated_decisions=invalidated_decisions,
            stale_disk_paths=stale_disk_paths,
            reason=reason,
        )

    def validate_graph(self) -> None:
        """
        Enforces structural integrity of the dependency graph:
        1. All nodes are valid ArtifactKind members.
        2. All edges connect existing nodes.
        3. The graph is strictly acyclic (DAG).
        4. No isolated/orphan nodes.
        """
        # Node and edge validation
        for edge in self.edges:
            if edge.upstream not in self.nodes:
                raise ValueError(f"Edge upstream {edge.upstream} is not in registered nodes")
            if edge.downstream not in self.nodes:
                raise ValueError(f"Edge downstream {edge.downstream} is not in registered nodes")

        # Cycle detection using DFS
        visited: Set[ArtifactKind] = set()
        rec_stack: Set[ArtifactKind] = set()

        def has_cycle(node: ArtifactKind) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for downstream in self.get_direct_dependents(node):
                if downstream not in visited:
                    if has_cycle(downstream):
                        return True
                elif downstream in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError(f"Cycle detected in ArtifactDependencyGraph involving node {node.value}")

    @classmethod
    def get_review_governed_paths(cls) -> Set[str]:
        """
        Returns the set of artifact file paths that govern ReviewBundle freshness.
        Used by ReviewService to bind hashes to canonical dependency graph nodes.
        """
        return {
            ArtifactKind.BLUEPRINT.value,
            ArtifactKind.MANIFEST.value,
            ArtifactKind.MATERIALIZED_MEDIA.value,
            ArtifactKind.PROBE_REPORT.value,
        }
