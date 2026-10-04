"""
ai/acquisition/dedupe.py
========================
Two-phase deduplication engine for media candidates and acquired assets (S28-M05).

Invariants:
- Pre-download deduplication filters redundant entries by provider identity and remote URLs.
- Post-download deduplication checks existing project assets via content hash (SHA-256).
- Zero redundant file writes if identical asset already exists in the project boundary.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from ai.acquisition.contracts import StockCandidate
from api.services.asset_service import AssetService


class StockDedupeEngine:
    """Provides pre-acquisition candidate deduplication and post-acquisition storage deduplication."""

    @classmethod
    def deduplicate_candidates(cls, candidates: List[StockCandidate]) -> List[StockCandidate]:
        """
        Deduplicates candidate search results before acquisition.
        Filters by composite provider ID and primary download URL.
        Preserves highest-ranked candidate when duplicate occurs.
        """
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()
        deduped: List[StockCandidate] = []

        # Assume candidates are already sorted by rank or will be evaluated in order
        for c in candidates:
            # 1. Identity key check
            id_key = f"{c.source.lower()}:{c.source_asset_id}"
            if id_key in seen_ids:
                continue

            # 2. Primary download URL check
            primary_url = c.selected_variant.url if c.selected_variant else (
                c.download_variants[0].url if c.download_variants else c.preview_url
            )
            if primary_url and primary_url in seen_urls:
                continue

            seen_ids.add(id_key)
            if primary_url:
                seen_urls.add(primary_url)

            deduped.append(c)

        return deduped

    @classmethod
    def find_existing_asset_by_hash(
        cls,
        project_id: str,
        content_hash: str,
    ) -> Optional[Dict[str, any]]:
        """
        Queries project assets to find if an asset with identical content hash already exists.
        Checks AssetService manifest first (honoring test mocks and local manifests),
        then queries CanonicalAssetRepository (durable authority across workers).
        Returns matching asset dictionary if found, else None.
        """
        # 1. Check AssetService manifest list
        try:
            assets = AssetService.list_assets(project_id)
            for a in assets:
                a_hash = a.get("content_hash") or (a.get("metadata", {}) or {}).get("content_hash")
                if a_hash == content_hash:
                    return a
        except Exception:
            pass

        # 2. Check authoritative database registry (CanonicalAssetRepository)
        try:
            from scripts.core.canonical_asset_repository import CanonicalAssetRepository
            repo = CanonicalAssetRepository()
            rec = repo.find_by_hash(project_id, content_hash)
            if rec:
                return rec.to_dict()
        except Exception:
            pass

        return None
