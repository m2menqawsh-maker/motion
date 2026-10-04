"""
tests/ai/knowledge/test_knowledge_platform.py
============================================
Comprehensive unit, negative, and behavioral test suite for Knowledge Platform (S28-02).

Covers:
- KnowledgeRegistry (registration, versioning, active status filtering)
- KnowledgeLoader (source loading, SHA-256 validation, hash mismatch rejection, missing source handling)
- KnowledgeIndexer (semantic chunking, provenance retention, inverted index)
- KnowledgeRetriever (metadata filtering, scoring, reranking, deduplication, context bounding)
- Hard exclusion of retired knowledge, wrong versions, and audio-incompatible content.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import (
    KnowledgeCategory,
    KnowledgeDescriptor,
    KnowledgeStatus,
    RetrievalMode,
)
from ai.knowledge.contracts import (
    KnowledgeChunk,
    KnowledgeRetrievalQuery,
)
from ai.knowledge.indexer import KnowledgeIndexer, tokenize
from ai.knowledge.loader import (
    KnowledgeHashMismatchError,
    KnowledgeLoader,
    KnowledgeRetiredError,
    KnowledgeSourceNotFoundError,
    LoadedKnowledgeDocument,
)
from ai.knowledge.registry import (
    DuplicateKnowledgeError,
    KnowledgeRegistry,
)
from ai.knowledge.retriever import KnowledgeRetriever
from ai.knowledge.router import KnowledgeRouter
from ai.knowledge.semantic import (
    BaseSemanticScorer,
    DenseConceptSemanticScorer,
    UnavailableSemanticScorer,
)


@pytest.fixture
def workspace_root():
    return Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def populated_platform(workspace_root):
    """Initializes and returns a fully populated KnowledgeRouter with canonical catalog."""
    registry = KnowledgeRegistry()
    loader = KnowledgeLoader(workspace_root=workspace_root)
    indexer = KnowledgeIndexer()
    router = KnowledgeRouter(
        registry=registry,
        indexer=indexer,
        loader=loader,
        workspace_root=workspace_root,
    )
    router.initialize_canonical_catalog(verify_hash=True)
    return router


# =========================================================================
# 1. KnowledgeRegistry Tests
# =========================================================================

def test_registry_registration_and_retrieval():
    reg = KnowledgeRegistry()
    desc = KnowledgeDescriptor(
        knowledge_id="know_test_01",
        title="Test Guide",
        category="ENGINEERING_GUIDE",
        source_uri="references/test.md",
        content_hash="abc123",
        version="1.0.0",
        status=KnowledgeStatus.ACTIVE,
    )
    reg.register(desc)

    assert reg.get("know_test_01") is not None
    assert reg.get("know_test_01").title == "Test Guide"
    assert reg.is_active("know_test_01") is True
    assert len(reg.list_active()) == 1


def test_registry_rejects_duplicate_when_disallowed():
    reg = KnowledgeRegistry()
    desc = KnowledgeDescriptor(
        knowledge_id="know_test_dup",
        title="Test Guide",
        category="ENGINEERING_GUIDE",
        source_uri="references/test.md",
        content_hash="abc123",
        version="1.0.0",
        status=KnowledgeStatus.ACTIVE,
    )
    reg.register(desc)
    with pytest.raises(DuplicateKnowledgeError):
        reg.register(desc, allow_overwrite=False)


def test_registry_excludes_retired_knowledge():
    reg = KnowledgeRegistry()
    desc_retired = KnowledgeDescriptor(
        knowledge_id="know_legacy_doc",
        title="Legacy Obsolete Guide",
        category="PLAYBOOK",
        source_uri="references/legacy.md",
        content_hash="def456",
        version="1.0.0",
        status=KnowledgeStatus.RETIRED,
    )
    reg.register(desc_retired)

    # get() returns the item for inspection
    assert reg.get("know_legacy_doc") is not None
    # get_active() strictly excludes RETIRED
    assert reg.get_active("know_legacy_doc") is None
    assert reg.is_active("know_legacy_doc") is False
    assert len(reg.list_active()) == 0


def test_registry_version_lookup():
    reg = KnowledgeRegistry()
    desc_v1 = KnowledgeDescriptor(
        knowledge_id="know_versioned",
        title="Doc v1",
        category="PLAYBOOK",
        source_uri="references/v1.md",
        content_hash="111",
        version="1.0.0",
        status=KnowledgeStatus.RETIRED,
    )
    desc_v2 = KnowledgeDescriptor(
        knowledge_id="know_versioned",
        title="Doc v2",
        category="PLAYBOOK",
        source_uri="references/v2.md",
        content_hash="222",
        version="2.0.0",
        status=KnowledgeStatus.ACTIVE,
    )
    reg.register(desc_v1)
    reg.register(desc_v2)

    assert reg.get("know_versioned", version="1.0.0").status == KnowledgeStatus.RETIRED
    assert reg.get("know_versioned", version="2.0.0").status == KnowledgeStatus.ACTIVE
    assert reg.get("know_versioned", version="3.0.0") is None
    # Latest active version returned by default
    assert reg.get("know_versioned").version == "2.0.0"


# =========================================================================
# 2. KnowledgeLoader Tests
# =========================================================================

def test_loader_loads_canonical_references(workspace_root):
    loader = KnowledgeLoader(workspace_root=workspace_root)
    docs = loader.load_canonical_catalog(verify_hash=True)
    assert len(docs) >= 15
    for doc in docs:
        assert len(doc.content) > 0
        assert doc.absolute_path.exists()
        assert doc.descriptor.knowledge_id.startswith("know_")


def test_loader_rejects_missing_file(workspace_root):
    loader = KnowledgeLoader(workspace_root=workspace_root)
    desc = KnowledgeDescriptor(
        knowledge_id="know_missing",
        title="Missing Doc",
        category="SOP",
        source_uri="references/non_existent_file_9999.md",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    with pytest.raises(KnowledgeSourceNotFoundError):
        loader.load_document(desc, verify_hash=True)


def test_loader_rejects_hash_mismatch(workspace_root):
    loader = KnowledgeLoader(workspace_root=workspace_root)
    desc = KnowledgeDescriptor(
        knowledge_id="know_tampered",
        title="Tampered Doc",
        category="SOP",
        source_uri="references/2_sops/spoken_vo_humanizer.md",
        content_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    with pytest.raises(KnowledgeHashMismatchError):
        loader.load_document(desc, verify_hash=True)


def test_loader_rejects_retired_doc_in_strict_mode(workspace_root):
    loader = KnowledgeLoader(workspace_root=workspace_root)
    desc = KnowledgeDescriptor(
        knowledge_id="know_retired",
        title="Retired Doc",
        category="SOP",
        source_uri="references/2_sops/spoken_vo_humanizer.md",
        content_hash="1b2dfc24a8de75716c0256045ecdd8ad8dce455bb2ae4f0a6120f963cefb513b",
        status=KnowledgeStatus.RETIRED,
    )
    with pytest.raises(KnowledgeRetiredError):
        loader.load_document(desc, verify_hash=True, strict_status=True)


# =========================================================================
# 3. KnowledgeIndexer Semantic Chunking Tests
# =========================================================================

def test_indexer_semantic_boundaries_and_provenance(workspace_root):
    loader = KnowledgeLoader(workspace_root=workspace_root)
    desc = KnowledgeDescriptor(
        knowledge_id="know_sop_spoken_vo",
        title="Spoken-VO Humanizer SOP (Speech & Cadence)",
        category="SOP",
        source_uri="references/2_sops/spoken_vo_humanizer.md",
        content_hash="1b2dfc24a8de75716c0256045ecdd8ad8dce455bb2ae4f0a6120f963cefb513b",
        version="1.0.0",
        tags=["voiceover", "speech"],
        audio_modes=[AudioMode.VO_ONLY, AudioMode.VO_MUSIC],
    )
    doc = loader.load_document(desc, verify_hash=True)
    indexer = KnowledgeIndexer()
    chunks = indexer.chunk_document(doc)

    assert len(chunks) > 5
    for chk in chunks:
        # Check complete provenance retention
        assert chk.document_id == "know_sop_spoken_vo"
        assert chk.version == "1.0.0"
        assert chk.source == "references/2_sops/spoken_vo_humanizer.md"
        assert len(chk.content_hash) == 64
        assert chk.chunk_id.startswith("chk_")
        assert len(chk.section) > 0
        assert chk.authority_level == 5

    # Check rule boundary detection
    rule_chunks = [c for c in chunks if "Rule 1" in c.section or "Rule 2" in c.section]
    assert len(rule_chunks) >= 2


# =========================================================================
# 4. KnowledgeRetriever Filtering, Deduplication & Bounding Tests
# =========================================================================

def test_retriever_music_only_excludes_voiceover(populated_platform):
    """
    Key Acceptance Scenario:
    music-only montage must NEVER retrieve spoken VO knowledge or TTS SOPs.
    """
    query = KnowledgeRetrievalQuery(
        query="High energy dynamic video montage with rhythmic cuts and audio beat drops",
        video_type="montage",
        audio_mode=AudioMode.MUSIC_ONLY,
        limit_chunks=5,
    )
    res = populated_platform.retriever.retrieve(query)

    assert len(res.chunks) > 0
    for rc in res.chunks:
        assert rc.chunk.document_id != "know_sop_spoken_vo"
        assert rc.chunk.document_id != "know_playbook_video_copy"
        assert "voiceover" not in rc.chunk.tags
        # Audio mode compatibility holds
        if rc.chunk.audio_modes:
            assert AudioMode.MUSIC_ONLY in rc.chunk.audio_modes or len(rc.chunk.audio_modes) == 0

    assert "know_sop_spoken_vo" in res.excluded_documents
    assert res.excluded_documents["know_sop_spoken_vo"] == "INCOMPATIBLE_AUDIO_MODE"


def test_retriever_excludes_retired_documents(populated_platform):
    # Dynamically retire a document in the registry
    desc = populated_platform.registry.get("know_playbook_ffmpeg")
    retired_desc = desc.model_copy(update={"status": KnowledgeStatus.RETIRED})
    populated_platform.registry.register(retired_desc, allow_overwrite=True)

    query = KnowledgeRetrievalQuery(
        query="FFmpeg normalization transcoding command line",
        limit_chunks=5,
    )
    res = populated_platform.retriever.retrieve(query)

    for rc in res.chunks:
        assert rc.chunk.document_id != "know_playbook_ffmpeg"
    assert "know_playbook_ffmpeg" in res.excluded_documents
    assert res.excluded_documents["know_playbook_ffmpeg"] == "STATUS_KnowledgeStatus.RETIRED" or "STATUS_RETIRED" in res.excluded_documents["know_playbook_ffmpeg"]


def test_retriever_excludes_mismatched_version(populated_platform):
    query = KnowledgeRetrievalQuery(
        query="Living canvas continuous explainer",
        version="2.5.0",  # Available is 1.0.0
        limit_chunks=5,
    )
    res = populated_platform.retriever.retrieve(query)
    for rc in res.chunks:
        assert rc.chunk.version == "2.5.0"
    assert "know_playbook_living_canvas" in res.excluded_documents


def test_retriever_deduplication(populated_platform):
    """Verifies that duplicated identical chunks are removed deterministically."""
    # Index duplicate copies of the same document under a temporary indexer
    indexer = KnowledgeIndexer()
    doc = populated_platform.loader.load_canonical_catalog()[0]
    indexer.index_document(doc)
    # Add a second doc with identical chunk text
    duplicate_doc = LoadedKnowledgeDocument(
        descriptor=doc.descriptor.model_copy(update={"knowledge_id": "know_mirror_copy"}),
        content=doc.content,
        absolute_path=doc.absolute_path,
    )
    indexer.index_document(duplicate_doc)

    retriever = KnowledgeRetriever(indexer=indexer)
    query = KnowledgeRetrievalQuery(
        query=doc.descriptor.title,
        limit_chunks=10,
    )
    res = retriever.retrieve(query)

    # Verify no identical content_hash appears twice
    hashes = [rc.chunk.content_hash for rc in res.chunks]
    assert len(hashes) == len(set(hashes))


def test_retriever_context_bounding(populated_platform):
    query = KnowledgeRetrievalQuery(
        query="animation explainer spring motion design physics remotion rules",
        limit_chunks=3,
        max_tokens=800,
    )
    res = populated_platform.retriever.retrieve(query)
    assert len(res.chunks) <= 3
    assert res.total_tokens_estimated <= 800


# =========================================================================
# 5. Hybrid & Semantic Retrieval Tests (S28-02A)
# =========================================================================

def test_semantic_paraphrase_retrieval(populated_platform):
    """
    Semantic Paraphrase Test:
    Query wording differs significantly from document titles/tags,
    but semantic meaning is equivalent (conversational speech delivery dynamics).
    Proves that semantic channel successfully identifies the relevant knowledge.
    """
    query = KnowledgeRetrievalQuery(
        query="dialogue delivery natural rhythm and pause dynamics without robotic monotonic cadence",
        video_type="explainer",
        audio_mode=AudioMode.VO_ONLY,
        retrieval_mode=RetrievalMode.HYBRID,
        limit_chunks=4,
    )
    res = populated_platform.retriever.retrieve(query)

    assert len(res.chunks) > 0
    assert res.retrieval_mode == RetrievalMode.HYBRID
    retrieved_doc_ids = {rc.chunk.document_id for rc in res.chunks}

    # Must retrieve spoken VO humanizer via semantic alignment
    assert "know_sop_spoken_vo" in retrieved_doc_ids
    vo_chunk = next(rc for rc in res.chunks if rc.chunk.document_id == "know_sop_spoken_vo")
    assert vo_chunk.semantic_score is not None
    assert vo_chunk.semantic_score > 0.15


def test_lexical_false_friend_resolution(populated_platform):
    """
    Lexical False-Friend Test:
    Query has lexical overlap with voiceover/spoken words,
    but semantic intent is audio volume ducking and sound design.
    Proves that sound design / SFX knowledge ranks higher than spoken VO.
    """
    query = KnowledgeRetrievalQuery(
        query="audio volume ducking and sound design attenuation under spoken voiceover",
        audio_mode=AudioMode.VO_MUSIC,
        retrieval_mode=RetrievalMode.HYBRID,
        limit_chunks=4,
    )
    res = populated_platform.retriever.retrieve(query)

    assert len(res.chunks) > 0
    top_doc_id = res.chunks[0].chunk.document_id
    # Top document must be sound design / SFX matrix, not spoken VO
    assert top_doc_id in ("know_taste_sfx_matrix", "know_sop_sound_design")

    # If spoken VO is present, sound design must have a strictly higher score
    vo_chunks = [rc for rc in res.chunks if rc.chunk.document_id == "know_sop_spoken_vo"]
    if vo_chunks:
        assert res.chunks[0].score > vo_chunks[0].score


def test_explicit_retrieval_modes(populated_platform):
    """
    Verifies that caller can explicitly invoke LEXICAL_ONLY, SEMANTIC_ONLY, or HYBRID.
    """
    base_query_text = "motion collage posters dynamic animation cut rhythm"

    # 1. Lexical only
    q_lex = KnowledgeRetrievalQuery(
        query=base_query_text,
        retrieval_mode=RetrievalMode.LEXICAL_ONLY,
        limit_chunks=3,
    )
    res_lex = populated_platform.retriever.retrieve(q_lex)
    assert res_lex.retrieval_mode == RetrievalMode.LEXICAL_ONLY
    for rc in res_lex.chunks:
        assert rc.lexical_score is not None

    # 2. Semantic only
    q_sem = KnowledgeRetrievalQuery(
        query=base_query_text,
        retrieval_mode=RetrievalMode.SEMANTIC_ONLY,
        limit_chunks=3,
    )
    res_sem = populated_platform.retriever.retrieve(q_sem)
    assert res_sem.retrieval_mode == RetrievalMode.SEMANTIC_ONLY
    for rc in res_sem.chunks:
        assert rc.semantic_score is not None

    # 3. Hybrid (default)
    q_hyb = KnowledgeRetrievalQuery(
        query=base_query_text,
        retrieval_mode=RetrievalMode.HYBRID,
        limit_chunks=3,
    )
    res_hyb = populated_platform.retriever.retrieve(q_hyb)
    assert res_hyb.retrieval_mode == RetrievalMode.HYBRID
    for rc in res_hyb.chunks:
        assert rc.fusion_score is not None


def test_degraded_lexical_mode_when_semantic_unavailable(populated_platform):
    """
    Offline / Failure Behavior Test:
    When semantic backend is unavailable or offline, retriever must:
    1. Explicitly switch to DEGRADED_LEXICAL mode (no silent fallback).
    2. Provide clear degraded_reason in the result.
    3. Maintain all hard metadata constraints (MUSIC_ONLY exclusion still strictly enforced).
    4. Not create any security or authority bypass.
    """
    failing_scorer = UnavailableSemanticScorer(failure_mode="model_service_timeout")
    degraded_retriever = KnowledgeRetriever(
        indexer=populated_platform.indexer,
        registry=populated_platform.registry,
        semantic_scorer=failing_scorer,
    )

    # Test degraded query under MUSIC_ONLY
    query = KnowledgeRetrievalQuery(
        query="High energy dynamic video montage with rhythmic cuts and audio beat drops",
        video_type="montage",
        audio_mode=AudioMode.MUSIC_ONLY,
        retrieval_mode=RetrievalMode.HYBRID,
        limit_chunks=4,
    )
    res = degraded_retriever.retrieve(query)

    # Must explicitly declare DEGRADED_LEXICAL mode
    assert res.retrieval_mode == RetrievalMode.DEGRADED_LEXICAL
    assert res.degraded_reason is not None
    assert "unavailable" in res.degraded_reason.lower()

    # Lexical results still returned
    assert len(res.chunks) > 0

    # Invariant preserved: MUSIC_ONLY still strictly excludes spoken VO
    retrieved_docs = {rc.chunk.document_id for rc in res.chunks}
    assert "know_sop_spoken_vo" not in retrieved_docs
    assert "know_sop_spoken_vo" in res.excluded_documents

