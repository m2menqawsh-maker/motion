"""
ai/feedback/service.py
======================
Creative Feedback Learning Service (S28-08A).

Coordinates the lifecycle of CreativeFeedback events:
1. Multi-tenant and user authorization verification.
2. AI Authority restriction enforcement (confidence & provenance clamping).
3. Semantic classification via FeedbackClassifier.
4. MemoryCandidate formulation for the S27 Memory System.
5. Authoritative evaluation through MemoryPolicy.
6. Persistence into canonical MemoryRepository.

Guarantees:
- Uses canonical S27 Memory System (no duplicate storage).
- Single action ≠ permanent truth (single inferences require confirmation).
- Tenant & user isolation strictly enforced.
- Cross-tenant or cross-user leakage fails closed.
"""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel, ConfigDict

from ai.contracts.creative.feedback import (
    CreativeFeedback,
    FeedbackClassification,
)
from ai.feedback.classifier import FeedbackClassifier, MalformedFeedbackError
from ai.memory.models import (
    MemoryCandidate,
    MemoryWriteDecision,
    TrustedTenantContext,
)
from ai.memory.service import MemoryService, TenantAuthorizationError
from ai.memory.types import (
    EpistemicStatus,
    MemoryScope,
    MemoryType,
    SourceType,
    WriteDecisionType,
)

logger = logging.getLogger(__name__)


class FeedbackProcessingResult(BaseModel):
    """Structured outcome of creative feedback processing and memory policy evaluation."""
    model_config = ConfigDict(frozen=True)

    feedback_id: str
    classification: FeedbackClassification
    decision: MemoryWriteDecision
    persisted: bool
    epistemic_status: EpistemicStatus
    effective_confidence: float
    target_entry_id: Optional[str] = None


class CreativeFeedbackService:
    """
    Authoritative coordinator for processing user creative feedback,
    mediating preference learning through the canonical S27 MemoryPolicy.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        classifier: Optional[FeedbackClassifier] = None,
    ) -> None:
        self.memory_service = memory_service
        self.classifier = classifier or FeedbackClassifier()

    def process_feedback(
        self,
        context: TrustedTenantContext,
        feedback: CreativeFeedback,
    ) -> FeedbackProcessingResult:
        """
        Processes a creative feedback event with strict tenant isolation and policy mediation.
        """
        # 1. Authoritative Multi-Tenant & User Boundary Validation
        if feedback.workspace_id and feedback.workspace_id != context.workspace_id:
            raise TenantAuthorizationError(
                f"Cross-tenant feedback rejected: caller workspace '{context.workspace_id}' "
                f"cannot submit feedback for workspace '{feedback.workspace_id}'."
            )

        if feedback.project_id and not context.can_access_project(feedback.project_id):
            raise TenantAuthorizationError(
                f"Tenant authorization failed: Actor '{context.user_id}' does not have access "
                f"to project '{feedback.project_id}' in workspace '{context.workspace_id}'."
            )

        if feedback.user_id and not context.can_access_user(feedback.user_id):
            raise TenantAuthorizationError(
                f"Cross-user feedback rejected: Actor '{context.user_id}' cannot mutate "
                f"feedback on behalf of user '{feedback.user_id}'."
            )

        # 2. Classification & Domain Normalization
        # AI Authority Guard: Do not blindly trust external classification confidence or source
        classification = self.classifier.classify(context, feedback)

        # If feedback doesn't map to a learning dimension, return early as ephemeral
        if not classification.preference_dimension or not classification.proposed_value:
            # Trivial or non-actionable feedback (e.g. general star rating without critique)
            dummy_candidate = MemoryCandidate(
                proposed_type=MemoryType.USER_PREFERENCE,
                proposed_scope=classification.scope,
                content=feedback.critique_text or "General non-actionable feedback",
                source_type=classification.source,
                user_id=context.user_id,
                project_id=feedback.project_id,
            )
            dummy_decision = MemoryWriteDecision(
                decision_type=WriteDecisionType.REJECT,
                reason_code="NON_ACTIONABLE_FEEDBACK",
                reason_detail="Feedback does not specify a quantifiable creative dimension.",
                candidate=dummy_candidate,
            )
            return FeedbackProcessingResult(
                feedback_id=feedback.feedback_id,
                classification=classification,
                decision=dummy_decision,
                persisted=False,
                epistemic_status=EpistemicStatus.INFERRED,
                effective_confidence=classification.confidence,
                target_entry_id=None,
            )

        # 3. Construct Canonical MemoryCandidate
        # Format standardized content payload for MemoryPolicy
        norm_content = f"User preference for {classification.preference_dimension}: {classification.proposed_value}"

        evidence_items = []
        if feedback.critique_text and feedback.critique_text.strip():
            evidence_items.append(feedback.critique_text.strip())
        else:
            evidence_items.append(f"Feedback event {feedback.feedback_id} on project {feedback.project_id}")

        candidate = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=classification.scope,
            content=norm_content,
            structured_payload={
                "dimension": classification.preference_dimension,
                "value": classification.proposed_value,
            },
            source_type=classification.source,
            source_id=feedback.feedback_id,
            user_id=context.user_id,
            project_id=feedback.project_id if classification.scope == MemoryScope.PROJECT else None,
            evidence=evidence_items,
            suggested_confidence=classification.confidence,
            metadata={
                "dimension": classification.preference_dimension,
                "value": classification.proposed_value,
                "category": classification.category.value,
                "target_type": classification.target_type.value,
                "evidence_count": 1,
                "feedback_id": feedback.feedback_id,
                "project_id": feedback.project_id,
            },
        )

        # 4. Mediate through S27 MemoryPolicy via MemoryService
        decision: MemoryWriteDecision = self.memory_service.propose_candidate(context, candidate)

        persisted = decision.decision_type in (
            WriteDecisionType.STORE,
            WriteDecisionType.SUPERSEDE,
            WriteDecisionType.MERGE,
        )

        epistemic = decision.epistemic_status or (
            EpistemicStatus.EXPLICIT if classification.source == SourceType.USER_STATEMENT else EpistemicStatus.INFERRED
        )

        effective_conf = decision.final_confidence or classification.confidence

        return FeedbackProcessingResult(
            feedback_id=feedback.feedback_id,
            classification=classification,
            decision=decision,
            persisted=persisted,
            epistemic_status=epistemic,
            effective_confidence=effective_conf,
            target_entry_id=decision.target_entry_id,
        )
