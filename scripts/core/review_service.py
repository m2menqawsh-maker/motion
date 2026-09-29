"""
Review Service — The Canonical Authority for Review Bundles, Decisions & Render Authorization (S09).

Architecture Rules (S09):
1. ReviewService is the SOLE authority for creating review snapshots (ReviewBundle),
   recording human review decisions (ReviewDecision), and authorizing render execution.
2. Direct inspection or reliance on .studio_approved alone for render authorization is forbidden.
3. User-supplied identity strings (e.g. approved_by="user") are NEVER accepted as authority.
   Identity is strictly derived from server-verified Principal contracts.
4. Upstream mutations (blueprint, media map, probe report, manifest) invalidate review decisions.
5. All render paths (CLI, API, Pipeline, Docker) MUST call assert_render_authorized().
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from scripts.core.failure_model import FailureCode
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.state_model import (
    LifecycleState,
    ProjectState,
    ReviewBundle,
    ReviewDecision,
    ReviewDecisionType,
    ValidationLevel,
)
from scripts.core.state_store import StateStore, StateConflictError
from scripts.core.lifecycle_service import LifecycleService, LifecycleError
from scripts.core.dependency_graph import ArtifactDependencyGraph, ArtifactKind


class ReviewError(Exception):
    """Base exception for all review domain errors."""
    pass


class ReviewIdentityInvalidError(ReviewError):
    """Raised when an unauthenticated, unauthorized, or forged principal attempts a review operation."""
    pass


class ReviewNotAllowedError(ReviewError):
    """Raised when a review operation is attempted in an illegal lifecycle state."""
    pass


class ReviewBundleMissingError(ReviewError):
    """Raised when a review operation references a non-existent review bundle."""
    pass


class ReviewBundleStaleError(ReviewError):
    """Raised when a review bundle is stale or invalid relative to current state or disk."""
    pass


class RenderNotAuthorizedError(ReviewError):
    """Raised when render execution is attempted without valid canonical review authorization."""
    def __init__(self, code: FailureCode, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")


class RenderAuthorizationResult(BaseModel):
    """Deterministic output of canonical render authorization check."""
    is_authorized: bool
    project_id: str
    bundle_id: Optional[str] = None
    decision_id: Optional[str] = None
    actor_id: Optional[str] = None
    decided_at: Optional[str] = None
    failure_code: Optional[FailureCode] = None
    failure_reason: Optional[str] = None
    checked_hashes: Dict[str, str] = Field(default_factory=dict)


class ReviewStatusDTO(BaseModel):
    """Safe read-only projection of the current review status for API and tooling."""
    project_id: str
    lifecycle_state: str
    active_bundle_id: Optional[str] = None
    active_decision: Optional[str] = None
    decision_id: Optional[str] = None
    decided_at: Optional[str] = None
    actor: Optional[str] = None
    is_stale: bool = False
    blocking_reason: Optional[str] = None
    bundles_count: int = 0
    decisions_count: int = 0


def create_local_trusted_principal(actor_id: str = "local_reviewer") -> Principal:
    """Helper to generate a local trusted reviewer principal for trusted local/CLI flows."""
    return Principal(
        principal_id=actor_id,
        principal_type=PrincipalType.SYSTEM_WORKER,
        roles={Role.ADMIN, Role.REVIEWER},
        project_scopes={"*": {Role.ADMIN, Role.REVIEWER}},
        auth_method="LOCAL_TRUSTED_SESSION"
    )


class ReviewService:
    """The Single Domain Authority for Review and Render Authorization."""

    @classmethod
    def _resolve_project_dir(cls, project_dir_or_id: Path | str) -> Path:
        p = Path(project_dir_or_id)
        if p.is_dir() and (p / StateStore.STATE_FILE).exists():
            return p.resolve()
        
        # Check projects/ relative
        candidate = Path.cwd().resolve() / "projects" / str(project_dir_or_id)
        if candidate.is_dir() and (candidate / StateStore.STATE_FILE).exists():
            return candidate
            
        return p.resolve()

    @classmethod
    def create_review_bundle(
        cls,
        project_dir: Path | str,
        actor: Optional[Principal] = None,
        timeout: float = 10.0,
        require_contact_sheet: bool = False,
        render_input_sha256: Optional[str] = None,
        probe_frame_plan_digest: Optional[str] = None,
        rendered_frames_sha256: Optional[Dict[str, str]] = None,
    ) -> ReviewBundle:
        """
        Creates an immutable ReviewBundle snapshot of all artifacts subject to review.
        Computes SHA256 digests of blueprint, manifest, media map, probe report, and contact sheet.
        Commits bundle atomically via CAS into ProjectState.
        """
        pdir = cls._resolve_project_dir(project_dir)
        state = StateStore.load(pdir)
        if not state:
            raise ReviewError(f"No state file found at {pdir}")

        curr_state = LifecycleState(state.lifecycle_state)
        # Bundle creation is allowed once scenes are probed and ready for human review
        allowed_states = (
            LifecycleState.MATERIALIZED,
            LifecycleState.PROBE_PASSED,
            LifecycleState.AWAITING_REVIEW,
            LifecycleState.REVIEW_APPROVED,
        )
        if curr_state not in allowed_states:
            raise ReviewNotAllowedError(
                f"Cannot create review bundle in lifecycle state '{curr_state.value}'. "
                f"Required state is at least PROBE_PASSED or AWAITING_REVIEW."
            )

        # 1. Collect and hash mandatory review artifacts
        bp_path = pdir / "05_blueprint.json"
        if not bp_path.exists():
            raise ReviewError(f"Mandatory blueprint file '{bp_path.name}' is missing on disk.")
        blueprint_sha = StateStore._compute_sha256(bp_path)

        mm_path = pdir / "media_map.json"
        if not mm_path.exists():
            raise ReviewError(f"Mandatory media map file '{mm_path.name}' is missing on disk.")
        media_map_sha = StateStore._compute_sha256(mm_path)

        probe_path = pdir / "probe_qc_report.json"
        if not probe_path.exists():
            raise ReviewError(f"Mandatory probe report file '{probe_path.name}' is missing on disk.")
        probe_report_sha = StateStore._compute_sha256(probe_path)

        # 2. Collect contact sheet (mandatory when require_contact_sheet=True or when present)
        contact_sheet_path = pdir / "contact_sheet.png"
        if require_contact_sheet:
            if not contact_sheet_path.exists():
                raise ReviewError(f"Mandatory contact sheet file '{contact_sheet_path.name}' is missing on disk.")
            if contact_sheet_path.stat().st_size == 0:
                raise ReviewError(f"Mandatory contact sheet file '{contact_sheet_path.name}' is empty (0 bytes).")
            contact_sheet_sha = StateStore._compute_sha256(contact_sheet_path)
        else:
            if contact_sheet_path.exists():
                if contact_sheet_path.stat().st_size == 0:
                    raise ReviewError(f"Contact sheet file '{contact_sheet_path.name}' is empty (0 bytes).")
                contact_sheet_sha = StateStore._compute_sha256(contact_sheet_path)
            else:
                contact_sheet_sha = None

        # 3. Collect optional review artifacts if present
        manifest_path = pdir / "02_asset_manifest.json"
        manifest_sha = StateStore._compute_sha256(manifest_path) if manifest_path.exists() else None

        # 4. Canonical render input (render_props.json)
        computed_rp_sha = None
        rp_path = pdir / "render_props.json"
        if rp_path.exists():
            computed_rp_sha = StateStore._compute_sha256(rp_path)
        final_render_input_sha = render_input_sha256 or computed_rp_sha

        bundle_id = f"bundle_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        bundle_dict = {
            "review_bundle_id": bundle_id,
            "project_id": state.project_id,
            "created_at": now_iso,
            "state_revision": state.revision,
            "blueprint_sha256": blueprint_sha,
            "manifest_sha256": manifest_sha,
            "media_map_sha256": media_map_sha,
            "probe_report_sha256": probe_report_sha,
            "contact_sheet_sha256": contact_sheet_sha,
            "render_input_sha256": final_render_input_sha,
            "probe_frame_plan_digest": probe_frame_plan_digest,
        }
        bundle_digest = ReviewBundle.compute_bundle_digest(bundle_dict)

        new_bundle = ReviewBundle(
            review_bundle_id=bundle_id,
            project_id=state.project_id,
            created_at=now_iso,
            state_revision=state.revision,
            blueprint_sha256=blueprint_sha,
            manifest_sha256=manifest_sha,
            media_map_sha256=media_map_sha,
            probe_report_sha256=probe_report_sha,
            contact_sheet_sha256=contact_sheet_sha,
            render_input_sha256=final_render_input_sha,
            probe_frame_plan_digest=probe_frame_plan_digest,
            rendered_frames_sha256=rendered_frames_sha256 or {},
            bundle_digest=bundle_digest,
            status="ACTIVE",
        )

        def mutator(working_copy: ProjectState) -> None:
            # Supersede any currently active bundles
            for existing in working_copy.review_bundles:
                if existing.status == "ACTIVE":
                    existing.status = "SUPERSEDED"
            working_copy.review_bundles.append(new_bundle)
            working_copy.active_review_bundle_id = bundle_id

        StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=state.revision,
            mutator=mutator,
            timeout=timeout,
        )

        return new_bundle

    @classmethod
    def approve(
        cls,
        project_dir: Path | str,
        bundle_id: str,
        principal: Principal,
        reason: Optional[str] = None,
        expected_revision: Optional[int] = None,
        timeout: float = 10.0,
    ) -> ReviewDecision:
        """
        Records human approval on a specific immutable ReviewBundle snapshot.
        Transitions the project lifecycle to REVIEW_APPROVED via CAS.
        """
        pdir = cls._resolve_project_dir(project_dir)

        # 1. Identity validation
        if not isinstance(principal, Principal) or not principal.is_authenticated:
            raise ReviewIdentityInvalidError(
                "Review approval requires a server-verified authenticated Principal; unauthenticated identity rejected."
            )
        if principal.principal_type == PrincipalType.ANONYMOUS:
            raise ReviewIdentityInvalidError(
                "Anonymous principal is strictly forbidden from approving reviews."
            )

        state = StateStore.load(pdir)
        if not state:
            raise ReviewError(f"Project state not found at {pdir}")

        if not (principal.has_role(Role.REVIEWER, state.project_id) or principal.has_role(Role.ADMIN, state.project_id)):
            raise ReviewIdentityInvalidError(
                f"Principal '{principal.principal_id}' lacks REVIEWER or ADMIN role for project '{state.project_id}'."
            )

        # 2. Lifecycle state validation
        curr_state = LifecycleState(state.lifecycle_state)
        if curr_state != LifecycleState.AWAITING_REVIEW:
            raise ReviewNotAllowedError(
                f"Review approval is only permitted in AWAITING_REVIEW state; current is '{curr_state.value}'."
            )

        # 3. Find bundle and verify freshness
        target_bundle = None
        for b in state.review_bundles:
            if b.review_bundle_id == bundle_id:
                target_bundle = b
                break

        if not target_bundle:
            raise ReviewBundleMissingError(
                f"Review bundle '{bundle_id}' does not exist on project '{state.project_id}'."
            )

        if target_bundle.status != "ACTIVE":
            raise ReviewBundleStaleError(
                f"Review bundle '{bundle_id}' is not ACTIVE (status: '{target_bundle.status}', "
                f"reason: {target_bundle.invalidated_reason}). A new bundle must be created."
            )

        # 4. Check disk hashes against bundle hashes to prevent approval on tampered files
        bp_path = pdir / "05_blueprint.json"
        if not bp_path.exists() or StateStore._compute_sha256(bp_path) != target_bundle.blueprint_sha256:
            raise ReviewBundleStaleError(
                "Blueprint file on disk has changed since review bundle creation. Approval rejected."
            )

        mm_path = pdir / "media_map.json"
        if not mm_path.exists() or StateStore._compute_sha256(mm_path) != target_bundle.media_map_sha256:
            raise ReviewBundleStaleError(
                "Media map on disk has changed since review bundle creation. Approval rejected."
            )

        probe_path = pdir / "probe_qc_report.json"
        if not probe_path.exists() or StateStore._compute_sha256(probe_path) != target_bundle.probe_report_sha256:
            raise ReviewBundleStaleError(
                "Probe QC report on disk has changed since review bundle creation. Approval rejected."
            )

        if target_bundle.contact_sheet_sha256:
            cs_path = pdir / "contact_sheet.png"
            if not cs_path.exists() or StateStore._compute_sha256(cs_path) != target_bundle.contact_sheet_sha256:
                raise ReviewBundleStaleError(
                    "Contact sheet on disk has changed since review bundle creation. Approval rejected."
                )

        if target_bundle.render_input_sha256:
            rp_path = pdir / "render_props.json"
            if not rp_path.exists() or StateStore._compute_sha256(rp_path) != target_bundle.render_input_sha256:
                raise ReviewBundleStaleError(
                    "Render input (render_props.json) on disk has changed since review bundle creation. Approval rejected."
                )

        # 5. Atomic CAS execution
        exp_rev = expected_revision if expected_revision is not None else state.revision
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        decision = ReviewDecision(
            decision_id=decision_id,
            review_bundle_id=bundle_id,
            project_id=state.project_id,
            decision=ReviewDecisionType.APPROVED,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            decided_at=now_iso,
            reason=reason,
            state_revision=exp_rev + 1,
            bundle_digest=target_bundle.bundle_digest,
            metadata={
                "auth_method": principal.auth_method,
                "approved_roles": [r.value for r in principal.get_roles_for_project(state.project_id)],
            }
        )

        # Write legacy marker for backward compatibility
        try:
            (pdir / ".studio_approved").write_text(
                json.dumps({
                    "decision_id": decision_id,
                    "review_bundle_id": bundle_id,
                    "approved_by": principal.principal_id,
                    "approved_at": now_iso,
                }, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

        def mutator(working_copy: ProjectState) -> None:
            working_copy.review_decisions.append(decision)
            working_copy.active_review_decision_id = decision_id
            working_copy.sync_approval_metadata()
            # Record required .studio_approved artifact evidence (S06 / S09 / S24)
            rec = StateStore.create_artifact_record(
                pdir,
                ".studio_approved",
                ValidationLevel.EXISTS,
                stage=LifecycleState.REVIEW_APPROVED.value,
                produced_at_revision=exp_rev + 1,
            )
            working_copy.record_evidence(rec)
            # Advance lifecycle to REVIEW_APPROVED
            LifecycleService.apply_transition_mutation(working_copy, LifecycleState.REVIEW_APPROVED)

        StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=exp_rev,
            mutator=mutator,
            timeout=timeout,
        )

        return decision

    @classmethod
    def reject(
        cls,
        project_dir: Path | str,
        bundle_id: str,
        principal: Principal,
        reason: str,
        expected_revision: Optional[int] = None,
        timeout: float = 10.0,
    ) -> ReviewDecision:
        """
        Records human rejection on a specific ReviewBundle.
        Keeps project in AWAITING_REVIEW, preserves full decision history, and removes legacy marker.
        """
        pdir = cls._resolve_project_dir(project_dir)

        if not isinstance(principal, Principal) or not principal.is_authenticated:
            raise ReviewIdentityInvalidError(
                "Review rejection requires a server-verified authenticated Principal."
            )
        if not reason or not reason.strip():
            raise ReviewError("A non-empty reason is required for review rejection.")

        state = StateStore.load(pdir)
        if not state:
            raise ReviewError(f"Project state not found at {pdir}")

        if not (principal.has_role(Role.REVIEWER, state.project_id) or principal.has_role(Role.ADMIN, state.project_id)):
            raise ReviewIdentityInvalidError(
                f"Principal '{principal.principal_id}' lacks REVIEWER or ADMIN role for project '{state.project_id}'."
            )

        target_bundle = None
        for b in state.review_bundles:
            if b.review_bundle_id == bundle_id:
                target_bundle = b
                break

        if not target_bundle:
            raise ReviewBundleMissingError(f"Review bundle '{bundle_id}' not found.")

        exp_rev = expected_revision if expected_revision is not None else state.revision
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        decision = ReviewDecision(
            decision_id=decision_id,
            review_bundle_id=bundle_id,
            project_id=state.project_id,
            decision=ReviewDecisionType.REJECTED,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            decided_at=now_iso,
            reason=reason.strip(),
            state_revision=exp_rev + 1,
            bundle_digest=target_bundle.bundle_digest,
            metadata={"auth_method": principal.auth_method}
        )

        def mutator(working_copy: ProjectState) -> None:
            working_copy.review_decisions.append(decision)
            working_copy.active_review_decision_id = decision_id
            working_copy.sync_approval_metadata()

        StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=exp_rev,
            mutator=mutator,
            timeout=timeout,
        )

        # Remove legacy .studio_approved if present
        marker = pdir / ".studio_approved"
        if marker.exists():
            try:
                marker.unlink()
            except Exception:
                pass

        return decision

    @classmethod
    def invalidate_review(cls, project_dir_or_id: Path | str, reason: str, bundle_id: Optional[str] = None) -> None:
        """
        Canonical Review Authority invalidation API.
        Invalidates active review bundle and approved decisions when upstream dependencies change.
        """
        pdir = cls._resolve_project_dir(project_dir_or_id)
        state = StateStore.load(pdir)
        if not state:
            return

        target_bundle_id = bundle_id
        if not target_bundle_id:
            active_bundle = state.get_active_review_bundle()
            if active_bundle:
                target_bundle_id = active_bundle.review_bundle_id

        if target_bundle_id:
            cls._invalidate_bundle_and_decision(pdir, target_bundle_id, reason)
        else:
            def mutator(working_copy: ProjectState) -> None:
                for b in working_copy.review_bundles:
                    if b.status == "ACTIVE":
                        b.invalidate(reason)
                for d in working_copy.review_decisions:
                    if d.decision == ReviewDecisionType.APPROVED:
                        d.invalidate(reason)
                working_copy.sync_approval_metadata()

            try:
                StateStore.atomic_update(
                    project_dir=pdir,
                    expected_revision=state.revision,
                    mutator=mutator,
                )
            except Exception:
                pass

        # Clean marker file
        marker = pdir / ".studio_approved"
        if marker.exists():
            try:
                marker.unlink()
            except Exception:
                pass

    @classmethod
    def _invalidate_bundle_and_decision(cls, project_dir: Path, bundle_id: str, reason: str) -> None:
        """Internal helper to atomically invalidate active bundle and decision when upstream changed."""
        try:
            state = StateStore.load(project_dir)
            if not state:
                return

            def mutator(working_copy: ProjectState) -> None:
                for b in working_copy.review_bundles:
                    if b.review_bundle_id == bundle_id:
                        b.invalidate(reason)
                for d in working_copy.review_decisions:
                    if d.review_bundle_id == bundle_id and d.decision == ReviewDecisionType.APPROVED:
                        d.invalidate(reason)
                working_copy.sync_approval_metadata()

            StateStore.atomic_update(
                project_dir=project_dir,
                expected_revision=state.revision,
                mutator=mutator,
            )

            marker = project_dir / ".studio_approved"
            if marker.exists():
                try:
                    marker.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    @classmethod
    def assert_render_authorized(cls, project_dir_or_id: Path | str) -> RenderAuthorizationResult:
        """
        Canonical Render Authorization Check.
        Used by CLI (render_project.py), API, and pipeline orchestrator.
        Fails closed if approval is missing, invalidated, or if files changed on disk.
        """
        pdir = cls._resolve_project_dir(project_dir_or_id)
        state = StateStore.load(pdir)

        if not state:
            raise RenderNotAuthorizedError(
                code=FailureCode.RENDER_NOT_AUTHORIZED,
                message=f"Project state file missing at {pdir}. Render denied."
            )

        # 1. State machine compatibility
        allowed_render_states = (
            LifecycleState.REVIEW_APPROVED,
            LifecycleState.RENDERED,
            LifecycleState.FINAL_QC_PASSED,
            LifecycleState.COMPLETE,
        )
        curr_state = LifecycleState(state.lifecycle_state)
        if curr_state not in allowed_render_states:
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_NOT_APPROVED,
                message=f"Project lifecycle state '{curr_state.value}' is not authorized for render (requires REVIEW_APPROVED or later)."
            )

        # 2. Active decision check
        active_decision = state.get_active_review_decision()
        if not active_decision or active_decision.decision != ReviewDecisionType.APPROVED:
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_NOT_APPROVED,
                message="No active APPROVED review decision found in canonical project state."
            )

        # 3. Referenced review bundle check
        active_bundle = None
        for b in state.review_bundles:
            if b.review_bundle_id == active_decision.review_bundle_id:
                active_bundle = b
                break

        if not active_bundle:
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_BUNDLE_MISSING,
                message=f"Referenced review bundle '{active_decision.review_bundle_id}' is missing from state history."
            )

        if active_bundle.status == "INVALIDATED":
            raise RenderNotAuthorizedError(
                code=FailureCode.RENDER_NOT_AUTHORIZED,
                message=f"Review bundle '{active_bundle.review_bundle_id}' was INVALIDATED: {active_bundle.invalidated_reason}."
            )

        # 4. Freshness check: current file hashes vs bundle hashes
        checked = {}

        bp_path = pdir / "05_blueprint.json"
        if not bp_path.exists():
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "BLUEPRINT_MISSING_ON_DISK")
            raise RenderNotAuthorizedError(
                code=FailureCode.RENDER_NOT_AUTHORIZED,
                message="Mandatory 05_blueprint.json is missing on disk."
            )
        current_bp_sha = StateStore._compute_sha256(bp_path)
        checked["blueprint"] = current_bp_sha
        if current_bp_sha != active_bundle.blueprint_sha256:
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "BLUEPRINT_CHANGED_AFTER_REVIEW")
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_BUNDLE_STALE,
                message="05_blueprint.json has changed since review approval was granted. Re-review required."
            )

        mm_path = pdir / "media_map.json"
        if not mm_path.exists():
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "MEDIA_MAP_MISSING_ON_DISK")
            raise RenderNotAuthorizedError(
                code=FailureCode.RENDER_NOT_AUTHORIZED,
                message="Mandatory media_map.json is missing on disk."
            )
        current_mm_sha = StateStore._compute_sha256(mm_path)
        checked["media_map"] = current_mm_sha
        if current_mm_sha != active_bundle.media_map_sha256:
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "MEDIA_MAP_CHANGED_AFTER_REVIEW")
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_BUNDLE_STALE,
                message="media_map.json has changed since review approval was granted. Re-review required."
            )

        probe_path = pdir / "probe_qc_report.json"
        if not probe_path.exists():
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "PROBE_REPORT_MISSING_ON_DISK")
            raise RenderNotAuthorizedError(
                code=FailureCode.RENDER_NOT_AUTHORIZED,
                message="Mandatory probe_qc_report.json is missing on disk."
            )
        current_probe_sha = StateStore._compute_sha256(probe_path)
        checked["probe_report"] = current_probe_sha
        if current_probe_sha != active_bundle.probe_report_sha256:
            cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "PROBE_REPORT_CHANGED_AFTER_REVIEW")
            raise RenderNotAuthorizedError(
                code=FailureCode.REVIEW_BUNDLE_STALE,
                message="probe_qc_report.json has changed since review approval was granted. Re-review required."
            )

        if active_bundle.manifest_sha256:
            mf_path = pdir / "02_asset_manifest.json"
            if mf_path.exists():
                cur_mf_sha = StateStore._compute_sha256(mf_path)
                checked["manifest"] = cur_mf_sha
                if cur_mf_sha != active_bundle.manifest_sha256:
                    cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "MANIFEST_CHANGED_AFTER_REVIEW")
                    raise RenderNotAuthorizedError(
                        code=FailureCode.REVIEW_BUNDLE_STALE,
                        message="02_asset_manifest.json has changed since review approval was granted."
                    )

        if active_bundle.contact_sheet_sha256:
            cs_path = pdir / "contact_sheet.png"
            if not cs_path.exists():
                cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "CONTACT_SHEET_MISSING_ON_DISK")
                raise RenderNotAuthorizedError(
                    code=FailureCode.RENDER_NOT_AUTHORIZED,
                    message="Mandatory contact_sheet.png is missing on disk."
                )
            cur_cs_sha = StateStore._compute_sha256(cs_path)
            checked["contact_sheet"] = cur_cs_sha
            if cur_cs_sha != active_bundle.contact_sheet_sha256:
                cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "CONTACT_SHEET_CHANGED_AFTER_REVIEW")
                raise RenderNotAuthorizedError(
                    code=FailureCode.REVIEW_BUNDLE_STALE,
                    message="contact_sheet.png has changed since review approval was granted. Re-review required."
                )

        if active_bundle.render_input_sha256:
            rp_path = pdir / "render_props.json"
            if rp_path.exists():
                cur_rp_sha = StateStore._compute_sha256(rp_path)
                checked["render_input"] = cur_rp_sha
                if cur_rp_sha != active_bundle.render_input_sha256:
                    cls._invalidate_bundle_and_decision(pdir, active_bundle.review_bundle_id, "RENDER_INPUT_CHANGED_AFTER_REVIEW")
                    raise RenderNotAuthorizedError(
                        code=FailureCode.REVIEW_BUNDLE_STALE,
                        message="render_props.json has changed since review approval was granted. Re-review required."
                    )

        return RenderAuthorizationResult(
            is_authorized=True,
            project_id=state.project_id,
            bundle_id=active_bundle.review_bundle_id,
            decision_id=active_decision.decision_id,
            actor_id=active_decision.actor_id,
            decided_at=active_decision.decided_at,
            checked_hashes=checked,
        )

    @classmethod
    def is_render_authorized(cls, project_dir_or_id: Path | str) -> Tuple[bool, str]:
        """Convenience boolean check for retry policies and guards."""
        try:
            res = cls.assert_render_authorized(project_dir_or_id)
            return True, f"Render authorized (bundle: {res.bundle_id}, actor: {res.actor_id})"
        except RenderNotAuthorizedError as e:
            return False, e.message

    @classmethod
    def get_active_bundle(cls, project_dir_or_id: Path | str) -> Optional[ReviewBundle]:
        """Returns the current active review bundle if one exists."""
        pdir = cls._resolve_project_dir(project_dir_or_id)
        state = StateStore.load(pdir)
        return state.get_active_review_bundle() if state else None

    @classmethod
    def get_review_status(cls, project_dir_or_id: Path | str) -> ReviewStatusDTO:
        """Reads current review status safely for external consumers."""
        pdir = cls._resolve_project_dir(project_dir_or_id)
        state = StateStore.load(pdir)
        if not state:
            return ReviewStatusDTO(
                project_id=Path(project_dir_or_id).name,
                lifecycle_state="UNKNOWN",
                blocking_reason="Project state file not found"
            )

        active_bundle = state.get_active_review_bundle()
        active_decision = state.get_active_review_decision()
        is_stale = False
        blocking_reason = None

        if active_bundle:
            bp_path = pdir / "05_blueprint.json"
            if bp_path.exists() and StateStore._compute_sha256(bp_path) != active_bundle.blueprint_sha256:
                is_stale = True
                blocking_reason = "Blueprint has changed since review bundle creation"

        return ReviewStatusDTO(
            project_id=state.project_id,
            lifecycle_state=state.lifecycle_state.value if hasattr(state.lifecycle_state, "value") else str(state.lifecycle_state),
            active_bundle_id=active_bundle.review_bundle_id if active_bundle else None,
            active_decision=active_decision.decision.value if active_decision else None,
            decision_id=active_decision.decision_id if active_decision else None,
            decided_at=active_decision.decided_at if active_decision else None,
            actor=active_decision.actor_id if active_decision else None,
            is_stale=is_stale,
            blocking_reason=blocking_reason,
            bundles_count=len(state.review_bundles),
            decisions_count=len(state.review_decisions),
        )


# Canonical top-level alias
assert_render_authorized = ReviewService.assert_render_authorized
