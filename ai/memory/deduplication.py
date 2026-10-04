"""
ai/memory/deduplication.py
==========================
Deduplication key calculation, collision detection, and conflict identification (S27.6, S27.7).
"""

from __future__ import annotations

import hashlib
from typing import Optional

from ai.memory.models import MemoryEntry, MemoryCandidate
from ai.memory.normalization import ContentNormalizer
from ai.memory.types import MemoryScope, MemoryType


class DeduplicationEngine:
    """
    Computes canonical deduplication keys and detects duplicate or conflicting memory candidates.
    """

    @classmethod
    def compute_dedup_key(
        cls,
        workspace_id: str,
        memory_type: MemoryType,
        scope: MemoryScope,
        content_hash: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        """
        Builds a canonical deduplication key string.
        """
        parts = [
            f"ws:{workspace_id}",
            f"type:{memory_type.value}",
            f"scope:{scope.value}",
            f"hash:{content_hash}",
        ]
        if user_id:
            parts.append(f"user:{user_id}")
        if project_id:
            parts.append(f"proj:{project_id}")

        raw_key = "|".join(parts)
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def extract_preference_topic(cls, text: str) -> Optional[str]:
        """
        Heuristic extraction of preference subject/topic for contradiction analysis.
        e.g., 'transitions', 'cuts', 'fonts', 'color palette', 'music volume'.
        """
        lower = text.lower()
        topics = [
            "transition", "transitions",
            "cut", "cuts",
            "font", "fonts", "typography",
            "pacing", "speed",
            "color", "palette", "theme",
            "music", "sfx", "volume",
            "voiceover", "voice",
            "subtitle", "subtitles", "caption", "captions",
            "motion", "intensity",
            "density", "complexity",
        ]
        for topic in topics:
            if topic in lower:
                return topic
        return None

    @classmethod
    def is_contradictory_preference(cls, existing: MemoryEntry, candidate: MemoryCandidate) -> bool:
        """
        Determines whether candidate contradicts an existing preference of the same user/project.
        """
        if existing.memory_type != MemoryType.USER_PREFERENCE or candidate.proposed_type != MemoryType.USER_PREFERENCE:
            return False

        # 1. Precise structured dimension comparison if available
        dim_existing = (existing.structured_payload or {}).get("dimension") or (existing.metadata or {}).get("dimension")
        dim_candidate = (candidate.structured_payload or {}).get("dimension") or (candidate.metadata or {}).get("dimension")
        if dim_existing and dim_candidate and dim_existing == dim_candidate:
            val_existing = (existing.structured_payload or {}).get("value") or (existing.metadata or {}).get("value")
            val_candidate = (candidate.structured_payload or {}).get("value") or (candidate.metadata or {}).get("value")
            if val_existing != val_candidate:
                return True
            return False

        # 2. Heuristic topic comparison from normalized text
        topic_existing = cls.extract_preference_topic(existing.content)
        topic_candidate = cls.extract_preference_topic(candidate.content)

        if topic_existing and topic_candidate and topic_existing == topic_candidate:
            norm_existing = ContentNormalizer.normalize_for_comparison(existing.content)
            norm_candidate = ContentNormalizer.normalize_for_comparison(candidate.content)
            # If topics match but normalized content is different, it is a contradictory/superseding update
            if norm_existing != norm_candidate:
                return True

        return False
