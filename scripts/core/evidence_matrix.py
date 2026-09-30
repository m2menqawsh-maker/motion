"""
Required Evidence Matrix & Verification Authority (S06).

Central Authority for required and cumulative evidence per lifecycle state.
Single source of truth used by LifecycleService, RecoveryEngine, and Pipeline.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    EvidenceStatus,
    ArtifactRecord,
    ProjectState,
)


class EvidenceIssueType(str, Enum):
    MISSING_RECORD = "MISSING_RECORD"      # Required evidence not recorded in state.artifact_records
    MISSING_FILE = "MISSING_FILE"          # File is missing on disk
    EMPTY_FILE = "EMPTY_FILE"              # File is empty (0 bytes) when non-empty required
    SIZE_MISMATCH = "SIZE_MISMATCH"        # File size on disk != size in record
    HASH_MISMATCH = "HASH_MISMATCH"        # SHA256 on disk != sha256 in record
    CORRUPTED = "CORRUPTED"                # File is unreadable or malformed


class EvidenceIssue(BaseModel):
    issue_type: EvidenceIssueType
    path: str
    logical_name: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str


class EvidenceValidationResult(BaseModel):
    is_valid: bool
    lifecycle_state: LifecycleState
    required_count: int
    verified_count: int
    issues: List[EvidenceIssue] = Field(default_factory=list)
    missing_paths: List[str] = Field(default_factory=list)
    mismatched_paths: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None

    def summary(self) -> str:
        if self.is_valid:
            return f"Valid ({self.verified_count}/{self.required_count} required verified)"
        issue_msgs = [f"{iss.issue_type.value}[{iss.path}]: {iss.message}" for iss in self.issues]
        return "; ".join(issue_msgs)


class RequiredEvidenceItem(BaseModel):
    logical_name: str
    path: str
    validation: ValidationLevel
    mandatory: bool = True
    min_size_bytes: int = 1
    description: str = ""


# Canonical evidence catalog across all stages
REQUIRED_EVIDENCE_ITEMS: Dict[str, RequiredEvidenceItem] = {
    "manifest": RequiredEvidenceItem(
        logical_name="asset_manifest",
        path="02_asset_manifest.json",
        validation=ValidationLevel.EXISTS,
        mandatory=True,
        description="Asset manifest declaring project media sources",
    ),
    "plan": RequiredEvidenceItem(
        logical_name="master_plan",
        path="master_plan.md",
        validation=ValidationLevel.SHA256,
        mandatory=True,
        description="Verified master plan markdown",
    ),
    "blueprint": RequiredEvidenceItem(
        logical_name="blueprint",
        path="05_blueprint.json",
        validation=ValidationLevel.SHA256,
        mandatory=True,
        description="Validated scene blueprint json",
    ),
    "media_map": RequiredEvidenceItem(
        logical_name="media_map",
        path="media_map.json",
        validation=ValidationLevel.EXISTS,
        mandatory=True,
        description="Materialized project media map",
    ),
    "probe_report": RequiredEvidenceItem(
        logical_name="probe_qc_report",
        path="probe_qc_report.json",
        validation=ValidationLevel.SHA256,
        mandatory=True,
        description="Probe QC verification report",
    ),
    "contact_sheet": RequiredEvidenceItem(
        logical_name="contact_sheet",
        path="contact_sheet.png",
        validation=ValidationLevel.SHA256,
        mandatory=True,
        min_size_bytes=1,
        description="Mandatory probe review contact sheet image",
    ),
    "studio_approved": RequiredEvidenceItem(
        logical_name="studio_approved",
        path=".studio_approved",
        validation=ValidationLevel.EXISTS,
        mandatory=True,
        description="Human studio review approval marker",
    ),
    "rendered_video": RequiredEvidenceItem(
        logical_name="rendered_video",
        path="out.mp4",
        validation=ValidationLevel.SIZE,
        mandatory=True,
        min_size_bytes=100,
        description="Final rendered MP4 video output",
    ),
}

# The authoritative required evidence matrix per lifecycle state.
# States require cumulative evidence from previous validated stages.
REQUIRED_EVIDENCE_BY_STATE: Dict[LifecycleState, List[RequiredEvidenceItem]] = {
    LifecycleState.DRAFT: [],
    LifecycleState.ASSETS_READY: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
    ],
    LifecycleState.PLAN_READY: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
    ],
    LifecycleState.BLUEPRINT_READY: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
    ],
    LifecycleState.MATERIALIZED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
    ],
    LifecycleState.PROBE_PASSED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["probe_report"],
    ],
    LifecycleState.AWAITING_REVIEW: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["probe_report"],
    ],
    LifecycleState.REVIEW_APPROVED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["probe_report"],
        REQUIRED_EVIDENCE_ITEMS["studio_approved"],
    ],
    LifecycleState.RENDERED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.FINAL_QC_PASSED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.COMPLETE: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["media_map"],
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.FAILED: [],
    LifecycleState.CANCELLED: [],
}


class EvidenceLedger:
    """
    Authoritative ledger for merging, tracking, and validating evidence records (S07.5).
    Prevents resurrection of INVALIDATED or SUPERSEDED records by stale incoming records.
    Maintains historical lineage for superseded records across generations.
    """

    @classmethod
    def merge_records(
        cls,
        existing: List[ArtifactRecord],
        incoming: List[ArtifactRecord],
    ) -> List[ArtifactRecord]:
        """
        Deterministically merges incoming artifact records into existing records with defensive protections:
        - If existing record is INVALIDATED or SUPERSEDED, an incoming VALID record cannot resurrect it
          unless it has a distinct new generation_id AND/OR a strictly newer produced_at_revision.
        - When a legitimate new generation or newer revision replaces an existing record, the previous record's
          lineage is preserved in metadata['superseded_lineage'].
        - Existing records with distinct paths are preserved.
        """
        if not existing:
            return [rec.model_copy(deep=True) for rec in incoming]
        if not incoming:
            return [rec.model_copy(deep=True) for rec in existing]

        result = [rec.model_copy(deep=True) for rec in existing]
        path_to_idx = {rec.path: i for i, rec in enumerate(result)}

        for inc in incoming:
            inc_copy = inc.model_copy(deep=True)
            if inc_copy.path not in path_to_idx:
                path_to_idx[inc_copy.path] = len(result)
                result.append(inc_copy)
                continue

            curr_idx = path_to_idx[inc_copy.path]
            curr = result[curr_idx]

            curr_status = getattr(curr, "status", EvidenceStatus.VALID)
            if isinstance(curr_status, str):
                try:
                    curr_status = EvidenceStatus(curr_status)
                except ValueError:
                    curr_status = EvidenceStatus.VALID

            inc_status = getattr(inc_copy, "status", EvidenceStatus.VALID)
            if isinstance(inc_status, str):
                try:
                    inc_status = EvidenceStatus(inc_status)
                except ValueError:
                    inc_status = EvidenceStatus.VALID

            curr_rev = curr.produced_at_revision or 0
            inc_rev = inc_copy.produced_at_revision or 0

            curr_gen = getattr(curr, "generation_id", None)
            inc_gen = getattr(inc_copy, "generation_id", None)

            # Case 1: Existing record is INVALIDATED or SUPERSEDED
            if curr_status in (EvidenceStatus.INVALIDATED, EvidenceStatus.SUPERSEDED):
                if inc_status == EvidenceStatus.VALID:
                    # Legitimate resurrection only permitted if:
                    # distinct new generation_id AND/OR strictly newer revision
                    is_new_generation = (
                        (inc_gen is not None and curr_gen is not None and inc_gen != curr_gen)
                        or (inc_rev > curr_rev)
                    )
                    # Must not be older revision even if gen is different
                    if not is_new_generation or inc_rev < curr_rev:
                        # Reject resurrection! Keep curr
                        continue

                    # Legitimate replacement by newer generation:
                    cls._record_lineage(inc_copy, curr)
                    result[curr_idx] = inc_copy
                else:
                    # If incoming is also INVALIDATED or SUPERSEDED
                    if inc_rev >= curr_rev:
                        result[curr_idx] = inc_copy
                continue

            # Case 2: Existing record is VALID
            if inc_status in (EvidenceStatus.INVALIDATED, EvidenceStatus.SUPERSEDED):
                # An explicit invalidation/superseding replaces valid record
                cls._record_lineage(inc_copy, curr)
                result[curr_idx] = inc_copy
                continue

            # Case 3: Both are VALID
            if inc_rev < curr_rev:
                # Stale incoming record cannot overwrite newer valid record
                continue

            if (inc_gen is not None and curr_gen is not None and inc_gen != curr_gen) or (inc_rev > curr_rev):
                cls._record_lineage(inc_copy, curr)

            result[curr_idx] = inc_copy

        return result

    @classmethod
    def _record_lineage(cls, new_rec: ArtifactRecord, old_rec: ArtifactRecord) -> None:
        """Records historical lineage of superseded/replaced records in metadata."""
        if not hasattr(new_rec, "metadata") or new_rec.metadata is None:
            new_rec.metadata = {}

        prior_entry = {
            "previous_generation_id": getattr(old_rec, "generation_id", None),
            "previous_revision": getattr(old_rec, "produced_at_revision", None),
            "previous_status": old_rec.status.value if hasattr(old_rec.status, "value") else str(old_rec.status),
            "previous_sha256": getattr(old_rec, "sha256", None),
            "previous_size_bytes": getattr(old_rec, "size_bytes", None),
            "replaced_at": datetime.now(timezone.utc).isoformat(),
        }

        old_lineage = old_rec.metadata.get("superseded_lineage", []) if hasattr(old_rec, "metadata") and old_rec.metadata else []
        new_lineage = list(old_lineage)
        new_lineage.append(prior_entry)
        new_rec.metadata["superseded_lineage"] = new_lineage


def merge_artifact_records(
    existing: List[ArtifactRecord],
    incoming: List[ArtifactRecord],
) -> List[ArtifactRecord]:
    """
    Deterministically merges incoming artifact records into existing records via EvidenceLedger.
    """
    return EvidenceLedger.merge_records(existing, incoming)


class RequiredEvidencePolicy:
    """
    Single Authoritative Policy for Required Evidence per Lifecycle State.
    Used by LifecycleService, RecoveryEngine, and Pipeline.
    """

    @classmethod
    def get_required_evidence(cls, state: LifecycleState) -> List[RequiredEvidenceItem]:
        """Returns the list of required evidence items for a given lifecycle state."""
        state_enum = LifecycleState(state)
        return list(REQUIRED_EVIDENCE_BY_STATE.get(state_enum, []))

    @classmethod
    def is_artifact_required(
        cls,
        state: Union[LifecycleState, str],
        logical_name_or_path: str = "media_map",
    ) -> bool:
        """
        Authoritative query to determine if an artifact is required for a lifecycle state (S06).
        Checks both logical_name and path against required evidence items for the state.
        """
        state_enum = LifecycleState(state) if isinstance(state, str) else state
        items = cls.get_required_evidence(state_enum)
        for itm in items:
            if itm.logical_name == logical_name_or_path or itm.path == logical_name_or_path:
                return True
        return False

    @classmethod
    def validate_required_evidence(
        cls,
        state: ProjectState,
        project_dir: Path | str,
    ) -> EvidenceValidationResult:
        """
        Validates that all required evidence for state.lifecycle_state exists and is valid.
        Also validates integrity of any additional recorded artifacts.
        Returns a rich structured EvidenceValidationResult.
        """
        from scripts.core.state_store import StateStore

        pdir = Path(project_dir)
        state_enum = LifecycleState(state.lifecycle_state)
        required_items = cls.get_required_evidence(state_enum)

        issues: List[EvidenceIssue] = []
        verified_count = 0
        missing_paths: List[str] = []
        mismatched_paths: List[str] = []

        valid_records = [
            rec for rec in state.artifact_records
            if getattr(rec, "status", "VALID") == "VALID"
        ]
        records_by_path = {rec.path: rec for rec in valid_records}
        all_records_by_path = {rec.path: rec for rec in state.artifact_records}

        # 1. Verify all required items for the current lifecycle state
        for item in required_items:
            file_path = pdir / item.path
            rec = records_by_path.get(item.path)
            raw_rec = all_records_by_path.get(item.path)

            # Check presence in records
            if rec is None:
                if raw_rec is not None and getattr(raw_rec, "status", None) == "INVALIDATED":
                    msg = f"Required evidence '{item.path}' was invalidated (reason: {raw_rec.invalidated_reason}) and is invalid for state {state_enum.value}"
                else:
                    msg = f"Required evidence '{item.path}' is missing from artifact_records for state {state_enum.value}"
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.MISSING_RECORD,
                    path=item.path,
                    logical_name=item.logical_name,
                    message=msg
                ))
                missing_paths.append(item.path)

            # Check presence on disk
            if not file_path.exists():
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.MISSING_FILE,
                    path=item.path,
                    logical_name=item.logical_name,
                    message=f"Required evidence file '{item.path}' does not exist on disk for state {state_enum.value}"
                ))
                if item.path not in missing_paths:
                    missing_paths.append(item.path)
                continue

            # Check for non-empty file
            file_stat = file_path.stat()
            if file_stat.st_size == 0 and item.min_size_bytes > 0:
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.EMPTY_FILE,
                    path=item.path,
                    logical_name=item.logical_name,
                    expected=f">={item.min_size_bytes} bytes",
                    actual="0 bytes",
                    message=f"Required evidence file '{item.path}' on disk is empty (0 bytes)"
                ))
                if item.path not in mismatched_paths:
                    mismatched_paths.append(item.path)

            # If recorded, verify size / hash consistency
            if rec is not None:
                if rec.validation in (ValidationLevel.SIZE, ValidationLevel.SHA256) and rec.size_bytes is not None:
                    if file_stat.st_size != rec.size_bytes:
                        issues.append(EvidenceIssue(
                            issue_type=EvidenceIssueType.SIZE_MISMATCH,
                            path=item.path,
                            logical_name=item.logical_name,
                            expected=str(rec.size_bytes),
                            actual=str(file_stat.st_size),
                            message=f"Size mismatch for '{item.path}': recorded {rec.size_bytes}B, disk has {file_stat.st_size}B"
                        ))
                        if item.path not in mismatched_paths:
                            mismatched_paths.append(item.path)

                if rec.validation == ValidationLevel.SHA256 and rec.sha256 is not None:
                    disk_sha = StateStore._compute_sha256(file_path)
                    if disk_sha != rec.sha256:
                        issues.append(EvidenceIssue(
                            issue_type=EvidenceIssueType.HASH_MISMATCH,
                            path=item.path,
                            logical_name=item.logical_name,
                            expected=rec.sha256,
                            actual=disk_sha,
                            message=f"Content SHA256 mismatch for '{item.path}'"
                        ))
                        if item.path not in mismatched_paths:
                            mismatched_paths.append(item.path)

            if not any(iss.path == item.path for iss in issues):
                verified_count += 1

        # 2. Check any additional recorded artifacts not in required_items
        for rec in state.artifact_records:
            if getattr(rec, "status", "VALID") != "VALID":
                continue
            if rec.path in (item.path for item in required_items):
                continue
            file_path = pdir / rec.path
            if not file_path.exists():
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.MISSING_FILE,
                    path=rec.path,
                    logical_name=rec.logical_name,
                    message=f"Recorded artifact '{rec.path}' is missing on disk"
                ))
                missing_paths.append(rec.path)
                continue

            file_stat = file_path.stat()
            if rec.validation in (ValidationLevel.SIZE, ValidationLevel.SHA256) and rec.size_bytes is not None:
                if file_stat.st_size != rec.size_bytes:
                    issues.append(EvidenceIssue(
                        issue_type=EvidenceIssueType.SIZE_MISMATCH,
                        path=rec.path,
                        expected=str(rec.size_bytes),
                        actual=str(file_stat.st_size),
                        message=f"Size mismatch for recorded artifact '{rec.path}'"
                    ))
                    mismatched_paths.append(rec.path)

            if rec.validation == ValidationLevel.SHA256 and rec.sha256 is not None:
                disk_sha = StateStore._compute_sha256(file_path)
                if disk_sha != rec.sha256:
                    issues.append(EvidenceIssue(
                        issue_type=EvidenceIssueType.HASH_MISMATCH,
                        path=rec.path,
                        expected=rec.sha256,
                        actual=disk_sha,
                        message=f"Content SHA256 mismatch for recorded artifact '{rec.path}'"
                    ))
        # 3. Canonical structured approval verification (S07.5 Obs A)
        # .studio_approved marker is non-authoritative without valid canonical approval_metadata
        if state_enum == LifecycleState.REVIEW_APPROVED:
            approved_by = state.approval_metadata.get("approved_by") if state.approval_metadata else None
            approval_status = state.approval_metadata.get("status") if state.approval_metadata else None
            if not approved_by or approval_status == "INVALIDATED":
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.CORRUPTED,
                    path=".studio_approved",
                    logical_name="studio_approved",
                    expected="Structured approval metadata with non-empty approved_by",
                    actual=f"approved_by={approved_by!r}, status={approval_status!r}",
                    message=(
                        "REVIEW_APPROVED requires structured approval_metadata with valid approved_by; "
                        ".studio_approved marker alone is non-authoritative (S07.5 Obs A)."
                    ),
                ))
                if ".studio_approved" not in mismatched_paths:
                    mismatched_paths.append(".studio_approved")

        is_valid = len(issues) == 0
        recommended_action = None
        if not is_valid:
            first_path = issues[0].path
            recommended_action = f"restart_from_stage_creating_{first_path}"

        return EvidenceValidationResult(
            is_valid=is_valid,
            lifecycle_state=state_enum,
            required_count=len(required_items),
            verified_count=verified_count,
            issues=issues,
            missing_paths=missing_paths,
            mismatched_paths=mismatched_paths,
            recommended_action=recommended_action,
        )

    @classmethod
    def auto_record_stage_evidence(
        cls,
        state: ProjectState,
        project_dir: Path,
        target_state: LifecycleState,
        revision: Optional[int] = None,
    ) -> List[ArtifactRecord]:
        """
        Auto-records any missing required evidence files for target_state that exist on disk.
        """
        from scripts.core.state_store import StateStore

        required = cls.get_required_evidence(target_state)
        existing_paths = {r.path for r in state.artifact_records}
        auto_records: List[ArtifactRecord] = []

        for item in required:
            if item.path not in existing_paths:
                file_path = project_dir / item.path
                if file_path.exists():
                    auto_records.append(StateStore.create_artifact_record(
                        project_dir=project_dir,
                        rel_path=item.path,
                        validation=item.validation,
                        logical_name=item.logical_name,
                        stage=target_state.value,
                        produced_at_revision=revision,
                    ))
        return auto_records
