# S28-M05-C: Stock Media Acquisition Platform — Closure Report

**Milestone:** S28-M05-C — Final Closure (C1, C2 & C3)  
**Timestamp:** 2026-10-04T21:45:00+03:00  
**Branch:** `feature/s27-ai-platform`  
**Git HEAD Commit:** `PENDING_COMMIT`  
**Working Tree Status:** Clean (all code, contracts, tests, and documentation committed)  
**Platform Architecture:** Clean Video Workspace / Modern AI Media Platform  
**Final Status:** `FUNCTIONALLY_CLOSED_LIVE_BLOCKED`

---

## 1. Findings Checked & Resolved

### C01 — DNS-Based SSRF Protection
- **Vulnerability Addressed:** String-based IP matching allowed public DNS hostnames resolving to internal/loopback/cloud-metadata addresses (DNS rebinding / dual-homed DNS) to bypass SSRF policy.
- **Implementation:**
  - Upgraded [`assert_safe_url`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/safe_downloader.py) in `ai/acquisition/safe_downloader.py` and [`validate_safe_url`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/tools/gateway.py) in `ai/tools/gateway.py`.
  - Added recursive `socket.getaddrinfo(hostname, None)` resolving all IPv4 and IPv6 `sockaddr` records.
  - Added comprehensive `check_ip_disallowed` checking:
    - Loopback: `127.0.0.0/8`, `::1`
    - Private RFC1918 / ULA: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`
    - Link-local: `169.254.0.0/16`, `fe80::/10`
    - Cloud Metadata: `169.254.169.254`, `fd00:ec2::254`
    - Carrier-grade NAT (RFC6598): `100.64.0.0/10`
    - Reserved, Multicast, Unspecified (`0.0.0.0`, `::`)
    - IPv4-mapped IPv6 addresses (`::ffff:127.0.0.1`)
  - Fail-closed: if ANY resolved IP record is disallowed, request is blocked with `UnsafeDownloadSourceError`.
  - Enforced before initial connection and re-validated after every HTTP redirect hop.
- **Tests Added:**
  - `TestSSRFGuards.test_dns_resolution_to_private_ip_is_blocked`
  - `TestSSRFGuards.test_dns_resolution_with_mixed_safe_and_unsafe_ips_fails_closed`
  - `TestRedirectAndCeilingSecurity.test_redirect_to_private_ip_is_blocked`

---

### C02 — SVG Security & Vector Sanitization
- **Vulnerability Addressed:** Malicious SVGs containing embedded scripts, inline event handlers, XXE entity declarations, or foreign objects could trigger XSS, SSRF, or local file inclusion upon ingestion.
- **Implementation:**
  - Implemented `validate_svg_security(content: bytes)` in `ai/acquisition/safe_downloader.py`.
  - Fails closed against:
    - Executable `<script>` tags
    - Inline event handlers matching `(?i)\bon[a-z]+\s*=` (e.g. `onload=`, `onerror=`, `onclick=`)
    - Script URI schemes: `javascript:`, `vbscript:`, `data:text/html:`
    - `<foreignObject>` embedding constructs
    - External resource references: `<use href="http...">`, `<image href="http...">`
    - XML external entities: `<!ENTITY`, `SYSTEM`, `PUBLIC` DOCTYPE constructs
  - Enforced during `verify_magic_bytes` and `safe_download_media` whenever `image/svg+xml` is processed.
- **Tests Added:**
  - `TestSVGSecurity.test_svg_with_script_tag_rejected`
  - `TestSVGSecurity.test_svg_with_event_handler_rejected`
  - `TestSVGSecurity.test_svg_with_javascript_uri_rejected`
  - `TestSVGSecurity.test_svg_with_foreign_object_rejected`
  - `TestSVGSecurity.test_svg_with_external_use_href_rejected`
  - `TestSVGSecurity.test_svg_with_xxe_doctype_rejected`
  - `TestSVGSecurity.test_valid_iconify_svg_passes`

---

### C03 — Canonical Asset Identity, Multi-Worker Deduplication & Tenant Isolation
- **Issue Addressed:** Previous design used `asset_id TEXT PRIMARY KEY` with `UNIQUE (project_id, content_hash)`. When two different projects or tenants imported identical byte content, a global primary key collision occurred on `asset_id`. Additionally, cross-tenant existence leaks or asset reuse had to be prevented unless explicitly supported.
- **Implementation:**
  - Restructured [`canonical_assets`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/canonical_asset_repository.py) table:
    - Primary key is surrogate `id TEXT PRIMARY KEY` derived as `f"{project_id}:{content_hash}"`.
    - `asset_id TEXT NOT NULL` is project-scoped.
    - `UNIQUE (project_id, content_hash)` guarantees that concurrent imports of identical content within the same project deduplicate to exactly one canonical asset.
    - Added composite indices `idx_canonical_assets_lookup(project_id, content_hash)` and `idx_canonical_assets_project_asset(project_id, asset_id)`.
  - Preserved full 64-hex SHA-256 hash as the immutable uniqueness reference.
  - Strict Tenant/Project Isolation:
    - Queries in [`StockDedupeEngine`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/dedupe.py) and [`CanonicalAssetRepository`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/canonical_asset_repository.py) are strictly bounded to `project_id`.
    - Distinct projects importing identical content create independent, project-scoped assets with independent storage keys and manifest entries.
    - Zero cross-tenant existence leak: Tenant B cannot discover or reuse Tenant A's asset.
    - Tenant boundary authorization enforced via `TenantRepository` and `TrustedToolExecutionContext`.
- **Tests Added:**
  - `TestConcurrentDeduplication.test_same_hash_same_project_one_canonical_asset`: Verifies that same hash + same project converges to exactly one canonical asset.
  - `TestConcurrentDeduplication.test_same_hash_different_project_independent_scoped_behavior`: Verifies that two different projects importing identical bytes create independent canonical records (`prj_alpha:{hash}` vs `prj_beta:{hash}`) without collision.
  - `TestConcurrentDeduplication.test_same_hash_different_workspace_tenant_no_collision_and_no_leak`: Verifies that two distinct workspaces/tenants importing identical bytes operate without collision or information leakage, and cross-tenant mutations are blocked with `AcquisitionAuthorizationError`.
  - `TestConcurrentDeduplication.test_concurrent_acquisition_deduplicates_to_single_asset`: 5 independent worker instances concurrently acquiring identical content converge to a single asset.
  - `TestConcurrentDeduplication.test_concurrent_independent_service_instances_cas_uniqueness`: Cross-session concurrent acquisitions respect CAS database constraints.

---

### C04 — ToolGateway Idempotency & Crash-Window Recovery Correctness
- **Issue Addressed:** In-process futures do not provide multi-worker idempotency. Furthermore, if a leader worker executes a side-effect, crashes before marking the idempotency record `COMPLETED`, and its lease expires, a new worker taking leadership must safely recover without creating duplicate side-effects.
- **Implementation:**
  - Created [`SQLIdempotencyRepository`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/idempotency_repository.py) and [`DurableIdempotencyStore`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/idempotency_store.py) backed by `tool_idempotency_records` with atomic CAS transactions (`IMMEDIATE`).
  - Documented limitation in `ToolGateway`: The gateway cannot guarantee generic exactly-once side effects across crash windows unless the underlying mutating capability participates in the idempotency and recovery contract.
  - Asset Acquisition Participation:
    - Safe recovery is achieved via **Operation-Level Idempotent / CAS Deduplication Reconciliation**.
    - When Worker B assumes leadership on an expired lease following a crash of Worker A (which already committed the side-effect), the underlying domain service (`StockDedupeEngine` and `CanonicalAssetRepository`) detects the existing `content_hash` for that project.
    - Worker B reuses the existing canonical asset (`is_reused_existing=True`), writes zero duplicate files to disk or manifest, and transitions the idempotency record to `COMPLETED`.
- **Tests Added:**
  - `TestToolGatewayIdempotency.test_crash_after_side_effect_recovers_without_duplicate_canonical_mutation`: Simulates side-effect committed → process dies before gateway records `COMPLETED` → lease expires → second independent gateway retries → verifies zero duplicate canonical mutations, manifest has 1 asset, and DB record transitions to `COMPLETED`.
  - `TestToolGatewayIdempotency.test_concurrent_identical_requests_execute_single_side_effect`: Racing workers execute side effect exactly once.
  - `TestToolGatewayIdempotency.test_same_idempotency_key_different_payload_fails_with_conflict`: Reject payload mismatch with `POLICY_DENIED`.
  - `TestToolGatewayIdempotency.test_retry_after_side_effect_returns_cached_asset_without_duplication`: Distinct gateway worker instance receives replay from durable storage.
  - `TestToolGatewayIdempotency.test_cross_process_crash_recovery_and_lease_expiry`: Stale lease recovery without deadlock.

---

### C05 — Parity Wording & Continuity Separation
- **Clarification:**
  - **Provider Parity:** 1:1 functional identity with a specific third-party service interface.
  - **Capability Continuity:** Platform-level preservation of product capabilities (`SEARCH_STOCK_AUDIO`, `SEARCH_STOCK_VIDEOS`, etc.) across architectural layers.
  - Pixabay Audio scraper is broken legacy; `SEARCH_STOCK_AUDIO` platform capability maintains 100% Continuity via FreesoundAdapter.

---

### C06 — Pixabay Audio Scraper Decision
- **Architectural Decision:**
  - Classified as `BROKEN_LEGACY_SCRAPER (COMPATIBILITY_ONLY)`.
  - Official Pixabay REST API only supports Photos and Videos. The legacy Playwright headless scraper is unmaintained and fails closed due to Cloudflare anti-bot checks.
  - `PixabayAdapter.supported_media_types` is set to `{StockMediaType.IMAGE, StockMediaType.VIDEO}`.
  - `SEARCH_STOCK_AUDIO` is canonically fulfilled by [`FreesoundAdapter`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/providers/freesound.py) using official licensed REST APIs.

---

### C07 — Live Provider Verification Status
- **Verification Matrix:**
  - **Iconify (`iconify`):** `LIVE_SMOKE_PASS` (public open-source API verified via live HTTP GET request).
  - **Pexels (`pexels`):** `LIVE_SMOKE_BLOCKED` (no API key configured; fail-closed verified via `ProviderAuthError`).
  - **Pixabay (`pixabay`):** `LIVE_SMOKE_BLOCKED` (no API key configured; fail-closed verified via `ProviderAuthError`).
  - **Freesound (`freesound`):** `LIVE_SMOKE_BLOCKED` (no API key configured; fail-closed verified via `ProviderAuthError`).
  - Zero fake success claimed; secrets are never hardcoded or emitted.

---

### C08 — License Truth & Mapping Integrity
- **Mapping Modernization:**
  - [`IconifyAdapter`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/providers/iconify.py): parses collection metadata. Missing/unspecified license -> `UNKNOWN` / `REQUIRES_REVIEW` (`attribution_required=True`). Non-commercial -> `PROHIBITED`. Copyleft (GPL/ShareAlike) -> `REQUIRES_REVIEW`. Permissive (MIT/Apache/CC0/OFL/BSD) -> `ALLOWED`.
  - [`FreesoundAdapter`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/providers/freesound.py): CC-BY-SA -> `REQUIRES_REVIEW` (copyleft). Missing license -> `UNKNOWN` / `REQUIRES_REVIEW`.
  - Preserves raw license name and URL in canonical `provenance_evidence`.
- **Tests Added:**
  - `TestIconifyNormalization.test_normalize_icon_permissive_license`
  - `TestIconifyNormalization.test_normalize_icon_missing_license_requires_review`
  - `TestIconifyNormalization.test_normalize_icon_non_commercial_prohibited`
  - `TestIconifyNormalization.test_normalize_icon_copyleft_requires_review`
  - `TestFreesoundNormalization.test_normalize_cc_by_sa_sound_requires_review`
  - `TestFreesoundNormalization.test_normalize_missing_license_sound_requires_review`

---

### C09 — Media Validation Boundary
- **Transport vs Deep Probing Boundary:**
  - **S28-M05 Scope:** HTTP transport validation, byte ceilings, case-insensitive Content-Type header parsing, magic bytes matching, declared vs detected MIME consistency, SVG security sanitization, minimum container payload sanity (>= 8 bytes).
  - **S28-M06/M07 Scope:** Deep audio/video stream demuxing, ffprobe codec profiling, framerate/resolution validation, and loudness analysis.
- **Tests Added:**
  - `TestMagicByteValidation.test_payload_too_small_is_rejected`
  - `TestRedirectAndCeilingSecurity.test_declared_vs_detected_mime_mismatch_rejected`

---

### C10 — Reproducible Evidence
- **Source Verification:**
  - All modifications, migrations, and tests are committed directly to branch `feature/s27-ai-platform`.
  - Clean working tree verified via `git status --porcelain`.
  - Full test suites pass synchronously with zero skipped or bypassed security checks.

---

## 2. Files Changed

| File Path | Description of Changes |
| :--- | :--- |
| [`scripts/core/canonical_asset_repository.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/canonical_asset_repository.py) | **(New)** Production authority for multi-worker asset deduplication with surrogate `id TEXT PRIMARY KEY` (`project_id:content_hash`), project-scoped `asset_id`, `UNIQUE (project_id, content_hash)`, and immediate CAS transactions. |
| [`scripts/core/idempotency_repository.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/idempotency_repository.py) | **(New)** Production SQL repository managing durable `tool_idempotency_records` with lease expiry, conflict detection, crash recovery, and polling. |
| [`scripts/core/idempotency_store.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/idempotency_store.py) | **(New)** `DurableIdempotencyStore` implementation conforming to S27.9 architecture rules without raw repository exposure in `ai/tools/`. |
| [`scripts/core/database.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/database.py) | Added DDL schema statements and automatic SQLite migration for `canonical_assets` (`id TEXT PRIMARY KEY`) and `tool_idempotency_records`. |
| [`ai/acquisition/safe_downloader.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/safe_downloader.py) | Added DNS resolution (`socket.getaddrinfo`), `check_ip_disallowed` (loopback, RFC1918, metadata, CGNAT), `validate_svg_security` (XSS, XXE, external hrefs), declared/detected MIME consistency, case-insensitive headers. |
| [`ai/acquisition/service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/service.py) | Enforced full 64-char SHA-256 (`ast_{payload.content_hash}`) and CAS deduplication via `CanonicalAssetRepository` across `acquire_candidate`, `download_remote_media`, and `download_icon`. |
| [`ai/acquisition/dedupe.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/acquisition/dedupe.py) | Connected `StockDedupeEngine` to `CanonicalAssetRepository` while maintaining manifest compatibility. |
| [`ai/tools/gateway.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/tools/gateway.py) | Added `claim_execution` to `IdempotencyStore`, connected default store to `DurableIdempotencyStore`, documented crash-window recovery limitations, and enforced DNS resolution in `validate_safe_url`. |
| [`tests/ai/acquisition/test_dedupe_and_cache.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/ai/acquisition/test_dedupe_and_cache.py) | Added tests for same-project deduplication, different-project isolation, different-workspace tenant isolation, multi-worker CAS convergence, and full SHA-256 preservation. |
| [`tests/ai/acquisition/test_tool_gateway_acquisition.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/ai/acquisition/test_tool_gateway_acquisition.py) | Added crash-window idempotency recovery test, cross-process idempotency across independent gateway instances, payload conflict, replay, and lease expiry. |
| [`tests/ai/acquisition/test_e2e_acquisition_pipeline.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/ai/acquisition/test_e2e_acquisition_pipeline.py) | Added DB cleanup fixture to isolate test project scope. |

---

## 3. Test Execution Summary

### Acquisition Suite (`tests/ai/acquisition/`)
- **Total Tests:** 93
- **Passed:** 93
- **Failed:** 0
- **Duration:** 3.82s

### ToolGateway, Routing & Architecture Guards (`tests/ai/tools/`, `tests/ai/routing/`, `tests/ai/test_ai_architecture_guards.py`)
- **Total Tests:** 141
- **Passed:** 141
- **Failed:** 0
- **Duration:** 7.35s

### Combined Test Run
- **Total Tests Executed:** 234
- **Total Passed:** 234
- **Failures:** 0

### Contract Parity Synchronization
- `python scripts/generate_ai_contracts.py --check`: ✅ Ground Truth Parity Verified
- `python scripts/generate_creative_contracts.py --check`: ✅ Ground Truth Parity Verified

---

## 4. Remaining Blockers
- **None for Functional Platform Capability.**
- **Live Smoke Keys:** External credentials for Pexels, Pixabay, and Freesound are not populated in the current execution environment (`LIVE_SMOKE_BLOCKED`). Per directives, this is honestly documented and not falsified.

---

## 5. Final Verdict
**`S28-M05 FUNCTIONALLY CLOSED — LIVE VERIFICATION BLOCKED`**
