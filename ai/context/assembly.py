"""
ai/context/assembly.py
======================
Deterministic context package assembly and canonical hashing engine (S27.8).

Guarantees:
- Stable prefix ordering across all 9 canonical sections:
  1. SYSTEM
  2. TOOLS
  3. SHARED
  4. PROJECT
  5. MEMORY
  6. KNOWLEDGE
  7. CONVERSATION
  8. MEDIA
  9. REQUEST
- Deterministic item ordering inside sections: (-relevance_score, -confidence, id ASC).
- Canonical context_hash computed from invariant structure (no volatile timestamps or random IDs).
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

from ai.context.types import (
    ContextDiagnostics,
    ContextExclusion,
    ContextItem,
    ContextPackage,
    ContextSection,
    ContextSectionPackage,
)

CANONICAL_SECTION_ORDER: List[ContextSection] = [
    ContextSection.SYSTEM,
    ContextSection.TOOLS,
    ContextSection.SHARED,
    ContextSection.PROJECT,
    ContextSection.MEMORY,
    ContextSection.KNOWLEDGE,
    ContextSection.CONVERSATION,
    ContextSection.MEDIA,
    ContextSection.REQUEST,
]


class ContextAssembler:
    """
    Assembles partitioned context items into canonical ContextPackage.
    """

    @classmethod
    def assemble(
        cls,
        request_id: str,
        items: List[ContextItem],
        diagnostics: ContextDiagnostics,
    ) -> ContextPackage:
        """
        Groups items into canonical sections, orders items deterministically,
        and computes canonical SHA-256 context hash.
        """
        # 1. Group items by section
        section_buckets: Dict[ContextSection, List[ContextItem]] = {
            sec: [] for sec in CANONICAL_SECTION_ORDER
        }
        for item in items:
            sec_enum = ContextSection(item.section)
            section_buckets[sec_enum].append(item)

        # 2. Sort items within each section deterministically
        for sec in CANONICAL_SECTION_ORDER:
            section_buckets[sec].sort(
                key=lambda it: (-it.relevance_score, -it.confidence, it.canonical_key or it.content_hash)
            )

        # 3. Build Section Packages
        section_packages: Dict[ContextSection, ContextSectionPackage] = {}
        for sec in CANONICAL_SECTION_ORDER:
            sec_items = section_buckets[sec]
            sec_tokens = sum(it.estimated_tokens for it in sec_items)
            section_packages[sec] = ContextSectionPackage(
                section=sec,
                items=sec_items,
                estimated_tokens=sec_tokens,
            )

        # 4. Compute canonical context hash
        context_hash = cls.compute_canonical_context_hash(section_packages)

        return ContextPackage(
            request_id=request_id,
            context_hash=context_hash,
            system_policy=section_packages[ContextSection.SYSTEM],
            tool_schema_context=section_packages[ContextSection.TOOLS],
            shared_context=section_packages[ContextSection.SHARED],
            project_context=section_packages[ContextSection.PROJECT],
            memory_context=section_packages[ContextSection.MEMORY],
            knowledge_context=section_packages[ContextSection.KNOWLEDGE],
            conversation_context=section_packages[ContextSection.CONVERSATION],
            media_context=section_packages[ContextSection.MEDIA],
            current_request=section_packages[ContextSection.REQUEST],
            diagnostics=diagnostics,
        )

    @classmethod
    def compute_canonical_context_hash(
        cls,
        section_packages: Dict[ContextSection, ContextSectionPackage],
    ) -> str:
        """
        Generates canonical deterministic SHA-256 hash.
        
        Invariants:
        - Evaluates sections in fixed CANONICAL_SECTION_ORDER.
        - Evaluates items in their deterministic internal sort order.
        - Contains no volatile execution timestamps, clocks, or random memory IDs.
        """
        canonical_structure = []
        for sec in CANONICAL_SECTION_ORDER:
            pkg = section_packages[sec]
            item_records = []
            for it in pkg.items:
                item_records.append({
                    "semantic_key": it.canonical_key or "",
                    "authority": it.authority.value,
                    "content_hash": it.content_hash,
                    "compressed": it.compressed,
                    "tokens": it.estimated_tokens,
                })
            canonical_structure.append({
                "section": sec.value,
                "items": item_records,
            })

        serialized = json.dumps(canonical_structure, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
