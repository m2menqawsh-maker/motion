"""
ai/tools/domain/qc.py
=====================
Domain tool adapter for inspecting Quality Control reports and review status (S27.9).

Invariants:
- STRICTLY READ-ONLY: AI has NO authority to approve, reject, or bypass QC gates.
- No direct mutation of approval files, lock seals, or review decisions.
- Reads verified artifacts via DomainArtifactService or ReviewService.
"""

from __future__ import annotations

from typing import Dict, Optional
from pydantic import JsonValue

from api.services.domain_artifact_service import DomainArtifactService
from scripts.core.review_service import ReviewService
from ai.tools.contracts import GetQcReportInput, GetQcReportOutput
from ai.tools.types import TrustedToolExecutionContext


def get_qc_report_adapter(
    input_data: GetQcReportInput,
    context: TrustedToolExecutionContext,
) -> GetQcReportOutput:
    """
    Retrieves QC / probe report information and human review status.
    """
    has_report = False
    status_str = "NOT_FOUND"
    summary_data: Optional[Dict[str, JsonValue]] = None
    verdict_str: Optional[str] = None
    review_state_str: Optional[str] = None

    # 1. Check probe QC report artifact
    try:
        content, _, _, _ = DomainArtifactService.read_artifact(input_data.project_id, "probe_report")
        if isinstance(content, dict):
            has_report = True
            status_str = "AVAILABLE"
            verdict_str = content.get("verdict") or content.get("status")
            summary_data = {
                "overall_status": content.get("overall_status") or verdict_str,
                "issues_count": len(content.get("issues", [])) if isinstance(content.get("issues"), list) else 0,
            }
    except Exception:
        pass

    # 2. Check Review Status
    try:
        review_dto = ReviewService.get_review_status(input_data.project_id)
        if review_dto:
            review_state_str = getattr(review_dto, "active_decision", None) or getattr(review_dto, "lifecycle_state", None)
            if not has_report and getattr(review_dto, "active_bundle_id", None):
                status_str = "PENDING_REVIEW"
    except Exception:
        pass

    return GetQcReportOutput(
        project_id=input_data.project_id,
        has_report=has_report,
        status=status_str,
        summary=summary_data,
        verdict=verdict_str,
        review_state=review_state_str,
    )
