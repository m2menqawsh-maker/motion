"""
creative_governance/candidates/repository.py
===========================
Abstract repository interface and in-memory test double for TemplateCandidate (S28-07A).

Invariants:
- Never imports direct DB drivers or executes raw SQL in ai/* (ADR-004 DEC-01).
- Mandatory tenant isolation: every lookup, list, update, and delete enforces workspace_id.
- Optimistic Concurrency Control (CAS): update requires expected_revision.
"""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ai.contracts.creative.template_candidate import (
    CandidatePromotionRecord,
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateStatus,
    CandidateValidationReport,
    TemplateCandidate,
)
from creative_governance.candidates.errors import CandidateConflictError, CandidateNotFoundError


class TemplateCandidateRepository(ABC):
    """Authoritative storage boundary for TemplateCandidate persistence."""

    @abstractmethod
    def save_candidate(self, candidate: TemplateCandidate) -> TemplateCandidate:
        """Persists a new TemplateCandidate record."""
        raise NotImplementedError

    @abstractmethod
    def get_candidate(self, candidate_id: str, workspace_id: str) -> Optional[TemplateCandidate]:
        """Retrieves a single candidate scoped to the workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_candidates(
        self, workspace_id: str, project_id: Optional[str] = None
    ) -> List[TemplateCandidate]:
        """Lists candidates belonging to the workspace, optionally filtered by project_id."""
        raise NotImplementedError

    @abstractmethod
    def update_candidate_cas(
        self, candidate: TemplateCandidate, expected_revision: int
    ) -> TemplateCandidate:
        """
        Updates an existing candidate using Check-And-Swap (CAS) on expected_revision.
        Atomically increments revision to expected_revision + 1.
        Raises CandidateConflictError on revision mismatch.
        Raises CandidateNotFoundError if candidate does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def update_candidate_status_cas(
        self,
        candidate_id: str,
        workspace_id: str,
        status: CandidateStatus,
        expected_revision: int,
    ) -> TemplateCandidate:
        """
        Updates candidate status using CAS on expected_revision without bumping revision.
        Raises CandidateConflictError on revision mismatch.
        Raises CandidateNotFoundError if candidate does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_candidate(self, candidate_id: str, workspace_id: str) -> bool:
        """Deletes a candidate record scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def save_validation_report(
        self, report: CandidateValidationReport
    ) -> CandidateValidationReport:
        """Persists a CandidateValidationReport record."""
        raise NotImplementedError

    @abstractmethod
    def get_validation_report(
        self, validation_id: str, workspace_id: str
    ) -> Optional[CandidateValidationReport]:
        """Retrieves a single validation report scoped to the workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_validation_reports(
        self, candidate_id: str, workspace_id: str
    ) -> List[CandidateValidationReport]:
        """Lists validation reports for a candidate scoped to the workspace."""
        raise NotImplementedError

    @abstractmethod
    def save_review_bundle(self, bundle: CandidateReviewBundle) -> CandidateReviewBundle:
        """Persists a CandidateReviewBundle record."""
        raise NotImplementedError

    @abstractmethod
    def get_review_bundle(self, review_bundle_id: str, workspace_id: str) -> Optional[CandidateReviewBundle]:
        """Retrieves a single review bundle scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_review_bundles(self, candidate_id: str, workspace_id: str) -> List[CandidateReviewBundle]:
        """Lists review bundles for a candidate scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def save_review_decision(self, decision: CandidateReviewDecision) -> CandidateReviewDecision:
        """Persists an append-only CandidateReviewDecision record."""
        raise NotImplementedError

    @abstractmethod
    def get_review_decision(self, decision_id: str, workspace_id: str) -> Optional[CandidateReviewDecision]:
        """Retrieves a single review decision scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_review_decisions(self, candidate_id: str, workspace_id: str) -> List[CandidateReviewDecision]:
        """Lists review decisions for a candidate scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def get_active_decision_for_bundle(self, review_bundle_id: str, workspace_id: str) -> Optional[CandidateReviewDecision]:
        """Retrieves the active decision for a review bundle scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def save_promotion_record(self, record: CandidatePromotionRecord) -> CandidatePromotionRecord:
        """Persists a CandidatePromotionRecord."""
        raise NotImplementedError

    @abstractmethod
    def get_promotion_record(self, promotion_id: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        """Retrieves a single promotion record scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def get_promotion_record_by_candidate(self, candidate_id: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        """Retrieves active promotion record for a candidate scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def get_promotion_record_by_manifest(self, manifest_hash: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        """Retrieves promotion record matching manifest hash scoped to workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_promotion_records(self, workspace_id: str, candidate_id: Optional[str] = None) -> List[CandidatePromotionRecord]:
        """Lists promotion records scoped to workspace."""
        raise NotImplementedError



class InMemoryTemplateCandidateRepository(TemplateCandidateRepository):
    """
    Hermetic, in-memory implementation of TemplateCandidateRepository
    for unit testing and mock scenarios.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Key: (workspace_id, candidate_id) -> TemplateCandidate
        self._candidates: Dict[tuple[str, str], TemplateCandidate] = {}
        # Key: (workspace_id, validation_id) -> CandidateValidationReport
        self._reports: Dict[tuple[str, str], CandidateValidationReport] = {}
        # Key: (workspace_id, review_bundle_id) -> CandidateReviewBundle
        self._bundles: Dict[tuple[str, str], CandidateReviewBundle] = {}
        # Key: (workspace_id, decision_id) -> CandidateReviewDecision
        self._decisions: Dict[tuple[str, str], CandidateReviewDecision] = {}
        # Key: (workspace_id, promotion_id) -> CandidatePromotionRecord
        self._promotions: Dict[tuple[str, str], CandidatePromotionRecord] = {}

    def save_candidate(self, candidate: TemplateCandidate) -> TemplateCandidate:
        with self._lock:
            key = (candidate.workspace_id, candidate.candidate_id)
            if key in self._candidates:
                raise CandidateConflictError(
                    f"Candidate '{candidate.candidate_id}' already exists in workspace '{candidate.workspace_id}'"
                )
            saved = copy.deepcopy(candidate)
            self._candidates[key] = saved
            return copy.deepcopy(saved)

    def get_candidate(self, candidate_id: str, workspace_id: str) -> Optional[TemplateCandidate]:
        with self._lock:
            key = (workspace_id, candidate_id)
            cand = self._candidates.get(key)
            return copy.deepcopy(cand) if cand else None

    def list_candidates(
        self, workspace_id: str, project_id: Optional[str] = None
    ) -> List[TemplateCandidate]:
        with self._lock:
            res: List[TemplateCandidate] = []
            for (ws, _), cand in self._candidates.items():
                if ws == workspace_id:
                    if project_id is None or cand.source_project_id == project_id:
                        res.append(copy.deepcopy(cand))
            return sorted(res, key=lambda c: c.created_at)

    def update_candidate_cas(
        self, candidate: TemplateCandidate, expected_revision: int
    ) -> TemplateCandidate:
        with self._lock:
            key = (candidate.workspace_id, candidate.candidate_id)
            existing = self._candidates.get(key)
            if not existing:
                raise CandidateNotFoundError(
                    f"Candidate '{candidate.candidate_id}' not found in workspace '{candidate.workspace_id}'"
                )

            if existing.revision != expected_revision:
                raise CandidateConflictError(
                    f"Stale revision: expected {expected_revision}, but current revision is {existing.revision}"
                )

            new_revision = expected_revision + 1
            updated = candidate.model_copy(update={"revision": new_revision})
            self._candidates[key] = copy.deepcopy(updated)
            return copy.deepcopy(updated)

    def update_candidate_status_cas(
        self,
        candidate_id: str,
        workspace_id: str,
        status: CandidateStatus,
        expected_revision: int,
    ) -> TemplateCandidate:
        with self._lock:
            key = (workspace_id, candidate_id)
            existing = self._candidates.get(key)
            if not existing:
                raise CandidateNotFoundError(
                    f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'"
                )

            if existing.revision != expected_revision:
                raise CandidateConflictError(
                    f"Stale revision: expected {expected_revision}, but current revision is {existing.revision}"
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            updated = existing.model_copy(update={"status": status, "updated_at": now_iso})
            self._candidates[key] = copy.deepcopy(updated)
            return copy.deepcopy(updated)

    def delete_candidate(self, candidate_id: str, workspace_id: str) -> bool:
        with self._lock:
            key = (workspace_id, candidate_id)
            if key in self._candidates:
                del self._candidates[key]
                return True
            return False

    def save_validation_report(
        self, report: CandidateValidationReport
    ) -> CandidateValidationReport:
        with self._lock:
            key = (report.workspace_id, report.validation_id)
            saved = copy.deepcopy(report)
            self._reports[key] = saved
            return copy.deepcopy(saved)

    def get_validation_report(
        self, validation_id: str, workspace_id: str
    ) -> Optional[CandidateValidationReport]:
        with self._lock:
            key = (workspace_id, validation_id)
            report = self._reports.get(key)
            return copy.deepcopy(report) if report else None

    def list_validation_reports(
        self, candidate_id: str, workspace_id: str
    ) -> List[CandidateValidationReport]:
        with self._lock:
            res: List[CandidateValidationReport] = []
            for (ws, _), rep in self._reports.items():
                if ws == workspace_id and rep.candidate_id == candidate_id:
                    res.append(copy.deepcopy(rep))
            return sorted(res, key=lambda r: r.completed_at)

    def save_review_bundle(self, bundle: CandidateReviewBundle) -> CandidateReviewBundle:
        with self._lock:
            key = (bundle.workspace_id, bundle.review_bundle_id)
            if key in self._bundles:
                raise CandidateConflictError(
                    f"Review bundle '{bundle.review_bundle_id}' already exists in workspace '{bundle.workspace_id}'"
                )
            saved = copy.deepcopy(bundle)
            self._bundles[key] = saved
            return copy.deepcopy(saved)

    def get_review_bundle(self, review_bundle_id: str, workspace_id: str) -> Optional[CandidateReviewBundle]:
        with self._lock:
            key = (workspace_id, review_bundle_id)
            bundle = self._bundles.get(key)
            return copy.deepcopy(bundle) if bundle else None

    def list_review_bundles(self, candidate_id: str, workspace_id: str) -> List[CandidateReviewBundle]:
        with self._lock:
            res: List[CandidateReviewBundle] = []
            for (ws, _), b in self._bundles.items():
                if ws == workspace_id and b.candidate_id == candidate_id:
                    res.append(copy.deepcopy(b))
            return sorted(res, key=lambda b: b.created_at)

    def save_review_decision(self, decision: CandidateReviewDecision) -> CandidateReviewDecision:
        with self._lock:
            key = (decision.workspace_id, decision.decision_id)
            if key in self._decisions:
                raise CandidateConflictError(
                    f"Review decision '{decision.decision_id}' already exists in workspace '{decision.workspace_id}'"
                )
            # Append-only check: cannot have conflicting active decisions for same bundle
            for (ws, _), d in self._decisions.items():
                if ws == decision.workspace_id and d.review_bundle_id == decision.review_bundle_id:
                    if d.decision != decision.decision:
                        raise CandidateConflictError(
                            f"Conflicting decision already exists for review bundle '{decision.review_bundle_id}' (existing: {d.decision}, proposed: {decision.decision})"
                        )
            saved = copy.deepcopy(decision)
            self._decisions[key] = saved
            return copy.deepcopy(saved)

    def get_review_decision(self, decision_id: str, workspace_id: str) -> Optional[CandidateReviewDecision]:
        with self._lock:
            key = (workspace_id, decision_id)
            dec = self._decisions.get(key)
            return copy.deepcopy(dec) if dec else None

    def list_review_decisions(self, candidate_id: str, workspace_id: str) -> List[CandidateReviewDecision]:
        with self._lock:
            res: List[CandidateReviewDecision] = []
            for (ws, _), d in self._decisions.items():
                if ws == workspace_id and d.candidate_id == candidate_id:
                    res.append(copy.deepcopy(d))
            return sorted(res, key=lambda d: d.decided_at)

    def get_active_decision_for_bundle(self, review_bundle_id: str, workspace_id: str) -> Optional[CandidateReviewDecision]:
        with self._lock:
            for (ws, _), d in self._decisions.items():
                if ws == workspace_id and d.review_bundle_id == review_bundle_id:
                    return copy.deepcopy(d)
            return None

    def save_promotion_record(self, record: CandidatePromotionRecord) -> CandidatePromotionRecord:
        with self._lock:
            key = (record.workspace_id, record.promotion_id)
            saved = copy.deepcopy(record)
            self._promotions[key] = saved
            return copy.deepcopy(saved)

    def get_promotion_record(self, promotion_id: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        with self._lock:
            key = (workspace_id, promotion_id)
            rec = self._promotions.get(key)
            return copy.deepcopy(rec) if rec else None

    def get_promotion_record_by_candidate(self, candidate_id: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        with self._lock:
            matches = [
                rec for (ws, _), rec in self._promotions.items()
                if ws == workspace_id and rec.candidate_id == candidate_id
            ]
            if not matches:
                return None
            matches.sort(key=lambda r: str(r.started_at), reverse=True)
            return copy.deepcopy(matches[0])

    def get_promotion_record_by_manifest(self, manifest_hash: str, workspace_id: str) -> Optional[CandidatePromotionRecord]:
        with self._lock:
            for (ws, _), rec in self._promotions.items():
                if ws == workspace_id and rec.promotion_manifest_hash == manifest_hash:
                    return copy.deepcopy(rec)
            return None

    def list_promotion_records(self, workspace_id: str, candidate_id: Optional[str] = None) -> List[CandidatePromotionRecord]:
        with self._lock:
            res: List[CandidatePromotionRecord] = []
            for (ws, _), rec in self._promotions.items():
                if ws == workspace_id:
                    if candidate_id is None or rec.candidate_id == candidate_id:
                        res.append(copy.deepcopy(rec))
            return sorted(res, key=lambda r: str(r.started_at))


