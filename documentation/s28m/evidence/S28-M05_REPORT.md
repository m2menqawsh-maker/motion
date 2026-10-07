# S28-M05 — Milestone Execution & Evidence Report
**Milestone:** S28-M05 — Stock Media Acquisition Platform  
**Date:** 2026-10-04  
**Status:** **PASS** (with explicit `LIVE_SMOKE_BLOCKED` for unconfigured external API keys)  
**Workspace:** `clean-video-workspace` (`/home/eng_Momen/Projects/المشروع الحالي/Video maker`)  
**Execution Authority:** Clean Video Workspace Platform Architecture

---

## 1. Executive Summary

Milestone **S28-M05** has achieved **PASS** with zero regressions, zero capability loss, and full enforcement of architectural decoupling.

Under S28-M05:
- The legacy stock media capabilities buried inside `media-sources-mcp` have been transformed from unmanaged MCP subprocesses and direct filesystem writes into a first-class canonical Domain Service: `AssetAcquisitionService`.
- All 8 `MEDIA_ACQUISITION` capabilities (`SEARCH_STOCK_IMAGES`, `SEARCH_STOCK_VIDEOS`, `SEARCH_STOCK_AUDIO`, `SEARCH_SOUND_EFFECTS`, `SEARCH_ICONS`, `DOWNLOAD_ICON`, `DOWNLOAD_REMOTE_MEDIA`, `EXTRACT_MEDIA_PAGE`) are now routed via `CapabilityRouter` through `ToolGateway` using `AssetAcquisitionAdapter`, completely isolating callers, Creative Planners, and recipes from provider implementation details.
- Invariant **"Use real/licensed media first before expensive generation"** is canonically wired into `AssetAcquisitionService.acquire_for_creative_requirement` and `parse_creative_asset_requirement`.
- Strict boundary security: `safe_downloader` enforces fail-closed SSRF protection (blocking localhost, loopback, RFC1918, cloud metadata 169.254.169.254, non-HTTP schemes), manual redirect policy validation, a 50MB budget ceiling, and binary magic-byte inspection (blocking disguised HTML/PHP error pages).
- Zero raw disk writes in `ai/acquisition/`: all media payloads stream into memory buffers and persist canonically via `AssetService.upload_asset` into `StorageService`.
- First-class license & provenance tracking: every acquired asset records provider ID, creator, license classification, commercial use authorization, attribution requirements, and original query into the asset manifest.
- Two-phase deduplication: pre-download deduplication across duplicate provider IDs/URLs, and post-download content-hash (SHA-256) deduplication reusing existing project assets.
- Invariant **NO CAPABILITY LOSS** is strictly maintained: all legacy MCP tools under `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/` remain untouched and functional under `COMPATIBILITY_ONLY`.
- Zero fake success: Live smoke tests report `LIVE_SMOKE_PASS` for the public Iconify API and accurately report `LIVE_SMOKE_BLOCKED` with structured `ProviderAuthError` for unconfigured credentials (`PEXELS_API_KEY`, `PIXABAY_API_KEY`, `FREESOUND_API_KEY`).

---

## 2. Baseline Inventory (Before vs. After)

| Provider / Capability | Legacy Implementation | Legacy Operation | Network & Download Behavior | Filesystem Side Effects | Secret Requirement | Target Modernized Capability | Modernized Status |
|---|---|---|---|---|---|---|---|
| **Pexels (Photos & Videos)** | `tools/pexels.py` | Direct REST API queries | `requests.get`, unvalidated streaming | Direct unmanaged writes via `downloader.py` | `PEXELS_API_KEY` | `SEARCH_STOCK_IMAGES`, `SEARCH_STOCK_VIDEOS` | `ACTIVE_CANONICAL` via `AssetAcquisitionAdapter` -> `AssetAcquisitionService` |
| **Pixabay (Images & Videos)** | `tools/pixabay.py` | Direct REST API queries | `requests.get`, unvalidated streaming | Direct unmanaged writes via `downloader.py` | `PIXABAY_API_KEY` | `SEARCH_STOCK_IMAGES`, `SEARCH_STOCK_VIDEOS` | `ACTIVE_CANONICAL` via `AssetAcquisitionAdapter` -> `AssetAcquisitionService` |
| **Pixabay (Audio Scraper)** | `utils/pixabay_scraper.py` | Web scraping `pixabay.com/music/search/` | Requires Playwright Chromium; returns HTTP 403 (Cloudflare) | Direct unmanaged writes | None | `SEARCH_STOCK_AUDIO` | `BROKEN_UNVERIFIED_M05` (fails closed safely to `ProviderUnavailableError`, allowing Freesound fallback) |
| **Freesound (Audio & SFX)** | `tools/freesound.py` | Text search API | `requests.get`, preview downloads | Direct unmanaged writes via `downloader.py` | `FREESOUND_API_KEY` | `SEARCH_STOCK_AUDIO`, `SEARCH_SOUND_EFFECTS` | `ACTIVE_CANONICAL` via `AssetAcquisitionAdapter` -> `AssetAcquisitionService` |
| **Iconify (SVG Icons)** | `tools/iconify.py` | Public REST search & SVG download | `requests.get` from `api.iconify.design` | Direct unmanaged writes via `downloader.py` | None (Public API) | `SEARCH_ICONS`, `DOWNLOAD_ICON` | `ACTIVE_CANONICAL` via `AssetAcquisitionAdapter` -> `AssetAcquisitionService` (Live Verified) |
| **Remote Media Download** | `tools/mcp-server::download_media` | Arbitrary URL download | Unrestricted `requests.get` (SSRF vulnerable) | Arbitrary path writes | None | `DOWNLOAD_REMOTE_MEDIA` | `ACTIVE_CANONICAL` with fail-closed SSRF, magic byte check, and `AssetService` ingestion |
| **Web Media Extraction** | `tools/mcp-server::extract_media_from_page` | Webpage media extraction | Unrestricted `requests.get` | Arbitrary path writes | None | `EXTRACT_MEDIA_PAGE` | `ACTIVE_CANONICAL` governed by safe downloader |

---

## 3. Architecture & Design Implementation

### 3.1 Domain Contracts (`ai/acquisition/contracts.py`)
Canonical, strictly typed Pydantic models (frozen value objects with `extra="forbid"`):
- `StockMediaType`: Enum (`image`, `video`, `audio`, `sound_effect`, `icon`).
- `LicenseClassification`: Enum (`PEXELS_LICENSE`, `PIXABAY_LICENSE`, `CC0`, `CC_BY`, `CC_BY_SA`, `CC_BY_NC`, `PUBLIC_DOMAIN`, `OPEN_SOURCE_ICON`, `UNKNOWN`).
- `CommercialUseStatus`: Enum (`ALLOWED`, `NON_COMMERCIAL_ONLY`, `PROHIBITED`, `REQUIRES_REVIEW`, `UNKNOWN`).
- `DownloadVariant`: Variant specification (`variant_id`, `url`, `width`, `height`, `quality`, `fps`, `format`, `file_size_bytes`, `bitrate_kbps`).
- `StockCandidate`: Normalized candidate with rich metadata, licensing, tags, and explainable ranking breakdown (`candidate_id`, `source`, `source_asset_id`, `title`, `preview_url`, `download_variants`, `selected_variant`, `orientation`, `provenance_evidence`, `ranking_score`, `ranking_features`).
- `StockSearchQuery`: Structured cross-provider query (`query`, `media_type`, `orientation`, `min_width`, `min_height`, `min_duration`, `max_duration`, `commercial_use_required`, `require_no_attribution`, `allowed_providers`).
- `AcquisitionDescriptor`: Verified specification for safe download (`download_url`, `max_bytes`, `expected_mime_type`, `expected_format`).
- `AcquiredAssetResult`: Authoritative asset platform result (`project_id`, `asset_id`, `storage_key`, `content_hash`, `media_type`, `file_size_bytes`, `content_type`, `provenance_evidence`, `is_reused_existing`).

### 3.2 Error Taxonomy (`ai/acquisition/errors.py`)
Structured error hierarchy inheriting from `AcquisitionError`, each with `to_ai_error()` conversion into canonical `AIError`:
- `AcquisitionErrorCode.PROVIDER_UNAVAILABLE` -> `ProviderUnavailableError` (maps to `AIErrorCode.SERVICE_UNAVAILABLE`)
- `AcquisitionErrorCode.PROVIDER_AUTH_ERROR` -> `ProviderAuthError` (maps to `AIErrorCode.AUTHENTICATION_FAILED`)
- `AcquisitionErrorCode.PROVIDER_RATE_LIMIT` -> `ProviderRateLimitError` (maps to `AIErrorCode.RATE_LIMIT_EXCEEDED`)
- `AcquisitionErrorCode.INVALID_RESPONSE` -> `InvalidProviderResponseError` (maps to `AIErrorCode.UPSTREAM_ERROR`)
- `AcquisitionErrorCode.NO_ELIGIBLE_RESULTS` -> `NoEligibleResultsError` (maps to `AIErrorCode.RESOURCE_NOT_FOUND`)
- `AcquisitionErrorCode.UNSAFE_DOWNLOAD_SOURCE` -> `UnsafeDownloadSourceError` (maps to `AIErrorCode.SECURITY_VIOLATION`)
- `AcquisitionErrorCode.MEDIA_VALIDATION_FAILED` -> `MediaValidationError` (maps to `AIErrorCode.VALIDATION_ERROR`)
- `AcquisitionErrorCode.DOWNLOAD_FAILED` -> `DownloadFailedError` (maps to `AIErrorCode.EXTERNAL_CALL_FAILED`)
- `AcquisitionErrorCode.ASSET_IMPORT_FAILED` -> `AssetImportError` (maps to `AIErrorCode.INTERNAL_ERROR`)
- `AcquisitionErrorCode.AUTHORIZATION_DENIED` -> `AcquisitionAuthorizationError` (maps to `AIErrorCode.PERMISSION_DENIED`)

### 3.3 Safe Downloader (`ai/acquisition/safe_downloader.py`)
- **Fail-Closed SSRF Validation (`assert_safe_url`):** Rejects all non-HTTP(S) schemes (`file://`, `ftp://`, `gopher://`, `data:`). Rejects internal hostnames (`localhost`, `metadata.google.internal`, `*.local`, `*.internal`). Rejects IP literals for loopback (`127.0.0.0/8`, `::1`), private RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and link-local cloud metadata (`169.254.169.254`).
- **Redirect Loop & Egress Guard:** `follow_redirects=False` with manual redirect loop (max 3 hops), re-validating `assert_safe_url(next_url)` before following any redirect.
- **Budget Ceiling:** Enforces 50MB ceiling on headers (`content-length`) and streamed payload bytes.
- **Binary Magic-Byte Inspection (`verify_magic_bytes`):** Verifies file signatures for MP4 (`ftyp`), WebM (`\x1a\x45\xdf\xa3`), JPEG (`\xff\xd8\xff`), PNG (`\x89PNG`), WebP (`RIFF...WEBP`), MP3 (`ID3` / frame sync), WAV (`RIFF...WAVE`), OGG (`OggS`), and SVG (`<svg`). Explicitly identifies and rejects HTML/PHP error pages disguised as media binaries.
- **Hermetic Memory:** Zero disk writes; returns in-memory `DownloadedPayload(content_bytes, content_hash, mime_type, file_size_bytes, suggested_extension)`.

### 3.4 Hard Filtering & Deterministic Ranking (`ai/acquisition/filtering.py`, `ranking.py`)
- **Hard Constraints First:** Disqualifies candidates before ranking on media type mismatch, orientation mismatch (portrait vs landscape), minimum dimension boundaries (width, height), duration limits (min/max seconds), commercial use prohibition, or attribution policies.
- **Multi-Factor Deterministic Ranking:** Computes auditable score `ranking_score = 0.40 * relevance + 0.20 * dimensions + 0.20 * duration + 0.15 * license + 0.05 * provider`, recording full feature breakdown in `candidate.ranking_features`.
- **Zero Hallucination:** Completely independent of non-deterministic LLM evaluation.

### 3.5 Deduplication & Caching (`ai/acquisition/dedupe.py`, `service.py`)
- **Pre-Download Deduplication:** Deduplicates duplicate provider composite keys (`source:source_asset_id`) and identical remote URLs, preserving the highest-ranked candidate.
- **Post-Download Deduplication:** Checks SHA-256 digest against `AssetService.list_assets(project_id)` before uploading. Reuses existing canonical asset record if matching hash exists (`is_reused_existing=True`).
- **In-Memory Search Cache (`SearchCache`):** 300s TTL cache on normalized query parameters preventing redundant remote API queries.

### 3.6 Authoritative Domain Service (`ai/acquisition/service.py`)
- `AssetAcquisitionService` coordinates multi-provider queries with fault isolation (Provider A failure does not crash Provider B).
- Validates tenant confinement: cross-tenant access between caller context and target project is denied.
- Canonically uploads via `AssetService.upload_asset(project_id, content, filename, kind)` and persists into `StorageService`.
- Includes `acquire_for_creative_requirement` and `parse_creative_asset_requirement` for direct `CreativePlan.asset_requirements` integration.

### 3.7 ToolGateway Adapter & Runtime Registration
- `AssetAcquisitionAdapter` (`ai/tools/adapters/acquisition.py`) executes all 8 `MEDIA_ACQUISITION` capabilities and translates outputs into canonical contracts (`StockMediaItem`, `IconSearchResultItem`, `DownloadRemoteMediaOutput`, etc.).
- Registered in `AdapterRegistry` with second priority (immediately following `DomainServiceAdapter`).
- `documentation/s28m/CAPABILITY_CATALOG.json` and `CAPABILITY_RUNTIME_MATRIX.md` updated: rows 19–26 marked as `AssetAcquisitionAdapter` -> `AssetAcquisitionService` (`ACTIVE_CANONICAL`).

---

## 4. Test Verification Results

### 4.1 Acquisition Test Suite (`tests/ai/acquisition/`) — 67/67 PASSED
```text
tests/ai/acquisition/test_contracts_and_normalization.py .........       [ 13%]
tests/ai/acquisition/test_dedupe_and_cache.py .......                    [ 23%]
tests/ai/acquisition/test_e2e_acquisition_pipeline.py .....              [ 31%]
tests/ai/acquisition/test_filtering_and_ranking.py .........             [ 44%]
tests/ai/acquisition/test_legacy_parity.py ....                          [ 50%]
tests/ai/acquisition/test_live_smoke.py ....                             [ 56%]
tests/ai/acquisition/test_provider_fault_tolerance.py ...                [ 61%]
tests/ai/acquisition/test_safe_downloader_and_security.py .............. [ 82%]
........                                                                 [ 94%]
tests/ai/acquisition/test_tool_gateway_acquisition.py ....               [100%]
============================== 67 passed in 1.35s ==============================
```

### 4.2 Tool Gateway & Routing Subsystems — 130/130 PASSED
```text
tests/ai/tools/ (10 test suites) ........................................ 78 passed
tests/ai/routing/ (9 test suites) ....................................... 52 passed
============================= 130 passed in 5.65s ==============================
```

### 4.3 Architecture Guards — 26/26 PASSED
```text
tests/ai/test_ai_architecture_guards.py ...........                      [ 42%]
tests/ai/media_intelligence/test_architecture_guards.py .......          [ 69%]
tests/ai/tools/test_architecture_guards.py ........                      [100%]
============================== 26 passed in 1.73s ==============================
```
- Verified: Zero raw filesystem writes (`open()`, `write_bytes()`) in `ai/acquisition/`.
- Verified: Zero hardcoded `"projects/"` path literals in `ai/acquisition/`.
- Verified: Zero direct provider adapter imports in recipes or planners.

### 4.4 Contract Synchronization & TypeScript Parity
- `scripts/generate_ai_contracts.py --check` -> ✅ **PASS**
- `scripts/generate_creative_contracts.py --check` -> ✅ **PASS**
- `scripts/validators/check_ground_truth_sync.py --check` -> ✅ **PASS**
- Vitest suite (`npm test`) -> ✅ **153/153 passed**
- TypeScript contract parity (`capability_contracts_parity.test.ts`, `creative_contracts_parity.test.ts`) -> ✅ **21/21 passed**

---

## 5. Live Smoke Status

| Provider | Authentication Type | Live Network Smoke Status | Verification Details |
|---|---|---|---|
| **Iconify** | Public REST API (No Key) | **`LIVE_SMOKE_PASS`** | Live network call to `https://api.iconify.design/search` returned HTTP 200 and normalized icon candidates (`test_live_smoke_iconify_public_api`). |
| **Pexels** | `PEXELS_API_KEY` | **`LIVE_SMOKE_BLOCKED`** | No API key in environment; `is_available()=False`; calling live search raises `ProviderAuthError` fail-closed (`test_live_smoke_pexels_credentials_check`). Mock/fixture contract tests 100% PASS. |
| **Pixabay** | `PIXABAY_API_KEY` | **`LIVE_SMOKE_BLOCKED`** | No API key in environment; `is_available()=False`; calling live search raises `ProviderAuthError` fail-closed (`test_live_smoke_pixabay_credentials_check`). Mock/fixture contract tests 100% PASS. Audio scraper fails closed to `ProviderUnavailableError`. |
| **Freesound** | `FREESOUND_API_KEY` | **`LIVE_SMOKE_BLOCKED`** | No API key in environment; `is_available()=False`; calling live search raises `ProviderAuthError` fail-closed (`test_live_smoke_freesound_credentials_check`). Mock/fixture contract tests 100% PASS. |

---

## 6. Gate Verification Checklist

| Requirement | Evaluation | Status |
|---|---|---|
| **1. NO CAPABILITY LOSS** | All legacy MCP server files preserved untouched under `.agents/.../media-sources-mcp/`. New canonical layer provides strict superset parity. | **MET** |
| **2. Architectural Decoupling** | AI callers invoke only capability contracts via `CapabilityRouter` -> `ToolGateway`. Zero provider leakage into planners or recipes. | **MET** |
| **3. Authoritative Domain Service** | `AssetAcquisitionService` governs search, normalization, filtering, ranking, deduplication, and safe ingestion. | **MET** |
| **4. Safe Downloader Boundary** | Fail-closed SSRF, redirect control, 50MB ceiling, magic-byte inspection, zero raw filesystem writes. | **MET** |
| **5. License & Provenance** | Explicit license categorization, commercial-use flags, attribution requirements, and retrieval timestamps stored as canonical metadata. | **MET** |
| **6. Hard Filtering & Ranking** | Incompatible candidates rejected before ranking. Deterministic multi-factor scoring with explainable feature breakdown. | **MET** |
| **7. Two-Phase Deduplication** | Pre-download URL/identity dedupe and post-download SHA-256 hash dedupe reusing existing project assets. | **MET** |
| **8. CreativePlan Seam** | `acquire_for_creative_requirement` and `parse_creative_asset_requirement` wired to enforce "real media first before generation". | **MET** |
| **9. Test Coverage & Contracts** | 67 acquisition unit/integration tests pass. 130 tool/routing tests pass. Architecture guards pass. Contracts synchronized. | **MET** |
| **10. Truthful Live Status** | Iconify verified live (`LIVE_SMOKE_PASS`). Uncredentialed providers accurately reported as `LIVE_SMOKE_BLOCKED` without fake success. | **MET** |

**Final Verdict: PASS (Exit Gate Met)**
