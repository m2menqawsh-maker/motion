# S28-M01 — Authoritative MCP Tool Matrix

> **Milestone:** S28-M01 — MCP Reality Audit & Baseline  
> **Status:** AUDITED & RUNTIME VERIFIED  
> **Total Tools Discovered:** 34  
> **Classification Breakdown:** 18 WORKING | 10 PARTIALLY_WORKING | 1 BROKEN | 5 UNVERIFIED  
> **Authority Principle:** Verified runtime behavior wins over static documentation.

---

## 1. Summary Matrix by Server

| MCP Server | Language / Runtime | Tool Count | WORKING | PARTIALLY_WORKING | BROKEN | UNVERIFIED |
|---|---|---|---|---|---|---|
| [`audio-tools-mcp`](#1-audio-tools-mcp-8-tools) | Python 3.12 (uv) | 8 | 8 | 0 | 0 | 0 |
| [`common-tools-mcp`](#2-common-tools-mcp-2-tools) | Python 3.12 (uv) | 2 | 1 | 1 | 0 | 0 |
| [`ffmpeg-mcp-server`](#3-ffmpeg-mcp-server-6-tools) | Node.js v26.7 | 6 | 1 | 5 | 0 | 0 |
| [`image-tools-mcp`](#4-image-tools-mcp-3-tools) | Python 3.12 (uv) | 3 | 3 | 0 | 0 | 0 |
| [`media-sources-mcp`](#5-media-sources-mcp-11-tools) | Python 3.12 (uv) | 11 | 2 | 3 | 1 | 5 |
| [`video-tools-mcp`](#6-video-tools-mcp-4-tools) | Python 3.12 (uv) | 4 | 3 | 1 | 0 | 0 |
| **Total Subsystem** | — | **34** | **18** | **10** | **1** | **5** |

---

## 2. Comprehensive Tool Inventory

### 1. `audio-tools-mcp` (8 Tools)

#### 1.1 `trim_audio`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/server.py` (`trim_audio`) -> `utils/ffmpeg_ops.py` (`trim_audio_file`)
- **Purpose:** Trims an audio file to a specified duration starting from the beginning.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`, `ai/mcp/adapters/audio.py`
- **Input Schema:**
  - `file_path` (string, required): Path to source audio file.
  - `target_duration` (number, required): Target duration in seconds.
  - `output_path` (string | null, optional): Destination file path. If null, generates `{stem}_trimmed.{ext}`.
- **Output Schema:** `string` (absolute path to output file).
- **Dependencies:** FFmpeg binary (`/usr/bin/ffmpeg`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source audio; writes trimmed audio; launches `ffmpeg -y -i <src> -t <target> -c copy <dst>`.
- **Tenant / StorageService:** None. Directly manipulates raw filesystem paths.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Trimmed a 3.0s synthetic WAV to 1.5s. `ffprobe` verified output duration = 1.500s. Cleaned up successfully.

#### 1.2 `extend_audio`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`extend_audio`) -> `utils/ffmpeg_ops.py` (`extend_audio_file`)
- **Purpose:** Extends audio duration via looping (`loop`) or looping with crossfades (`fade_extend`), with silence detection pre-trim.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`, `ai/mcp/adapters/audio.py`
- **Input Schema:**
  - `file_path` (string, required): Source audio path.
  - `target_duration` (number, required): Desired extended duration.
  - `method` (string, optional, default: `"loop"`): `"loop"` or `"fade_extend"`.
  - `output_path` (string | null, optional): Output destination path.
  - `auto_trim_silence_before_loop` (boolean, optional, default: `true`).
  - `short_duration_threshold` (number, optional, default: `2.0`).
- **Output Schema:** `string` (absolute path to output file).
- **Dependencies:** FFmpeg, ffprobe.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source audio; writes extended audio; executes FFmpeg stream looping (`-stream_loop -1`).
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Extended 3.0s WAV to 5.0s via loop method. `ffprobe` verified duration = 5.000s.

#### 1.3 `normalize_loudness`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`normalize_loudness`) -> `utils/ffmpeg_ops.py` (`normalize_loudness_file`)
- **Purpose:** Normalizes integrated audio loudness to a target LUFS (e.g. -16 LUFS for voiceover, -24 LUFS for SFX) using FFmpeg's `loudnorm` filter.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`, `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/audio.py`
- **Input Schema:**
  - `file_path` (string, required): Source audio path.
  - `target_lufs` (number, required): Target integrated loudness (e.g. -16.0).
  - `output_path` (string | null, optional): Destination file path.
- **Output Schema:** `string` (absolute path to normalized file).
- **Dependencies:** FFmpeg (`loudnorm=I={target_lufs}:LRA=11:TP=-1.5`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source audio; writes normalized audio; launches FFmpeg subprocess.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Applied `-16.0` LUFS normalization to test WAV file. Wrote valid output WAV.

#### 1.4 `detect_and_trim_silence`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`detect_and_trim_silence`) -> `utils/ffmpeg_ops.py` (`detect_and_trim_silence_file`)
- **Purpose:** Detects and trims silence at the start and/or end of an audio file using FFmpeg `silencedetect`.
- **Consumers:** `references/ROUTER.md`, `ai/mcp/adapters/audio.py`
- **Input Schema:**
  - `file_path` (string, required): Source audio path.
  - `threshold_db` (number, optional, default: `-40.0`): Silence threshold in dB.
  - `min_silence_duration` (number, optional, default: `0.1`): Minimum duration of silence in seconds.
  - `trim_start` (boolean, optional, default: `true`): Trim leading silence.
  - `trim_end` (boolean, optional, default: `true`): Trim trailing silence.
  - `output_path` (string | null, optional): Destination path.
- **Output Schema:** `dict` containing `output_path` (string), `trimmed_start_seconds` (number), `trimmed_end_seconds` (number).
- **Dependencies:** FFmpeg, ffprobe.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Executes FFmpeg `silencedetect`, parses stderr output, and executes FFmpeg trim slice.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Detected and trimmed silence intervals, returned structured metadata.

#### 1.5 `analyze_voiceover`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`analyze_voiceover`) -> `utils/voiceover_ops.py` (`analyze_voiceover_file`)
- **Purpose:** Performs local automated speech recognition (ASR), multi-language speech transcription, and word-level timestamp extraction.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`, `recipes/dynamic-montage-ad.json`
- **Input Schema:**
  - `audio_path` (string, required): Audio file path.
  - `language` (string | null, optional): Target language code (e.g. `'ar'`, `'en'`).
  - `model_size` (string | null, optional): Whisper model size (`'tiny'`, `'base'`, `'small'`, etc. Defaults to `'base'`).
- **Output Schema:** `dict` containing `full_text`, `language`, `language_probability`, `duration`, `model_device`, `compute_type`, `model_size`, `segments`, `speech_periods`, `silence_periods`.
- **Dependencies:** `faster-whisper`, `ctranslate2`, `onnxruntime`, `numpy`, PyAV (`av`), FFmpeg.
- **External Providers / Models:** **Embedded Local ML Models**: `faster-whisper` (ASR) + `Silero VAD` (Voice Activity Detection).
- **Filesystem / Subprocess:** Reads audio file; writes cache file `.{stem}_{hash[:8]}.analysis.json`; writes `.device_capability.json`.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py` on real repository asset `assets/incoming/tests/human_vo_01.wav`. Loaded `faster-whisper` and `Silero VAD`, generated word-level timestamps and speech periods, returned duration=2.85s.

#### 1.6 `split_voiceover_sentences`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`split_voiceover_sentences`) -> `utils/sentence_splitter.py` (`split_voiceover_sentences_logic`)
- **Purpose:** Splits a voiceover audio file into separate sentence WAV files based on Whisper analysis timestamps and punctuation/duration rules.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`, `recipes/dynamic-montage-ad.json`
- **Input Schema:**
  - `audio_path` (string, required): Source audio file path.
  - `analysis_path` (string, required): Path to JSON file generated by `analyze_voiceover`.
  - `output_dir` (string, required): Destination directory for sentence audio slices.
  - `min_sentence_duration` (number, optional, default: `2.0`).
  - `max_sentence_duration` (number, optional, default: `10.0`).
  - `silence_threshold` (number, optional, default: `0.30`).
- **Output Schema:** `dict` containing list of sentence records with `id`, `text`, `start`, `end`, `duration`, `path`, and `words`.
- **Dependencies:** FFmpeg (`asyncio.create_subprocess_exec`).
- **External Providers / Models:** Consumes output of `faster-whisper` / `Silero VAD`.
- **Filesystem / Subprocess:** Reads analysis JSON and audio file; creates `output_dir`; writes sentence slice WAV files (`sentence_001.wav`, etc.).
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Sliced `human_vo_01.wav` into sentence chunks in `/tmp/mcp_reality_audit_tmp/split_sentences`.

#### 1.7 `get_voiceover_manifest`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`get_voiceover_manifest`) -> `utils/manifest_builder.py` (`build_voiceover_manifest_logic`)
- **Purpose:** Aggregates analysis and sentence-split data into a unified, strictly validated voiceover manifest with timeline coverage calculation.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`
- **Input Schema:**
  - `audio_path` (string, required): Path to audio file.
  - `analysis` (dict | null, optional): In-memory analysis payload.
  - `analysis_path` (string | null, optional): Path to analysis JSON.
  - `split_result` (dict | null, optional): In-memory sentence split payload.
  - `split_result_path` (string | null, optional): Path to sentence split JSON.
  - `output_path` (string | null, optional): Destination manifest file path.
- **Output Schema:** `dict` conforming to voiceover manifest structure with absolute word mapping and timeline coverage statistics.
- **Dependencies:** None outside standard library.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads input JSON files; writes output manifest JSON if `output_path` provided.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Produced valid manifest JSON with timeline coverage metrics.

#### 1.8 `build_voiceover_timeline`
- **MCP Server:** `audio-tools-mcp`
- **Source:** `server.py` (`build_voiceover_timeline`) -> `utils/timeline_builder.py` (`build_voiceover_timeline_logic`)
- **Purpose:** Converts a voiceover manifest into a fully chronological, strictly validated audio timeline map with flat arrays of sentences, words, and silence intervals.
- **Consumers:** `references/ROUTER.md`, `.agents/rules/video-production-protocol.md`
- **Input Schema:**
  - `manifest` (dict | null, optional): In-memory manifest dictionary.
  - `manifest_path` (string | null, optional): Path to manifest JSON.
  - `output_path` (string | null, optional): Destination timeline JSON path.
- **Output Schema:** `dict` containing flat chronological timeline (`sentences`, `words`, `silence_intervals`, `total_duration`).
- **Dependencies:** None outside standard library.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads manifest JSON; writes timeline JSON.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Built chronological timeline JSON with sentence, word, and silence interval mappings.

---

### 2. `common-tools-mcp` (2 Tools)

#### 2.1 `check_cache`
- **MCP Server:** `common-tools-mcp`
- **Source:** `server.py` (`check_cache`) -> `utils/cache_ops.py` (`check_cache_file`)
- **Purpose:** Checks whether a processed media file exists in the cache by checking `ground-truth/ASSET_INDEX.json`, `assets/ready`, and `assets/cache`.
- **Consumers:** `references/ROUTER.md`, `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/parity.py`
- **Input Schema:**
  - `asset_id` (string, required): Unique asset identifier.
  - `specs_hash` (string, required): Specification hash for transformation parameters.
  - `cache_dir` (string, required): Cache directory path.
- **Output Schema:** `string | null` (path to cached file if hit, or null on miss).
- **Dependencies:** Standard library (`os`, `pathlib`, `json`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Read-only lookup in filesystem directories.
- **Tenant / StorageService:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Correctly returned absolute file path on hit, and `None` on cache miss. Read-only with zero side effects.

#### 2.2 `save_to_cache`
- **MCP Server:** `common-tools-mcp`
- **Source:** `server.py` (`save_to_cache`) -> `utils/cache_ops.py` (`save_to_cache_file`)
- **Purpose:** Copies a processed media file into the cache directory under `{asset_id}_{specs_hash}.{ext}`.
- **Consumers:** `references/ROUTER.md`, `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/parity.py`
- **Input Schema:**
  - `file_path` (string, required): Source file to cache.
  - `asset_id` (string, required): Asset identifier.
  - `specs_hash` (string, required): Transformation hash.
  - `cache_dir` (string, required): Cache directory (passed as parameter).
- **Output Schema:** `string` (path to newly cached file).
- **Dependencies:** Standard library (`shutil.copy2`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads `file_path`; copies file to `CACHE_DIR`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Architectural drift: `save_to_cache_file` accepts a `cache_dir` argument, but completely ignores it in its implementation (`cache_path = CACHE_DIR`). It always writes to the module-level constant `CACHE_DIR` (`DATA_DIR / "assets" / "cache"`).
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Successfully copies files with `{asset_id}_{specs_hash}.ext` naming, but confirms argument bypass defect.

---

### 3. `ffmpeg-mcp-server` (6 Tools)

#### 3.1 `speed_up_video`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/server.js` (`speedUpVideo`)
- **Purpose:** Spawns a background FFmpeg job to accelerate video by a speed factor (e.g. 2x, 50x) with PTS filter (`setpts=(1/speed)*PTS`) and writes job state to `.agents/mcp_state/ffmpeg_jobs.json`.
- **Consumers:** `references/ROUTER.md` (§2, §4)
- **Input Schema:**
  - `filename` (string, required): Name of the video file in `VIDEOS_PATH`.
  - `speed_factor` (number, required, min: 1): Acceleration multiplier.
  - `output_suffix` (string, optional): Suffix for output file (default: `x{speed_factor}`).
- **Output Schema:** Object containing text content with job ID, estimated time, and output path.
- **Dependencies:** Node.js `child_process.spawn`, FFmpeg CLI.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Spawns detached background FFmpeg process; writes job state to `.agents/mcp_state/ffmpeg_jobs.json` and process stdout/stderr to `.agents/mcp_state/{jobId}.log`.
- **Tenant / StorageService:** None. Raw filesystem and local state file.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:**
  1. Relies on PowerShell WMI (`powershell -NoProfile -Command "Get-WmiObject Win32_Process..."`) to verify running background jobs upon startup and recovery. On Linux, this command fails silently, rendering process recovery inoperative.
  2. Resolves workspace root via `path.resolve(__dirname, '../../..')`, which creates `.agents/mcp_state/` inside `.agents/plugins/super-video-maker-plugin/` rather than the repository root.
- **Verification Evidence:** Executed live via stdio JSON-RPC in `scratch/run_media_and_ffmpeg_verification.py`. Created job, spawned background FFmpeg, and wrote log and state entries.

#### 3.2 `check_processing_status`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `server.js` (`checkProcessingStatus`)
- **Purpose:** Reports status and details of background video processing jobs in the queue.
- **Consumers:** `references/ROUTER.md`
- **Input Schema:** `{}` (no arguments).
- **Output Schema:** Object containing summary list of jobs (`status`, `fileSize`, `elapsed`, `pid`).
- **Dependencies:** Node.js filesystem, WMI (on Windows).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads `.agents/mcp_state/ffmpeg_jobs.json` and job log files.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Active process verification loop attempts WMI execution on Linux, which fails and returns empty array, falling back to reading log files.
- **Verification Evidence:** Executed live via stdio JSON-RPC in `scratch/run_media_and_ffmpeg_verification.py`. Successfully returned job statuses from state file.

#### 3.3 `cancel_video_processing`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `server.js` (`cancelVideoProcessing`)
- **Purpose:** Cancels an active video processing job, terminates the underlying process, and marks status as `'cancelled'`.
- **Consumers:** `references/ROUTER.md`
- **Input Schema:**
  - `jobId` (string, required): Identifier of job to cancel.
- **Output Schema:** Object containing confirmation message.
- **Dependencies:** Node.js `process.kill`, Windows `taskkill`.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Attempts `taskkill /F /PID <pid>` (Windows) with fallback to `process.kill(pid, 'SIGKILL')`; writes updated status to `ffmpeg_jobs.json`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:**
  1. Uses Windows `taskkill` first before fallback.
  2. Throws an unhandled error if the job has already finished (`Error: Job <id> is not active (status: completed)`).
- **Verification Evidence:** Executed live on active spawned job in `scratch/run_media_and_ffmpeg_verification.py`. Successfully cancelled active job and killed process.

#### 3.4 `increase_keyframes`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `server.js` (`increaseKeyframes`)
- **Purpose:** Transcodes video with fixed keyframe interval (`-g <gop_value>`) in the background.
- **Consumers:** `references/ROUTER.md`
- **Input Schema:**
  - `filename` (string, required): Video filename in `VIDEOS_PATH`.
  - `gop_value` (number, required, min: 1): Keyframe interval in frames.
  - `output_suffix` (string, optional): Suffix for output file.
- **Output Schema:** Object containing job ID and monitoring instructions.
- **Dependencies:** FFmpeg CLI, Node.js `spawn`.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Spawns background FFmpeg process with `-c:v libx264 -g <gop_value>`; writes state to `ffmpeg_jobs.json`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Same platform dependency on Windows PowerShell WMI for background job tracking as `speed_up_video`.
- **Verification Evidence:** Executed live via stdio JSON-RPC in `scratch/run_media_and_ffmpeg_verification.py`. Successfully spawned transcode job.

#### 3.5 `get_files_info`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `server.js` (`getFilesInfo`)
- **Purpose:** Scans a directory, lists files, formatted sizes, and ISO modification timestamps.
- **Consumers:** `references/ROUTER.md`
- **Input Schema:**
  - `directory` (string, optional): Directory path to scan (falls back to `VIDEOS_PATH`).
- **Output Schema:** Object containing formatted list of files and human-readable file sizes.
- **Dependencies:** Node.js `fs/promises`.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads directory stats (`fs.stat`).
- **Tenant / StorageService:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via stdio JSON-RPC in `scratch/run_media_and_ffmpeg_verification.py`. Accurately listed files, sizes, and timestamps in test directory.

#### 3.6 `concatenate_videos`
- **MCP Server:** `ffmpeg-mcp-server`
- **Source:** `server.js` (`concatenateVideos`)
- **Purpose:** Concatenates multiple video files using FFmpeg concat demuxer (`-f concat -safe 0`).
- **Consumers:** `references/ROUTER.md` (§2, §4)
- **Input Schema:**
  - `video_files` (array of strings, required): Array of filenames in `VIDEOS_PATH`.
  - `output_filename` (string, required): Name of output video file.
- **Output Schema:** Object containing confirmation and output path.
- **Dependencies:** FFmpeg CLI, Node.js `execAsync`.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Writes temporary list file `concat_list.txt`; executes FFmpeg via shell `execAsync`; unlinks `concat_list.txt`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Security finding: Uses raw shell interpolation (`const command = `ffmpeg -f concat -safe 0 -i ${tempListFile} -c copy ${output_filename}`; await execAsync(command)`), which presents shell injection risk if filenames contain shell metacharacters.
- **Verification Evidence:** Executed live via stdio JSON-RPC in `scratch/run_media_and_ffmpeg_verification.py`. Concatenated 2 test video clips into valid MP4 and cleaned up temporary list file.

---

### 4. `image-tools-mcp` (3 Tools)

#### 4.1 `upscale_image`
- **MCP Server:** `image-tools-mcp`
- **Source:** `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/server.py` (`upscale_image`) -> `utils/image_ops.py` (`upscale_image_file`)
- **Purpose:** Resizes or upscales an image using Lanczos sinc resampling (`Image.Resampling.LANCZOS`).
- **Consumers:** `references/ROUTER.md`, `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/image.py`
- **Input Schema:**
  - `file_path` (string, required): Source image path.
  - `target_width` (integer, optional, default: 0): Target width in pixels.
  - `target_height` (integer, optional, default: 0): Target height in pixels.
  - `output_path` (string | null, optional): Output destination path.
- **Output Schema:** `string` (absolute path to upscaled image).
- **Dependencies:** Python Pillow (`PIL.Image`).
- **External Providers / Models:** None (Classical resampling algorithm).
- **Filesystem / Subprocess:** Reads source image; writes resized image (`quality=95`).
- **Tenant / StorageService:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Upscaled test image to 200x150. Verified dimensions with PIL. Verified rejection of 0x0 inputs with `ValueError`.

#### 4.2 `crop_to_ratio`
- **MCP Server:** `image-tools-mcp`
- **Source:** `server.py` (`crop_to_ratio`) -> `utils/image_ops.py` (`crop_to_ratio_file`)
- **Purpose:** Performs a center crop of an image to match a target aspect ratio (e.g. `"9:16"`, `"1:1"`, `"16:9"`).
- **Consumers:** `references/ROUTER.md`, `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/image.py`
- **Input Schema:**
  - `file_path` (string, required): Source image path.
  - `target_ratio` (string, required): Ratio string (e.g. `"9:16"`).
  - `output_path` (string | null, optional): Output path.
- **Output Schema:** `string` (absolute path to cropped image).
- **Dependencies:** Python Pillow (`PIL.Image`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source image; writes cropped image.
- **Tenant / StorageService:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Cropped image to 1:1 square aspect ratio. Rejects malformed ratio strings with `ValueError`.

#### 4.3 `auto_crop_content`
- **MCP Server:** `image-tools-mcp`
- **Source:** `server.py` (`auto_crop_content`) -> `utils/image_ops.py` (`auto_crop_content_file`)
- **Purpose:** Automatically detects and strips solid or transparent borders around the main content of an image using bounding box difference algorithms.
- **Consumers:** `references/ROUTER.md`, `ai/mcp/adapters/image.py`
- **Input Schema:**
  - `file_path` (string, required): Source image path.
  - `background_color` (string, optional, default: `"auto"`): `"auto"`, `"transparent"`, `"white"`, or `"black"`.
  - `background_threshold` (integer, optional, default: 10): Color variance tolerance (0-255).
  - `output_path` (string | null, optional): Destination file path.
- **Output Schema:** `string` (absolute path to cropped image).
- **Dependencies:** Python Pillow (`PIL.Image`, `PIL.ImageChops`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source image; writes bounding-box cropped image.
- **Tenant / StorageService:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Stripped solid white border from 100x100 fixture containing 50x50 red center, producing cropped image of 51x51 pixels.

---

### 5. `media-sources-mcp` (11 Tools)

#### 5.1 `download_direct_file`
- **MCP Server:** `media-sources-mcp`
- **Source:** `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/server.py` (`download_direct_file`) -> `utils/downloader.py` (`download_media`)
- **Purpose:** Streams and downloads media files directly from an HTTP/HTTPS URL into the incoming asset tree.
- **Consumers:** `references/ROUTER.md` (§2, §4, §10)
- **Input Schema:**
  - `url` (string, required): Direct media URL.
  - `asset_type` (string, required): `"audio"`, `"image"`, `"video"`, or `"icons"`.
  - `source` (string, required): Source label (e.g. `"iconify"`, `"user"`).
  - `asset_id` (string, required): Asset identifier.
  - `custom_path` (string | null, optional): Relative directory under `SVM_DATA_DIR`.
- **Output Schema:** `string` (absolute path to downloaded file).
- **Dependencies:** `httpx` (streaming client), `mimetypes`.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Streams chunks (8KB) to disk at `assets/incoming/{asset_type}/{source}_{asset_type}_{asset_id}.{ext}`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:**
  1. Default workspace directory is hardcoded to Windows path `c:\video\clean-video-workspace` if `SVM_DATA_DIR` is not set.
  2. `safe_resolve` checks `resolved_path.relative_to(base_dir.resolve())`, so any Linux path outside `SVM_DATA_DIR` is rejected as path traversal. Works cleanly when `SVM_DATA_DIR` is explicitly set to a valid workspace directory.
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Downloaded Iconify SVG with `SVM_DATA_DIR` set; verified path traversal prevention on `/tmp/malicious`; verified rejection of invalid `asset_type`.

#### 5.2 `download_media_page`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`download_media_page`) -> `utils/downloader.py` (`download_via_ytdlp`)
- **Purpose:** Extracts and downloads media from web pages using `yt-dlp`.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `url` (string, required): Webpage URL.
  - `asset_type` (string, required): `"audio"`, `"image"`, `"video"`, or `"icons"`.
  - `source` (string, required): Source label.
  - `asset_id` (string, required): Asset identifier.
  - `custom_path` (string | null, optional): Custom subpath.
- **Output Schema:** `string` (absolute path to downloaded file).
- **Dependencies:** `yt-dlp` library.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Invokes `yt_dlp.YoutubeDL`.
- **Tenant / StorageService:** None.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Shares the same Windows fallback path and `safe_resolve` constraints as `download_direct_file`.
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Verified clean failure handling and exception raising on unreachable URLs.

#### 5.3 `change_asset_status`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`change_asset_status`) -> `utils/file_organizer.py` (`move_asset_status`)
- **Purpose:** Moves an asset file between status directories on the raw filesystem (`incoming`, `processing`, `ready`, `cache`).
- **Consumers:** `references/ROUTER.md` (§2), `ai/mcp/adapters/parity.py`
- **Input Schema:**
  - `file_path` (string, required): Relative or absolute path to source asset.
  - `from_status` (string, required): Expected origin status (`"incoming"`, `"processing"`, `"ready"`, `"cache"`).
  - `to_status` (string, required): Destination status.
  - `asset_type` (string, required): `"audio"`, `"image"`, `"video"`, `"icons"`.
- **Output Schema:** `string` (new absolute file path).
- **Dependencies:** Standard library (`shutil.move`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Moves file directly on disk (`shutil.move`).
- **Tenant / StorageService:** **Direct bypass of StorageService / AssetService**. Modifies raw filesystem layout without database or manifest transactional synchronization.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Direct raw filesystem mutation without canonical lifecycle locking; hardcoded to Windows default `c:\video\...` unless `SVM_DATA_DIR` is set.
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Successfully moved asset file from `incoming` to `processing/image`; verified rejection of invalid status.

#### 5.4 `iconify_search`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`iconify_search`) -> `tools/iconify.py` (`search_iconify`)
- **Purpose:** Searches for open-source vector SVG icons across 150+ icon sets via the official Iconify API.
- **Consumers:** `references/ROUTER.md` (§2, §4)
- **Input Schema:**
  - `query` (string, required): Search keyword (e.g. `"arrow"`, `"home"`).
  - `limit` (integer, optional, default: 30): Maximum results to return.
- **Output Schema:** `dict` containing list of icon names and icon set collections.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Iconify API (`https://api.iconify.design/search`).
- **Filesystem / Subprocess:** None (network only).
- **Secret Requirements:** None required (public free API).
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Queried `"home"` and received 32 icon results from the official Iconify API.

#### 5.5 `download_iconify_icon`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`download_iconify_icon`) -> `tools/iconify.py` (`download_iconify`)
- **Purpose:** Downloads an SVG icon from Iconify with optional color and dimensions.
- **Consumers:** `references/ROUTER.md` (§2, §4)
- **Input Schema:**
  - `prefix` (string, required): Icon set prefix (e.g. `"mdi"`).
  - `name` (string, required): Icon name (e.g. `"home"`).
  - `color` (string | null, optional): Hex color code or CSS color string.
  - `width` (integer | null, optional): SVG width.
  - `height` (integer | null, optional): SVG height.
  - `output_path` (string | null, optional): Destination directory.
- **Output Schema:** `string` (absolute path to downloaded SVG).
- **Dependencies:** `httpx`.
- **External Providers / Models:** Iconify API (`https://api.iconify.design/{prefix}/{name}.svg`).
- **Filesystem / Subprocess:** Writes `.svg` file to disk.
- **Secret Requirements:** None.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Downloaded `mdi:home` icon in red (`#ff0000`) to `/tmp/mcp_media_ffmpeg_audit_tmp/custom_icons/mdi_home.svg`. Verified file exists and contains valid SVG XML.

#### 5.6 `pixabay_search_images`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`pixabay_search_images`) -> `tools/pixabay.py` (`search_pixabay_images`)
- **Purpose:** Searches Pixabay for photos and illustrations via official Pixabay API.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `per_page` (integer, optional, default: 20).
  - `orientation` (string, optional, default: `"all"`).
- **Output Schema:** `list[dict]` containing photo hits with URLs, tags, dimensions.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Pixabay API (`https://pixabay.com/api/`).
- **Secret Requirements:** `PIXABAY_API_KEY` (required in environment).
- **Classification:** **`UNVERIFIED`**
- **Reason:** Blocked by missing secret. `PIXABAY_API_KEY` is not configured in `.env` or system environment. Invoking the tool raises `ValueError: PIXABAY_API_KEY environment variable not set`.

#### 5.7 `pixabay_search_videos`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`pixabay_search_videos`) -> `tools/pixabay.py` (`search_pixabay_videos`)
- **Purpose:** Searches Pixabay for stock video footage via official Pixabay API.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `per_page` (integer, optional, default: 20).
- **Output Schema:** `list[dict]` containing video hits and stream resolutions.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Pixabay Video API (`https://pixabay.com/api/videos/`).
- **Secret Requirements:** `PIXABAY_API_KEY` (required in environment).
- **Classification:** **`UNVERIFIED`**
- **Reason:** Blocked by missing secret. `PIXABAY_API_KEY` is missing from environment. Invoking the tool raises `ValueError: PIXABAY_API_KEY environment variable not set`.

#### 5.8 `pixabay_search_audio`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`pixabay_search_audio`) -> `utils/pixabay_scraper.py` (`search_pixabay_audio`)
- **Purpose:** Web-scrapes Pixabay music and sound effects using a headless Playwright Chromium browser.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `max_results` (integer, optional, default: 10).
- **Output Schema:** `list[dict]` containing audio track records.
- **Dependencies:** `playwright.async_api`.
- **External Providers / Models:** Unofficial browser-based web scraper targeting `https://pixabay.com/music/search/`.
- **Secret Requirements:** None (scrapes public web page).
- **Classification:** **`BROKEN`**
- **Defect / Blocker Observed:** Runtime environment failure: The Playwright Chromium browser binaries are not installed on the host (`Executable doesn't exist at /home/eng_Momen/.cache/ms-playwright/chromium_headless_shell-1234/...`). Invoking the tool raises `RuntimeError: Failed to fetch Pixabay audio: BrowserType.launch: Executable doesn't exist`.
- **Verification Evidence:** Executed live via `scratch/run_media_and_ffmpeg_verification.py`. Verified exact runtime crash trace.

#### 5.9 `freesound_search`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`freesound_search`) -> `tools/freesound.py` (`search_freesound`)
- **Purpose:** Searches Freesound.org API for sound effects and ambient audio.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `page` (integer, optional, default: 1).
  - `page_size` (integer, optional, default: 15).
- **Output Schema:** `list[dict]` containing sound effect records.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Freesound API (`https://freesound.org/apiv2/search/text/`).
- **Secret Requirements:** `FREESOUND_API_KEY` (required in environment).
- **Classification:** **`UNVERIFIED`**
- **Reason:** Blocked by missing secret. `FREESOUND_API_KEY` is not configured in `.env` or system environment. Invoking the tool raises `ValueError: FREESOUND_API_KEY environment variable not set`.

#### 5.10 `pexels_search_images`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`pexels_search_images`) -> `tools/pexels.py` (`search_pexels_images`)
- **Purpose:** Searches Pexels photo catalog via official Pexels API.
- **Consumers:** `references/ROUTER.md` (§2)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `per_page` (integer, optional, default: 15).
  - `orientation` (string | null, optional): `'landscape'`, `'portrait'`, `'square'`.
- **Output Schema:** `list[dict]` containing photo records.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Pexels API (`https://api.pexels.com/v1/search`).
- **Secret Requirements:** `PEXELS_API_KEY` (required in environment).
- **Classification:** **`UNVERIFIED`**
- **Reason:** Blocked by missing secret. `PEXELS_API_KEY` is missing from environment. Invoking the tool raises `ValueError: PEXELS_API_KEY environment variable not set`.

#### 5.11 `pexels_search_videos`
- **MCP Server:** `media-sources-mcp`
- **Source:** `server.py` (`pexels_search_videos`) -> `tools/pexels.py` (`search_pexels_videos`)
- **Purpose:** Searches Pexels video catalog for B-Roll video clips via official Pexels API.
- **Consumers:** `references/ROUTER.md` (§2, §4)
- **Input Schema:**
  - `query` (string, required): Search query.
  - `per_page` (integer, optional, default: 15).
  - `orientation` (string | null, optional).
- **Output Schema:** `list[dict]` containing video records.
- **Dependencies:** `httpx`.
- **External Providers / Models:** Pexels Video API (`https://api.pexels.com/videos/search`).
- **Secret Requirements:** `PEXELS_API_KEY` (required in environment).
- **Classification:** **`UNVERIFIED`**
- **Reason:** Blocked by missing secret. `PEXELS_API_KEY` is missing from environment. Invoking the tool raises `ValueError: PEXELS_API_KEY environment variable not set`.

---

### 6. `video-tools-mcp` (4 Tools)

#### 6.1 `trim_video`
- **MCP Server:** `video-tools-mcp`
- **Source:** `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/server.py` (`trim_video`) -> `utils/ffmpeg_ops.py` (`trim_video_file`)
- **Purpose:** Trims a video file to target duration from the beginning using FFmpeg streamcopy.
- **Consumers:** `references/ROUTER.md` (§2, §4), `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/video.py`
- **Input Schema:**
  - `file_path` (string, required): Source video path.
  - `target_duration` (number, required): Desired duration in seconds.
  - `output_path` (string | null, optional): Output path.
- **Output Schema:** `string` (absolute path to trimmed video).
- **Dependencies:** FFmpeg CLI (`-c copy`).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source video; writes trimmed video; launches FFmpeg subprocess.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Trimmed 3.0s synthetic MP4 to 1.5s. `ffprobe` verified output duration = 1.566s (nearest keyframe).

#### 6.2 `extend_video`
- **MCP Server:** `video-tools-mcp`
- **Source:** `server.py` (`extend_video`) -> `utils/ffmpeg_ops.py` (`extend_video_file`)
- **Purpose:** Extends video duration via stream looping (`method="loop"`) or last frame freeze padding (`method="freeze_last_frame"`).
- **Consumers:** `references/ROUTER.md` (§2, §4), `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/video.py`
- **Input Schema:**
  - `file_path` (string, required): Source video path.
  - `target_duration` (number, required): Target extended duration.
  - `method` (string, optional, default: `"loop"`): `"loop"` or `"freeze_last_frame"`.
  - `short_duration_threshold` (number, optional, default: `2.0`).
  - `output_path` (string | null, optional): Output destination path.
- **Output Schema:** `string` (confirmation text containing output path and warning message if applicable).
- **Dependencies:** FFmpeg CLI, ffprobe.
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source video; writes extended video; launches FFmpeg subprocess.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Extended 3.0s test video to 5.0s via stream loop. `ffprobe` verified duration = 5.089s.

#### 6.3 `resize_video`
- **MCP Server:** `video-tools-mcp`
- **Source:** `server.py` (`resize_video`) -> `utils/ffmpeg_ops.py` (`resize_video_file`)
- **Purpose:** Resizes video to target dimensions with letterboxing/pillarboxing (`maintain_aspect_ratio=True`) or stretch (`maintain_aspect_ratio=False`).
- **Consumers:** `references/ROUTER.md` (§2, §4), `recipes/dynamic-montage-ad.json`, `ai/mcp/adapters/video.py`
- **Input Schema:**
  - `file_path` (string, required): Source video path.
  - `target_width` (integer, required): Target width in pixels.
  - `target_height` (integer, required): Target height in pixels.
  - `maintain_aspect_ratio` (boolean, optional, default: `true`).
  - `output_path` (string | null, optional): Output path.
- **Output Schema:** `string` (absolute path to resized video).
- **Dependencies:** FFmpeg CLI (`scale` and `pad` video filters).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Reads source video; encodes to `libx264` MP4 at target dimensions.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`WORKING`**
- **Verification Evidence:** Executed live via `scratch/run_actual_mcp_verification.py`. Resized 320x240 video to 640x360 with letterboxing. Output file verified with `ffprobe`.

#### 6.4 `detect_and_trim_black_frames`
- **MCP Server:** `video-tools-mcp`
- **Source:** `server.py` (`detect_and_trim_black_frames`) -> `utils/ffmpeg_ops.py` (`detect_and_trim_black_frames_file`)
- **Purpose:** Automatically detects and trims black frames from video start and/or end using FFmpeg `blackdetect`.
- **Consumers:** `references/ROUTER.md` (§2, §4), `ai/mcp/adapters/video.py`
- **Input Schema:**
  - `file_path` (string, required): Source video path.
  - `threshold` (number, optional, default: `0.1`): Threshold parameter.
  - `min_duration` (number, optional, default: `0.1`): Minimum black interval duration in seconds.
  - `trim_start` (boolean, optional, default: `true`).
  - `trim_end` (boolean, optional, default: `true`).
  - `output_path` (string | null, optional): Output path.
- **Output Schema:** `string` (JSON string containing trimming statistics, `trimmed` boolean, `black_intervals_detected`, and `output_path`).
- **Dependencies:** FFmpeg CLI (`blackdetect` filter).
- **External Providers / Models:** None.
- **Filesystem / Subprocess:** Executes FFmpeg `blackdetect`, parses stderr intervals, executes FFmpeg slice.
- **Tenant / StorageService:** None. Raw filesystem only.
- **Classification:** **`PARTIALLY_WORKING`**
- **Defect / Drift Observed:** Critical parameter mismatch: In `ffmpeg_ops.py` line 178, the FFmpeg filter command passes `blackdetect=d={min_duration}:pic_th={threshold}` with default `threshold=0.1`. In FFmpeg, `pic_th` represents the percentage of black pixels in the frame (default 0.98), whereas `pix_th` represents the luminance threshold (default 0.10). Passing `pic_th=0.1` causes FFmpeg to classify any frame with >= 10% dark pixels as black, resulting in `ValueError: Video is entirely black frames` on normal videos. When explicitly called with `threshold=0.98`, the tool detects and trims black frames perfectly.
- **Verification Evidence:** Verified both behaviors in `scratch/run_actual_mcp_verification.py`. With default `threshold=0.1`, failed with `ValueError: Video is entirely black frames`. With `threshold=0.98`, successfully trimmed 1.0s leading and trailing black intervals from 6.0s test video, outputting clean 4.0s video.
