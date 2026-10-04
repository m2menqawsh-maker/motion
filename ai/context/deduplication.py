"""
ai/context/deduplication.py
===========================
Deduplication and conflict resolution engine (S27.8).

Guarantees:
- Eliminates exact duplicate context items across sources (Project, Memory, Knowledge, Request).
- Resolves semantic conflicts via epistemic authority precedence:
  DOMAIN_SOURCE_OF_TRUTH > HUMAN_CONFIRMED > EXPLICIT_USER > DERIVED > INFERRED.
- Contradictory stale memory never overrides canonical domain service facts.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ai.context.types import (
    AUTHORITY_PRECEDENCE,
    ContextAuthority,
    ContextExclusion,
    ContextItem,
    ExclusionReason,
)


class ContextDeduplicator:
    """
    Identifies duplicates and resolves authority conflicts between candidates.
    """

    def deduplicate(
        self,
        ranked_items: List[ContextItem],
    ) -> Tuple[List[ContextItem], List[ContextExclusion]]:
        """
        Deduplicates candidate items and resolves conflicts against authoritative sources.
        
        Preserves candidate ordering while substituting or dropping lower-authority items.
        """
        kept_items: List[ContextItem] = []
        exclusions: List[ContextExclusion] = []

        # Index maps for tracking seen facts
        seen_by_hash: Dict[str, ContextItem] = {}
        seen_by_key: Dict[str, ContextItem] = {}

        for item in ranked_items:
            # 1. Exact content hash match check
            if item.content_hash in seen_by_hash:
                existing = seen_by_hash[item.content_hash]
                item_prec = AUTHORITY_PRECEDENCE[item.authority]
                exist_prec = AUTHORITY_PRECEDENCE[existing.authority]

                if item_prec > exist_prec:
                    # Item has higher authority: replace existing in kept_items
                    kept_items = [item if it.id == existing.id else it for it in kept_items]
                    seen_by_hash[item.content_hash] = item
                    if item.canonical_key:
                        seen_by_key[item.canonical_key] = item

                    exclusions.append(
                        ContextExclusion(
                            candidate_id=existing.id,
                            section=existing.section,
                            reason=ExclusionReason.DUPLICATE,
                            details=(
                                f"Superseded by higher-authority duplicate {item.id} "
                                f"({item.authority.value} > {existing.authority.value})."
                            ),
                            source_type=existing.source_type,
                        )
                    )
                else:
                    # Existing has equal or higher authority: drop candidate
                    exclusions.append(
                        ContextExclusion(
                            candidate_id=item.id,
                            section=item.section,
                            reason=ExclusionReason.DUPLICATE,
                            details=f"Identical content already provided by {existing.id} ({existing.source_type.value}).",
                            source_type=item.source_type,
                        )
                    )
                continue

            # 2. Canonical semantic key conflict check
            if item.canonical_key and item.canonical_key in seen_by_key:
                existing = seen_by_key[item.canonical_key]
                item_prec = AUTHORITY_PRECEDENCE[item.authority]
                exist_prec = AUTHORITY_PRECEDENCE[existing.authority]

                # Check if content matches or conflicts
                if item.content.strip() == existing.content.strip():
                    # Same semantic fact with identical content
                    if item_prec > exist_prec:
                        kept_items = [item if it.id == existing.id else it for it in kept_items]
                        seen_by_key[item.canonical_key] = item
                        seen_by_hash[item.content_hash] = item
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=existing.id,
                                section=existing.section,
                                reason=ExclusionReason.DUPLICATE,
                                details=f"Superseded by higher authority duplicate for key '{item.canonical_key}'.",
                                source_type=existing.source_type,
                            )
                        )
                    else:
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=item.id,
                                section=item.section,
                                reason=ExclusionReason.DUPLICATE,
                                details=f"Duplicate canonical key '{item.canonical_key}' already present.",
                                source_type=item.source_type,
                            )
                        )
                    continue
                else:
                    # Contradictory semantic content -> Conflict Resolution!
                    if item_prec > exist_prec:
                        # Higher authority wins: replace existing
                        kept_items = [item if it.id == existing.id else it for it in kept_items]
                        seen_by_key[item.canonical_key] = item
                        seen_by_hash[item.content_hash] = item
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=existing.id,
                                section=existing.section,
                                reason=ExclusionReason.AUTHORITY_CONFLICT,
                                details=(
                                    f"Conflict on '{item.canonical_key}': Conflicting lower-authority fact "
                                    f"({existing.authority.value}) overridden by {item.authority.value}."
                                ),
                                source_type=existing.source_type,
                            )
                        )
                    else:
                        # Lower authority candidate loses against existing higher authority
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=item.id,
                                section=item.section,
                                reason=ExclusionReason.AUTHORITY_CONFLICT,
                                details=(
                                    f"Conflict on '{item.canonical_key}': Stale or conflicting candidate "
                                    f"({item.authority.value}) rejected in favor of authoritative "
                                    f"source ({existing.authority.value})."
                                ),
                                source_type=item.source_type,
                            )
                        )
                    continue

            # First time seeing this hash and key: record and keep
            seen_by_hash[item.content_hash] = item
            if item.canonical_key:
                seen_by_key[item.canonical_key] = item
            kept_items.append(item)

        return kept_items, exclusions
