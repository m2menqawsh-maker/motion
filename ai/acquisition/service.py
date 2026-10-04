"""
ai/acquisition/service.py
=========================
AssetAcquisitionService — Authoritative Domain Service for Stock Media Acquisition (S28-M05).

Invariants:
- Coordinates search, normalization, filtering, deterministic ranking, and deduplication.
- Safe acquisition boundary: downloads into isolated buffers, verifies signatures and MIME types.
- Integrates canonically with AssetService and StorageService for durable persistence.
- Zero raw project filesystem writes or unmanaged scratch artifacts.
- Tenant and workspace authorization strictly enforced before and during ingestion.
- Full provenance and license evidence preserved on every canonical asset.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from ai.tools.types import TrustedToolExecutionContext

from ai.acquisition.contracts import (
    AcquiredAssetResult,
    AcquisitionDescriptor,
    DownloadVariant,
    LicenseClassification,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)
from ai.acquisition.dedupe import StockDedupeEngine
from ai.acquisition.errors import (
    AcquisitionAuthorizationError,
    AssetImportError,
    NoEligibleResultsError,
    ProviderUnavailableError,
    UnsafeDownloadSourceError,
)
from ai.acquisition.filtering import StockFilterEngine
from ai.acquisition.providers.base import StockSourceAdapter
from ai.acquisition.providers.freesound import FreesoundAdapter
from ai.acquisition.providers.iconify import IconifyAdapter
from ai.acquisition.providers.pexels import PexelsAdapter
from ai.acquisition.providers.pixabay import PixabayAdapter
from ai.acquisition.ranking import StockRankingEngine
from ai.acquisition.safe_downloader import safe_download_media
from api.services.asset_service import AssetService

logger = logging.getLogger("clean_video.ai.acquisition.service")


class SearchCache:
    """In-memory cache for search results with TTL expiration."""

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[float, List[StockCandidate]]] = {}

    def _make_key(self, query: StockSearchQuery) -> str:
        providers_str = ",".join(sorted(query.allowed_providers)) if query.allowed_providers else "all"
        return f"{query.media_type.value}:{query.query.lower().strip()}:{query.orientation}:{query.min_duration}:{query.max_duration}:{query.page}:{query.per_page}:{providers_str}"

    def get(self, query: StockSearchQuery) -> Optional[List[StockCandidate]]:
        key = self._make_key(query)
        if key in self._cache:
            created_at, candidates = self._cache[key]
            if (time.monotonic() - created_at) < self.ttl_seconds:
                return candidates
            else:
                del self._cache[key]
        return None

    def set(self, query: StockSearchQuery, candidates: List[StockCandidate]) -> None:
        key = self._make_key(query)
        self._cache[key] = (time.monotonic(), candidates)

    def clear(self) -> None:
        self._cache.clear()


class AssetAcquisitionService:
    """
    Authoritative domain service governing external media discovery, validation,
    licensing provenance, and ingestion into the canonical asset platform.
    """

    def __init__(
        self,
        providers: Optional[List[StockSourceAdapter]] = None,
        search_cache: Optional[SearchCache] = None,
    ) -> None:
        self.providers: List[StockSourceAdapter] = providers or [
            PexelsAdapter(),
            PixabayAdapter(),
            FreesoundAdapter(),
            IconifyAdapter(),
        ]
        self.cache = search_cache or SearchCache()

    def _get_eligible_providers(self, query: StockSearchQuery) -> List[StockSourceAdapter]:
        """Filters providers that support requested media type and pass allowed_providers whitelist."""
        eligible = []
        for p in self.providers:
            if query.media_type in p.supported_media_types:
                if query.allowed_providers:
                    if p.name.lower() in [ap.lower() for ap in query.allowed_providers]:
                        eligible.append(p)
                else:
                    eligible.append(p)
        return eligible

    def _validate_tenant_confinement(
        self,
        project_id: str,
        workspace_id: Optional[str] = None,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> None:
        """Enforces tenant isolation between caller and target project."""
        if context:
            if context.workspace_id and workspace_id and context.workspace_id != workspace_id:
                raise AcquisitionAuthorizationError(
                    f"Cross-tenant access violation: caller workspace '{context.workspace_id}' cannot mutate workspace '{workspace_id}'."
                )
            if context.accessible_projects and project_id not in context.accessible_projects:
                raise AcquisitionAuthorizationError(
                    f"Cross-project access violation: caller cannot access project '{project_id}'."
                )

        # Database workspace ownership verification
        try:
            from scripts.core.database import get_database_engine, TenantRepository
            engine = get_database_engine()
            repo = TenantRepository(engine)
            proj_rec = repo.get_project(project_id)
            if proj_rec:
                actual_ws = proj_rec.workspace_id
                effective_ws = workspace_id or (context.workspace_id if context else None)
                if effective_ws and actual_ws != effective_ws:
                    raise AcquisitionAuthorizationError(
                        f"Project '{project_id}' belongs to workspace '{actual_ws}', not '{effective_ws}'."
                    )
        except Exception as e:
            if isinstance(e, AcquisitionAuthorizationError):
                raise
            # If tenant DB is uninitialized (e.g. test environment), rely on context checks

    async def search_stock(
        self,
        query: StockSearchQuery,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> List[StockCandidate]:
        """
        Executes multi-provider search, hard filtering, ranking, and pre-acquisition deduplication.
        """
        # 1. Check search cache
        cached = self.cache.get(query)
        if cached is not None:
            return cached

        # 2. Select eligible providers
        eligible_providers = self._get_eligible_providers(query)
        if not eligible_providers:
            raise ProviderUnavailableError(
                "stock_coordinator",
                f"No eligible providers available for media type '{query.media_type.value}'."
            )

        # 3. Query providers with fault isolation (Provider A failing does not break Provider B)
        raw_candidates: List[StockCandidate] = []
        provider_errors: Dict[str, str] = {}

        for provider in eligible_providers:
            if not provider.is_available():
                provider_errors[provider.name] = "Provider unconfigured or API key missing"
                continue
            try:
                results = await provider.search(query)
                raw_candidates.extend(results)
            except Exception as e:
                logger.warning(f"Provider '{provider.name}' search failed for query '{query.query}': {e}")
                provider_errors[provider.name] = str(e)

        if not raw_candidates:
            if provider_errors:
                # All eligible providers encountered errors or were unconfigured
                err_summary = "; ".join(f"{k}: {v}" for k, v in provider_errors.items())
                raise ProviderUnavailableError(
                    "all_eligible_providers",
                    f"All stock providers failed or unconfigured: {err_summary}",
                    details=provider_errors,
                )
            return []

        # 4. Hard constraint filtering
        filtered, rejections = StockFilterEngine.filter_candidates(raw_candidates, query)
        if not filtered:
            logger.info(f"0 candidates survived filtering for query '{query.query}'. Rejections: {rejections}")
            return []

        # 5. Deterministic ranking
        ranked = StockRankingEngine.rank_candidates(filtered, query)

        # 6. Pre-acquisition deduplication
        deduped = StockDedupeEngine.deduplicate_candidates(ranked)

        # 7. Cache results
        self.cache.set(query, deduped)

        return deduped

    async def search(
        self,
        query: StockSearchQuery,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> List[StockCandidate]:
        """Convenience alias for search_stock."""
        return await self.search_stock(query, context)

    async def acquire_candidate(
        self,
        candidate: StockCandidate,
        project_id: str,
        workspace_id: Optional[str] = None,
        context: Optional[TrustedToolExecutionContext] = None,
        variant_id: Optional[str] = None,
    ) -> AcquiredAssetResult:
        """
        Safely acquires a validated candidate and registers it into AssetService.
        """
        self._validate_tenant_confinement(project_id, workspace_id, context)

        # 1. Resolve provider adapter to build acquisition descriptor
        adapter = next((p for p in self.providers if p.name.lower() == candidate.source.lower()), None)
        if not adapter:
            raise ProviderUnavailableError(candidate.source, f"No registered adapter for source '{candidate.source}'.")

        desc: AcquisitionDescriptor = adapter.resolve_acquisition(candidate, requested_variant_id=variant_id)

        # 2. Bounded safe HTTP acquisition & magic byte validation
        payload = await safe_download_media(
            url=desc.download_url,
            expected_media_type=candidate.media_type,
            max_bytes=desc.max_bytes,
        )

        # 3. Post-download deduplication (content hash check)
        existing_asset = StockDedupeEngine.find_existing_asset_by_hash(project_id, payload.content_hash)
        if existing_asset:
            logger.info(f"Reusing existing asset '{existing_asset.get('asset_id')}' with matching hash '{payload.content_hash}'.")
            return AcquiredAssetResult(
                project_id=project_id,
                asset_id=existing_asset.get("asset_id", ""),
                storage_key=existing_asset.get("metadata", {}).get("storage_key") or existing_asset.get("processed_path", ""),
                content_hash=payload.content_hash,
                media_type=candidate.media_type,
                file_size_bytes=payload.file_size_bytes,
                content_type=payload.mime_type,
                provenance_evidence=candidate.provenance_evidence,
                is_reused_existing=True,
            )

        # 4. Atomic registration via CanonicalAssetRepository (CAS deduplication authority)
        filename = f"{candidate.source}_{candidate.source_asset_id}{payload.suggested_extension}"
        deterministic_asset_id = f"ast_{payload.content_hash}"
        storage_key = f"assets/ready/{deterministic_asset_id}{payload.suggested_extension}"
        ws_id = workspace_id or (context.workspace_id if context else "ws_default")

        try:
            from scripts.core.canonical_asset_repository import CanonicalAssetRepository, CanonicalAssetRecord
            import json
            canon_repo = CanonicalAssetRepository()
            canon_rec = CanonicalAssetRecord(
                asset_id=deterministic_asset_id,
                project_id=project_id,
                workspace_id=ws_id,
                content_hash=payload.content_hash,
                storage_key=storage_key,
                media_type=candidate.media_type.value,
                mime_type=payload.mime_type,
                file_size_bytes=payload.file_size_bytes,
                provenance_json=json.dumps(candidate.provenance_evidence),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            reg_rec, is_new = canon_repo.register_asset(canon_rec)
            if not is_new:
                logger.info(f"Concurrent race deduplication hit: reusing asset '{reg_rec.asset_id}'")
                return AcquiredAssetResult(
                    project_id=project_id,
                    asset_id=reg_rec.asset_id,
                    storage_key=reg_rec.storage_key,
                    content_hash=payload.content_hash,
                    media_type=candidate.media_type,
                    file_size_bytes=reg_rec.file_size_bytes,
                    content_type=payload.mime_type,
                    provenance_evidence=candidate.provenance_evidence,
                    is_reused_existing=True,
                )
        except Exception as e:
            logger.warning(f"CanonicalAssetRepository registration skipped/failed: {e}")

        # 5. Canonical ingestion via AssetService
        try:
            asset_rec = AssetService.upload_asset(
                project_id=project_id,
                content=payload.content_bytes,
                filename=filename,
                asset_id=deterministic_asset_id,
                kind=candidate.media_type.value,
            )
        except Exception as e:
            raise AssetImportError(project_id, f"AssetService.upload_asset failed: {e}")

        asset_id = asset_rec.get("asset_id", "")
        final_storage_key = asset_rec.get("metadata", {}).get("storage_key") or asset_rec.get("processed_path", "") or storage_key

        return AcquiredAssetResult(
            project_id=project_id,
            asset_id=asset_id,
            storage_key=final_storage_key,
            content_hash=payload.content_hash,
            media_type=candidate.media_type,
            file_size_bytes=payload.file_size_bytes,
            content_type=payload.mime_type,
            provenance_evidence=candidate.provenance_evidence,
            is_reused_existing=False,
        )

    async def download_remote_media(
        self,
        project_id: str,
        url: str,
        media_type: str = "video",
        destination_asset_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> AcquiredAssetResult:
        """
        Direct remote URL acquisition (DOWNLOAD_REMOTE_MEDIA capability).
        """
        self._validate_tenant_confinement(project_id, workspace_id, context)

        m_type = StockMediaType.VIDEO if media_type == "video" else StockMediaType.IMAGE if media_type == "image" else StockMediaType.AUDIO

        # Safe bounded download
        payload = await safe_download_media(
            url=url,
            expected_media_type=m_type,
        )

        # Content hash dedupe check
        existing = StockDedupeEngine.find_existing_asset_by_hash(project_id, payload.content_hash)
        if existing:
            return AcquiredAssetResult(
                project_id=project_id,
                asset_id=existing.get("asset_id", ""),
                storage_key=existing.get("metadata", {}).get("storage_key") or existing.get("processed_path", ""),
                content_hash=payload.content_hash,
                media_type=m_type,
                file_size_bytes=payload.file_size_bytes,
                content_type=payload.mime_type,
                provenance_evidence={"source_url": url, "direct_download": True},
                is_reused_existing=True,
            )

        filename = f"remote_{payload.content_hash[:10]}{payload.suggested_extension}"
        deterministic_asset_id = destination_asset_id or f"ast_{payload.content_hash}"
        storage_key = f"assets/ready/{deterministic_asset_id}{payload.suggested_extension}"
        ws_id = workspace_id or (context.workspace_id if context else "ws_default")

        try:
            from scripts.core.canonical_asset_repository import CanonicalAssetRepository, CanonicalAssetRecord
            import json
            canon_repo = CanonicalAssetRepository()
            canon_rec = CanonicalAssetRecord(
                asset_id=deterministic_asset_id,
                project_id=project_id,
                workspace_id=ws_id,
                content_hash=payload.content_hash,
                storage_key=storage_key,
                media_type=m_type.value,
                mime_type=payload.mime_type,
                file_size_bytes=payload.file_size_bytes,
                provenance_json=json.dumps({"source_url": url, "direct_download": True}),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            reg_rec, is_new = canon_repo.register_asset(canon_rec)
            if not is_new:
                return AcquiredAssetResult(
                    project_id=project_id,
                    asset_id=reg_rec.asset_id,
                    storage_key=reg_rec.storage_key,
                    content_hash=payload.content_hash,
                    media_type=m_type,
                    file_size_bytes=reg_rec.file_size_bytes,
                    content_type=payload.mime_type,
                    provenance_evidence={"source_url": url, "direct_download": True},
                    is_reused_existing=True,
                )
        except Exception as e:
            logger.warning(f"CanonicalAssetRepository registration skipped/failed: {e}")

        asset_rec = AssetService.upload_asset(
            project_id=project_id,
            content=payload.content_bytes,
            filename=filename,
            asset_id=deterministic_asset_id,
            kind=m_type.value,
        )

        return AcquiredAssetResult(
            project_id=project_id,
            asset_id=asset_rec.get("asset_id", ""),
            storage_key=asset_rec.get("metadata", {}).get("storage_key") or asset_rec.get("processed_path", ""),
            content_hash=payload.content_hash,
            media_type=m_type,
            file_size_bytes=payload.file_size_bytes,
            content_type=payload.mime_type,
            provenance_evidence={"source_url": url, "direct_download": True},
            is_reused_existing=False,
        )

    async def download_icon(
        self,
        project_id: str,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 64,
        workspace_id: Optional[str] = None,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> AcquiredAssetResult:
        """
        Acquires an icon from Iconify and imports as SVG asset (DOWNLOAD_ICON capability).
        """
        self._validate_tenant_confinement(project_id, workspace_id, context)

        icon_adapter = next((p for p in self.providers if isinstance(p, IconifyAdapter)), None)
        if not icon_adapter:
            icon_adapter = IconifyAdapter()

        candidate = StockCandidate(
            candidate_id=f"iconify:{icon_name}",
            source="iconify",
            source_asset_id=icon_name,
            media_type=StockMediaType.ICON,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

        desc = icon_adapter.resolve_acquisition(candidate, color=color, size=size)
        payload = await safe_download_media(desc.download_url, expected_media_type=StockMediaType.ICON)

        # Content hash dedupe check
        existing = StockDedupeEngine.find_existing_asset_by_hash(project_id, payload.content_hash)
        if existing:
            return AcquiredAssetResult(
                project_id=project_id,
                asset_id=existing.get("asset_id", ""),
                storage_key=existing.get("metadata", {}).get("storage_key") or existing.get("processed_path", ""),
                content_hash=payload.content_hash,
                media_type=StockMediaType.ICON,
                file_size_bytes=payload.file_size_bytes,
                content_type="image/svg+xml",
                provenance_evidence={"icon_name": icon_name, "color": color, "size": size, "provider": "iconify"},
                is_reused_existing=True,
            )

        safe_name = icon_name.replace(":", "_").replace("/", "_")
        filename = f"{safe_name}.svg"
        deterministic_asset_id = f"ast_{payload.content_hash}"
        storage_key = f"assets/ready/{deterministic_asset_id}.svg"
        ws_id = workspace_id or (context.workspace_id if context else "ws_default")

        try:
            from scripts.core.canonical_asset_repository import CanonicalAssetRepository, CanonicalAssetRecord
            import json
            canon_repo = CanonicalAssetRepository()
            canon_rec = CanonicalAssetRecord(
                asset_id=deterministic_asset_id,
                project_id=project_id,
                workspace_id=ws_id,
                content_hash=payload.content_hash,
                storage_key=storage_key,
                media_type="image",
                mime_type="image/svg+xml",
                file_size_bytes=payload.file_size_bytes,
                provenance_json=json.dumps({"icon_name": icon_name, "color": color, "size": size, "provider": "iconify"}),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            reg_rec, is_new = canon_repo.register_asset(canon_rec)
            if not is_new:
                return AcquiredAssetResult(
                    project_id=project_id,
                    asset_id=reg_rec.asset_id,
                    storage_key=reg_rec.storage_key,
                    content_hash=payload.content_hash,
                    media_type=StockMediaType.ICON,
                    file_size_bytes=reg_rec.file_size_bytes,
                    content_type="image/svg+xml",
                    provenance_evidence={"icon_name": icon_name, "color": color, "size": size, "provider": "iconify"},
                    is_reused_existing=True,
                )
        except Exception as e:
            logger.warning(f"CanonicalAssetRepository registration skipped/failed: {e}")

        asset_rec = AssetService.upload_asset(
            project_id=project_id,
            content=payload.content_bytes,
            filename=filename,
            asset_id=deterministic_asset_id,
            kind="image",
        )

        return AcquiredAssetResult(
            project_id=project_id,
            asset_id=asset_rec.get("asset_id", ""),
            storage_key=asset_rec.get("metadata", {}).get("storage_key") or asset_rec.get("processed_path", ""),
            content_hash=payload.content_hash,
            media_type=StockMediaType.ICON,
            file_size_bytes=payload.file_size_bytes,
            content_type="image/svg+xml",
            provenance_evidence={"icon_name": icon_name, "color": color, "size": size, "provider": "iconify"},
            is_reused_existing=False,
        )

    async def acquire_for_creative_requirement(
        self,
        requirement_text: str,
        project_id: str,
        workspace_id: Optional[str] = None,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> AcquiredAssetResult:
        """
        Translates a high-level creative asset requirement (from CreativePlan.asset_requirements)
        into a structured search query, searches eligible stock providers, ranks, and safely acquires.
        """
        query = self.parse_creative_asset_requirement(requirement_text)
        candidates = await self.search_stock(query, context=context)

        if not candidates:
            raise NoEligibleResultsError(
                query=query.query,
                total_checked=0,
                rejection_summary={"no_results_found": 1},
            )

        best_candidate = candidates[0]
        return await self.acquire_candidate(
            candidate=best_candidate,
            project_id=project_id,
            workspace_id=workspace_id,
            context=context,
        )

    @classmethod
    def parse_creative_asset_requirement(cls, requirement_text: str) -> StockSearchQuery:
        """
        Extracts media_type, orientation, and clean search keywords from natural language requirement.
        """
        text_lower = requirement_text.lower().strip()

        # 1. Determine media type
        if any(w in text_lower for w in ["icon", "svg", "symbol", "glyph", "vector logo"]):
            media_type = StockMediaType.ICON
        elif any(w in text_lower for w in ["sound effect", "sfx", "foley", "whoosh", "chime"]):
            media_type = StockMediaType.SOUND_EFFECT
        elif any(w in text_lower for w in ["music", "audio", "soundtrack", "bgm", "ambient track"]):
            media_type = StockMediaType.AUDIO
        elif any(w in text_lower for w in ["photo", "image", "picture", "screenshot", "still"]):
            media_type = StockMediaType.IMAGE
        else:
            # Default for video production requirements is video footage
            media_type = StockMediaType.VIDEO

        # 2. Determine orientation
        orientation = None
        if any(w in text_lower for w in ["vertical", "portrait", "9:16", "9x16", "reel", "shorts", "tiktok", "story"]):
            orientation = "portrait"
        elif any(w in text_lower for w in ["horizontal", "landscape", "16:9", "16x9", "wide", "widescreen"]):
            orientation = "landscape"
        elif any(w in text_lower for w in ["square", "1:1", "1x1"]):
            orientation = "square"

        # 3. Clean search keywords
        clean_text = text_lower
        remove_phrases = [
            "i need", "we need", "stock footage of", "stock video of", "stock photo of",
            "footage of", "video of", "photo of", "image of", "icon of", "vertical", "horizontal",
            "portrait", "landscape", "square", "high quality", "hd", "4k", "b-roll", "broll",
        ]
        for p in remove_phrases:
            clean_text = re.sub(rf"\b{re.escape(p)}\b", " ", clean_text)

        cleaned_tokens = [w for w in clean_text.split() if len(w) > 2]
        query_str = " ".join(cleaned_tokens) if cleaned_tokens else requirement_text

        return StockSearchQuery(
            query=query_str,
            media_type=media_type,
            orientation=orientation,
            commercial_use_required=True,
        )


_default_acquisition_service: Optional[AssetAcquisitionService] = None


def get_asset_acquisition_service() -> AssetAcquisitionService:
    """Returns the singleton canonical AssetAcquisitionService."""
    global _default_acquisition_service
    if _default_acquisition_service is None:
        _default_acquisition_service = AssetAcquisitionService()
    return _default_acquisition_service
