"""
tests/ai/memory/test_normalization.py
====================================
Tests for content normalization, multilingual/Arabic safety, and deterministic hashing (S27.6).
"""

from ai.memory.normalization import ContentNormalizer


class TestContentNormalization:

    def test_arabic_diacritics_and_typography_preserved(self):
        """Verifies Arabic diacritics, hamzas, and letters are never stripped destructively."""
        arabic_text = "تَفْضِيلُ الخَطِّ: اسْتَخْدِمْ خَطَّ 'القَاهِرَة' (Cairo) مَعَ خَلْفِيَّةٍ عَالِيَةِ التَّبَايُنِ."
        normalized = ContentNormalizer.normalize_text(arabic_text)

        # Diacritics and letters must remain intact
        assert "تَفْضِيلُ" in normalized
        assert "القَاهِرَة" in normalized
        assert "Cairo" in normalized

    def test_arabic_english_mixed_script_preserved(self):
        """Verifies mixed Arabic and English sentences are normalized cleanly."""
        mixed = "  نريد استخدام font Cairo بحجم 32px مع transition fade  "
        normalized = ContentNormalizer.normalize_text(mixed)
        assert normalized == "نريد استخدام font Cairo بحجم 32px مع transition fade"

    def test_whitespace_and_newline_collapsing(self):
        """Collapses excessive internal whitespace without destroying structure."""
        messy = "Line 1   with    multiple   spaces.\n\n\n\nLine 2 after quadruple newline."
        normalized = ContentNormalizer.normalize_text(messy)
        assert normalized == "Line 1 with multiple spaces.\n\nLine 2 after quadruple newline."

    def test_structured_payload_normalization(self):
        """Sorts dictionary keys and trims string values in nested dictionaries."""
        payload = {
            "z_key": "  last value  ",
            "a_key": {
                "nested_2": 42,
                "nested_1": "  first value  ",
            },
        }
        normalized = ContentNormalizer.normalize_structured_payload(payload)
        assert list(normalized.keys()) == ["a_key", "z_key"]
        assert normalized["z_key"] == "last value"
        assert normalized["a_key"]["nested_1"] == "first value"

    def test_content_hash_determinism_and_time_independence(self):
        """Guarantees content hash is deterministic and free from timestamps."""
        text_a = "User prefers quick cuts of 1.5 seconds maximum."
        text_b = "  User prefers quick cuts of 1.5 seconds maximum.  \n"

        hash_a = ContentNormalizer.compute_content_hash(text_a)
        hash_b = ContentNormalizer.compute_content_hash(text_b)

        assert hash_a == hash_b
        assert len(hash_a) == 64  # SHA-256 hex string

    def test_content_hash_differentiates_distinct_content(self):
        """Guarantees distinct text produces distinct hashes."""
        h1 = ContentNormalizer.compute_content_hash("User prefers quick cuts.")
        h2 = ContentNormalizer.compute_content_hash("User prefers slow cuts.")
        assert h1 != h2
