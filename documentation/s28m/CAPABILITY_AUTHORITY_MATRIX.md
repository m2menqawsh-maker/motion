# S28-M02 / S28-M02.1 — Capability Authority & Boundary Matrix

> **Milestone:** S28-M02 / S28-M02.1 — Capability Taxonomy & Contracts Hardening  
> **Purpose:** Structural audit matrix preventing MCP utilities from masquerading as domain authorities, and enforcing explicit boundaries between semantic ownership, execution mechanisms, tenant isolation, and canonical storage authorities.

---

## 1. Executive Matrix: All 32 Canonical Capabilities

| # | Capability Identifier | Category | Semantic Owner | Current Implementation (Legacy MCP) | Future Architectural Owner | Multi-Side Effects | Tenant Scope | Canonical Target Storage Boundary | Target Phase |
|---|---|---|---|---|---|---|---|---|---|
| **1** | `SPEECH_TO_TEXT` | **`MODEL`** | Model Subsystem | `audio-tools-mcp::analyze_voiceover` | `ModelRouter` | `LOCAL_TEMP_WRITE` | `PROJECT` | `ArtifactService / Transient Analysis Cache` | **S28-M04** |
| **2** | `SEGMENT_SPEECH_AUDIO` | **`TOOL`** | Media Processing | `audio-tools-mcp::split_voiceover_sentences` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Audio Slices` | **S28-M03 / S28-M07** |
| **3** | `GENERATE_SPEECH_MANIFEST` | **`DOMAIN_SERVICE`** | Artifact Service (Domain Authority) | `audio-tools-mcp::get_voiceover_manifest` | `DomainArtifactService` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | `PROJECT` | `ArtifactService / Speech Manifest` | **S28-M03 / S28-M07** |
| **4** | `BUILD_SPEECH_TIMELINE` | **`DOMAIN_SERVICE`** | Artifact Service (Domain Authority) | `audio-tools-mcp::build_voiceover_timeline` | `DomainArtifactService` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | `PROJECT` | `ArtifactService / Speech Timeline` | **S28-M03 / S28-M07** |
| **5** | `TRIM_AUDIO` | **`TOOL`** | Media Processing | `audio-tools-mcp::trim_audio` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Audio` | **S28-M03 / S28-M07** |
| **6** | `EXTEND_AUDIO` | **`TOOL`** | Media Processing | `audio-tools-mcp::extend_audio` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Audio` | **S28-M03 / S28-M07** |
| **7** | `NORMALIZE_AUDIO_LOUDNESS` | **`TOOL`** | Media Processing | `audio-tools-mcp::normalize_loudness` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Audio` | **S28-M03 / S28-M07** |
| **8** | `TRIM_AUDIO_SILENCE` | **`TOOL`** | Media Processing | `audio-tools-mcp::detect_and_trim_silence` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Audio` | **S28-M03 / S28-M07** |
| **9** | `CHECK_MEDIA_CACHE` | **`DOMAIN_SERVICE`** | Cache / Asset Authority | `common-tools-mcp::check_cache` | `AssetService` | `READ_ONLY` | `PROJECT` | `AssetService / Managed Cache Hierarchy` | **S28-M03** |
| **10** | `STORE_MEDIA_CACHE` | **`DOMAIN_SERVICE`** | Cache / Asset Authority | `common-tools-mcp::save_to_cache` | `AssetService` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | `PROJECT` | `AssetService / Managed Cache Hierarchy` | **S28-M03** |
| **11** | `CHANGE_VIDEO_SPEED` | **`TOOL`** | Media Processing | `ffmpeg-mcp-server::speed_up_video` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS`, `BACKGROUND_JOB` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **12** | `GET_JOB_STATUS` | **`DOMAIN_SERVICE`** | Job Execution Authority | `ffmpeg-mcp-server::check_processing_status` | `RunService` | `READ_ONLY` | `PROJECT` | `RunService / Durable Job Record` | **S28-M03** |
| **13** | `CANCEL_PROCESSING_JOB` | **`DOMAIN_SERVICE`** | Job Execution Authority | `ffmpeg-mcp-server::cancel_video_processing` | `RunService` | `DOMAIN_MUTATION`, `SUBPROCESS` | `PROJECT` | `RunService / Durable Job Record` | **S28-M03** |
| **14** | `ENFORCE_KEYFRAME_INTERVAL` | **`TOOL`** | Media Processing | `ffmpeg-mcp-server::increase_keyframes` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **15** | `INSPECT_MEDIA` | **`TOOL`** | Media Processing | `ffmpeg-mcp-server::get_files_info` | `MediaProcessingService` | `READ_ONLY`, `SUBPROCESS` | `PROJECT` | `StorageService / Read-Only Probe` | **S28-M03 / S28-M06** |
| **16** | `CONCATENATE_VIDEOS` | **`TOOL`** | Media Processing | `ffmpeg-mcp-server::concatenate_videos` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **17** | `RESIZE_IMAGE` | **`TOOL`** | Media Processing | `image-tools-mcp::upscale_image` | `MediaProcessingService` | `PERSISTENT_WRITE` | `PROJECT` | `StorageService / Project Images` | **S28-M03 / S28-M08** |
| **18** | `CROP_IMAGE_TO_RATIO` | **`TOOL`** | Media Processing | `image-tools-mcp::crop_to_ratio` | `MediaProcessingService` | `PERSISTENT_WRITE` | `PROJECT` | `StorageService / Project Images` | **S28-M03 / S28-M08** |
| **19** | `AUTO_CROP_IMAGE` | **`TOOL`** | Media Processing | `image-tools-mcp::auto_crop_content` | `MediaProcessingService` | `PERSISTENT_WRITE` | `PROJECT` | `StorageService / Project Images` | **S28-M03 / S28-M08** |
| **20** | `DOWNLOAD_REMOTE_MEDIA` | **`TOOL`** | Media Acquisition | `media-sources-mcp::download_direct_file` | `MediaAcquisitionService` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | `PROJECT` | `StorageService / Ingestion Hierarchy` | **S28-M03 / S28-M05** |
| **21** | `EXTRACT_MEDIA_PAGE` | **`TOOL`** | Media Acquisition | `media-sources-mcp::download_media_page` | `MediaAcquisitionService` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | `PROJECT` | `StorageService / Ingestion Hierarchy` | **S28-M03 / S28-M05** |
| **22** | `MUTATE_ASSET_STATUS` | **`DOMAIN_SERVICE`** | Asset Domain Authority | `media-sources-mcp::change_asset_status` | `AssetService` | `DOMAIN_MUTATION`, `PERSISTENT_WRITE` | `PROJECT` | `AssetService / ManifestV2 Authority` | **S28-M03** |
| **23** | `SEARCH_ICONS` | **`TOOL`** | Stock Media Search | `media-sources-mcp::iconify_search` | `StockMediaService` | `EXTERNAL_NETWORK`, `READ_ONLY` | `WORKSPACE` | `Stateless In-Memory API` | **S28-M03 / S28-M05** |
| **24** | `DOWNLOAD_ICON` | **`TOOL`** | Stock Media Search | `media-sources-mcp::download_iconify_icon` | `StockMediaService` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | `PROJECT` | `StorageService / Project Icons` | **S28-M03 / S28-M05** |
| **25** | `SEARCH_STOCK_IMAGES` | **`TOOL`** | Stock Media Search | `media-sources-mcp::pixabay_search_images` & `pexels_search_images` | `StockMediaService` | `EXTERNAL_NETWORK`, `READ_ONLY` | `WORKSPACE` | `Stateless In-Memory API` | **S28-M03 / S28-M05** |
| **26** | `SEARCH_STOCK_VIDEOS` | **`TOOL`** | Stock Media Search | `media-sources-mcp::pixabay_search_videos` & `pexels_search_videos` | `StockMediaService` | `EXTERNAL_NETWORK`, `READ_ONLY` | `WORKSPACE` | `Stateless In-Memory API` | **S28-M03 / S28-M05** |
| **27** | `SEARCH_STOCK_AUDIO` | **`TOOL`** | Stock Media Search | `media-sources-mcp::pixabay_search_audio` | `StockMediaService` | `EXTERNAL_NETWORK`, `READ_ONLY` | `WORKSPACE` | `Stateless In-Memory API` | **S28-M03 / S28-M05** |
| **28** | `SEARCH_SOUND_EFFECTS` | **`TOOL`** | Stock Media Search | `media-sources-mcp::freesound_search` | `StockMediaService` | `EXTERNAL_NETWORK`, `READ_ONLY` | `WORKSPACE` | `Stateless In-Memory API` | **S28-M03 / S28-M05** |
| **29** | `TRIM_VIDEO` | **`TOOL`** | Media Processing | `video-tools-mcp::trim_video` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **30** | `EXTEND_VIDEO` | **`TOOL`** | Media Processing | `video-tools-mcp::extend_video` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **31** | `RESIZE_VIDEO` | **`TOOL`** | Media Processing | `video-tools-mcp::resize_video` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |
| **32** | `TRIM_BLACK_FRAMES` | **`TOOL`** | Media Processing | `video-tools-mcp::detect_and_trim_black_frames` | `MediaProcessingService` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `StorageService / Project Video` | **S28-M03 / S28-M06** |

---

## 2. Critical Boundary Normalization (S28-M02.1)

### 2.1 Decoupling Target Architectural Authority from Legacy Filesystem Behavior
- **Hardening Principle:** In S28-M02.1, canonical capability definitions point strictly to target architectural authorities (`StorageService`, `AssetService`, `ArtifactService`, `RunService`, `Stateless In-Memory API`).
- **Legacy Implementation Isolation:** Raw filesystem details (e.g. `reads/writes raw unconfined path via FFmpeg streamcopy`, `creates ad-hoc .{stem}.analysis.json`, `writes concat list in cwd`) are strictly encapsulated in `ImplementationDescriptor.legacy_storage_behavior`.
- **Zero Raw Paths in Contracts:** Canonical request and response contracts reference media assets exclusively via `project_id` and abstract `storage_key`. Host absolute paths are completely forbidden.

### 2.2 TenantScope Normalization
- **Rule:** `TenantScope` represents the authorization and resource isolation boundary required to execute the capability, not whether the upstream data provider is public or private.
- **Project Scope (27 Capabilities):** All operations acting on Project Assets (trimming, extending, resizing, transcoding, loudness normalization, speech analysis, caching, status mutation, background jobs) are strictly scoped to `TenantScope.PROJECT`.
- **Workspace Scope (5 Capabilities):** External search operations (`SEARCH_ICONS`, `SEARCH_STOCK_IMAGES`, `SEARCH_STOCK_VIDEOS`, `SEARCH_STOCK_AUDIO`, `SEARCH_SOUND_EFFECTS`) are scoped to `TenantScope.WORKSPACE` where API keys, tenant rate-limits, and user authorization contexts are enforced.
- **Invariant Enforcement:** Any capability that performs persistent writes or domain mutations is strictly forbidden from declaring `TenantScope.NONE`.

---

## 3. Summary of Category Distribution

| Category | Count | Percentage | Architectural Significance |
|---|---|---|---|
| **`MODEL`** | **1** | 3.1% | Local neural inference (`faster-whisper`), destined for `ModelRouter`. |
| **`TOOL`** | **24** | 75.0% | Deterministic media processing primitives and external stock queries. |
| **`DOMAIN_SERVICE`** | **7** | 21.9% | Authoritative state operations (asset status, cache, job lifecycle, manifests). |
| **Total** | **32** | 100.0% | Complete coverage of all 34 legacy MCP tools without capability loss. |
