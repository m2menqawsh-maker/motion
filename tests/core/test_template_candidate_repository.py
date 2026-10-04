"""
tests/core/test_template_candidate_repository.py
================================================
Durable SQL persistence and CAS tests for SqlTemplateCandidateRepository (S28-07A).
"""

import pytest
from datetime import datetime, timezone

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from creative_governance.candidates.errors import CandidateConflictError, CandidateNotFoundError
from scripts.core.database import DatabaseEngine
from scripts.core.template_candidate_repository import SqlTemplateCandidateRepository


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def db_engine(tmp_path):
    db_file = tmp_path / "test_candidates.db"
    return DatabaseEngine(db_url=f"sqlite:///{db_file}")


@pytest.fixture
def sql_repo(db_engine):
    return SqlTemplateCandidateRepository(engine=db_engine)


def test_sql_repository_crud_and_tenant_isolation(sql_repo):
    now = _now()
    cand1 = TemplateCandidate(
        candidate_id="cand_1",
        workspace_id="ws_1",
        source_project_id="prj_1",
        creator_ai_run_id="run_1",
        creative_plan_reference="cplan_1",
        creative_tier_decision_reference="tier_1",
        why_reuse_failed="REUSE failed",
        why_compose_failed="COMPOSE failed",
        source_code="",
        source_code_path="workspaces/ws_1/projects/prj_1/candidates/cand_1/source.tsx",
        template_schema={"p": "str"},
        dependencies=["pkg-a"],
        fixtures={"p": "val"},
        content_hash="hash1",
        revision=1,
        status=CandidateStatus.DRAFT,
        name="Candidate 1",
        description="Desc 1",
        author="usr_1",
        proposed_category="ui",
        proposed_tags=["tag1"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="plan:1", timestamp=now),
        storage_keys={"source_code": "k1"},
        created_at=now,
        updated_at=now,
    )

    # 1. Save
    saved = sql_repo.save_candidate(cand1)
    assert saved.candidate_id == "cand_1"

    # 2. Get from same workspace
    retrieved = sql_repo.get_candidate("cand_1", "ws_1")
    assert retrieved is not None
    assert retrieved.candidate_id == "cand_1"
    assert retrieved.revision == 1
    assert retrieved.status == CandidateStatus.DRAFT

    # 3. Get from different workspace -> None (isolated)
    other = sql_repo.get_candidate("cand_1", "ws_2")
    assert other is None

    # 4. List scoped to workspace
    ws1_list = sql_repo.list_candidates("ws_1")
    assert len(ws1_list) == 1

    ws2_list = sql_repo.list_candidates("ws_2")
    assert len(ws2_list) == 0

    # 5. CAS update success
    cand1_updated = cand1.model_copy(update={"name": "Candidate 1 Updated"})
    updated = sql_repo.update_candidate_cas(cand1_updated, expected_revision=1)
    assert updated.revision == 2

    # 6. CAS update with stale revision -> conflict
    with pytest.raises(CandidateConflictError, match="Stale revision"):
        sql_repo.update_candidate_cas(cand1_updated, expected_revision=1)

    # 7. Delete
    deleted = sql_repo.delete_candidate("cand_1", "ws_1")
    assert deleted is True
    assert sql_repo.get_candidate("cand_1", "ws_1") is None


def test_sql_repository_validation_reports_and_status_cas(sql_repo):
    now = _now()
    cand = TemplateCandidate(
        candidate_id="cand_val_1",
        workspace_id="ws_val_1",
        source_project_id="prj_1",
        creator_ai_run_id="run_1",
        creative_plan_reference="cplan_1",
        creative_tier_decision_reference="tier_1",
        why_reuse_failed="REUSE failed",
        why_compose_failed="COMPOSE failed",
        source_code="",
        source_code_path="workspaces/ws_val_1/projects/prj_1/candidates/cand_val_1/source.tsx",
        template_schema={"p": "str"},
        dependencies=[],
        fixtures={},
        content_hash="hash_val_1",
        revision=1,
        status=CandidateStatus.DRAFT,
        name="Candidate Val",
        description="Desc",
        author="usr_1",
        proposed_category="ui",
        proposed_tags=[],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="plan:1", timestamp=now),
        storage_keys={},
        created_at=now,
        updated_at=now,
    )
    sql_repo.save_candidate(cand)

    # Status CAS update
    updated_cand = sql_repo.update_candidate_status_cas(
        candidate_id="cand_val_1",
        workspace_id="ws_val_1",
        status=CandidateStatus.VALIDATING,
        expected_revision=1,
    )
    assert updated_cand.status == CandidateStatus.VALIDATING
    assert updated_cand.revision == 1

    # Conflict if stale revision
    with pytest.raises(CandidateConflictError, match="Stale revision"):
        sql_repo.update_candidate_status_cas(
            candidate_id="cand_val_1",
            workspace_id="ws_val_1",
            status=CandidateStatus.VALIDATING,
            expected_revision=999,
        )

    # Validation Report persistence
    report = CandidateValidationReport(
        validation_id="val_rep_1",
        candidate_id="cand_val_1",
        workspace_id="ws_val_1",
        candidate_content_hash="hash_val_1",
        candidate_revision=1,
        phase=ValidationPhase.STATIC,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[
            CandidateGateResult(
                gate_id="contract_gate",
                status=GateStatus.PASS,
                summary="Pass",
            )
        ],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"report": "ref_1"},
    )
    sql_repo.save_validation_report(report)

    # Get report
    fetched = sql_repo.get_validation_report("val_rep_1", "ws_val_1")
    assert fetched is not None
    assert fetched.validation_id == "val_rep_1"
    assert fetched.overall_result == ValidationOverallResult.PASS
    assert len(fetched.gates) == 1

    # Tenant isolation on report
    other_tenant = sql_repo.get_validation_report("val_rep_1", "other_ws")
    assert other_tenant is None

    # List reports
    reps = sql_repo.list_validation_reports("cand_val_1", "ws_val_1")
    assert len(reps) == 1
    assert reps[0].validation_id == "val_rep_1"


def test_sql_repository_review_bundle_and_decision_persistence(sql_repo):
    from ai.contracts.creative.template_candidate import (
        CandidateReviewBundle,
        CandidateReviewDecision,
        CandidateReviewVerdict,
    )
    now = _now()
    bundle = CandidateReviewBundle(
        review_bundle_id="rbd_test_01",
        candidate_id="cand_test_01",
        workspace_id="ws_test_01",
        candidate_content_hash="hash_c_01",
        candidate_revision=1,
        static_validation_id="val_s_01",
        runtime_validation_id="val_r_01",
        static_report_hash="hash_s_rep",
        runtime_report_hash="hash_r_rep",
        render_evidence_refs={"smoke": "key_smoke.png"},
        representative_frame_refs=["key_smoke.png"],
        probe_report_ref="key_probe.json",
        qc_report_ref="key_qc.json",
        source_code_hash="hash_src",
        schema_hash="hash_sch",
        fixtures_hash="hash_fix",
        created_at=now,
        review_policy_version="1.0.0",
        review_bundle_hash="hash_bundle_01",
    )

    # Save and retrieve review bundle
    saved_bundle = sql_repo.save_review_bundle(bundle)
    assert saved_bundle.review_bundle_id == "rbd_test_01"

    fetched_bundle = sql_repo.get_review_bundle("rbd_test_01", "ws_test_01")
    assert fetched_bundle is not None
    assert fetched_bundle.review_bundle_hash == "hash_bundle_01"

    # Cross-tenant bundle isolation
    assert sql_repo.get_review_bundle("rbd_test_01", "other_ws") is None

    # List bundles
    bundles = sql_repo.list_review_bundles("cand_test_01", "ws_test_01")
    assert len(bundles) == 1
    assert bundles[0].review_bundle_id == "rbd_test_01"

    # Save and retrieve review decision
    decision = CandidateReviewDecision(
        decision_id="rdec_test_01",
        review_bundle_id="rbd_test_01",
        candidate_id="cand_test_01",
        workspace_id="ws_test_01",
        decision=CandidateReviewVerdict.APPROVED,
        reviewer_principal_id="usr_reviewer_01",
        reviewer_role="reviewer",
        reason="Approved after manual inspection.",
        candidate_content_hash="hash_c_01",
        candidate_revision=1,
        review_bundle_hash="hash_bundle_01",
        static_validation_report_hash="hash_s_rep",
        runtime_validation_report_hash="hash_r_rep",
        decided_at=now,
        decision_revision=1,
    )
    saved_decision = sql_repo.save_review_decision(decision)
    assert saved_decision.decision_id == "rdec_test_01"

    fetched_dec = sql_repo.get_review_decision("rdec_test_01", "ws_test_01")
    assert fetched_dec is not None
    assert fetched_dec.decision == CandidateReviewVerdict.APPROVED

    # Cross-tenant decision isolation
    assert sql_repo.get_review_decision("rdec_test_01", "other_ws") is None

    # Active decision for bundle
    active = sql_repo.get_active_decision_for_bundle("rbd_test_01", "ws_test_01")
    assert active is not None
    assert active.decision_id == "rdec_test_01"

