"""
tests/ai/candidates/test_candidate_contracts.py
================================================
Canonical contract tests for TemplateCandidate (S28-07A).

Invariants:
- TemplateCandidate must define all required provenance and isolation fields.
- Server-controlled status vocabulary: DRAFT, VALIDATING, VALIDATED, AWAITING_APPROVAL,
  APPROVED, REJECTED, PROMOTED, RETIRED.
- Initial state must always be DRAFT.
- Extra fields are forbidden (extra = 'forbid').
- Missing provenance, invalid plan reference, or invalid tier decision reference fails validation.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier
from ai.contracts.creative.template_candidate import (
    CandidateStatus,
    PromotionStatus,
    TemplateCandidate,
    PromotionDecision,
    CandidateValidationReport,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_valid_template_candidate_canonical_contract():
    now = _now_iso()
    cand = TemplateCandidate(
        candidate_id="cand_test_pulse_box",
        workspace_id="ws_acme",
        source_project_id="prj_brand_video",
        creator_ai_run_id="run_ai_planner_123",
        creative_plan_reference="cplan_tech_001",
        creative_tier_decision_reference="tier_dec_001",
        why_reuse_failed="No existing template supports multi-glow border pulse with custom SVG geometry.",
        why_compose_failed="Composing primitives produces frame-rate drops; unified WebGL/SVG shader candidate required.",
        source_code="export const PulseBox = () => <div className='pulse'></div>;",
        source_code_path="workspaces/ws_acme/projects/prj_brand_video/candidates/cand_test_pulse_box/source.tsx",
        template_schema={
            "type": "object",
            "properties": {"glowColor": {"type": "string"}, "pulseSpeed": {"type": "number"}},
            "required": ["glowColor"],
        },
        dependencies=["clsx@^2.0.0"],
        fixtures={"glowColor": "#00ffcc", "pulseSpeed": 1.5},
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        revision=1,
        status=CandidateStatus.DRAFT,
        name="Pulse Box",
        description="Pulsing geometric box for hero sections",
        author="agent_creative_planner",
        proposed_category="elements/ui",
        proposed_tags=["glow", "box", "pulse"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="plan:cplan_tech_001", timestamp=now),
        storage_keys={
            "source_code": "workspaces/ws_acme/projects/prj_brand_video/candidates/cand_test_pulse_box/source.tsx",
            "fixtures": "workspaces/ws_acme/projects/prj_brand_video/candidates/cand_test_pulse_box/fixtures.json",
        },
        created_at=now,
        updated_at=now,
    )

    assert cand.candidate_id == "cand_test_pulse_box"
    assert cand.workspace_id == "ws_acme"
    assert cand.source_project_id == "prj_brand_video"
    assert cand.status == CandidateStatus.DRAFT
    assert cand.revision == 1
    assert cand.content_hash != ""
    assert cand.why_reuse_failed != ""
    assert cand.why_compose_failed != ""
    assert cand.creative_plan_reference == "cplan_tech_001"
    assert cand.creative_tier_decision_reference == "tier_dec_001"


def test_candidate_missing_required_provenance():
    now = _now_iso()
    with pytest.raises(ValidationError):
        TemplateCandidate(
            candidate_id="cand_invalid_prov",
            workspace_id="ws_acme",
            source_project_id="prj_1",
            creative_plan_reference="cplan_1",
            creative_tier_decision_reference="tier_1",
            why_reuse_failed="insufficient",
            why_compose_failed="insufficient",
            source_code="export const X = () => null;",
            required_provenance=ProvenanceRecord(source="  ", timestamp=now),
            created_at=now,
            updated_at=now,
        )


def test_candidate_invalid_status_enum():
    now = _now_iso()
    with pytest.raises(ValidationError):
        TemplateCandidate(
            candidate_id="cand_invalid_status",
            workspace_id="ws_acme",
            source_project_id="prj_1",
            creative_plan_reference="cplan_1",
            creative_tier_decision_reference="tier_1",
            why_reuse_failed="insufficient",
            why_compose_failed="insufficient",
            source_code="export const X = () => null;",
            status="NOT_A_VALID_STATUS",  # type: ignore
            created_at=now,
            updated_at=now,
        )


def test_candidate_status_vocabulary_complete():
    expected_statuses = {
        "DRAFT",
        "VALIDATING",
        "VALIDATED",
        "AWAITING_APPROVAL",
        "APPROVED",
        "REJECTED",
        "PROMOTED",
        "RETIRED",
    }
    actual_statuses = {s.value for s in CandidateStatus}
    assert expected_statuses == actual_statuses, f"Mismatch in CandidateStatus enum: {expected_statuses ^ actual_statuses}"


def test_candidate_forbids_arbitrary_extra_fields():
    now = _now_iso()
    with pytest.raises(ValidationError):
        TemplateCandidate(
            candidate_id="cand_extra",
            workspace_id="ws_1",
            source_project_id="prj_1",
            creative_plan_reference="cplan_1",
            creative_tier_decision_reference="tier_1",
            why_reuse_failed="insufficient",
            why_compose_failed="insufficient",
            source_code="export const X = () => null;",
            created_at=now,
            updated_at=now,
            arbitrary_untrusted_field="malicious_payload",  # type: ignore
        )
