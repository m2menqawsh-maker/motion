"""
ai/context/builder.py
=====================
Authoritative Context Builder Facade (S27.8).

Coordinates the end-to-end bounded context pipeline:
Current Request + Trusted Context + Project Facts + Relevant Memory + Relevant Knowledge
-> Bounded, Relevant, Deterministic, Tenant-Safe ContextPackage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ai.context.assembly import ContextAssembler
from ai.context.budgeting import ContextBudgetManager, ContextBudgetPolicy, DeterministicTokenEstimator, TokenEstimator
from ai.context.compression import DeterministicContextCompressor
from ai.context.deduplication import ContextDeduplicator
from ai.context.needs import classify_context_needs
from ai.context.ranking import ContextRanker, ContextRankingPolicy
from ai.context.retrieval import (
    DeterministicKnowledgeRetriever,
    KnowledgeRetriever,
    MemoryRetriever,
    ProjectFactRetriever,
    RequestRetriever,
    SharedConfigRetriever,
    SystemPolicyRetriever,
    contains_secret,
)
from ai.context.types import (
    ContextDiagnostics,
    ContextExclusion,
    ContextItem,
    ContextPackage,
    ContextRequest,
    ContextSection,
    ContextSourceType,
    ExclusionReason,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
)
from ai.memory.service import MemoryService


class ContextBuilder:
    """
    Central orchestrator for constructing prompt-ready context packages.
    
    Guarantees:
    - Never dumps all workspace data or unfiltered conversation history.
    - Strictly enforces tenant boundaries and project authorization before retrieval.
    - Resolves conflicts in favor of authoritative domain services over stale memory.
    - Enforces hard token ceilings with output reservation.
    - Yields deterministic output and canonical context_hash for identical state.
    """

    def __init__(
        self,
        project_service: Optional[object] = None,
        asset_service: Optional[object] = None,
        review_service: Optional[object] = None,
        memory_service: Optional[MemoryService] = None,
        knowledge_retriever: Optional[KnowledgeRetriever] = None,
        ranking_policy: Optional[ContextRankingPolicy] = None,
        budget_policy: Optional[ContextBudgetPolicy] = None,
        compressor: Optional[DeterministicContextCompressor] = None,
        token_estimator: Optional[TokenEstimator] = None,
    ):
        self.project_fact_retriever = ProjectFactRetriever(
            project_service=project_service,
            asset_service=asset_service,
            review_service=review_service,
        )
        self.memory_retriever = MemoryRetriever(memory_service=memory_service)
        self.knowledge_retriever = knowledge_retriever or DeterministicKnowledgeRetriever()
        self.system_policy_retriever = SystemPolicyRetriever()
        self.shared_config_retriever = SharedConfigRetriever()
        self.request_retriever = RequestRetriever()

        self.ranker = ContextRanker(policy=ranking_policy)
        self.deduplicator = ContextDeduplicator()
        self.token_estimator = token_estimator or DeterministicTokenEstimator()
        self.compressor = compressor or DeterministicContextCompressor()
        self.budget_manager = ContextBudgetManager(
            policy=budget_policy,
            estimator=self.token_estimator,
            compressor=self.compressor,
        )

    def build(self, request: ContextRequest) -> ContextPackage:
        """
        Executes canonical context assembly pipeline for a given request.
        """
        exclusions: List[ContextExclusion] = []

        # 1. Authoritative Tenant & Project Authorization Gate
        if request.project_id:
            if not request.trusted_context.can_access_project(request.project_id):
                raise ProjectAccessDeniedError(
                    f"Actor '{request.trusted_context.user_id}' denied access to project '{request.project_id}'."
                )

        # 2. Classify Context Needs
        needs = classify_context_needs(request)

        # 3. Retrieve Candidate Items
        raw_candidates: List[ContextItem] = []

        # 3a. System Policy
        raw_candidates.extend(self.system_policy_retriever.retrieve_policies())

        # 3b. Shared Configuration
        raw_candidates.extend(self.shared_config_retriever.retrieve_shared_config(request.trusted_context))

        # 3c. Canonical Project Facts
        if request.project_id and needs.needs_project_state:
            project_facts = self.project_fact_retriever.retrieve_project_facts(
                context=request.trusted_context,
                project_id=request.project_id,
                needs=needs,
            )
            raw_candidates.extend(project_facts)

        # 3d. Relevant AI Memory
        now = request.created_at
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        mem_items, mem_exclusions = self.memory_retriever.retrieve_memories(
            context=request.trusted_context,
            request=request,
            needs=needs,
            now=now,
        )
        raw_candidates.extend(mem_items)
        exclusions.extend(mem_exclusions)

        # 3e. Relevant Knowledge & Playbooks
        if needs.needs_knowledge or request.recipe_ref:
            knowledge_items = self.knowledge_retriever.retrieve_knowledge(
                context=request.trusted_context,
                tags=needs.knowledge_tags,
                query=request.query_text,
                recipe_ref=request.recipe_ref,
            )
            raw_candidates.extend(knowledge_items)

        # 3f. Request Item
        raw_candidates.extend(self.request_retriever.retrieve_request_item(request))

        total_candidates_retrieved = len(raw_candidates)

        # 4. Secret Sanitization Guard
        sanitized_candidates: List[ContextItem] = []
        for it in raw_candidates:
            if contains_secret(it.content):
                exclusions.append(
                    ContextExclusion(
                        candidate_id=it.id,
                        section=it.section,
                        reason=ExclusionReason.SECRET_DETECTED,
                        details="Candidate content matched secret or credential pattern.",
                        source_type=it.source_type,
                    )
                )
            else:
                sanitized_candidates.append(it)

        # 5. Candidate Ranking
        ranked_items, rank_exclusions = self.ranker.rank_items(
            sanitized_candidates,
            reference_time=request.created_at,
        )
        exclusions.extend(rank_exclusions)

        # 6. Deduplication & Conflict Resolution
        deduped_items, dedup_exclusions = self.deduplicator.deduplicate(ranked_items)
        exclusions.extend(dedup_exclusions)

        # 7. Token Budgeting & Compression
        effective_budget = request.token_budget
        effective_reserve = request.output_reserve

        final_items, budget_exclusions, tokens_by_sec = self.budget_manager.apply_budget(
            deduped_items,
            override_total_budget=effective_budget,
            override_output_reserve=effective_reserve,
        )
        exclusions.extend(budget_exclusions)

        # 8. Diagnostics Compilation
        items_compressed_count = sum(1 for it in final_items if it.compressed)
        total_tokens = sum(it.estimated_tokens for it in final_items)
        ceiling = self.budget_manager.policy.calculate_usable_input_ceiling(
            override_total_budget=effective_budget,
            override_output_reserve=effective_reserve,
        )
        curr_reserve = effective_reserve if effective_reserve is not None else self.budget_manager.policy.output_reserve

        diagnostics = ContextDiagnostics(
            total_candidates_retrieved=total_candidates_retrieved,
            total_items_included=len(final_items),
            total_items_excluded=len(exclusions),
            items_compressed=items_compressed_count,
            tokens_by_section=tokens_by_sec,
            total_estimated_tokens=total_tokens,
            output_reserve=curr_reserve,
            budget_ceiling=ceiling,
            remaining_budget=max(0, ceiling - total_tokens),
            exclusions=exclusions,
        )

        # 9. Stable Assembly
        package = ContextAssembler.assemble(
            request_id=request.request_id,
            items=final_items,
            diagnostics=diagnostics,
        )

        return package
