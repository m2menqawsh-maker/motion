# S28-M03 — Capability Runtime Execution Matrix

This document provides the authoritative runtime resolution matrix for all **32 canonical capabilities** recognized by `CapabilityRouter` and executed via `ToolGateway` / `ModelRouterSeam`.

---

## 1. Summary Breakdown

| Category | Capability Count | Primary Runtime Router | Primary Adapters |
|---|---|---|---|
| **MODEL** | 1 | `CapabilityRouter` -> `ModelRouter` / `ModelRouterSeam` | `LocalSTTProvider` (`faster-whisper-base`, `faster-whisper-tiny`) |
| **TOOL** | 24 | `CapabilityRouter` -> `ToolGateway` | `AssetAcquisitionAdapter`, `MCPToolAdapter`, `RemoteAPIAdapter`, `WorkerToolAdapter` |
| **DOMAIN_SERVICE** | 7 | `CapabilityRouter` -> `ToolGateway` | `DomainServiceAdapter` (`AssetService`, `RunService`) |
| **TOTAL** | **32** | — | — |

---

## 2. Master Capability Runtime Matrix

| # | Capability ID | Category | Family | Input Contract | Output Contract | Side Effects | Tenant Scope | Mode | Adapter Resolved | Target Authority | Runtime Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `SPEECH_TO_TEXT` | `MODEL` | `SPEECH_INTELLIGENCE` | `SpeechToTextInput` | `SpeechIntelligence` | `LOCAL_TEMP_WRITE` | `PROJECT` | `MODEL` | `ModelRouterSeam` / `ModelRouter` | `LocalSTTProvider` (faster-whisper / Silero VAD) [Legacy `audio-tools-mcp::analyze_voiceover` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 2 | `SEGMENT_SPEECH_AUDIO` | `TOOL` | `SPEECH_INTELLIGENCE` | `SegmentSpeechInput` | `SegmentSpeechOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `SpeechPreparationService` / `MediaProcessingAdapter` | `SpeechPreparationService` [Legacy `audio-tools-mcp::split_voiceover_sentences` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 3 | `GENERATE_SPEECH_MANIFEST` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `SpeechManifestInput` | `SpeechManifestOutput` | `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `SpeechManifestBuilder` [Legacy `audio-tools-mcp::get_voiceover_manifest` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 4 | `BUILD_SPEECH_TIMELINE` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `SpeechTimelineInput` | `SpeechTimelineOutput` | `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `SpeechTimelineBuilder` [Legacy `audio-tools-mcp::build_voiceover_timeline` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 5 | `TRIM_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `TrimAudioInput` | `TrimAudioOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.trim_audio` [Legacy `audio-tools-mcp::trim_audio` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 6 | `EXTEND_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `ExtendAudioInput` | `ExtendAudioOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.extend_audio` [Legacy `audio-tools-mcp::extend_audio` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 7 | `NORMALIZE_AUDIO_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `NormalizeLoudnessInput` | `NormalizeLoudnessOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.normalize_media` [Legacy `audio-tools-mcp::normalize_loudness` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 8 | `TRIM_AUDIO_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `TrimSilenceInput` | `TrimSilenceOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.trim_silence` [Legacy `audio-tools-mcp::detect_and_trim_silence` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 9 | `TRIM_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `TrimVideoInput` | `TrimVideoOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MCPToolAdapter` | `video-tools-mcp::trim_video` | `ACTIVE_COMPATIBILITY` |
| 10 | `EXTEND_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `ExtendVideoInput` | `ExtendVideoOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MCPToolAdapter` | `video-tools-mcp::extend_video_loop` | `ACTIVE_COMPATIBILITY` |
| 11 | `RESIZE_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `ResizeVideoInput` | `ResizeVideoOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MCPToolAdapter` | `video-tools-mcp::resize_video` | `ACTIVE_COMPATIBILITY` |
| 12 | `TRIM_BLACK_FRAMES` | `TOOL` | `VIDEO_PROCESSING` | `DetectBlackFramesInput` | `DetectBlackFramesOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MCPToolAdapter` | `video-tools-mcp::detect_and_trim_black_frames` | `PARTIALLY_WORKING` |
| 13 | `CHANGE_VIDEO_SPEED` | `TOOL` | `VIDEO_PROCESSING` | `ChangeVideoSpeedInput` | `ChangeVideoSpeedOutput` | `PERSISTENT_WRITE`, `SUBPROCESS`, `BACKGROUND_JOB` | `PROJECT` | `WORKER` | `MCPToolAdapter` | `video-tools-mcp::change_video_speed` | `ACTIVE_COMPATIBILITY` |
| 14 | `ENFORCE_KEYFRAME_INTERVAL` | `TOOL` | `VIDEO_PROCESSING` | `EnforceKeyframesInput` | `EnforceKeyframesOutput` | `PERSISTENT_WRITE`, `SUBPROCESS`, `BACKGROUND_JOB` | `PROJECT` | `WORKER` | `MCPToolAdapter` | `video-tools-mcp::enforce_keyframe_interval` | `ACTIVE_COMPATIBILITY` |
| 15 | `CONCATENATE_VIDEOS` | `TOOL` | `VIDEO_PROCESSING` | `ConcatenateVideosInput` | `ConcatenateVideosOutput` | `PERSISTENT_WRITE`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.concat_media` [Legacy `ffmpeg-mcp-server::concatenate_videos` is `COMPATIBILITY_BLOCKED`] | `ACTIVE_CANONICAL` |
| 16 | `RESIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `ResizeImageRequest` / `UpscaleImageInput` | `ResizeImageResult` / `UpscaleImageOutput` | `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.resize_image` [Legacy `image-tools-mcp::upscale_image` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 17 | `CROP_IMAGE_TO_RATIO` | `TOOL` | `IMAGE_PROCESSING` | `CropImageRatioRequest` / `CropRatioInput` | `CropImageRatioResult` / `CropRatioOutput` | `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.crop_to_ratio` [Legacy `image-tools-mcp::crop_image_ratio` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 18 | `AUTO_CROP_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `AutoCropImageRequest` / `AutoCropInput` | `AutoCropImageResult` / `AutoCropOutput` | `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.auto_crop` [Legacy `image-tools-mcp::auto_crop_smart` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 19 | `DOWNLOAD_REMOTE_MEDIA` | `TOOL` | `MEDIA_ACQUISITION` | `DownloadRemoteMediaInput` | `DownloadRemoteMediaOutput` | `EXTERNAL_NETWORK`, `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.acquire_from_descriptor` [Legacy `media-sources-mcp::download_media` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 20 | `EXTRACT_MEDIA_PAGE` | `TOOL` | `MEDIA_ACQUISITION` | `ExtractMediaPageInput` | `ExtractMediaPageOutput` | `EXTERNAL_NETWORK`, `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.extract_media_page` [Legacy `media-sources-mcp::extract_media_from_page` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 21 | `SEARCH_ICONS` | `TOOL` | `MEDIA_ACQUISITION` | `SearchIconsInput` | `SearchIconsOutput` | `EXTERNAL_NETWORK` | `WORKSPACE` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.search_icons` [Iconify REST / Legacy `media-sources-mcp::iconify_search_icons` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 22 | `DOWNLOAD_ICON` | `TOOL` | `MEDIA_ACQUISITION` | `DownloadIconInput` | `DownloadIconOutput` | `EXTERNAL_NETWORK`, `PERSISTENT_WRITE` | `PROJECT` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.download_icon` [Iconify REST / Legacy `media-sources-mcp::iconify_download_icon` is `COMPATIBILITY_ONLY`] | `ACTIVE_CANONICAL` |
| 23 | `SEARCH_STOCK_IMAGES` | `TOOL` | `MEDIA_ACQUISITION` | `SearchStockImagesInput` | `SearchStockImagesOutput` | `EXTERNAL_NETWORK` | `WORKSPACE` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.search_stock_images` (Pexels / Pixabay) | `ACTIVE_CANONICAL` |
| 24 | `SEARCH_STOCK_VIDEOS` | `TOOL` | `MEDIA_ACQUISITION` | `SearchStockVideosInput` | `SearchStockVideosOutput` | `EXTERNAL_NETWORK` | `WORKSPACE` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.search_stock_videos` (Pexels / Pixabay) | `ACTIVE_CANONICAL` |
| 25 | `SEARCH_STOCK_AUDIO` | `TOOL` | `MEDIA_ACQUISITION` | `SearchStockAudioInput` | `SearchStockAudioOutput` | `EXTERNAL_NETWORK` | `WORKSPACE` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.search_stock_audio` (Freesound / Pixabay) | `ACTIVE_CANONICAL` |
| 26 | `SEARCH_SOUND_EFFECTS` | `TOOL` | `MEDIA_ACQUISITION` | `SearchSoundEffectsInput` | `SearchSoundEffectsOutput` | `EXTERNAL_NETWORK` | `WORKSPACE` | `EXTERNAL_API` | `AssetAcquisitionAdapter` | `AssetAcquisitionService.search_sound_effects` (Freesound SFX) | `ACTIVE_CANONICAL` |
| 27 | `INSPECT_MEDIA` | `TOOL` | `MEDIA_INSPECTION` | `InspectMediaInput` | `InspectMediaOutput` | `READ_ONLY`, `SUBPROCESS` | `PROJECT` | `LOCAL` | `MCPToolAdapter` | `video-tools-mcp::inspect_media` | `ACTIVE_COMPATIBILITY` |
| 28 | `MUTATE_ASSET_STATUS` | `DOMAIN_SERVICE` | `ASSET_DOMAIN_OPERATIONS` | `MutateAssetStatusInput` | `MutateAssetStatusOutput` | `DOMAIN_MUTATION` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `AssetService.update_asset_status` | `ACTIVE_CANONICAL` |
| 29 | `CHECK_MEDIA_CACHE` | `DOMAIN_SERVICE` | `CACHE_MANAGEMENT` | `CheckCacheInput` | `CheckCacheOutput` | `READ_ONLY` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `AssetService.check_asset_cache` | `ACTIVE_CANONICAL` |
| 30 | `STORE_MEDIA_CACHE` | `DOMAIN_SERVICE` | `CACHE_MANAGEMENT` | `StoreCacheInput` | `StoreCacheOutput` | `DOMAIN_MUTATION`, `PERSISTENT_WRITE` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `AssetService.save_asset_to_cache` | `ACTIVE_CANONICAL` |
| 31 | `GET_JOB_STATUS` | `DOMAIN_SERVICE` | `JOB_MANAGEMENT` | `GetJobStatusInput` | `GetJobStatusOutput` | `READ_ONLY` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `RunService.get_run` | `ACTIVE_CANONICAL` |
| 32 | `CANCEL_PROCESSING_JOB` | `DOMAIN_SERVICE` | `JOB_MANAGEMENT` | `CancelJobInput` | `CancelJobOutput` | `DOMAIN_MUTATION` | `PROJECT` | `LOCAL` | `DomainServiceAdapter` | `RunService.cancel_run` | `ACTIVE_CANONICAL` |

---

## 2.1 S28-M06 Canonical Unified Media Processing Suite

In addition to legacy compatibility dispatch, S28-M06 establishes the canonical, typed media processing capabilities executed natively via `MediaProcessingAdapter` -> `MediaProcessingService` + `FFmpegAdapter` inside isolated worker staging with guaranteed cleanup and deep output validation:

| Capability ID | Category | Family | Input Contract | Output Contract | Execution Mode | Adapter Resolved | Target Implementation | Status |
|---|---|---|---|---|---|---|---|---|
| `PROBE_MEDIA` | `TOOL` | `MEDIA_INSPECTION` | `ProbeMediaInput` | `ProbeMediaOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.probe_media` | `ACTIVE_CANONICAL` |
| `TRANSCODE_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `TranscodeVideoInput` | `TranscodeVideoOutput` | `LOCAL` / `WORKER` | `MediaProcessingAdapter` | `MediaProcessingService.transcode_video` | `ACTIVE_CANONICAL` |
| `EXTRACT_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `ExtractAudioInput` | `ExtractAudioOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.extract_audio` | `ACTIVE_CANONICAL` |
| `EXTRACT_FRAMES` | `TOOL` | `VIDEO_PROCESSING` | `ExtractFramesInput` | `ExtractFramesOutput` | `LOCAL` / `WORKER` | `MediaProcessingAdapter` | `MediaProcessingService.extract_frames` | `ACTIVE_CANONICAL` |
| `CONCAT_MEDIA` | `TOOL` | `VIDEO_PROCESSING` | `ConcatMediaInput` | `ConcatMediaOutput` | `LOCAL` / `WORKER` | `MediaProcessingAdapter` | `MediaProcessingService.concat_media` | `ACTIVE_CANONICAL` |
| `CHANGE_CONTAINER` | `TOOL` | `VIDEO_PROCESSING` | `ChangeContainerInput` | `ChangeContainerOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.change_container` | `ACTIVE_CANONICAL` |
| `NORMALIZE_MEDIA` | `TOOL` | `AUDIO_PROCESSING` | `NormalizeMediaInput` | `NormalizeMediaOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.normalize_media` | `ACTIVE_CANONICAL` |

---

## 2.2 S28-M07 Canonical Modernized Audio & Speech Suite

S28-M07 decomposes `audio-tools-mcp` into strictly owned, typed canonical capabilities with zero duplicate authority:
- Generic media transformations / FFmpeg operations route to `MediaProcessingAdapter` -> `MediaProcessingService`
- Deterministic text/word splitting routes to `SpeechPreparationService`
- Manifest construction routes to `DomainServiceAdapter` -> `SpeechManifestBuilder`
- Timeline construction routes to `DomainServiceAdapter` -> `SpeechTimelineBuilder`

| Capability ID | Category | Family | Input Contract | Output Contract | Execution Mode | Adapter Resolved | Target Implementation | Status |
|---|---|---|---|---|---|---|---|---|
| `NORMALIZE_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `NormalizeAudioInput` | `NormalizeAudioOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.normalize_media` | `ACTIVE_CANONICAL` |
| `ANALYZE_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `AnalyzeLoudnessInput` | `AnalyzeLoudnessOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.analyze_loudness` | `ACTIVE_CANONICAL` |
| `DETECT_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `DetectSilenceInput` | `DetectSilenceOutput` | `LOCAL` | `MediaProcessingAdapter` | `MediaProcessingService.detect_silence` | `ACTIVE_CANONICAL` |
| `SPLIT_SPEECH_TEXT` | `TOOL` | `SPEECH_INTELLIGENCE` | `SplitSpeechTextInput` | `SplitSpeechTextOutput` | `LOCAL` | `SpeechPreparationService` | `SpeechPreparationService.split_speech_text` | `ACTIVE_CANONICAL` |
| `PREPARE_VO_SEGMENTS` | `TOOL` | `SPEECH_INTELLIGENCE` | `PrepareVoSegmentsInput` | `PrepareVoSegmentsOutput` | `LOCAL` | `SpeechPreparationService` | `SpeechPreparationService.prepare_vo_segments` | `ACTIVE_CANONICAL` |
| `ALIGN_AUDIO_METADATA` | `TOOL` | `SPEECH_INTELLIGENCE` | `AlignAudioMetadataInput` | `AlignAudioMetadataOutput` | `LOCAL` | `SpeechPreparationService` | `SpeechPreparationService.align_audio_metadata` | `ACTIVE_CANONICAL` |

---

## 2.3 S28-M08 Canonical Modernized Image Processing Suite

S28-M08 establishes the canonical, typed image processing subsystem executed natively via `ImageProcessingAdapter` -> `ImageProcessingService` + `PillowImageAdapter` with in-memory execution, strict bounds (1..8192px, 32MP, 50MB), decompression bomb defense, content-addressed caching, and canonical `StorageService` / `AssetService` ownership:

| Capability ID | Category | Family | Input Contract | Output Contract | Execution Mode | Adapter Resolved | Target Implementation | Status |
|---|---|---|---|---|---|---|---|---|
| `RESIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `ResizeImageRequest` | `ResizeImageResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.resize_image` | `ACTIVE_CANONICAL` |
| `CROP_IMAGE_TO_RATIO` | `TOOL` | `IMAGE_PROCESSING` | `CropImageRatioRequest` | `CropImageRatioResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.crop_to_ratio` | `ACTIVE_CANONICAL` |
| `AUTO_CROP_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `AutoCropImageRequest` | `AutoCropImageResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.auto_crop` | `ACTIVE_CANONICAL` |
| `PROBE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `ProbeImageRequest` | `ProbeImageResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.probe_image` | `ACTIVE_CANONICAL` |
| `CONVERT_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `ConvertImageRequest` | `ConvertImageResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.convert_image` | `ACTIVE_CANONICAL` |
| `OPTIMIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `OptimizeImageRequest` | `OptimizeImageResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.optimize_image` | `ACTIVE_CANONICAL` |
| `PREPARE_IMAGE_ASSET` | `TOOL` | `IMAGE_PROCESSING` | `PrepareImageAssetRequest` | `PrepareImageAssetResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.prepare_image_asset` | `ACTIVE_CANONICAL` |
| `THUMBNAIL` | `TOOL` | `IMAGE_PROCESSING` | `ThumbnailRequest` | `ThumbnailResult` | `LOCAL` | `ImageProcessingAdapter` | `ImageProcessingService.create_thumbnail` | `ACTIVE_CANONICAL` |

---

## 3. Status Definitions

- **`ACTIVE_CANONICAL`**: Fully governed and executed by authoritative domain services (`AssetService`, `RunService`, etc.). Zero MCP involvement.
- **`ACTIVE_COMPATIBILITY`**: Executed via `MCPToolAdapter` using bounded subprocess argument vectors with full 15-stage gateway protection.
- **`SEAM_DEFERRED_M04`**: Integration seam established in `CapabilityRouter`. Full local provider lifecycle and `faster-whisper` extraction scheduled for S28-M04.
- **`SECURITY_BLOCKED_M06`**: Verified shell injection vulnerability in legacy tool (`ffmpeg-mcp-server::concatenate_videos`). Blocked by gateway until safe native rewrite in S28-M06.
- **`PARTIALLY_WORKING`**: Documented known issue in black frame detection filter. Executes with telemetry warning.
- **`UNVERIFIED_STOCK`**: Stock provider searches require valid external API keys. Fails closed safely if credentials absent. Rebuilt in S28-M05.
- **`BROKEN_UNVERIFIED_M05`**: Legacy HTML scraper broken. Rebuilt under official provider contracts in S28-M05.
