"""
ai/memory/embeddings.py
=======================
Provider-neutral embedding interface and deterministic fake implementations (S27.6).
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List

from ai.memory.normalization import ContentNormalizer


class EmbeddingProvider(ABC):
    """Abstract provider-neutral boundary for vector embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embeds a single text string into a normalized floating-point vector."""
        raise NotImplementedError

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds multiple text strings into a list of normalized vectors."""
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the canonical model identifier (e.g. text-embedding-3-small)."""
        raise NotImplementedError

    @abstractmethod
    def get_version(self) -> str:
        """Returns the embedding model schema or configuration version."""
        raise NotImplementedError

    @abstractmethod
    def get_dimension(self) -> int:
        """Returns the fixed vector dimension size."""
        raise NotImplementedError


class DeterministicFakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, hermetic embedding provider for testing.
    
    Guarantees:
    - Same normalized content yields the EXACT same unit vector.
    - Semantically identical text (varying only by whitespace/casing) yields the same vector.
    - Vectors are L2-normalized so dot-product equals cosine similarity.
    - Zero network dependencies and zero financial costs.
    """

    def __init__(self, dimension: int = 384, model_name: str = "fake-deterministic-embedder", version: str = "1.0.0"):
        if dimension <= 0:
            raise ValueError("Dimension must be positive.")
        self.dimension = dimension
        self.model_name = model_name
        self.version = version

    def embed_text(self, text: str) -> List[float]:
        norm_text = ContentNormalizer.normalize_for_comparison(text)
        
        # Generate pseudo-random deterministic floats using chained SHA-256 hashes
        vector: List[float] = []
        seed = norm_text.encode("utf-8")
        counter = 0

        while len(vector) < self.dimension:
            counter += 1
            hasher = hashlib.sha256(seed + counter.to_bytes(4, "big"))
            digest = hasher.digest()
            # Unpack 8 floats (32 bytes / 4 bytes each)
            for i in range(0, len(digest), 4):
                if len(vector) >= self.dimension:
                    break
                int_val = int.from_bytes(digest[i:i+4], "big", signed=True)
                # Map to float in range [-1.0, 1.0]
                vector.append(float(int_val) / (2**31))

        # L2-normalize the vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0.0:
            vector[0] = 1.0
            magnitude = 1.0

        return [v / magnitude for v in vector]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def get_model_name(self) -> str:
        return self.model_name

    def get_version(self) -> str:
        return self.version

    def get_dimension(self) -> int:
        return self.dimension
