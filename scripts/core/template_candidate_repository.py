"""
scripts/core/template_candidate_repository.py
=============================================
SQL-backed persistent implementation of TemplateCandidateRepository (S28-07A).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ (approved persistence layer) to satisfy S27.0 / S28 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, PostgreSQL, and transactions.
- Implements atomic CAS revision check-and-swap, multi-tenant isolation, and durable persistence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from creative_governance.candidates.errors import CandidateConflictError, CandidateNotFoundError
from creative_governance.candidates.repository import TemplateCandidateRepository
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier
from ai.contracts.creative.template_candidate import (
    CandidatePromotionRecord,
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateStatus,
    CandidateValidationReport,
    PromotionRecordStatus,
    TemplateCandidate,
)
from scripts.core.database import DatabaseEngine, get_database_engine

TEMPLATE_CANDIDATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS template_candidates (
    candidate_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_project_id TEXT NOT NULL,
    creator_ai_run_id TEXT,
    creative_plan_reference TEXT NOT NULL,
    creative_tier_decision_reference TEXT NOT NULL,
    why_reuse_failed TEXT NOT NULL,
    why_compose_failed TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    author TEXT NOT NULL,
    proposed_category TEXT NOT NULL,
    proposed_tags_json TEXT NOT NULL DEFAULT '[]',
    target_tier TEXT NOT NULL DEFAULT 'REUSE',
    source_code_path TEXT,
    template_schema_json TEXT NOT NULL DEFAULT '{}',
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    fixtures_json TEXT NOT NULL DEFAULT '{}',
    provenance_json TEXT NOT NULL DEFAULT '{}',
    storage_keys_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_template_cand_ws_proj ON template_candidates(workspace_id, source_project_id);
CREATE INDEX IF NOT EXISTS idx_template_cand_ws_status ON template_candidates(workspace_id, status);

CREATE TABLE IF NOT EXISTS candidate_validation_reports (
    validation_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    candidate_content_hash TEXT NOT NULL,
    candidate_revision INTEGER NOT NULL DEFAULT 1,
    phase TEXT NOT NULL DEFAULT 'STATIC',
    policy_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    gates_json TEXT NOT NULL DEFAULT '[]',
    overall_result TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '{}',
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_val_ws_cand ON candidate_validation_reports(workspace_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_cand_val_ws_cand_hash ON candidate_validation_reports(workspace_id, candidate_id, candidate_content_hash);

CREATE TABLE IF NOT EXISTS candidate_review_bundles (
    review_bundle_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    candidate_content_hash TEXT NOT NULL,
    candidate_revision INTEGER NOT NULL,
    static_validation_id TEXT NOT NULL,
    runtime_validation_id TEXT NOT NULL,
    static_report_hash TEXT NOT NULL,
    runtime_report_hash TEXT NOT NULL,
    render_evidence_refs_json TEXT NOT NULL DEFAULT '{}',
    representative_frame_refs_json TEXT NOT NULL DEFAULT '[]',
    probe_report_ref TEXT,
    qc_report_ref TEXT,
    source_code_hash TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    fixtures_hash TEXT NOT NULL,
    review_policy_version TEXT NOT NULL,
    review_bundle_hash TEXT NOT NULL,
    bundle_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_rbd_ws_cand ON candidate_review_bundles(workspace_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_cand_rbd_ws_cand_hash ON candidate_review_bundles(workspace_id, candidate_id, candidate_content_hash);

CREATE TABLE IF NOT EXISTS candidate_review_decisions (
    decision_id TEXT PRIMARY KEY,
    review_bundle_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer_principal_id TEXT NOT NULL,
    reviewer_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    candidate_content_hash TEXT NOT NULL,
    candidate_revision INTEGER NOT NULL,
    review_bundle_hash TEXT NOT NULL,
    static_validation_report_hash TEXT NOT NULL,
    runtime_validation_report_hash TEXT NOT NULL,
    render_evidence_ref TEXT,
    qc_report_ref TEXT,
    decision_revision INTEGER NOT NULL DEFAULT 1,
    decision_json TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_rdec_ws_cand ON candidate_review_decisions(workspace_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_cand_rdec_bundle ON candidate_review_decisions(workspace_id, review_bundle_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cand_rdec_bundle_rev ON candidate_review_decisions(workspace_id, review_bundle_id, decision_revision);
CREATE TABLE IF NOT EXISTS candidate_promotion_records (
    promotion_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    promotion_manifest_hash TEXT NOT NULL,
    approval_decision_id TEXT NOT NULL,
    review_bundle_hash TEXT NOT NULL,
    target_template_id TEXT NOT NULL,
    target_template_version TEXT NOT NULL,
    pre_publish_registry_hash TEXT NOT NULL,
    post_publish_registry_hash TEXT NOT NULL,
    published_artifact_hashes_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    promoted_by_principal_id TEXT,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_prom_ws_cand ON candidate_promotion_records(workspace_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_cand_prom_manifest ON candidate_promotion_records(workspace_id, promotion_manifest_hash);
CREATE INDEX IF NOT EXISTS idx_cand_prom_target ON candidate_promotion_records(target_template_id);
"""


def _format_dt(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


class SqlTemplateCandidateRepository(TemplateCandidateRepository):
    """
    SQL-backed durable repository for TemplateCandidate records.
    Provides strict workspace scoping and atomic CAS revision increments.
    """

    def __init__(self, engine: Optional[DatabaseEngine] = None) -> None:
        self.engine = engine or get_database_engine()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.engine.transaction("IMMEDIATE") as conn:
            for statement in TEMPLATE_CANDIDATE_SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    def _row_to_model(self, row: Any) -> TemplateCandidate:
        candidate_id = row[0]
        workspace_id = row[1]
        source_project_id = row[2]
        creator_ai_run_id = row[3]
        creative_plan_reference = row[4]
        creative_tier_decision_reference = row[5]
        why_reuse_failed = row[6]
        why_compose_failed = row[7]
        content_hash = row[8]
        revision = row[9]
        status = row[10]
        name = row[11]
        description = row[12]
        author = row[13]
        proposed_category = row[14]
        proposed_tags = json.loads(row[15] or "[]")
        target_tier = CreativeTier(row[16]) if row[16] else CreativeTier.REUSE
        source_code_path = row[17]
        template_schema = json.loads(row[18] or "{}")
        dependencies = json.loads(row[19] or "[]")
        fixtures = json.loads(row[20] or "{}")
        prov_dict = json.loads(row[21] or "{}")
        required_provenance = ProvenanceRecord.model_validate(prov_dict) if prov_dict else None
        storage_keys = json.loads(row[22] or "{}")
        created_at = row[23]
        updated_at = row[24]

        return TemplateCandidate(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            source_project_id=source_project_id,
            origin_project_id=source_project_id,
            creator_ai_run_id=creator_ai_run_id,
            creative_plan_reference=creative_plan_reference,
            creative_tier_decision_reference=creative_tier_decision_reference,
            why_reuse_failed=why_reuse_failed,
            why_compose_failed=why_compose_failed,
            source_code="",  # Resolved from StorageService
            source_code_path=source_code_path,
            template_schema=template_schema,
            dependencies=dependencies,
            fixtures=fixtures,
            content_hash=content_hash,
            revision=revision,
            status=CandidateStatus(status),
            name=name,
            description=description,
            author=author,
            proposed_category=proposed_category,
            proposed_tags=proposed_tags,
            target_tier=target_tier,
            required_provenance=required_provenance,
            storage_keys=storage_keys,
            created_at=created_at,
            updated_at=updated_at,
        )

    def save_candidate(self, candidate: TemplateCandidate) -> TemplateCandidate:
        with self.engine.transaction() as conn:
            # Check for conflict
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM template_candidates WHERE candidate_id = ?",
                (candidate.candidate_id,),
            )
            if cur.fetchone():
                raise CandidateConflictError(
                    f"Candidate '{candidate.candidate_id}' already exists."
                )

            cur.execute(
                """
                INSERT INTO template_candidates (
                    candidate_id,
                    workspace_id,
                    source_project_id,
                    creator_ai_run_id,
                    creative_plan_reference,
                    creative_tier_decision_reference,
                    why_reuse_failed,
                    why_compose_failed,
                    content_hash,
                    revision,
                    status,
                    name,
                    description,
                    author,
                    proposed_category,
                    proposed_tags_json,
                    target_tier,
                    source_code_path,
                    template_schema_json,
                    dependencies_json,
                    fixtures_json,
                    provenance_json,
                    storage_keys_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.candidate_id,
                    candidate.workspace_id,
                    candidate.source_project_id,
                    candidate.creator_ai_run_id,
                    candidate.creative_plan_reference,
                    candidate.creative_tier_decision_reference,
                    candidate.why_reuse_failed,
                    candidate.why_compose_failed,
                    candidate.content_hash,
                    candidate.revision,
                    candidate.status.value,
                    candidate.name,
                    candidate.description,
                    candidate.author,
                    candidate.proposed_category,
                    json.dumps(candidate.proposed_tags),
                    candidate.target_tier.value,
                    candidate.source_code_path,
                    json.dumps(candidate.template_schema),
                    json.dumps(candidate.dependencies),
                    json.dumps(candidate.fixtures),
                    json.dumps(candidate.required_provenance.model_dump(mode="json")) if candidate.required_provenance else "{}",
                    json.dumps(candidate.storage_keys),
                    _format_dt(candidate.created_at),
                    _format_dt(candidate.updated_at),
                ),
            )
            return candidate

    def get_candidate(self, candidate_id: str, workspace_id: str) -> Optional[TemplateCandidate]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    candidate_id, workspace_id, source_project_id, creator_ai_run_id,
                    creative_plan_reference, creative_tier_decision_reference,
                    why_reuse_failed, why_compose_failed, content_hash, revision,
                    status, name, description, author, proposed_category,
                    proposed_tags_json, target_tier, source_code_path,
                    template_schema_json, dependencies_json, fixtures_json,
                    provenance_json, storage_keys_json, created_at, updated_at
                FROM template_candidates
                WHERE candidate_id = ? AND workspace_id = ?
                """,
                (candidate_id, workspace_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_model(row)

    def list_candidates(
        self, workspace_id: str, project_id: Optional[str] = None
    ) -> List[TemplateCandidate]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            if project_id:
                cur.execute(
                    """
                    SELECT
                        candidate_id, workspace_id, source_project_id, creator_ai_run_id,
                        creative_plan_reference, creative_tier_decision_reference,
                        why_reuse_failed, why_compose_failed, content_hash, revision,
                        status, name, description, author, proposed_category,
                        proposed_tags_json, target_tier, source_code_path,
                        template_schema_json, dependencies_json, fixtures_json,
                        provenance_json, storage_keys_json, created_at, updated_at
                    FROM template_candidates
                    WHERE workspace_id = ? AND source_project_id = ?
                    ORDER BY created_at ASC
                    """,
                    (workspace_id, project_id),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        candidate_id, workspace_id, source_project_id, creator_ai_run_id,
                        creative_plan_reference, creative_tier_decision_reference,
                        why_reuse_failed, why_compose_failed, content_hash, revision,
                        status, name, description, author, proposed_category,
                        proposed_tags_json, target_tier, source_code_path,
                        template_schema_json, dependencies_json, fixtures_json,
                        provenance_json, storage_keys_json, created_at, updated_at
                    FROM template_candidates
                    WHERE workspace_id = ?
                    ORDER BY created_at ASC
                    """,
                    (workspace_id,),
                )
            rows = cur.fetchall()
            return [self._row_to_model(r) for r in rows]

    def update_candidate_cas(
        self, candidate: TemplateCandidate, expected_revision: int
    ) -> TemplateCandidate:
        with self.engine.transaction() as conn:
            cur = conn.cursor()

            # Attempt atomic update using expected_revision
            new_revision = expected_revision + 1
            cur.execute(
                """
                UPDATE template_candidates
                SET revision = ?,
                    status = ?,
                    content_hash = ?,
                    why_reuse_failed = ?,
                    why_compose_failed = ?,
                    name = ?,
                    description = ?,
                    proposed_category = ?,
                    proposed_tags_json = ?,
                    template_schema_json = ?,
                    dependencies_json = ?,
                    fixtures_json = ?,
                    source_code_path = ?,
                    storage_keys_json = ?,
                    updated_at = ?
                WHERE candidate_id = ? AND workspace_id = ? AND revision = ?
                """,
                (
                    new_revision,
                    candidate.status.value,
                    candidate.content_hash,
                    candidate.why_reuse_failed,
                    candidate.why_compose_failed,
                    candidate.name,
                    candidate.description,
                    candidate.proposed_category,
                    json.dumps(candidate.proposed_tags),
                    json.dumps(candidate.template_schema),
                    json.dumps(candidate.dependencies),
                    json.dumps(candidate.fixtures),
                    candidate.source_code_path,
                    json.dumps(candidate.storage_keys),
                    _format_dt(candidate.updated_at),
                    candidate.candidate_id,
                    candidate.workspace_id,
                    expected_revision,
                ),
            )

            if cur.rowcount == 0:
                # Disambiguate not found vs revision mismatch
                cur.execute(
                    "SELECT revision FROM template_candidates WHERE candidate_id = ? AND workspace_id = ?",
                    (candidate.candidate_id, candidate.workspace_id),
                )
                row = cur.fetchone()
                if not row:
                    raise CandidateNotFoundError(
                        f"Candidate '{candidate.candidate_id}' not found in workspace '{candidate.workspace_id}'."
                    )
                current_rev = row[0]
                raise CandidateConflictError(
                    f"Stale revision: expected {expected_revision}, but current revision is {current_rev}."
                )

            return candidate.model_copy(update={"revision": new_revision})

    def update_candidate_status_cas(
        self,
        candidate_id: str,
        workspace_id: str,
        status: CandidateStatus,
        expected_revision: int,
    ) -> TemplateCandidate:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            now = _format_dt(datetime.now(timezone.utc))

            cur.execute(
                """
                UPDATE template_candidates
                SET status = ?, updated_at = ?
                WHERE candidate_id = ? AND workspace_id = ? AND revision = ?
                """,
                (status.value, now, candidate_id, workspace_id, expected_revision),
            )

            if cur.rowcount == 0:
                cur.execute(
                    "SELECT revision FROM template_candidates WHERE candidate_id = ? AND workspace_id = ?",
                    (candidate_id, workspace_id),
                )
                row = cur.fetchone()
                if not row:
                    raise CandidateNotFoundError(
                        f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'."
                    )
                current_rev = row[0]
                raise CandidateConflictError(
                    f"Stale revision: expected {expected_revision}, but current revision is {current_rev}."
                )

            # Return updated model using current transaction cursor
            cur.execute(
                """
                SELECT
                    candidate_id, workspace_id, source_project_id, creator_ai_run_id,
                    creative_plan_reference, creative_tier_decision_reference,
                    why_reuse_failed, why_compose_failed, content_hash, revision,
                    status, name, description, author, proposed_category,
                    proposed_tags_json, target_tier, source_code_path,
                    template_schema_json, dependencies_json, fixtures_json,
                    provenance_json, storage_keys_json, created_at, updated_at
                FROM template_candidates
                WHERE candidate_id = ? AND workspace_id = ?
                """,
                (candidate_id, workspace_id),
            )
            row = cur.fetchone()
            return self._row_to_model(row)

    def delete_candidate(self, candidate_id: str, workspace_id: str) -> bool:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM template_candidates WHERE candidate_id = ? AND workspace_id = ?",
                (candidate_id, workspace_id),
            )
            return cur.rowcount > 0

    def save_validation_report(
        self, report: CandidateValidationReport
    ) -> CandidateValidationReport:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            gates_json = json.dumps([g.model_dump(mode="json") for g in report.gates])
            evidence_json = json.dumps(report.evidence_refs)
            report_json = report.model_dump_json()
            now = _format_dt(datetime.now(timezone.utc))

            cur.execute(
                """
                INSERT INTO candidate_validation_reports (
                    validation_id, candidate_id, workspace_id, candidate_content_hash,
                    candidate_revision, phase, policy_version, started_at, completed_at,
                    gates_json, overall_result, evidence_refs_json, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(validation_id) DO UPDATE SET
                    gates_json = excluded.gates_json,
                    overall_result = excluded.overall_result,
                    evidence_refs_json = excluded.evidence_refs_json,
                    report_json = excluded.report_json,
                    completed_at = excluded.completed_at
                """,
                (
                    report.validation_id,
                    report.candidate_id,
                    report.workspace_id,
                    report.candidate_content_hash,
                    report.candidate_revision,
                    report.phase.value if hasattr(report.phase, "value") else str(report.phase),
                    report.policy_version,
                    _format_dt(report.started_at),
                    _format_dt(report.completed_at),
                    gates_json,
                    report.overall_result.value if hasattr(report.overall_result, "value") else str(report.overall_result),
                    evidence_json,
                    report_json,
                    now,
                ),
            )
            return report

    def get_validation_report(
        self, validation_id: str, workspace_id: str
    ) -> Optional[CandidateValidationReport]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT report_json FROM candidate_validation_reports WHERE validation_id = ? AND workspace_id = ?",
                (validation_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidateValidationReport.model_validate_json(row[0])

    def list_validation_reports(
        self, candidate_id: str, workspace_id: str
    ) -> List[CandidateValidationReport]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT report_json FROM candidate_validation_reports WHERE candidate_id = ? AND workspace_id = ? ORDER BY completed_at ASC",
                (candidate_id, workspace_id),
            )
            rows = cur.fetchall()
            return [CandidateValidationReport.model_validate_json(r[0]) for r in rows if r[0]]

    def save_review_bundle(self, bundle: CandidateReviewBundle) -> CandidateReviewBundle:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM candidate_review_bundles WHERE review_bundle_id = ?",
                (bundle.review_bundle_id,),
            )
            if cur.fetchone():
                raise CandidateConflictError(
                    f"Review bundle '{bundle.review_bundle_id}' already exists."
                )

            now = _format_dt(datetime.now(timezone.utc))
            cur.execute(
                """
                INSERT INTO candidate_review_bundles (
                    review_bundle_id, candidate_id, workspace_id, candidate_content_hash,
                    candidate_revision, static_validation_id, runtime_validation_id,
                    static_report_hash, runtime_report_hash, render_evidence_refs_json,
                    representative_frame_refs_json, probe_report_ref, qc_report_ref,
                    source_code_hash, schema_hash, fixtures_hash, review_policy_version,
                    review_bundle_hash, bundle_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bundle.review_bundle_id,
                    bundle.candidate_id,
                    bundle.workspace_id,
                    bundle.candidate_content_hash,
                    bundle.candidate_revision,
                    bundle.static_validation_id,
                    bundle.runtime_validation_id,
                    bundle.static_report_hash,
                    bundle.runtime_report_hash,
                    json.dumps(bundle.render_evidence_refs),
                    json.dumps(bundle.representative_frame_refs),
                    bundle.probe_report_ref,
                    bundle.qc_report_ref,
                    bundle.source_code_hash,
                    bundle.schema_hash,
                    bundle.fixtures_hash,
                    bundle.review_policy_version,
                    bundle.review_bundle_hash,
                    bundle.model_dump_json(),
                    now,
                ),
            )
            return bundle

    def get_review_bundle(
        self, review_bundle_id: str, workspace_id: str
    ) -> Optional[CandidateReviewBundle]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT bundle_json FROM candidate_review_bundles WHERE review_bundle_id = ? AND workspace_id = ?",
                (review_bundle_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidateReviewBundle.model_validate_json(row[0])

    def list_review_bundles(
        self, candidate_id: str, workspace_id: str
    ) -> List[CandidateReviewBundle]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT bundle_json FROM candidate_review_bundles WHERE candidate_id = ? AND workspace_id = ? ORDER BY created_at ASC",
                (candidate_id, workspace_id),
            )
            rows = cur.fetchall()
            return [CandidateReviewBundle.model_validate_json(r[0]) for r in rows if r[0]]

    def save_review_decision(
        self, decision: CandidateReviewDecision
    ) -> CandidateReviewDecision:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM candidate_review_decisions WHERE decision_id = ?",
                (decision.decision_id,),
            )
            if cur.fetchone():
                raise CandidateConflictError(
                    f"Review decision '{decision.decision_id}' already exists."
                )

            # Conflict protection: cannot have conflicting decisions for same review bundle
            cur.execute(
                "SELECT decision FROM candidate_review_decisions WHERE review_bundle_id = ? AND workspace_id = ?",
                (decision.review_bundle_id, decision.workspace_id),
            )
            existing = cur.fetchone()
            if existing and existing[0] != decision.decision.value:
                raise CandidateConflictError(
                    f"Conflicting decision already exists for review bundle '{decision.review_bundle_id}' (existing: {existing[0]}, proposed: {decision.decision.value})"
                )

            now = _format_dt(datetime.now(timezone.utc))
            cur.execute(
                """
                INSERT INTO candidate_review_decisions (
                    decision_id, review_bundle_id, candidate_id, workspace_id,
                    decision, reviewer_principal_id, reviewer_role, reason,
                    candidate_content_hash, candidate_revision, review_bundle_hash,
                    static_validation_report_hash, runtime_validation_report_hash,
                    render_evidence_ref, qc_report_ref, decision_revision,
                    decision_json, decided_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.review_bundle_id,
                    decision.candidate_id,
                    decision.workspace_id,
                    decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision),
                    decision.reviewer_principal_id,
                    decision.reviewer_role,
                    decision.reason,
                    decision.candidate_content_hash,
                    decision.candidate_revision,
                    decision.review_bundle_hash,
                    decision.static_validation_report_hash,
                    decision.runtime_validation_report_hash,
                    decision.render_evidence_ref,
                    decision.qc_report_ref,
                    decision.decision_revision,
                    decision.model_dump_json(),
                    _format_dt(decision.decided_at),
                    now,
                ),
            )
            return decision

    def get_review_decision(
        self, decision_id: str, workspace_id: str
    ) -> Optional[CandidateReviewDecision]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT decision_json FROM candidate_review_decisions WHERE decision_id = ? AND workspace_id = ?",
                (decision_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidateReviewDecision.model_validate_json(row[0])

    def list_review_decisions(
        self, candidate_id: str, workspace_id: str
    ) -> List[CandidateReviewDecision]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT decision_json FROM candidate_review_decisions WHERE candidate_id = ? AND workspace_id = ? ORDER BY decided_at ASC",
                (candidate_id, workspace_id),
            )
            rows = cur.fetchall()
            return [CandidateReviewDecision.model_validate_json(r[0]) for r in rows if r[0]]

    def get_active_decision_for_bundle(
        self, review_bundle_id: str, workspace_id: str
    ) -> Optional[CandidateReviewDecision]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT decision_json FROM candidate_review_decisions WHERE review_bundle_id = ? AND workspace_id = ? ORDER BY decided_at DESC LIMIT 1",
                (review_bundle_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidateReviewDecision.model_validate_json(row[0])

    def save_promotion_record(
        self, record: CandidatePromotionRecord
    ) -> CandidatePromotionRecord:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO candidate_promotion_records (
                    promotion_id,
                    candidate_id,
                    workspace_id,
                    promotion_manifest_hash,
                    approval_decision_id,
                    review_bundle_hash,
                    target_template_id,
                    target_template_version,
                    pre_publish_registry_hash,
                    post_publish_registry_hash,
                    published_artifact_hashes_json,
                    status,
                    promoted_by_principal_id,
                    error_message,
                    started_at,
                    completed_at,
                    record_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(promotion_id) DO UPDATE SET
                    status = excluded.status,
                    post_publish_registry_hash = excluded.post_publish_registry_hash,
                    published_artifact_hashes_json = excluded.published_artifact_hashes_json,
                    error_message = excluded.error_message,
                    completed_at = excluded.completed_at,
                    record_json = excluded.record_json
                """,
                (
                    record.promotion_id,
                    record.candidate_id,
                    record.workspace_id,
                    record.promotion_manifest_hash,
                    record.approval_decision_id,
                    record.review_bundle_hash,
                    record.target_template_id,
                    record.target_template_version,
                    record.pre_publish_registry_hash,
                    record.post_publish_registry_hash,
                    json.dumps(record.published_artifact_hashes),
                    record.status.value,
                    record.promoted_by_principal_id,
                    record.error_message,
                    _format_dt(record.started_at),
                    _format_dt(record.completed_at) if record.completed_at else None,
                    record.model_dump_json(),
                    _format_dt(record.started_at),
                ),
            )
            return record

    def get_promotion_record(
        self, promotion_id: str, workspace_id: str
    ) -> Optional[CandidatePromotionRecord]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT record_json FROM candidate_promotion_records WHERE promotion_id = ? AND workspace_id = ?",
                (promotion_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidatePromotionRecord.model_validate_json(row[0])

    def get_promotion_record_by_candidate(
        self, candidate_id: str, workspace_id: str
    ) -> Optional[CandidatePromotionRecord]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT record_json FROM candidate_promotion_records WHERE candidate_id = ? AND workspace_id = ? ORDER BY started_at DESC LIMIT 1",
                (candidate_id, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidatePromotionRecord.model_validate_json(row[0])

    def get_promotion_record_by_manifest(
        self, manifest_hash: str, workspace_id: str
    ) -> Optional[CandidatePromotionRecord]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT record_json FROM candidate_promotion_records WHERE promotion_manifest_hash = ? AND workspace_id = ? ORDER BY started_at DESC LIMIT 1",
                (manifest_hash, workspace_id),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return CandidatePromotionRecord.model_validate_json(row[0])

    def list_promotion_records(
        self, workspace_id: str, candidate_id: Optional[str] = None
    ) -> List[CandidatePromotionRecord]:
        with self.engine.transaction() as conn:
            cur = conn.cursor()
            if candidate_id:
                cur.execute(
                    "SELECT record_json FROM candidate_promotion_records WHERE workspace_id = ? AND candidate_id = ? ORDER BY started_at ASC",
                    (workspace_id, candidate_id),
                )
            else:
                cur.execute(
                    "SELECT record_json FROM candidate_promotion_records WHERE workspace_id = ? ORDER BY started_at ASC",
                    (workspace_id,),
                )
            rows = cur.fetchall()
            return [CandidatePromotionRecord.model_validate_json(r[0]) for r in rows if r[0]]


