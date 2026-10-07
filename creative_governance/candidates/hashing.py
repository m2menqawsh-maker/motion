"""
creative_governance/candidates/hashing.py
========================
Deterministic server-side content hashing for TemplateCandidate (S28-07A).

Invariants:
- Canonical JSON serialization with sorted keys and separators (',', ':').
- Dependencies are normalized and sorted.
- String fields are trimmed.
- Server-side authoritative; client-provided hashes are never trusted.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def compute_candidate_content_hash(
    source_code: str,
    template_schema: Dict[str, Any],
    dependencies: List[str],
    fixtures: Dict[str, Any],
    why_reuse_failed: str,
    why_compose_failed: str,
    creative_plan_reference: str,
    creative_tier_decision_reference: str,
) -> str:
    """
    Computes a canonical SHA-256 digest representing all semantically meaningful
    components of a candidate template.
    """
    canonical_payload = {
        "creative_plan_reference": (creative_plan_reference or "").strip(),
        "creative_tier_decision_reference": (creative_tier_decision_reference or "").strip(),
        "dependencies": sorted([str(d).strip() for d in (dependencies or [])]),
        "fixtures": fixtures or {},
        "source_code": (source_code or "").strip(),
        "template_schema": template_schema or {},
        "why_compose_failed": (why_compose_failed or "").strip(),
        "why_reuse_failed": (why_reuse_failed or "").strip(),
    }
    canonical_json = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_review_bundle_hash(
    candidate_id: str,
    workspace_id: str,
    candidate_content_hash: str,
    candidate_revision: int,
    static_validation_id: str,
    runtime_validation_id: str,
    static_report_hash: str,
    runtime_report_hash: str,
    render_evidence_refs: Dict[str, str],
    representative_frame_refs: List[str],
    probe_report_ref: Optional[str],
    qc_report_ref: Optional[str],
    source_code_hash: str,
    schema_hash: str,
    fixtures_hash: str,
    review_policy_version: str = "1.0.0",
) -> str:
    """
    Computes a deterministic, canonical SHA-256 digest representing all
    frozen evidence artifacts in a CandidateReviewBundle (S28-07D).
    """
    canonical_payload = {
        "candidate_content_hash": (candidate_content_hash or "").strip(),
        "candidate_id": (candidate_id or "").strip(),
        "candidate_revision": int(candidate_revision),
        "fixtures_hash": (fixtures_hash or "").strip(),
        "probe_report_ref": (probe_report_ref or "").strip(),
        "qc_report_ref": (qc_report_ref or "").strip(),
        "render_evidence_refs": dict(sorted((render_evidence_refs or {}).items())),
        "representative_frame_refs": sorted([str(r).strip() for r in (representative_frame_refs or [])]),
        "review_policy_version": (review_policy_version or "1.0.0").strip(),
        "runtime_report_hash": (runtime_report_hash or "").strip(),
        "runtime_validation_id": (runtime_validation_id or "").strip(),
        "schema_hash": (schema_hash or "").strip(),
        "source_code_hash": (source_code_hash or "").strip(),
        "static_report_hash": (static_report_hash or "").strip(),
        "static_validation_id": (static_validation_id or "").strip(),
        "workspace_id": (workspace_id or "").strip(),
    }
    canonical_json = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_promotion_manifest_hash(
    promotion_id: str,
    candidate_id: str,
    workspace_id: str,
    candidate_content_hash: str,
    candidate_revision: int,
    approval_decision_id: str,
    review_bundle_id: str,
    review_bundle_hash: str,
    static_validation_id: str,
    runtime_validation_id: str,
    target_template_id: str,
    target_template_version: str,
    source_code_hash: str,
    schema_hash: str,
    promotion_policy_version: str = "1.0.0",
) -> str:
    """
    Computes a deterministic, canonical SHA-256 digest representing all
    parameters in a PromotionManifest (S28-07E).
    """
    canonical_payload = {
        "approval_decision_id": (approval_decision_id or "").strip(),
        "candidate_content_hash": (candidate_content_hash or "").strip(),
        "candidate_id": (candidate_id or "").strip(),
        "candidate_revision": int(candidate_revision),
        "promotion_id": (promotion_id or "").strip(),
        "promotion_policy_version": (promotion_policy_version or "1.0.0").strip(),
        "review_bundle_hash": (review_bundle_hash or "").strip(),
        "review_bundle_id": (review_bundle_id or "").strip(),
        "runtime_validation_id": (runtime_validation_id or "").strip(),
        "schema_hash": (schema_hash or "").strip(),
        "source_code_hash": (source_code_hash or "").strip(),
        "static_validation_id": (static_validation_id or "").strip(),
        "target_template_id": (target_template_id or "").strip(),
        "target_template_version": (target_template_version or "1.0.0").strip(),
        "workspace_id": (workspace_id or "").strip(),
    }
    canonical_json = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


