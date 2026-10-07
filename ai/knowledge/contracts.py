"""
ai/knowledge/contracts.py
=========================
Runtime types, chunks, query specifications, and retrieval results for the
Knowledge Platform (S28-02).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Strict provenance tracking for every semantic chunk (document_id, section, version, source, hash).
- Provider neutrality: retrieval structures are independent of third-party APIs.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import (
    KnowledgeCategory,
    KnowledgeDescriptor,
    KnowledgeStatus,
    RetrievalMode,
)


class KnowledgeChunk(AIContractModel):
    """
    Atomic semantic unit of knowledge extracted from a document.
    Maintains rigorous provenance linking back to the originating KnowledgeDescriptor.
    """
    chunk_id: str = Field(description="Unique deterministic identifier for the chunk")
    document_id: str = Field(description="Identifier of the originating KnowledgeDescriptor")
    section: str = Field(description="Section heading or structural boundary (e.g., '1. The 12 rules of spoken-human scripts')")
    version: str = Field(description="Version of the source document at chunking time")
    source: str = Field(description="Relative path or URI of source document")
    content: str = Field(description="Raw markdown/text content of this semantic chunk")
    content_hash: str = Field(description="SHA-256 hash of the chunk text content")
    category: str = Field(description="Category inherited from parent document")
    authority_level: int = Field(default=5, ge=1, le=5, description="Hierarchy level (Level 5 = Reference)")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    video_types: List[str] = Field(default_factory=list, description="Target video types")
    platforms: List[str] = Field(default_factory=list, description="Target platforms")
    audio_modes: List[strict_enum(AudioMode)] = Field(default_factory=list, description="Compatible audio presentation modes")
    language: str = Field(default="any", description="Language code (e.g., 'ar', 'en', 'any')")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Additional structural metadata")

    @classmethod
    def create(
        cls,
        document_id: str,
        section: str,
        version: str,
        source: str,
        content: str,
        category: str,
        tags: Optional[List[str]] = None,
        video_types: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        audio_modes: Optional[List[AudioMode]] = None,
        language: str = "any",
        metadata: Optional[Dict[str, JsonValue]] = None,
        authority_level: int = 5,
    ) -> KnowledgeChunk:
        """Constructs a KnowledgeChunk computing a deterministic chunk_id and content_hash."""
        normalized_content = content.strip()
        c_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        raw_id_input = f"{document_id}:{version}:{section}:{c_hash[:16]}"
        chunk_id = f"chk_{hashlib.sha256(raw_id_input.encode('utf-8')).hexdigest()[:16]}"

        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            section=section,
            version=version,
            source=source,
            content=normalized_content,
            content_hash=c_hash,
            category=category,
            authority_level=authority_level,
            tags=tags or [],
            video_types=video_types or [],
            platforms=platforms or [],
            audio_modes=audio_modes or [],
            language=language,
            metadata=metadata or {},
        )


class KnowledgeRetrievalQuery(AIContractModel):
    """
    Search and scoping query for creative knowledge retrieval.
    Expresses structured filters and lexical/semantic search parameters.
    """
    query: str = Field(description="Freeform search query or creative context summary")
    video_type: Optional[str] = Field(default=None, description="Optional target video type filter (e.g., 'montage', 'explainer')")
    platform: Optional[str] = Field(default=None, description="Optional target platform filter (e.g., 'youtube', 'tiktok')")
    audio_mode: Optional[strict_enum(AudioMode)] = Field(default=None, description="Target audio mode (enforces hard incompatibility)")
    language: Optional[str] = Field(default=None, description="Language preference or filter (e.g., 'ar', 'en')")
    tags: List[str] = Field(default_factory=list, description="Tags for preference boosting")
    category: Optional[str] = Field(default=None, description="Optional category filter (e.g., 'PLAYBOOK', 'SOP')")
    required_knowledge_ids: List[str] = Field(
        default_factory=list,
        description="Explicit knowledge IDs requested by skills or workflow"
    )
    version: Optional[str] = Field(default=None, description="Specific document version required (if applicable)")
    limit_chunks: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return")
    max_tokens: int = Field(default=2500, ge=100, le=10000, description="Maximum estimated token budget for retrieved context")
    retrieval_mode: strict_enum(RetrievalMode) = Field(
        default=RetrievalMode.HYBRID,
        description="Target retrieval channel: HYBRID, LEXICAL_ONLY, or SEMANTIC_ONLY",
    )


class RetrievedChunk(AIContractModel):
    """An individual retrieved chunk with ranking score, component scores, and decision rationale."""
    chunk: KnowledgeChunk = Field(description="The underlying semantic chunk")
    score: float = Field(ge=0.0, description="Final composite relevance score")
    lexical_score: Optional[float] = Field(default=None, description="Lexical relevance score (BM25/TF-IDF)")
    semantic_score: Optional[float] = Field(default=None, description="Semantic cosine similarity score")
    fusion_score: Optional[float] = Field(default=None, description="Candidate fusion score (RRF or blended)")
    match_reasons: List[str] = Field(default_factory=list, description="Explanations for why this chunk was selected")


class KnowledgeRetrievalResult(AIContractModel):
    """
    The bounded, deterministic output of a knowledge retrieval operation.
    """
    query: KnowledgeRetrievalQuery = Field(description="The query that generated this result")
    chunks: List[RetrievedChunk] = Field(default_factory=list, description="Ranked, deduplicated, bounded chunks")
    selected_documents: List[str] = Field(default_factory=list, description="IDs of documents represented in the chunks")
    excluded_documents: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of document_id to exclusion rationale (e.g., 'INCOMPATIBLE_AUDIO_MODE', 'RETIRED')"
    )
    total_candidates_examined: int = Field(default=0, ge=0, description="Total candidate chunks evaluated")
    total_tokens_estimated: int = Field(default=0, ge=0, description="Estimated total tokens in returned chunks")
    retrieval_mode: strict_enum(RetrievalMode) = Field(
        default=RetrievalMode.HYBRID,
        description="Actual execution mode: HYBRID, LEXICAL_ONLY, SEMANTIC_ONLY, or DEGRADED_LEXICAL",
    )
    degraded_reason: Optional[str] = Field(
        default=None,
        description="Explicit rationale if degraded from HYBRID to LEXICAL_ONLY",
    )
    audit_trail: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Structured decision metadata for observability"
    )
