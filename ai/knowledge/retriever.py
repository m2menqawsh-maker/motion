"""
ai/knowledge/retriever.py
=========================
Knowledge Retriever implementing metadata filtering, hybrid (lexical + semantic) retrieval,
candidate fusion, reranking, deduplication, and context bounding (S28-02A).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Strict exclusion of retired knowledge, wrong versions, and hard-incompatible audio modes.
- True Hybrid Retrieval: Combines Lexical (BM25/TF-IDF) and Semantic (dense concept & LSA vector space).
- Explicit Degradation: If semantic backend is unavailable or errors, explicitly reports
  retrieval_mode=DEGRADED_LEXICAL with degraded_reason in evidence/trace (no silent fallback).
- Deduplication by content hash and provenance.
- Bounded context output adhering to chunk and token budgets.
- Provider-neutral: hermetic, zero third-party cloud SDK dependencies.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Set, Tuple

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import KnowledgeStatus, RetrievalMode
from ai.knowledge.contracts import (
    KnowledgeChunk,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    RetrievedChunk,
)
from ai.knowledge.indexer import KnowledgeIndexer, tokenize
from ai.knowledge.registry import KnowledgeRegistry
from ai.knowledge.semantic import BaseSemanticScorer, DenseConceptSemanticScorer


GENERIC_TERMS = {"video", "audio", "make", "create", "generate", "content", "document"}


class KnowledgeRetriever:
    """
    Orchestrates the multi-stage hybrid knowledge retrieval pipeline:
    1. Hard Metadata Filtering
    2. Candidate Generation (Lexical Channel + Semantic Channel)
    3. Candidate Fusion (Reciprocal Rank Fusion + Normalized Score Blending)
    4. Context Reranking
    5. Deterministic Deduplication
    6. Context Bounding
    """

    def __init__(
        self,
        indexer: KnowledgeIndexer,
        registry: Optional[KnowledgeRegistry] = None,
        semantic_scorer: Optional[BaseSemanticScorer] = None,
    ) -> None:
        self.indexer = indexer
        self.registry = registry
        self.semantic_scorer = semantic_scorer if semantic_scorer is not None else DenseConceptSemanticScorer()

    def _estimate_tokens(self, text: str) -> int:
        """Conservative token estimator: max(1, len(text) // 4)."""
        return max(1, math.ceil(len(text) / 4.0))

    def _check_audio_compatibility(
        self,
        chunk: KnowledgeChunk,
        query_mode: Optional[AudioMode],
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates hard incompatibility between query audio mode and chunk metadata.
        Returns (is_compatible, rejection_reason).
        """
        if query_mode is None:
            return True, None

        chunk_modes = chunk.audio_modes or []
        tags = set(chunk.tags)

        # 1. Query is MUSIC_ONLY
        if query_mode == AudioMode.MUSIC_ONLY:
            # If chunk explicitly requires VO_ONLY and does not support MUSIC_ONLY
            if chunk_modes and AudioMode.MUSIC_ONLY not in chunk_modes:
                return False, f"Incompatible with MUSIC_ONLY: chunk requires {chunk_modes}"
            # Hard rejection for voiceover / speech humanization in MUSIC_ONLY
            if "voiceover" in tags or "spoken_vo" in tags or "tts" in tags:
                if AudioMode.MUSIC_ONLY not in chunk_modes:
                    return False, "Incompatible with MUSIC_ONLY: voiceover/speech specific knowledge"

        # 2. Query is VO_ONLY
        elif query_mode == AudioMode.VO_ONLY:
            if chunk_modes and AudioMode.VO_ONLY not in chunk_modes and AudioMode.VO_MUSIC not in chunk_modes:
                return False, f"Incompatible with VO_ONLY: chunk requires {chunk_modes}"

        # 3. Query is SILENT
        elif query_mode == AudioMode.SILENT:
            if chunk_modes and not any(m in chunk_modes for m in [AudioMode.SILENT]):
                if "audio" in tags or "sfx" in tags or "voiceover" in tags:
                    return False, "Incompatible with SILENT: audio-dependent knowledge"

        return True, None

    def _check_metadata_eligibility(
        self,
        chunk: KnowledgeChunk,
        query: KnowledgeRetrievalQuery,
        excluded_docs: Dict[str, str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates hard metadata filtering:
        - Registry active status
        - Version alignment
        - AudioMode compatibility
        - Language compatibility
        - Category filter
        """
        doc_id = chunk.document_id

        # 1. Registry status check (RETIRED documents strictly excluded)
        if self.registry is not None:
            desc = self.registry.get(doc_id, version=chunk.version)
            if desc is None:
                excluded_docs[doc_id] = "NOT_IN_REGISTRY"
                return False, "Document not registered in KnowledgeRegistry"
            if desc.status != KnowledgeStatus.ACTIVE:
                excluded_docs[doc_id] = f"STATUS_{desc.status}"
                return False, f"Document status is {desc.status} (only ACTIVE allowed)"

        # 2. Explicit version check if query requested a specific version
        if query.version is not None and chunk.version != query.version:
            excluded_docs[doc_id] = f"VERSION_MISMATCH_EXPECTED_{query.version}"
            return False, f"Version mismatch: chunk is v{chunk.version}, expected v{query.version}"

        # 3. Audio mode hard incompatibility
        audio_ok, audio_reason = self._check_audio_compatibility(chunk, query.audio_mode)
        if not audio_ok:
            excluded_docs[doc_id] = "INCOMPATIBLE_AUDIO_MODE"
            return False, audio_reason

        # 4. Language filter (if requested and chunk has specific differing language)
        if query.language and chunk.language not in ("any", query.language):
            excluded_docs[doc_id] = f"LANGUAGE_MISMATCH_{chunk.language}"
            return False, f"Language mismatch: expected '{query.language}', chunk is '{chunk.language}'"

        # 5. Category filter (if explicitly filtered)
        if query.category and chunk.category.upper() != query.category.upper():
            return False, f"Category mismatch: expected '{query.category}', chunk is '{chunk.category}'"

        return True, None

    # =========================================================================
    # Channel 1: Lexical Retrieval
    # =========================================================================

    def _run_lexical_channel(
        self,
        chunks: Sequence[KnowledgeChunk],
        query: KnowledgeRetrievalQuery,
    ) -> List[Tuple[KnowledgeChunk, float, List[str]]]:
        """
        Computes keyword relevance:
        - Exact token matches in section title and chunk body
        - Sublinear term frequency (log1p)
        - Classification tag overlap
        """
        query_tokens = [t for t in tokenize(query.query) if t not in GENERIC_TERMS]
        results: List[Tuple[KnowledgeChunk, float, List[str]]] = []

        for chunk in chunks:
            score = 0.0
            reasons: List[str] = []

            chunk_text_lower = f"{chunk.section} {chunk.content}".lower()
            chunk_tokens = tokenize(chunk_text_lower)
            chunk_token_set = set(chunk_tokens)

            # Heading token matches (weighted 3.0x)
            section_tokens = set(tokenize(chunk.section.lower())) - GENERIC_TERMS
            heading_matches = [t for t in query_tokens if t in section_tokens]
            if heading_matches:
                score += len(heading_matches) * 3.0
                reasons.append(f"Lexical heading match on: {', '.join(heading_matches[:3])}")

            # Content token matches
            content_matches = [t for t in query_tokens if t in chunk_token_set]
            if content_matches:
                term_count = sum(chunk_tokens.count(t) for t in content_matches)
                score += math.log1p(term_count) * 1.5
                reasons.append(f"Lexical content matches ({len(content_matches)} terms)")

            # Tag token matches
            tag_set = {t.lower() for t in chunk.tags} - GENERIC_TERMS
            tag_matches = [t for t in query_tokens if t in tag_set]
            if tag_matches:
                score += len(tag_matches) * 2.5
                reasons.append(f"Lexical tag matches: {', '.join(tag_matches)}")

            results.append((chunk, score, reasons))

        return results

    # =========================================================================
    # Channel 2: Semantic Retrieval
    # =========================================================================

    def _run_semantic_channel(
        self,
        chunks: Sequence[KnowledgeChunk],
        query: KnowledgeRetrievalQuery,
    ) -> List[Tuple[KnowledgeChunk, float, List[str]]]:
        """
        Computes dense semantic similarity using provider-neutral semantic scorer.
        Captures synonyms, domain taxonomies, and conceptual relatedness.
        """
        raw_scores = self.semantic_scorer.score_chunks(query.query, chunks)
        results: List[Tuple[KnowledgeChunk, float, List[str]]] = []

        for chunk, sim in zip(chunks, raw_scores):
            reasons: List[str] = []
            if sim >= 0.25:
                reasons.append(f"Semantic concept alignment ({sim:.2f})")
            results.append((chunk, sim, reasons))

        return results

    # =========================================================================
    # Stage 3: Candidate Fusion (Reciprocal Rank Fusion + Normalized Score Blending)
    # =========================================================================

    def _fuse_candidates(
        self,
        eligible_chunks: Sequence[KnowledgeChunk],
        lexical_results: List[Tuple[KnowledgeChunk, float, List[str]]],
        semantic_results: List[Tuple[KnowledgeChunk, float, List[str]]],
        query: KnowledgeRetrievalQuery,
        rrf_k: int = 20,
    ) -> List[RetrievedChunk]:
        """
        Fuses candidates from lexical and semantic channels using Reciprocal Rank Fusion (RRF)
        and normalized convex combination:
        RRF(d) = 0.5 / (k + rank_lex) + 0.5 / (k + rank_sem)
        """
        # Sort each channel descending to get ranks
        sorted_lex = sorted(lexical_results, key=lambda x: x[1], reverse=True)
        sorted_sem = sorted(semantic_results, key=lambda x: x[1], reverse=True)

        lex_rank_map: Dict[str, int] = {}
        for rank, (chk, s, _) in enumerate(sorted_lex, start=1):
            if s > 0.0:
                lex_rank_map[chk.chunk_id] = rank

        sem_rank_map: Dict[str, int] = {}
        for rank, (chk, s, _) in enumerate(sorted_sem, start=1):
            if s > 0.15:
                sem_rank_map[chk.chunk_id] = rank

        max_lex = max([s for _, s, _ in lexical_results], default=1.0) or 1.0

        lex_map = {chk.chunk_id: (s, r) for chk, s, r in lexical_results}
        sem_map = {chk.chunk_id: (s, r) for chk, s, r in semantic_results}

        fused_candidates: List[RetrievedChunk] = []

        for chk in eligible_chunks:
            cid = chk.chunk_id
            s_lex, r_lex = lex_map.get(cid, (0.0, []))
            s_sem, r_sem = sem_map.get(cid, (0.0, []))

            # If explicit ID requested, always retain
            is_explicit = chk.document_id in query.required_knowledge_ids

            # Check if chunk qualifies in either channel
            in_lex = cid in lex_rank_map
            in_sem = cid in sem_rank_map

            if not in_lex and not in_sem and not is_explicit:
                continue

            # Reciprocal Rank Fusion
            rank_lex = lex_rank_map.get(cid, 1000)
            rank_sem = sem_rank_map.get(cid, 1000)
            rrf_score = (0.5 / (rrf_k + rank_lex)) + (0.5 / (rrf_k + rank_sem))

            # Normalized score combination
            norm_lex = min(1.0, s_lex / max_lex)
            norm_sem = min(1.0, s_sem)

            # Composite fusion score
            fusion_score = (rrf_score * 10.0) + (0.4 * norm_lex) + (0.6 * norm_sem)

            # Combine match explanations
            combined_reasons = []
            if in_sem and r_sem:
                combined_reasons.extend(r_sem)
            if in_lex and r_lex:
                combined_reasons.extend(r_lex)

            fused_candidates.append(
                RetrievedChunk(
                    chunk=chk,
                    score=fusion_score,
                    lexical_score=float(s_lex),
                    semantic_score=float(s_sem),
                    fusion_score=float(fusion_score),
                    match_reasons=combined_reasons,
                )
            )

        return fused_candidates

    # =========================================================================
    # Stage 4: Context Reranking
    # =========================================================================

    def _rerank_candidates(
        self,
        candidates: List[RetrievedChunk],
        query: KnowledgeRetrievalQuery,
    ) -> List[RetrievedChunk]:
        """
        Applies domain context adjustments to candidate scores:
        - Explicit required_knowledge_ids boost (+10.0)
        - Video type alignment boost (+5.0) or incompatibility penalty (-3.0)
        - Platform alignment boost (+2.0)
        - Preserves strict deterministic tie-breaking.
        """
        reranked: List[RetrievedChunk] = []

        for cand in candidates:
            chk = cand.chunk
            adj_score = cand.score
            reasons = list(cand.match_reasons)

            # 1. Explicit ID boost (highest authority)
            if chk.document_id in query.required_knowledge_ids:
                adj_score += 10.0
                reasons.insert(0, f"Explicitly required by ID '{chk.document_id}'")

            # 2. Video type alignment
            if query.video_type and chk.video_types:
                vt_lower = [vt.lower() for vt in chk.video_types]
                if query.video_type.lower() in vt_lower:
                    adj_score += 5.0
                    reasons.append(f"Video type aligned: '{query.video_type}'")
                else:
                    # Mild mismatch penalty
                    adj_score = max(0.0, adj_score - 2.5)

            # 3. Platform alignment
            if query.platform and chk.platforms:
                p_lower = [p.lower() for p in chk.platforms]
                if query.platform.lower() in p_lower:
                    adj_score += 2.0
                    reasons.append(f"Platform aligned: '{query.platform}'")

            reranked.append(
                RetrievedChunk(
                    chunk=chk,
                    score=adj_score,
                    lexical_score=cand.lexical_score,
                    semantic_score=cand.semantic_score,
                    fusion_score=cand.fusion_score,
                    match_reasons=reasons,
                )
            )

        # Strict deterministic sort: descending by score, tie-break by document_id and chunk_id
        reranked.sort(key=lambda rc: (rc.score, rc.chunk.document_id, rc.chunk.chunk_id), reverse=True)
        return reranked

    # =========================================================================
    # Master Retrieval Pipeline
    # =========================================================================

    def retrieve(self, query: KnowledgeRetrievalQuery) -> KnowledgeRetrievalResult:
        """
        Executes the full hybrid retrieval flow:
        1. Hard Metadata Filtering
        2. Candidate Generation (Lexical and/or Semantic)
        3. Candidate Fusion
        4. Context Reranking
        5. Deterministic Deduplication
        6. Context Bounding
        """
        query_tokens = tokenize(query.query)
        excluded_docs: Dict[str, str] = {}
        all_chunks = self.indexer.all_chunks()
        total_candidates_examined = len(all_chunks)

        # Stage 1: Metadata Filtering (Hard constraints)
        eligible_chunks: List[KnowledgeChunk] = []
        for chk in all_chunks:
            ok, reason = self._check_metadata_eligibility(chk, query, excluded_docs)
            if ok:
                eligible_chunks.append(chk)

        # Stage 2: Candidate Generation & Channel Execution
        target_mode = query.retrieval_mode
        actual_mode = target_mode
        degraded_reason: Optional[str] = None
        fused_candidates: List[RetrievedChunk] = []

        lex_count = 0
        sem_count = 0

        # Mode A: LEXICAL_ONLY
        if target_mode == RetrievalMode.LEXICAL_ONLY:
            lex_results = self._run_lexical_channel(eligible_chunks, query)
            lex_count = sum(1 for _, s, _ in lex_results if s > 0.0)
            for chk, s_lex, reasons in lex_results:
                if s_lex > 0.0 or chk.document_id in query.required_knowledge_ids:
                    fused_candidates.append(
                        RetrievedChunk(
                            chunk=chk,
                            score=s_lex,
                            lexical_score=s_lex,
                            match_reasons=reasons,
                        )
                    )

        # Mode B: SEMANTIC_ONLY
        elif target_mode == RetrievalMode.SEMANTIC_ONLY:
            sem_results = self._run_semantic_channel(eligible_chunks, query)
            sem_count = sum(1 for _, s, _ in sem_results if s > 0.15)
            for chk, s_sem, reasons in sem_results:
                if s_sem > 0.15 or chk.document_id in query.required_knowledge_ids:
                    fused_candidates.append(
                        RetrievedChunk(
                            chunk=chk,
                            score=s_sem * 10.0,
                            semantic_score=s_sem,
                            match_reasons=reasons,
                        )
                    )

        # Mode C: HYBRID (Default)
        else:
            # Check availability of semantic backend
            if not self.semantic_scorer.is_available():
                actual_mode = RetrievalMode.DEGRADED_LEXICAL
                degraded_reason = "Semantic retrieval backend unavailable (offline or disabled)"
                lex_results = self._run_lexical_channel(eligible_chunks, query)
                lex_count = sum(1 for _, s, _ in lex_results if s > 0.0)
                for chk, s_lex, reasons in lex_results:
                    if s_lex > 0.0 or chk.document_id in query.required_knowledge_ids:
                        fused_candidates.append(
                            RetrievedChunk(
                                chunk=chk,
                                score=s_lex,
                                lexical_score=s_lex,
                                match_reasons=reasons,
                            )
                        )
            else:
                try:
                    lex_results = self._run_lexical_channel(eligible_chunks, query)
                    sem_results = self._run_semantic_channel(eligible_chunks, query)
                    lex_count = sum(1 for _, s, _ in lex_results if s > 0.0)
                    sem_count = sum(1 for _, s, _ in sem_results if s > 0.15)

                    fused_candidates = self._fuse_candidates(
                        eligible_chunks=eligible_chunks,
                        lexical_results=lex_results,
                        semantic_results=sem_results,
                        query=query,
                    )
                    actual_mode = RetrievalMode.HYBRID
                except Exception as exc:
                    actual_mode = RetrievalMode.DEGRADED_LEXICAL
                    degraded_reason = f"Semantic retrieval failure: {exc}"
                    lex_results = self._run_lexical_channel(eligible_chunks, query)
                    lex_count = sum(1 for _, s, _ in lex_results if s > 0.0)
                    for chk, s_lex, reasons in lex_results:
                        if s_lex > 0.0 or chk.document_id in query.required_knowledge_ids:
                            fused_candidates.append(
                                RetrievedChunk(
                                    chunk=chk,
                                    score=s_lex,
                                    lexical_score=s_lex,
                                    match_reasons=reasons,
                                )
                            )

        # Stage 3: Context Reranking
        reranked_candidates = self._rerank_candidates(fused_candidates, query)

        # Stage 4: Deduplication
        deduplicated: List[RetrievedChunk] = []
        seen_content_hashes: Set[str] = set()
        seen_sections: Set[Tuple[str, str]] = set()

        for cand in reranked_candidates:
            c_hash = cand.chunk.content_hash
            section_key = (cand.chunk.document_id, cand.chunk.section)

            if c_hash in seen_content_hashes:
                continue
            if section_key in seen_sections:
                continue

            seen_content_hashes.add(c_hash)
            seen_sections.add(section_key)
            deduplicated.append(cand)

        # Stage 5: Context Bounding
        bounded_chunks: List[RetrievedChunk] = []
        current_tokens = 0

        for cand in deduplicated:
            if len(bounded_chunks) >= query.limit_chunks:
                break
            chunk_tokens = self._estimate_tokens(cand.chunk.content)
            if current_tokens + chunk_tokens > query.max_tokens and bounded_chunks:
                break
            bounded_chunks.append(cand)
            current_tokens += chunk_tokens

        selected_doc_ids = sorted(list({rc.chunk.document_id for rc in bounded_chunks}))

        return KnowledgeRetrievalResult(
            query=query,
            chunks=bounded_chunks,
            selected_documents=selected_doc_ids,
            excluded_documents=excluded_docs,
            total_candidates_examined=total_candidates_examined,
            total_tokens_estimated=current_tokens,
            retrieval_mode=actual_mode,
            degraded_reason=degraded_reason,
            audit_trail={
                "retrieval_mode": actual_mode.value,
                "degraded_reason": degraded_reason,
                "lexical_candidates_count": lex_count,
                "semantic_candidates_count": sem_count,
                "query_token_count": len(query_tokens),
                "eligible_chunks_count": len(eligible_chunks),
                "scored_candidates_count": len(fused_candidates),
                "deduplicated_count": len(deduplicated),
                "bounded_count": len(bounded_chunks),
                "excluded_doc_count": len(excluded_docs),
            },
        )
