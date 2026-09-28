"""
Artifact Service (S10).

The canonical mutation authority for governed project artifacts.
Guarantees that any change to an upstream artifact:
1. Calculates the affected downstream dependency set via ArtifactDependencyGraph.
2. Generates an explicit, audit-preserved InvalidationPlan.
3. Applies invalidations atomically via CAS (monotonically increasing state revision).
4. Invalidates downstream evidence records (status=INVALIDATED, retaining history).
5. Invalidates active review bundles and decisions without bypassing ReviewService.
6. Cleans stale disk authorization tokens (.studio_approved, .studio_unlocked).
7. Rejects stale concurrent mutations with StateConflictError.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Union, Optional
from datetime import datetime, timezone

logger = logging.getLogger("clean_video.artifact_service")

from scripts.core.state_model import (
    ProjectState,
    ArtifactRecord,
    ValidationLevel,
    EvidenceStatus,
    ReviewDecisionType,
)
from scripts.core.state_store import (
    StateStore,
    StateConflictError,
    StateStoreError,
    StateNotFoundError,
)
from scripts.core.dependency_graph import (
    ArtifactDependencyGraph,
    ArtifactKind,
    InvalidationPlan,
)


class ArtifactService:
    """Canonical service for governed artifact mutations and invalidations."""

    _graph = ArtifactDependencyGraph()

    @classmethod
    def _resolve_project_dir(cls, project_dir_or_id: Union[Path, str]) -> Path:
        p = Path(project_dir_or_id)
        if not p.is_dir() and not p.exists() and not str(p).startswith("projects/"):
            cand = Path("projects") / str(project_dir_or_id)
            if cand.exists():
                return cand
        return p

    @classmethod
    def apply_invalidation_plan(
        cls,
        project_dir: Union[Path, str],
        plan: InvalidationPlan,
    ) -> ProjectState:
        """
        Applies a computed InvalidationPlan atomically with CAS.
        Fails with StateConflictError if state revision changed since plan was generated.
        """
        pdir = cls._resolve_project_dir(project_dir)
        current_state = StateStore.load(pdir)
        if not current_state:
            raise StateNotFoundError(f"Project state not found in {pdir}")

        if current_state.revision != plan.source_revision:
            raise StateConflictError(
                expected_revision=plan.source_revision,
                actual_revision=current_state.revision,
                message=(
                    f"Cannot apply InvalidationPlan '{plan.plan_id}': expected revision {plan.source_revision} "
                    f"but project state is currently at revision {current_state.revision}."
                ),
            )

        def mutator(working_copy: ProjectState) -> None:
            # 1. Invalidate artifact evidence records (never delete; preserve history)
            for rec in working_copy.artifact_records:
                if rec.path in plan.invalidated_evidence_paths:
                    rec.invalidate(reason=plan.reason, plan_id=plan.plan_id)

            # 2. Invalidate review bundles
            for bundle in working_copy.review_bundles:
                if bundle.review_bundle_id in plan.invalidated_review_bundles:
                    bundle.invalidate(reason=plan.reason)
                elif ArtifactKind.REVIEW_BUNDLE.value in plan.invalidated_artifacts and bundle.status == "ACTIVE":
                    bundle.invalidate(reason=plan.reason)

            # 3. Invalidate review decisions
            for decision in working_copy.review_decisions:
                if decision.decision_id in plan.invalidated_decisions:
                    decision.invalidate(reason=plan.reason)
                elif ArtifactKind.REVIEW_DECISION.value in plan.invalidated_artifacts and decision.decision == ReviewDecisionType.APPROVED:
                    decision.invalidate(reason=plan.reason)

            # 4. Sync approval metadata with active decision
            working_copy.sync_approval_metadata()

            # 5. Audit log invalidation plan
            if "invalidation_history" not in working_copy.run_metadata:
                working_copy.run_metadata["invalidation_history"] = []
            working_copy.run_metadata["invalidation_history"].append(plan.model_dump())
            working_copy.run_metadata["last_invalidation_plan"] = plan.model_dump()

        # Execute atomic CAS update
        updated_state = StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=plan.source_revision,
            mutator=mutator,
        )

        # 6. Best-effort housekeeping: clean stale legacy disk markers after canonical commit
        for stale_file in plan.stale_disk_paths:
            marker_path = pdir / stale_file
            if marker_path.exists():
                try:
                    marker_path.unlink()
                except OSError as e:
                    logger.warning(
                        "Best-effort cleanup failed to unlink legacy marker '%s' in '%s': %s. "
                        "State invalidation remains committed and authoritative.",
                        stale_file,
                        pdir,
                        e,
                    )

        return updated_state

    @classmethod
    def mutate_artifact(
        cls,
        project_dir: Union[Path, str],
        artifact_kind: Union[ArtifactKind, str],
        new_content: Union[str, bytes],
        reason: str,
        expected_revision: Optional[int] = None,
    ) -> InvalidationPlan:
        """
        Authoritative pipeline for mutating a governed artifact:
        1. Verifies revision preconditions.
        2. Computes downstream InvalidationPlan.
        3. Writes artifact to disk.
        4. Applies invalidation plan and updates mutated artifact's record via CAS.
        """
        pdir = cls._resolve_project_dir(project_dir)
        state = StateStore.load(pdir)
        if not state:
            raise StateNotFoundError(f"Project state not found in {pdir}")

        if expected_revision is not None and state.revision != expected_revision:
            raise StateConflictError(
                expected_revision=expected_revision,
                actual_revision=state.revision,
                message=(
                    f"Mutation conflict on {artifact_kind}: expected revision {expected_revision} "
                    f"does not match current revision {state.revision}."
                ),
            )

        # Resolve ArtifactKind
        kind = artifact_kind if isinstance(artifact_kind, ArtifactKind) else ArtifactKind.from_string(str(artifact_kind))
        if not kind:
            raise ValueError(f"Unknown governed artifact kind: {artifact_kind}")

        # Compute invalidation plan before writing
        plan = cls._graph.compute_invalidation_plan(
            project_state=state,
            changed_nodes=[kind],
            reason=reason,
        )

        # Write new content to disk
        file_path = pdir / kind.value
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(new_content, str):
            file_path.write_text(new_content, encoding="utf-8")
        else:
            file_path.write_bytes(new_content)

        # Compute new file metadata
        new_sha = StateStore._compute_sha256(file_path)
        new_size = file_path.stat().st_size

        # Apply plan and update the mutated record in state
        def mutator(working_copy: ProjectState) -> None:
            # First, apply the invalidation plan logic
            for rec in working_copy.artifact_records:
                if rec.path in plan.invalidated_evidence_paths:
                    rec.invalidate(reason=plan.reason, plan_id=plan.plan_id)

            for bundle in working_copy.review_bundles:
                if bundle.review_bundle_id in plan.invalidated_review_bundles:
                    bundle.invalidate(reason=plan.reason)
                elif ArtifactKind.REVIEW_BUNDLE.value in plan.invalidated_artifacts and bundle.status == "ACTIVE":
                    bundle.invalidate(reason=plan.reason)

            for decision in working_copy.review_decisions:
                if decision.decision_id in plan.invalidated_decisions:
                    decision.invalidate(reason=plan.reason)
                elif ArtifactKind.REVIEW_DECISION.value in plan.invalidated_artifacts and decision.decision == ReviewDecisionType.APPROVED:
                    decision.invalidate(reason=plan.reason)

            working_copy.sync_approval_metadata()

            # Record or update the mutated artifact itself as VALID
            updated_record = ArtifactRecord(
                path=kind.value,
                validation=ValidationLevel.SHA256,
                size_bytes=new_size,
                sha256=new_sha,
                status=EvidenceStatus.VALID,
                stage=working_copy.lifecycle_state.value if hasattr(working_copy.lifecycle_state, "value") else str(working_copy.lifecycle_state),
                metadata={"mutated_by": "ArtifactService", "mutation_reason": reason},
            )
            working_copy.record_evidence(updated_record)

            if "invalidation_history" not in working_copy.run_metadata:
                working_copy.run_metadata["invalidation_history"] = []
            working_copy.run_metadata["invalidation_history"].append(plan.model_dump())
            working_copy.run_metadata["last_invalidation_plan"] = plan.model_dump()

        StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=state.revision,
            mutator=mutator,
        )

        # Best-effort housekeeping: clean stale legacy disk markers after canonical commit
        for stale_file in plan.stale_disk_paths:
            marker_path = pdir / stale_file
            if marker_path.exists():
                try:
                    marker_path.unlink()
                except OSError as e:
                    logger.warning(
                        "Best-effort cleanup failed to unlink legacy marker '%s' in '%s': %s. "
                        "State invalidation remains committed and authoritative.",
                        stale_file,
                        pdir,
                        e,
                    )

        return plan
