"""
ai/memory/normalization.py
==========================
Canonical content normalization and deterministic hashing for AI Memory (S27.6, S27.7).

Handles multilingual text safely, preserving Arabic typography, diacritics,
and mixed Arabic/English content without destructive transformations.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Dict, Optional, Tuple
from pydantic import JsonValue


class ContentNormalizer:
    """
    Multilingual-safe content normalization and canonical hashing engine.
    """

    # Regex to collapse multiple whitespace characters (including tabs and newlines)
    _WHITESPACE_RE = re.compile(r"[ \t]+")
    _MULTILINE_RE = re.compile(r"\n{3,}")

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalizes text whitespace and Unicode representation safely.
        
        Preserves Arabic letters, diacritics (tashkeel), punctuation,
        and mixed Arabic/English scripts.
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFC preserves Arabic combined characters cleanly)
        normalized = unicodedata.normalize("NFC", text)

        # 2. Normalize carriage returns to standard newlines
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Collapse multiple spaces and tabs per line
        lines = [cls._WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]

        # 4. Remove empty lines at boundaries and collapse >2 empty lines to 1
        cleaned_text = "\n".join(lines).strip()
        cleaned_text = cls._MULTILINE_RE.sub("\n\n", cleaned_text)

        return cleaned_text

    @classmethod
    def normalize_for_comparison(cls, text: str) -> str:
        """
        Produces a normalized representation specifically for semantic comparison and deduplication.
        Lowercases ASCII segments while preserving Unicode/Arabic characters.
        """
        normalized = cls.normalize_text(text)
        # Safe ASCII lowercasing (does not alter Arabic letter shapes)
        return normalized.lower()

    @classmethod
    def normalize_structured_payload(cls, payload: Optional[Dict[str, JsonValue]]) -> Optional[Dict[str, JsonValue]]:
        """
        Recursively normalizes dictionary keys and string values in structured payloads.
        """
        if payload is None:
            return None

        normalized_dict: Dict[str, JsonValue] = {}
        for key in sorted(payload.keys()):
            val = payload[key]
            norm_key = key.strip()
            if isinstance(val, str):
                normalized_dict[norm_key] = cls.normalize_text(val)
            elif isinstance(val, dict):
                normalized_dict[norm_key] = cls.normalize_structured_payload(val)
            elif isinstance(val, list):
                normalized_dict[norm_key] = [
                    cls.normalize_text(item) if isinstance(item, str)
                    else (cls.normalize_structured_payload(item) if isinstance(item, dict) else item)
                    for item in val
                ]
            else:
                normalized_dict[norm_key] = val
        return normalized_dict

    @classmethod
    def compute_content_hash(
        cls,
        text: str,
        structured_payload: Optional[Dict[str, JsonValue]] = None,
    ) -> str:
        """
        Computes a deterministic canonical SHA-256 hash.
        
        Strict Invariants:
        - NEVER includes timestamps.
        - Same normalized text and payload produce the EXACT same hash.
        """
        norm_text = cls.normalize_for_comparison(text)
        norm_payload = cls.normalize_structured_payload(structured_payload)

        hasher = hashlib.sha256()
        hasher.update(norm_text.encode("utf-8"))

        if norm_payload:
            hasher.update(b"|PAYLOAD|")
            payload_json = json.dumps(norm_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            hasher.update(payload_json.encode("utf-8"))

        return hasher.hexdigest()
