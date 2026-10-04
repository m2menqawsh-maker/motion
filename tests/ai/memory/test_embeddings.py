"""
tests/ai/memory/test_embeddings.py
==================================
Tests for EmbeddingProvider abstraction and DeterministicFakeEmbeddingProvider (S27.6).
"""

import math
import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider


class TestEmbeddings:

    def test_deterministic_fake_embedding_properties(self):
        """Verifies deterministic unit vector generation, dimensions, and L2 normalization."""
        provider = DeterministicFakeEmbeddingProvider(dimension=384, model_name="test-embedder", version="1.0.0")

        assert provider.get_dimension() == 384
        assert provider.get_model_name() == "test-embedder"
        assert provider.get_version() == "1.0.0"

        text = "Brand guideline: Use #1E3A8A as primary theme color."
        vec = provider.embed_text(text)

        assert len(vec) == 384
        # Verify L2 unit norm
        norm = math.sqrt(sum(v * v for v in vec))
        assert pytest.approx(norm, 1e-5) == 1.0

    def test_same_normalized_content_yields_exact_same_vector(self):
        """Guarantees embedding determinism across invocations."""
        provider = DeterministicFakeEmbeddingProvider(dimension=128)

        text1 = "User prefers 16:9 widescreen layout."
        text2 = "  User prefers 16:9 widescreen layout. \n"

        vec1 = provider.embed_text(text1)
        vec2 = provider.embed_text(text2)

        assert vec1 == vec2

    def test_distinct_content_yields_different_vectors(self):
        """Distinct sentences must yield distinct vectors."""
        provider = DeterministicFakeEmbeddingProvider(dimension=128)

        v1 = provider.embed_text("High energy upbeat electronic background music.")
        v2 = provider.embed_text("Solemn acoustic guitar ambient background music.")

        assert v1 != v2
        # Cosine similarity should be less than 1.0
        similarity = sum(a * b for a, b in zip(v1, v2))
        assert similarity < 0.99

    def test_batch_embedding(self):
        """Verifies embed_batch produces expected output length."""
        provider = DeterministicFakeEmbeddingProvider(dimension=64)
        texts = ["Text A", "Text B", "Text C"]
        vecs = provider.embed_batch(texts)
        assert len(vecs) == 3
        assert len(vecs[0]) == 64
