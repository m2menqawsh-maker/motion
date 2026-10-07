"""
ai/memory/policy.py
===================
Canonical Memory Write Policy governing all persistence decisions (S27.7).

Rules Enforced:
1. AI cannot write permanent memory directly; candidates must be evaluated by policy.
2. Sensitive credentials (API keys, bearer tokens, private keys) are strictly rejected.
3. User/tenant content proposed with scope = GLOBAL is strictly rejected.
4. Epistemic classification:
   - EXPLICIT: explicit user statement -> HIGH confidence (0.9), candidate stored.
   - INFERRED: single inferred action -> LOW confidence (0.4), NOT stored as permanent confirmed fact
     unless repeated evidence threshold is met.
   - CONFIRMED: human confirmation -> HIGH confidence (0.95), stored/promoted.
5. Worth-Remembering filter: rejects greetings, filler, temporary execution requests, and model speculation.
6. Deduplication and Contradiction handling:
   - Repeated identical preference -> MERGE / reinforce existing memory.
   - Contradictory preference -> SUPERSEDE old memory with audit preservation.
7. TTL Policies: applies type-based and scope-based TTL defaults.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ai.memory.deduplication import DeduplicationEngine
from ai.memory.models import (
    Clock,
    MemoryCandidate,
    MemoryEntry,
    MemoryFilter,
    MemoryWriteDecision,
    SystemClock,
    TrustedTenantContext,
)
from ai.memory.normalization import ContentNormalizer
from ai.memory.repository import MemoryRepository
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    WriteDecisionType,
    confidence_to_level,
)


class MemoryPolicyConfig(BaseModel):
    """Configuration governing policy rules, thresholds, and default TTLs."""
    model_config = ConfigDict(frozen=True)

    policy_id: str = "canonical_memory_policy"
    version: str = "1.0.0"

    min_worth_tokens: int = 3
    min_confidence_to_store: float = 0.5
    inferred_initial_confidence: float = 0.4
    inferred_evidence_promotion_threshold: int = 3
    explicit_default_confidence: float = 0.9
    confirmed_default_confidence: float = 0.95

    default_ttls: Dict[str, Optional[int]] = Field(
        default_factory=lambda: {
            MemoryType.WORKING.value: 3600,            # 1 hour
            MemoryType.CONVERSATION.value: 86400,      # 24 hours
            MemoryType.USER_PREFERENCE.value: None,    # Permanent
            MemoryType.DECISION.value: None,           # Permanent
            MemoryType.PROJECT.value: None,            # Permanent
            MemoryType.WORKSPACE.value: None,          # Permanent
            MemoryType.KNOWLEDGE.value: None,          # Permanent
            MemoryType.MEDIA_INTELLIGENCE.value: 2592000,  # 30 days
        }
    )


class MemoryPolicy:
    """
    Authoritative Policy Engine mediating all AI Memory candidate write proposals.
    """

    # Secret and credential regex patterns
    SENSITIVE_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),                          # OpenAI / Fal / Generic API keys
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),                          # Google API keys
        re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),  # Bearer tokens
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),              # RSA / EC Private keys
        re.compile(r"(?:password|passwd|secret)\s*[:=]\s*[^\s]{4,}", re.IGNORECASE), # Passwords
    ]

    # Domain preference concepts that immediately distinguish real preferences from small talk
    PREFERENCE_INDICATORS = [
        "transition", "transitions", "font", "fonts", "cut", "cuts", "color", "theme",
        "speed", "ratio", "size", "lufs", "fps", "resolution", "aspect", "audio", "video",
        "heading", "title", "duration", "تفضيل", "أفضل", "اعتمد", "استخدم", "خط", "لون",
        "حجم", "موسيقى", "صوت", "خلفية", "قالب", "لا تستخدم",
    ]

    # Small talk, filler, and greeting words (English + Arabic)
    TRIVIAL_ROOTS = [
        "hello", "hi", "hey", "good morning", "good evening", "good afternoon",
        "how are you", "whats up", "what is up", "ok", "okay", "thanks", "thank you",
        "bye", "goodbye", "cool", "nice", "got it", "sure thing", "sure", "yes", "no",
        "مرحبا", "أهلا", "اهلا", "صباح الخير", "صباح النور", "مساء الخير", "كيف حالك",
        "شكرا", "شكراً", "تمام", "مع السلامة", "تسلم", "حسنا", "اوكي", "نعم", "لا",
        "ماشي", "ممتاز",
    ]

    # Ephemeral execution requests that are not long-term memory
    EPHEMERAL_REQUEST_PATTERNS = [
        re.compile(r"^(?:render|export|preview|generate)\s+now", re.IGNORECASE),
        re.compile(r"\b(?:show|display)\s+(?:me\s+)?(?:the\s+)?(?:preview|video|status|frame)", re.IGNORECASE),
        re.compile(r"\b(?:status\s+of\s+run|display\s+status|what\s+is\s+the\s+status|cancel\s+run|start\s+pipeline)\b", re.IGNORECASE),
        re.compile(r"\b(?:أرني|اعرض|ابدأ|صدر|شغل)\s+(?:المعاينة|الرندر|الفيديو|الحالة|المشهد)", re.IGNORECASE),
        re.compile(r"^render\s+now\s+item", re.IGNORECASE),
    ]

    # AI speculation markers without grounded evidence
    SPECULATION_PATTERNS = [
        re.compile(r"^(?:maybe|perhaps)\s+the\s+user\s+(?:likes|prefers|wants)", re.IGNORECASE),
        re.compile(r"^(?:i\s+guess|it\s+could\s+be\s+that)\s+the\s+user", re.IGNORECASE),
        re.compile(r"^(?:ربما|قد|احتمال)\s+(?:يفضل|يحب|يريد)\s+المستخدم", re.IGNORECASE),
    ]

    def __init__(self, config: Optional[MemoryPolicyConfig] = None, clock: Optional[Clock] = None):
        self.config = config or MemoryPolicyConfig()
        self.clock: Clock = clock or SystemClock()

    def evaluate_candidate(
        self,
        context: TrustedTenantContext,
        candidate: MemoryCandidate,
        repository: Optional[MemoryRepository] = None,
    ) -> MemoryWriteDecision:
        """
        Evaluates a proposed candidate against the policy pipeline.
        
        Pipeline:
        1. Sensitive data check
        2. Scope validation (GLOBAL guard)
        3. Worth-remembering check (greetings, filler, temporary requests, speculation)
        4. Normalization and content hashing
        5. Epistemic classification (Explicit vs Inferred vs Confirmed)
        6. Deduplication and Contradiction analysis
        7. TTL computation
        """
        raw_text = candidate.content.strip()

        # 1. Sensitive Data Check (API keys, tokens, credentials)
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.search(raw_text):
                return MemoryWriteDecision(
                    decision_type=WriteDecisionType.REJECT,
                    reason_code="SENSITIVE_DATA_DETECTED",
                    reason_detail="Candidate contains credential, secret, or private key pattern.",
                    candidate=candidate,
                )

        # 2. Scope Validation: GLOBAL Scope Guard
        if candidate.proposed_scope == MemoryScope.GLOBAL:
            if context.workspace_id not in ("global", "system", "shared") and not context.is_admin:
                return MemoryWriteDecision(
                    decision_type=WriteDecisionType.REJECT,
                    reason_code="GLOBAL_SCOPE_RESTRICTED",
                    reason_detail="User or tenant cannot propose memories with scope = GLOBAL.",
                    candidate=candidate,
                )

        # Check if explicitly an authorized decision or brand guideline
        is_explicit_decision = (
            candidate.source_type in (SourceType.DECISION, SourceType.HUMAN_CONFIRMATION)
            or raw_text.lower().startswith("decision:")
            or raw_text.lower().startswith("brand guideline:")
        )

        # 3. Worth-Remembering Evaluation
        if not is_explicit_decision:
            lower_text = raw_text.lower()
            clean_punct = re.sub(r"[^\w\s]", "", lower_text).strip()
            words = clean_punct.split()

            # Check if domain preference concepts exist
            has_domain_concept = any(ind in lower_text for ind in self.PREFERENCE_INDICATORS)

            if not has_domain_concept:
                # A. Greetings, filler, and trivial small talk
                is_trivial = False
                if len(words) <= 4:
                    is_trivial = any(
                        clean_punct == root
                        or clean_punct.startswith(root)
                        or root in words
                        for root in self.TRIVIAL_ROOTS
                    )
                if is_trivial or len(words) <= 1:
                    return MemoryWriteDecision(
                        decision_type=WriteDecisionType.REJECT,
                        reason_code="NOT_WORTH_REMEMBERING_TRIVIAL",
                        reason_detail=f"Content '{raw_text}' is small talk, greeting, or filler.",
                        candidate=candidate,
                    )

            # B. Ephemeral execution requests
            for ephem_pat in self.EPHEMERAL_REQUEST_PATTERNS:
                if ephem_pat.search(raw_text):
                    return MemoryWriteDecision(
                        decision_type=WriteDecisionType.REJECT,
                        reason_code="NOT_WORTH_REMEMBERING_EPHEMERAL",
                        reason_detail="Content is a short-lived execution or preview request.",
                        candidate=candidate,
                    )

            # C. AI Speculation without evidence
            for spec_pat in self.SPECULATION_PATTERNS:
                if spec_pat.search(raw_text):
                    if not candidate.evidence or len(candidate.evidence) == 0:
                        return MemoryWriteDecision(
                            decision_type=WriteDecisionType.REJECT,
                            reason_code="NOT_WORTH_REMEMBERING_SPECULATION",
                            reason_detail="Content is ungrounded AI speculation without supporting evidence.",
                            candidate=candidate,
                        )

        # 4. Normalization and Content Hashing
        norm_text = ContentNormalizer.normalize_text(raw_text)
        content_hash = ContentNormalizer.compute_content_hash(norm_text, candidate.structured_payload)

        # 5. Epistemic Classification (Explicit vs Inferred vs Confirmed)
        epistemic_status: EpistemicStatus
        final_confidence: float

        if candidate.source_type in (SourceType.USER_STATEMENT, SourceType.DECISION):
            epistemic_status = EpistemicStatus.EXPLICIT
            final_confidence = candidate.suggested_confidence or self.config.explicit_default_confidence
        elif candidate.source_type == SourceType.HUMAN_CONFIRMATION:
            epistemic_status = EpistemicStatus.CONFIRMED
            final_confidence = candidate.suggested_confidence or self.config.confirmed_default_confidence
        elif candidate.source_type == SourceType.AI_INFERENCE:
            epistemic_status = EpistemicStatus.INFERRED
            # Inferences start with low confidence
            final_confidence = self.config.inferred_initial_confidence
        else:
            epistemic_status = EpistemicStatus.EXPLICIT
            final_confidence = candidate.suggested_confidence or 0.8

        # 6. Deduplication and Contradiction Analysis
        if repository is not None:
            # Check for exact duplicate active memory
            existing_duplicate = repository.find_by_hash(
                workspace_id=context.workspace_id,
                content_hash=content_hash,
                memory_type=candidate.proposed_type,
                scope=candidate.proposed_scope,
                user_id=candidate.user_id,
                project_id=candidate.project_id,
            )

            if existing_duplicate is not None:
                # If identical, decide MERGE to reinforce confidence
                new_conf = min(1.0, existing_duplicate.confidence + 0.05)
                return MemoryWriteDecision(
                    decision_type=WriteDecisionType.MERGE,
                    reason_code="DUPLICATE_REINFORCED",
                    reason_detail=f"Identical memory exists (ID: {existing_duplicate.id}); reinforcing evidence.",
                    candidate=candidate,
                    target_entry_id=existing_duplicate.id,
                    final_type=candidate.proposed_type,
                    final_scope=candidate.proposed_scope,
                    final_confidence=new_conf,
                    final_confidence_level=confidence_to_level(new_conf),
                    epistemic_status=existing_duplicate.epistemic_status,
                    normalized_content=norm_text,
                    content_hash=content_hash,
                )

            # Check for contradictory preference under the same user / scope
            if candidate.proposed_type == MemoryType.USER_PREFERENCE:
                existing_prefs = repository.query_structured(
                    MemoryFilter(
                        workspace_id=context.workspace_id,
                        memory_types=[MemoryType.USER_PREFERENCE],
                        scopes=[candidate.proposed_scope],
                        user_id=candidate.user_id,
                        limit=50,
                    )
                )
                for existing in existing_prefs:
                    if DeduplicationEngine.is_contradictory_preference(existing, candidate):
                        # Supersede existing contradictory preference
                        return MemoryWriteDecision(
                            decision_type=WriteDecisionType.SUPERSEDE,
                            reason_code="CONTRADICTION_SUPERSEDED",
                            reason_detail=f"Contradicts existing preference '{existing.id}'; superseding with new choice.",
                            candidate=candidate,
                            supersedes_id=existing.id,
                            final_type=candidate.proposed_type,
                            final_scope=candidate.proposed_scope,
                            final_confidence=final_confidence,
                            final_confidence_level=confidence_to_level(final_confidence),
                            epistemic_status=epistemic_status,
                            normalized_content=norm_text,
                            content_hash=content_hash,
                        )

        # 7. Inferred Policy Threshold Guard:
        # A single inferred action does NOT become permanent high-confidence memory!
        if epistemic_status == EpistemicStatus.INFERRED:
            evidence_count = len(candidate.evidence)
            if evidence_count < self.config.inferred_evidence_promotion_threshold:
                # Single inference: require human confirmation or reject long-term storage
                if candidate.proposed_type in (MemoryType.USER_PREFERENCE, MemoryType.DECISION):
                    return MemoryWriteDecision(
                        decision_type=WriteDecisionType.REQUIRE_CONFIRMATION,
                        reason_code="INFERENCE_NEEDS_CONFIRMATION",
                        reason_detail=(
                            f"Single inferred preference/decision has evidence count {evidence_count} "
                            f"(needs {self.config.inferred_evidence_promotion_threshold}); confirmation required."
                        ),
                        candidate=candidate,
                        final_confidence=final_confidence,
                        final_confidence_level=confidence_to_level(final_confidence),
                        epistemic_status=epistemic_status,
                        normalized_content=norm_text,
                        content_hash=content_hash,
                    )

        # 8. Compute Expiration TTL
        now = self.clock.now_utc()
        expires_at: Optional[datetime] = None
        ttl_sec = candidate.suggested_ttl_seconds or self.config.default_ttls.get(candidate.proposed_type.value)
        if ttl_sec is not None:
            expires_at = now + timedelta(seconds=ttl_sec)

        # 9. Outcome: STORE
        return MemoryWriteDecision(
            decision_type=WriteDecisionType.STORE,
            reason_code="ACCEPTED_FOR_STORAGE",
            reason_detail="Candidate passed all policy criteria and is approved for persistence.",
            candidate=candidate,
            final_type=candidate.proposed_type,
            final_scope=candidate.proposed_scope,
            final_confidence=final_confidence,
            final_confidence_level=confidence_to_level(final_confidence),
            epistemic_status=epistemic_status,
            normalized_content=norm_text,
            content_hash=content_hash,
            expires_at=expires_at,
        )
