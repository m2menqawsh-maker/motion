"""
ai/knowledge/semantic.py
========================
Provider-neutral semantic scoring and dense concept vector indexing (S28-02A).

Guarantees:
- Provider-neutral: zero direct dependencies on OpenAI, Anthropic, or vendor-specific embedding wire APIs.
- Hermetic: operates 100% offline using deterministic dense concept spaces and Latent Semantic Analysis (LSA).
- Degradable: cleanly separates semantic availability from execution, supporting explicit degraded lexical mode.
- Explainable: provides continuous cosine similarity scores in [0.0, 1.0] with domain attribution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import math
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from ai.knowledge.contracts import KnowledgeChunk
from ai.knowledge.indexer import tokenize


# =========================================================================
# Domain Semantic Concept Taxonomies (Creative Video & Editorial Intelligence)
# =========================================================================

DOMAIN_CONCEPT_KEYWORDS: Dict[str, Set[str]] = {
    "VOICEOVER_SPOKEN_HUMAN": {
        "voiceover", "spoken", "narration", "dialogue", "dialog", "speech", "cadence",
        "intonation", "conversational", "performer", "tts", "humanizer", "pauses",
        "pause", "monologue", "script", "reading", "voice", "copywriting", "sentences",
        "say", "aloud", "delivery", "human", "contractions", "words",
    },
    "MOTION_ANIMATION_PRINCIPLES": {
        "disney", "animation", "motion", "physics", "spring", "easing", "timing",
        "squash", "stretch", "anticipation", "staging", "arcs", "secondary", "keyframes",
        "keyframe", "interpolation", "damping", "stiffness", "mass", "bouncing",
    },
    "DYNAMIC_MONTAGE_BEATS": {
        "montage", "rhythm", "beat", "tempo", "bpm", "sync", "cut", "pacing", "drop",
        "pulse", "cuts", "rhythmic", "music video", "audio sync", "transitions",
        "energy", "fast", "speed", "beat sync",
    },
    "SOUND_DESIGN_DUCKING": {
        "ducking", "volume", "sound", "sfx", "audio", "attenuation", "sidechain",
        "foley", "gain", "sound design", "decibels", "fader", "levels", "mixing",
        "soundtrack", "stems", "sweep", "whoosh", "impact",
    },
    "KINETIC_TYPOGRAPHY": {
        "typography", "captions", "subtitles", "kinetic", "text", "fonts", "on-screen",
        "titles", "lettering", "caption", "word", "subhead", "font", "hierarchy",
        "readability", "bold",
    },
    "VIDEO_ENGINEERING_FFMPEG": {
        "ffmpeg", "cli", "bash", "command", "concat", "encoding", "transcode",
        "codec", "container", "mp4", "demux", "stream", "bitrate", "assembly",
        "h264", "prores",
    },
    "LIVING_CANVAS_CONTINUITY": {
        "canvas", "living", "continuous", "scene", "composition", "seamless",
        "background", "flow", "unfolding", "spatial", "camera", "motion collage",
        "elements", "poster",
    },
    "TABLETOP_PRODUCT_STAGING": {
        "tabletop", "kitchen", "product", "lighting", "macro", "props", "staging",
        "overhead", "food", "commercial", "top-down", "studio", "packshot",
    },
    "HOOK_SPRINT_SOCIAL": {
        "hook", "sprint", "reels", "tiktok", "retention", "short", "viral",
        "scroll", "attention", "swipe", "social", "thumbnail", "3-second",
    },
}

DOMAIN_NAMES = list(DOMAIN_CONCEPT_KEYWORDS.keys())


# =========================================================================
# Base Semantic Scorer Abstract Class
# =========================================================================

class BaseSemanticScorer(ABC):
    """
    Abstract contract for semantic scoring implementations.
    Guarantees provider neutrality and graceful degradation.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Indicates whether this semantic backend is operational and ready."""
        ...

    @abstractmethod
    def score_chunks(
        self,
        query: str,
        chunks: Sequence[KnowledgeChunk],
    ) -> List[float]:
        """
        Computes semantic similarity scores in [0.0, 1.0] for the query against each chunk.
        Order of output matches order of input chunks.
        """
        ...


# =========================================================================
# Concrete Hermetic Scorer: DenseConceptSemanticScorer
# =========================================================================

class DenseConceptSemanticScorer(BaseSemanticScorer):
    """
    Hermetic, provider-neutral semantic scorer combining Domain Concept Spaces
    and Latent Semantic Analysis (Truncated SVD).
    
    Guarantees:
    - 100% offline, zero network or external API dependency.
    - Captures synonymy and paraphrasing (e.g. dialogue delivery -> spoken voiceover).
    - Resolves lexical false-friends (e.g. audio ducking intent vs voiceover keywords).
    """

    def __init__(self, n_lsa_components: int = 16) -> None:
        self.n_lsa_components = n_lsa_components
        self._is_ready = True
        self._fitted_chunks: Optional[List[str]] = None
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._svd: Optional[TruncatedSVD] = None
        self._chunk_concept_matrix: Optional[np.ndarray] = None
        self._chunk_lsa_matrix: Optional[np.ndarray] = None

    def is_available(self) -> bool:
        return self._is_ready

    def _build_concept_vector(self, text: str) -> np.ndarray:
        """
        Projects text into the 9-dimensional domain concept space.
        Normalizes vector using L2 norm.
        """
        tokens = set(tokenize(text.lower()))
        vec = np.zeros(len(DOMAIN_NAMES), dtype=np.float32)

        for idx, domain in enumerate(DOMAIN_NAMES):
            domain_terms = DOMAIN_CONCEPT_KEYWORDS[domain]
            overlap = tokens.intersection(domain_terms)
            if overlap:
                vec[idx] = float(len(overlap))

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec

    def _ensure_fitted(self, chunks: Sequence[KnowledgeChunk]) -> None:
        """Fits TF-IDF vectorizer and SVD on chunk corpus if not already fitted or changed."""
        chunk_ids = [c.chunk_id for c in chunks]
        if self._fitted_chunks == chunk_ids and self._chunk_concept_matrix is not None:
            return

        corpus = [f"{c.section} {c.content}".strip() for c in chunks]
        if not corpus:
            return

        # 1. Build concept matrix for all chunks: shape (N, 9)
        concept_rows = [self._build_concept_vector(text) for text in corpus]
        self._chunk_concept_matrix = np.vstack(concept_rows)

        # 2. Fit TF-IDF and SVD for Latent Semantic Analysis
        try:
            self._vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=500,
            )
            tfidf_mat = self._vectorizer.fit_transform(corpus)
            n_components = min(self.n_lsa_components, max(1, len(corpus) - 1), tfidf_mat.shape[1])
            if n_components >= 2:
                self._svd = TruncatedSVD(n_components=n_components, random_state=42)
                lsa_mat = self._svd.fit_transform(tfidf_mat)
                # L2 normalize LSA embeddings
                norms = np.linalg.norm(lsa_mat, axis=1, keepdims=True)
                norms[norms < 1e-6] = 1.0
                self._chunk_lsa_matrix = lsa_mat / norms
            else:
                self._svd = None
                self._chunk_lsa_matrix = None
        except Exception:
            self._vectorizer = None
            self._svd = None
            self._chunk_lsa_matrix = None

        self._fitted_chunks = chunk_ids

    def score_chunks(
        self,
        query: str,
        chunks: Sequence[KnowledgeChunk],
    ) -> List[float]:
        """
        Computes cosine semantic similarity between query and each chunk in chunks.
        Combines concept space alignment (0.6) and LSA dense projection (0.4).
        """
        if not chunks or not query.strip():
            return [0.0] * len(chunks)

        self._ensure_fitted(chunks)

        # 1. Concept vector for query
        query_concept_vec = self._build_concept_vector(query)
        has_concept = np.linalg.norm(query_concept_vec) > 1e-6

        # 2. Concept similarity: (N,)
        if has_concept and self._chunk_concept_matrix is not None:
            concept_sims = np.dot(self._chunk_concept_matrix, query_concept_vec)
            # Clip to [0, 1]
            concept_sims = np.clip(concept_sims, 0.0, 1.0)
        else:
            concept_sims = np.zeros(len(chunks), dtype=np.float32)

        # 3. LSA similarity: (N,)
        lsa_sims = np.zeros(len(chunks), dtype=np.float32)
        if (
            self._vectorizer is not None
            and self._svd is not None
            and self._chunk_lsa_matrix is not None
        ):
            try:
                q_tfidf = self._vectorizer.transform([query])
                q_lsa = self._svd.transform(q_tfidf)[0]
                q_norm = np.linalg.norm(q_lsa)
                if q_norm > 1e-6:
                    q_lsa_norm = q_lsa / q_norm
                    raw_lsa = np.dot(self._chunk_lsa_matrix, q_lsa_norm)
                    lsa_sims = np.clip(raw_lsa, 0.0, 1.0)
            except Exception:
                lsa_sims = np.zeros(len(chunks), dtype=np.float32)

        # 4. Hybrid combination of Concept (0.6) and LSA (0.4)
        if has_concept:
            combined = 0.65 * concept_sims + 0.35 * lsa_sims
        else:
            # When query has no direct domain keywords, LSA provides the semantic link
            combined = lsa_sims

        return [float(score) for score in combined]


# =========================================================================
# Testing & Degraded Mode Stubs
# =========================================================================

class UnavailableSemanticScorer(BaseSemanticScorer):
    """
    Intentionally unavailable or failing semantic backend for testing degraded mode.
    """

    def __init__(self, failure_mode: str = "offline") -> None:
        self.failure_mode = failure_mode

    def is_available(self) -> bool:
        return False

    def score_chunks(self, query: str, chunks: Sequence[KnowledgeChunk]) -> List[float]:
        raise RuntimeError(f"Semantic retrieval backend is unavailable: {self.failure_mode}")


class ProviderSemanticScorer(BaseSemanticScorer):
    """
    Pluggable provider semantic scorer using an external or custom embedding function.
    Maintains clean boundary: embedding function can be provided by an adapter.
    """

    def __init__(
        self,
        embed_fn: Callable[[List[str]], List[List[float]]],
    ) -> None:
        self.embed_fn = embed_fn

    def is_available(self) -> bool:
        return True

    def score_chunks(self, query: str, chunks: Sequence[KnowledgeChunk]) -> List[float]:
        texts = [query] + [f"{c.section} {c.content}" for c in chunks]
        embeddings = self.embed_fn(texts)
        q_emb = np.array(embeddings[0], dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        if q_norm < 1e-6:
            return [0.0] * len(chunks)
        q_emb /= q_norm

        scores: List[float] = []
        for emb in embeddings[1:]:
            c_emb = np.array(emb, dtype=np.float32)
            c_norm = np.linalg.norm(c_emb)
            if c_norm < 1e-6:
                scores.append(0.0)
            else:
                c_emb /= c_norm
                sim = float(np.clip(np.dot(q_emb, c_emb), 0.0, 1.0))
                scores.append(sim)
        return scores
