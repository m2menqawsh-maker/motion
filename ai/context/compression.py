"""
ai/context/compression.py
=========================
Deterministic context compression and bounded trimming engine (S27.8).

Guarantees:
- Never executes blind truncation (`text[:4000]`).
- Bounded, sentence-aware compression with explicit markers:
  `[Compressed: trimmed from X to Y chars]`.
- Protects critical system policy, request payload, and core lifecycle facts from compression.
- Updates item content hash, token count, and sets compressed=True.
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from ai.context.types import ContextAuthority, ContextItem, ContextSection


class ContextCompressor(Protocol):
    """Protocol for abstracting context compression implementations."""
    def compress_item(self, item: ContextItem, max_chars: int = 500) -> ContextItem:
        ...

    def is_compressible(self, item: ContextItem) -> bool:
        ...


class DeterministicContextCompressor:
    """
    Offline deterministic compressor with boundary awareness.
    """
    def __init__(self, default_max_chars: int = 600):
        self.default_max_chars = default_max_chars

    def is_compressible(self, item: ContextItem) -> bool:
        """Determines if an item can be compressed safely."""
        # Never compress critical system policies or current user request
        if item.section in (ContextSection.SYSTEM, ContextSection.REQUEST, ContextSection.TOOLS):
            return False

        # Protect core lifecycle facts
        if item.canonical_key in ("fact:project:status", "fact:project:revision"):
            return False

        # System authority and domain source of truth items are preserved unless long
        if item.authority == ContextAuthority.SYSTEM_AUTHORITY:
            return False

        return True

    def compress_item(
        self,
        item: ContextItem,
        max_chars: Optional[int] = None,
        estimator: Optional[object] = None,
    ) -> ContextItem:
        """
        Compresses an item if content exceeds max_chars.
        """
        target_max = max_chars or self.default_max_chars

        if not self.is_compressible(item) or len(item.content) <= target_max:
            return item

        orig_len = len(item.content)
        # Allocate room for the explicit marker
        marker_template = "\n[Compressed: trimmed from {orig} to {new} chars]"
        room_for_text = max(100, target_max - 80)

        # Truncate at natural sentence or word boundary
        candidate_text = item.content[:room_for_text]
        last_punct = max(
            candidate_text.rfind(". "),
            candidate_text.rfind(".\n"),
            candidate_text.rfind(";\n"),
            candidate_text.rfind("! "),
            candidate_text.rfind("? "),
        )
        if last_punct > 50:
            trimmed_text = candidate_text[:last_punct + 1]
        else:
            last_space = candidate_text.rfind(" ")
            if last_space > 50:
                trimmed_text = candidate_text[:last_space] + "..."
            else:
                trimmed_text = candidate_text + "..."

        marker = marker_template.format(orig=orig_len, new=len(trimmed_text))
        new_content = trimmed_text + marker

        # Re-estimate tokens if estimator provided
        new_tokens = item.estimated_tokens
        if estimator is not None and hasattr(estimator, "estimate_tokens"):
            new_tokens = estimator.estimate_tokens(new_content)
        else:
            import math
            new_tokens = max(1, math.ceil(len(new_content) / 3.5))

        return item.model_copy(
            update={
                "content": new_content,
                "compressed": True,
                "estimated_tokens": new_tokens,
                "content_hash": ContextItem.compute_content_hash(new_content),
            }
        )
