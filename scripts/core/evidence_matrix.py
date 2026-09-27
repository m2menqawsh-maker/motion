"""
Required Evidence Matrix & Verification Authority (S06).

Central Authority for required and cumulative evidence per lifecycle state.
Single source of truth used by LifecycleService, RecoveryEngine, and Pipeline.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
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
        validation=ValidationLevel.EXISTS,
        mandatory=True,
        description="Probe QC verification report",
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
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.FINAL_QC_PASSED: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.COMPLETE: [
        REQUIRED_EVIDENCE_ITEMS["manifest"],
        REQUIRED_EVIDENCE_ITEMS["plan"],
        REQUIRED_EVIDENCE_ITEMS["blueprint"],
        REQUIRED_EVIDENCE_ITEMS["rendered_video"],
    ],
    LifecycleState.FAILED: [],
    LifecycleState.CANCELLED: [],
}


def merge_artifact_records(
    existing: List[ArtifactRecord],
    incoming: List[ArtifactRecord],
) -> List[ArtifactRecord]:
    """
    Deterministically merges incoming artifact records into existing records.
    - If a record with the same relative path already exists in existing:
      it is replaced in-place by the incoming record (preserving position).
    - If incoming has a new path:
      it is appended to the list.
    - Previous records with distinct paths are ALWAYS preserved.
    """
    if not existing:
        return list(incoming)
    if not incoming:
        return list(existing)

    result = list(existing)
    path_to_idx = {rec.path: i for i, rec in enumerate(result)}

    for inc in incoming:
        if inc.path in path_to_idx:
            result[path_to_idx[inc.path]] = inc
        else:
            path_to_idx[inc.path] = len(result)
            result.append(inc)

    return result


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

        records_by_path = {rec.path: rec for rec in state.artifact_records}

        # 1. Verify all required items for the current lifecycle state
        for item in required_items:
            file_path = pdir / item.path
            rec = records_by_path.get(item.path)

            # Check presence in records
            if rec is None:
                issues.append(EvidenceIssue(
                    issue_type=EvidenceIssueType.MISSING_RECORD,
                    path=item.path,
                    logical_name=item.logical_name,
                    message=f"Required evidence '{item.path}' is missing from artifact_records for state {state_enum.value}"
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
                    mismatched_paths.append(rec.path)

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
