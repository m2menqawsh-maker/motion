"""
Tests for Stock Media Deduplication and Caching (S28-M05).
"""

import time
from unittest.mock import patch
import pytest

from ai.acquisition.contracts import (
    StockCandidate,
    StockMediaType,
    DownloadVariant,
    LicenseClassification,
    CommercialUseStatus,
    StockSearchQuery,
)
from ai.acquisition.dedupe import StockDedupeEngine
from ai.acquisition.service import SearchCache


def _make_candidate(
    source="pexels",
    source_asset_id="1",
    url="https://example.com/asset1.mp4",
) -> StockCandidate:
    return StockCandidate(
        candidate_id=f"{source}:{source_asset_id}",
        source=source,
        source_asset_id=source_asset_id,
        media_type=StockMediaType.VIDEO,
        title="Test Candidate",
        preview_url="https://example.com/prev.jpg",
        download_variants=[DownloadVariant(variant_id="hd", url=url)],
        selected_variant=DownloadVariant(variant_id="hd", url=url),
        duration_seconds=10.0,
        license=LicenseClassification.PUBLIC_DOMAIN,
        commercial_use=CommercialUseStatus.ALLOWED,
        attribution_required=False,
        retrieved_at="2026-10-04T12:00:00Z",
    )


class TestCandidateDeduplication:
    """Verifies pre-acquisition candidate deduplication."""

    def test_dedupes_identical_provider_id(self):
        c1 = _make_candidate(source="pexels", source_asset_id="100", url="https://example.com/v1.mp4")
        c2 = _make_candidate(source="pexels", source_asset_id="100", url="https://example.com/v2.mp4")
        c3 = _make_candidate(source="pexels", source_asset_id="200", url="https://example.com/v3.mp4")

        deduped = StockDedupeEngine.deduplicate_candidates([c1, c2, c3])
        assert len(deduped) == 2
        assert [c.source_asset_id for c in deduped] == ["100", "200"]

    def test_dedupes_identical_download_url(self):
        c1 = _make_candidate(source="pexels", source_asset_id="100", url="https://example.com/shared.mp4")
        c2 = _make_candidate(source="pixabay", source_asset_id="999", url="https://example.com/shared.mp4")
        c3 = _make_candidate(source="pixabay", source_asset_id="888", url="https://example.com/unique.mp4")

        deduped = StockDedupeEngine.deduplicate_candidates([c1, c2, c3])
        assert len(deduped) == 2
        assert deduped[0].candidate_id == "pexels:100"
        assert deduped[1].candidate_id == "pixabay:888"


class TestStorageDeduplication:
    """Verifies post-download content-hash deduplication against AssetService."""

    @patch("ai.acquisition.dedupe.AssetService.list_assets")
    def test_find_existing_asset_hit(self, mock_list_assets):
        target_hash = "abcdef1234567890"
        mock_list_assets.return_value = [
            {"asset_id": "asset_001", "metadata": {"content_hash": "other_hash"}},
            {"asset_id": "asset_002", "metadata": {"content_hash": target_hash}},
        ]

        found = StockDedupeEngine.find_existing_asset_by_hash("proj_123", target_hash)
        assert found is not None
        assert found["asset_id"] == "asset_002"

    @patch("ai.acquisition.dedupe.AssetService.list_assets")
    def test_find_existing_asset_miss(self, mock_list_assets):
        target_hash = "non_existent_hash"
        mock_list_assets.return_value = [
            {"asset_id": "asset_001", "metadata": {"content_hash": "hash_1"}},
        ]

        found = StockDedupeEngine.find_existing_asset_by_hash("proj_123", target_hash)
        assert found is None


class TestSearchCache:
    """Verifies TTL caching for stock searches."""

    def test_cache_hit_and_miss(self):
        cache = SearchCache(ttl_seconds=10.0)
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO)
        c1 = _make_candidate()

        assert cache.get(query) is None

        cache.set(query, [c1])
        cached = cache.get(query)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].candidate_id == c1.candidate_id

    def test_cache_expiration(self):
        cache = SearchCache(ttl_seconds=0.05)
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO)
        c1 = _make_candidate()

        cache.set(query, [c1])
        time.sleep(0.06)

        assert cache.get(query) is None

    def test_cache_clear(self):
        cache = SearchCache(ttl_seconds=10.0)
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO)
        cache.set(query, [_make_candidate()])
        cache.clear()
        assert cache.get(query) is None


class TestConcurrentDeduplication:
    """Verifies that concurrent acquisition of identical content yields exactly one canonical asset via database CAS authority."""

    @pytest.mark.asyncio
    async def test_concurrent_acquisition_deduplicates_to_single_asset(self):
        import asyncio
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        from ai.acquisition.safe_downloader import DownloadedPayload
        from ai.acquisition.service import AssetAcquisitionService
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository

        project_id = "prj_concurrent_dedupe"
        proj_dir = Path("projects") / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = proj_dir / "02_asset_manifest.json"
        manifest_path.write_text('{"schema_version": "2.0.0", "project_id": "prj_concurrent_dedupe", "assets": []}', encoding="utf-8")

        # Independent service instances simulating distinct worker execution contexts
        services = [AssetAcquisitionService() for _ in range(5)]
        candidate = _make_candidate(source="pexels", source_asset_id="concur_1", url="https://example.com/asset.mp4")

        dummy_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00" + (b"\x11" * 100)
        dummy_hash = hashlib.sha256(dummy_bytes).hexdigest()
        assert len(dummy_hash) == 64, "Must be full 64-char SHA-256"

        mock_payload = DownloadedPayload(
            content_bytes=dummy_bytes,
            content_hash=dummy_hash,
            mime_type="video/mp4",
            file_size_bytes=len(dummy_bytes),
            suggested_extension=".mp4",
        )

        canon_repo = CanonicalAssetRepository()
        try:
            with canon_repo.db.transaction("IMMEDIATE") as conn:
                conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))

            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                # Run 5 concurrent acquisition requests across 5 INDEPENDENT service instances
                results = await asyncio.gather(*[
                    services[i].acquire_candidate(candidate, project_id)
                    for i in range(5)
                ])

            # 1. All return successfully
            assert len(results) == 5
            # 2. All point to the exact same canonical asset_id using full SHA-256
            expected_asset_id = f"ast_{dummy_hash}"
            assert all(r.asset_id == expected_asset_id for r in results)
            assert all(r.content_hash == dummy_hash for r in results)

            # 3. Exactly 1 leader executed full ingestion, 4 reused existing via CAS
            reused_statuses = [r.is_reused_existing for r in results]
            assert reused_statuses.count(False) == 1
            assert reused_statuses.count(True) == 4

            # 4. Check database authority has exactly ONE canonical asset record
            db_record = canon_repo.find_by_hash(project_id, dummy_hash)
            assert db_record is not None
            assert db_record.asset_id == expected_asset_id
            assert db_record.content_hash == dummy_hash

            # 5. Check manifest has exactly ONE asset
            assets = AssetService.list_assets(project_id)
            assert len(assets) == 1
            assert assets[0]["asset_id"] == expected_asset_id
            assert assets[0]["content_hash"] == dummy_hash
        finally:
            try:
                with canon_repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))
            except Exception:
                pass
            if proj_dir.exists():
                shutil.rmtree(proj_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_concurrent_independent_service_instances_cas_uniqueness(self):
        """Cross-session test verifying that separate service instances respect DB unique constraints."""
        import asyncio
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        from ai.acquisition.safe_downloader import DownloadedPayload
        from ai.acquisition.service import AssetAcquisitionService
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository

        project_id = "prj_cas_uniqueness"
        proj_dir = Path("projects") / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = proj_dir / "02_asset_manifest.json"
        manifest_path.write_text('{"schema_version": "2.0.0", "project_id": "prj_cas_uniqueness", "assets": []}', encoding="utf-8")

        service_worker_a = AssetAcquisitionService()
        service_worker_b = AssetAcquisitionService()

        dummy_bytes = b"\x00\x00\x00\x18ftypisom" + (b"\x99" * 80)
        full_hash = hashlib.sha256(dummy_bytes).hexdigest()

        mock_payload = DownloadedPayload(
            content_bytes=dummy_bytes,
            content_hash=full_hash,
            mime_type="video/mp4",
            file_size_bytes=len(dummy_bytes),
            suggested_extension=".mp4",
        )

        canon_repo = CanonicalAssetRepository()
        try:
            with canon_repo.db.transaction("IMMEDIATE") as conn:
                conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))

            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                res_a, res_b = await asyncio.gather(
                    service_worker_a.download_remote_media(project_id, "https://example.com/v.mp4", "video"),
                    service_worker_b.download_remote_media(project_id, "https://example.com/v.mp4", "video"),
                )

            assert res_a.asset_id == res_b.asset_id == f"ast_{full_hash}"
            assert res_a.content_hash == res_b.content_hash == full_hash
            assert {res_a.is_reused_existing, res_b.is_reused_existing} == {True, False}

            # Check single persistence
            rec = canon_repo.find_by_hash(project_id, full_hash)
            assert rec is not None
            assert rec.asset_id == f"ast_{full_hash}"
        finally:
            try:
                with canon_repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))
            except Exception:
                pass
            if proj_dir.exists():
                shutil.rmtree(proj_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_same_hash_same_project_one_canonical_asset(self):
        """same hash + same project → one canonical asset (deduplication)"""
        import asyncio
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        from ai.acquisition.safe_downloader import DownloadedPayload
        from ai.acquisition.service import AssetAcquisitionService
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository

        project_id = "prj_same_hash_same_proj"
        proj_dir = Path("projects") / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = proj_dir / "02_asset_manifest.json"
        manifest_path.write_text(f'{{"schema_version": "2.0.0", "project_id": "{project_id}", "assets": []}}', encoding="utf-8")

        service = AssetAcquisitionService()
        dummy_bytes = b"\x00\x00\x00\x18ftypisom" + (b"\xaa" * 120)
        full_hash = hashlib.sha256(dummy_bytes).hexdigest()

        mock_payload = DownloadedPayload(
            content_bytes=dummy_bytes,
            content_hash=full_hash,
            mime_type="video/mp4",
            file_size_bytes=len(dummy_bytes),
            suggested_extension=".mp4",
        )

        canon_repo = CanonicalAssetRepository()
        try:
            with canon_repo.db.transaction("IMMEDIATE") as conn:
                conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))

            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                res_1 = await service.download_remote_media(project_id, "https://example.com/item.mp4", "video")
                res_2 = await service.download_remote_media(project_id, "https://example.com/item.mp4", "video")

            # 1. First run creates, second reuses existing
            assert res_1.is_reused_existing is False
            assert res_2.is_reused_existing is True
            assert res_1.asset_id == res_2.asset_id == f"ast_{full_hash}"
            assert res_1.content_hash == res_2.content_hash == full_hash

            # 2. Database contains strictly ONE canonical asset record
            db_records = canon_repo.list_by_project(project_id)
            assert len(db_records) == 1
            assert db_records[0].id == f"{project_id}:{full_hash}"
            assert db_records[0].content_hash == full_hash

            # 3. Manifest contains strictly ONE asset
            assets = AssetService.list_assets(project_id)
            assert len(assets) == 1
            assert assets[0]["asset_id"] == f"ast_{full_hash}"
            assert assets[0]["content_hash"] == full_hash
        finally:
            try:
                with canon_repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))
            except Exception:
                pass
            if proj_dir.exists():
                shutil.rmtree(proj_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_same_hash_different_project_independent_scoped_behavior(self):
        """same hash + different project → valid independent project-scoped behavior without collision"""
        import asyncio
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        from ai.acquisition.safe_downloader import DownloadedPayload
        from ai.acquisition.service import AssetAcquisitionService
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository

        project_a = "prj_scope_alpha"
        project_b = "prj_scope_beta"
        for p_id in [project_a, project_b]:
            p_dir = Path("projects") / p_id
            p_dir.mkdir(parents=True, exist_ok=True)
            m_path = p_dir / "02_asset_manifest.json"
            m_path.write_text(f'{{"schema_version": "2.0.0", "project_id": "{p_id}", "assets": []}}', encoding="utf-8")

        service_a = AssetAcquisitionService()
        service_b = AssetAcquisitionService()

        identical_bytes = b"\x00\x00\x00\x18ftypisom" + (b"\xbb" * 150)
        full_hash = hashlib.sha256(identical_bytes).hexdigest()

        mock_payload = DownloadedPayload(
            content_bytes=identical_bytes,
            content_hash=full_hash,
            mime_type="video/mp4",
            file_size_bytes=len(identical_bytes),
            suggested_extension=".mp4",
        )

        canon_repo = CanonicalAssetRepository()
        try:
            with canon_repo.db.transaction("IMMEDIATE") as conn:
                conn.execute("DELETE FROM canonical_assets WHERE project_id IN (?, ?)", (project_a, project_b))

            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                res_a = await service_a.download_remote_media(project_a, "https://example.com/shared.mp4", "video")
                res_b = await service_b.download_remote_media(project_b, "https://example.com/shared.mp4", "video")

            # 1. Both successfully import without constraint collision
            assert res_a.is_reused_existing is False
            assert res_b.is_reused_existing is False
            assert res_a.content_hash == res_b.content_hash == full_hash

            # 2. Database contains independent scoped records with distinct composite primary keys
            rec_a = canon_repo.find_by_hash(project_a, full_hash)
            rec_b = canon_repo.find_by_hash(project_b, full_hash)
            assert rec_a is not None and rec_b is not None
            assert rec_a.id == f"{project_a}:{full_hash}"
            assert rec_b.id == f"{project_b}:{full_hash}"
            assert rec_a.id != rec_b.id
            assert rec_a.project_id == project_a
            assert rec_b.project_id == project_b

            # 3. Both projects maintain independent manifests
            manifest_a = AssetService.list_assets(project_a)
            manifest_b = AssetService.list_assets(project_b)
            assert len(manifest_a) == 1
            assert len(manifest_b) == 1
            assert manifest_a[0]["content_hash"] == full_hash
            assert manifest_b[0]["content_hash"] == full_hash
        finally:
            try:
                with canon_repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM canonical_assets WHERE project_id IN (?, ?)", (project_a, project_b))
            except Exception:
                pass
            for p_id in [project_a, project_b]:
                shutil.rmtree(Path("projects") / p_id, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_same_hash_different_workspace_tenant_no_collision_and_no_leak(self):
        """same hash + different workspace/tenant → no collision and no information leak"""
        import asyncio
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        import pytest
        from ai.acquisition.errors import AcquisitionAuthorizationError
        from ai.acquisition.safe_downloader import DownloadedPayload
        from ai.acquisition.service import AssetAcquisitionService
        from ai.tools.types import TrustedToolExecutionContext
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository
        from scripts.core.database import TenantRepository, UserStatus

        ws_tenant_1 = "ws_tenant_corp_1"
        ws_tenant_2 = "ws_tenant_corp_2"
        prj_tenant_1 = "prj_tenant_corp_1"
        prj_tenant_2 = "prj_tenant_corp_2"

        canon_repo = CanonicalAssetRepository()
        tenant_repo = TenantRepository(canon_repo.db)

        # Register tenants and projects in database authority
        with canon_repo.db.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM canonical_assets WHERE project_id IN (?, ?)", (prj_tenant_1, prj_tenant_2))
            conn.execute("DELETE FROM projects WHERE id IN (?, ?)", (prj_tenant_1, prj_tenant_2))
            conn.execute("DELETE FROM workspaces WHERE id IN (?, ?)", (ws_tenant_1, ws_tenant_2))
            conn.execute("DELETE FROM users WHERE id IN ('usr_t1', 'usr_t2')")

        tenant_repo.create_user("usr_t1", "t1@example.com", UserStatus.ACTIVE)
        tenant_repo.create_user("usr_t2", "t2@example.com", UserStatus.ACTIVE)
        tenant_repo.create_workspace(ws_tenant_1, "Tenant 1", "usr_t1")
        tenant_repo.create_workspace(ws_tenant_2, "Tenant 2", "usr_t2")
        tenant_repo.create_project(project_id=prj_tenant_1, workspace_id=ws_tenant_1, name="Project T1", created_by="usr_t1")
        tenant_repo.create_project(project_id=prj_tenant_2, workspace_id=ws_tenant_2, name="Project T2", created_by="usr_t2")

        for p_id in [prj_tenant_1, prj_tenant_2]:
            p_dir = Path("projects") / p_id
            p_dir.mkdir(parents=True, exist_ok=True)
            m_path = p_dir / "02_asset_manifest.json"
            m_path.write_text(f'{{"schema_version": "2.0.0", "project_id": "{p_id}", "assets": []}}', encoding="utf-8")

        ctx_1 = TrustedToolExecutionContext(
            workspace_id=ws_tenant_1,
            actor_id="usr_t1",
            roles=["editor"],
            permissions=["editor"],
            accessible_projects=[prj_tenant_1],
        )
        ctx_2 = TrustedToolExecutionContext(
            workspace_id=ws_tenant_2,
            actor_id="usr_t2",
            roles=["editor"],
            permissions=["editor"],
            accessible_projects=[prj_tenant_2],
        )

        service_1 = AssetAcquisitionService()
        service_2 = AssetAcquisitionService()

        identical_bytes = b"\x00\x00\x00\x18ftypisom" + (b"\xcc" * 200)
        full_hash = hashlib.sha256(identical_bytes).hexdigest()

        mock_payload = DownloadedPayload(
            content_bytes=identical_bytes,
            content_hash=full_hash,
            mime_type="video/mp4",
            file_size_bytes=len(identical_bytes),
            suggested_extension=".mp4",
        )

        try:
            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                res_1 = await service_1.download_remote_media(
                    prj_tenant_1, "https://example.com/asset.mp4", "video", workspace_id=ws_tenant_1, context=ctx_1
                )
                res_2 = await service_2.download_remote_media(
                    prj_tenant_2, "https://example.com/asset.mp4", "video", workspace_id=ws_tenant_2, context=ctx_2
                )

            # 1. No collision, independent creations, no information leak
            assert res_1.is_reused_existing is False
            assert res_2.is_reused_existing is False
            assert res_1.content_hash == res_2.content_hash == full_hash

            # 2. Database records reflect strict tenant isolation
            rec_1 = canon_repo.find_by_hash(prj_tenant_1, full_hash)
            rec_2 = canon_repo.find_by_hash(prj_tenant_2, full_hash)
            assert rec_1 is not None and rec_2 is not None
            assert rec_1.workspace_id == ws_tenant_1
            assert rec_2.workspace_id == ws_tenant_2
            assert rec_1.project_id == prj_tenant_1
            assert rec_2.project_id == prj_tenant_2
            assert rec_1.id != rec_2.id

            # 3. Cross-tenant mutation is strictly blocked
            with pytest.raises(AcquisitionAuthorizationError):
                await service_2.download_remote_media(
                    prj_tenant_1, "https://example.com/asset.mp4", "video", workspace_id=ws_tenant_2, context=ctx_2
                )
        finally:
            try:
                with canon_repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM canonical_assets WHERE project_id IN (?, ?)", (prj_tenant_1, prj_tenant_2))
                    conn.execute("DELETE FROM projects WHERE id IN (?, ?)", (prj_tenant_1, prj_tenant_2))
                    conn.execute("DELETE FROM workspaces WHERE id IN (?, ?)", (ws_tenant_1, ws_tenant_2))
                    conn.execute("DELETE FROM users WHERE id IN ('usr_t1', 'usr_t2')")
            except Exception:
                pass
            for p_id in [prj_tenant_1, prj_tenant_2]:
                shutil.rmtree(Path("projects") / p_id, ignore_errors=True)


