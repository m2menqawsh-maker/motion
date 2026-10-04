# S28-M01 Closure Report — MCP Reality Audit & Baseline

> **Milestone:** S28-M01 — MCP Reality Audit & Baseline  
> **Status:** **`PASS`**  
> **Repository:** `motion / clean-video-workspace`  
> **Execution Date:** 2026-10-03  
> **Author:** Antigravity AI Coding Assistant  
> **Principle:** `NO CAPABILITY LOSS` | Verified Runtime Reality Wins Over Static Documentation

---

## 1. Executive Summary

| Metric | Measured Value | Target Gate | Result |
|---|---|---|---|
| **Discovered MCP Servers** | **6** | All discovered (>= 6) | **PASS** |
| **Discovered MCP Tools** | **34** | All discovered (>= 33) | **PASS** |
| **`WORKING` Tools** | **18** | Actual execution verified | **VERIFIED** |
| **`PARTIALLY_WORKING` Tools** | **10** | Documented with exact reproductions | **VERIFIED** |
| **`BROKEN` Tools** | **1** | Documented root-cause evidence | **VERIFIED** |
| **`UNVERIFIED` Tools** | **5** (External stock APIs requiring secrets) | 0 critical tools unverified | **PASS** |
| **Discovered Embedded Models** | **2** (`faster-whisper`, `Silero VAD`) | Exhaustive identification | **PASS** |
| **Unknown MCP Servers** | **0** | Exactly 0 | **PASS** |
| **Unknown Tools** | **0** | Exactly 0 | **PASS** |
| **Unknown Embedded Models** | **0** | Exactly 0 | **PASS** |
| **Production Code Modifications** | **`NONE`** | Zero modifications | **PASS** |
| **S28-M02 Started?** | **`NO`** | Must not start M02 | **PASS** |
| **Final Milestone Gate** | **`PASS`** | All criteria met | **PASS** |

### Top 5 Findings & Blockers
1. **Tool Discovery Discrepancy & Regex Blindspot:** Historical documentation (`ground-truth/MCP_INDEX.md`) reported 33 tools across 6 servers, missing the `speed_up_video` tool in `ffmpeg-mcp-server` due to an imperfect regex in `build_ground_truth.py`. Live protocol querying via JSON-RPC stdio revealed **34 actual tools**.
2. **Windows Path Hardcoding & Path Traversal Trigger:** `media-sources-mcp` defaults its workspace path to `c:\video\clean-video-workspace` unless `SVM_DATA_DIR` is explicitly defined. When executed on Linux without this environment variable, absolute Linux paths are rejected as "Path traversal detected" by `safe_resolve`.
3. **FFmpeg `blackdetect` Threshold Parameter Bug:** In `video-tools-mcp` (`detect_and_trim_black_frames`), the tool passes default `threshold=0.1` to FFmpeg's `pic_th` parameter rather than `pix_th`. In FFmpeg, `pic_th` represents the percentage of black pixels (default 0.98), so `0.1` causes FFmpeg to classify almost every real frame as black and abort with `ValueError: Video is entirely black frames`. Passing `threshold=0.98` executes properly.
4. **Platform-Locked Background Process Management:** `ffmpeg-mcp-server` attempts to monitor running background FFmpeg processes via PowerShell WMI (`Get-WmiObject Win32_Process`) and terminate them with `taskkill /F /PID`. On Linux, PowerShell is absent, causing WMI process polling to fail silently and process recovery to be non-functional.
5. **Missing Playwright Browser Dependency & Unconfigured External Secrets:**
   - `pixabay_search_audio` in `media-sources-mcp` is **`BROKEN`** because it uses an unofficial browser scraping script, and Playwright Chromium binaries are not installed on the system.
   - 5 external search tools (`pixabay_search_images`, `pixabay_search_videos`, `freesound_search`, `pexels_search_images`, `pexels_search_videos`) are **`UNVERIFIED`** for live queries because their respective external API keys are not provisioned in `.env` (only `OPENROUTER_API_KEY` is present).

---

## 2. Scope Inspected

The audit surveyed every file, configuration, test, wrapper, and dependency across the repository:
- **Server Implementations:**
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp`
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp`
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server`
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp`
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp`
  - `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp`
- **Configuration & Registration Files:**
  - `.agents/plugins/super-video-maker-plugin/mcp_config.json`
  - `.agents/plugins/super-video-maker-plugin/plugin.json`
  - `.agents/plugins/super-video-maker-plugin/verify.py`
  - Root `pyproject.toml`, `package.json`, `uv.lock`, `.env.example`, `.env`
  - Each MCP server's internal `pyproject.toml`, `package.json`, and `uv.lock`
- **Consumer Authorities & Routing Rules:**
  - `references/ROUTER.md`
  - `.agents/rules/video-production-protocol.md`
  - `.agents/AGENTS.md`
  - `recipes/*.json` (including `dynamic-montage-ad.json`)
  - `scripts/generators/build_ground_truth.py`
  - `scripts/validators/audit_skill.py`
- **AI Abstraction & Hardened Adapters:**
  - `ai/mcp/catalog.py`
  - `ai/mcp/contracts.py`
  - `ai/mcp/policy.py`
  - `ai/mcp/audit.py`
  - `ai/mcp/adapters/` (`base.py`, `audio.py`, `video.py`, `image.py`, `parity.py`)
- **Existing Test Suites:**
  - `tests/ai/mcp/` (85 unit and adversarial tests)
  - `tests/security/`
  - `tests/architecture/`

---

## 3. Baseline & Historical Reconciliation

Historical documentation referenced 7 MCP servers:
1. `audio-tools-mcp`
2. `common-tools-mcp`
3. `ffmpeg-mcp-server`
4. `image-tools-mcp`
5. `media-sources-mcp`
6. `video-tools-mcp`
7. `Video_Editor_MCP`

**Historical Reconciliation Findings:**
- In commit `fc764b9` ("chore(phase5): establish quarantine structure baseline"), `Video_Editor_MCP` was quarantined and removed from `mcp_config.json`.
- In commit `7e94c15` ("refactor(plugin): overhaul super-video-maker-plugin..."), `Video_Editor_MCP` source files were completely purged from the repository tree, and `.agents/AGENTS.md` formally quarantined it (`❌ Do not use the Video_Editor_MCP (quarantined)`).
- Therefore, exactly **6 active MCP servers** exist in the repository today.

---

## 4. MCP Servers Found

| Server ID | Path | Language / Runtime | Entrypoint | Transport | Status |
|---|---|---|---|---|---|
| `audio-tools-mcp` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp` | Python 3.12 (uv) | `server.py` | stdio FastMCP | Starts successfully |
| `common-tools-mcp` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp` | Python 3.12 (uv) | `server.py` | stdio FastMCP | Starts successfully |
| `ffmpeg-mcp-server` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server` | Node.js v26.7 (npm) | `server.js` | stdio StdioServerTransport | Starts successfully |
| `image-tools-mcp` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp` | Python 3.12 (uv) | `server.py` | stdio FastMCP | Starts successfully |
| `media-sources-mcp` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp` | Python 3.12 (uv) | `server.py` | stdio FastMCP | Starts successfully |
| `video-tools-mcp` | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp` | Python 3.12 (uv) | `server.py` | stdio FastMCP | Starts successfully |

---

## 5. Tool Verification Matrix Summary

The full tool specifications, input/output schemas, consumers, and side effects are recorded in [`MCP_TOOL_MATRIX.md`](file:///home/eng_Momen/Projects/%D8%A7%D9%84%D9%85%D8%B4%D8%B1%D9%88%D8%B9%20%D8%A7%D9%84%D8%AD%D8%A7%D9%84%D9%8A/Video%20maker/documentation/s28m/MCP_TOOL_MATRIX.md).

### Summary Breakdown:
- **`WORKING` (18 Tools):**
  - `audio-tools-mcp`: `trim_audio`, `extend_audio`, `normalize_loudness`, `detect_and_trim_silence`, `analyze_voiceover`, `split_voiceover_sentences`, `get_voiceover_manifest`, `build_voiceover_timeline` (8 tools)
  - `common-tools-mcp`: `check_cache` (1 tool)
  - `image-tools-mcp`: `upscale_image`, `crop_to_ratio`, `auto_crop_content` (3 tools)
  - `video-tools-mcp`: `trim_video`, `extend_video`, `resize_video` (3 tools)
  - `media-sources-mcp`: `iconify_search`, `download_iconify_icon` (2 tools)
  - `ffmpeg-mcp-server`: `get_files_info` (1 tool)
- **`PARTIALLY_WORKING` (10 Tools):**
  - `common-tools-mcp`: `save_to_cache` (works but ignores `cache_dir` argument, always writing to repository root `assets/cache`)
  - `video-tools-mcp`: `detect_and_trim_black_frames` (works with `threshold=0.98`, but default `threshold=0.1` causes `pic_th=0.1` false-positive black detection)
  - `media-sources-mcp`: `download_direct_file`, `download_media_page`, `change_asset_status` (work with `SVM_DATA_DIR` set, but hardcoded to Windows default `c:\video\...`, reject Linux paths as path traversal, and directly mutate raw disk state without manifest transactions)
  - `ffmpeg-mcp-server`: `speed_up_video`, `check_processing_status`, `cancel_video_processing`, `increase_keyframes` (background jobs work, but PowerShell WMI process monitoring fails on Linux; `cancel_video_processing` errors out on completed jobs); `concatenate_videos` (works, but contains raw shell string interpolation)
- **`BROKEN` (1 Tool):**
  - `media-sources-mcp`: `pixabay_search_audio` (Playwright Chromium browser binary missing in execution environment; raises `RuntimeError`)
- **`UNVERIFIED` (5 Tools):**
  - `media-sources-mcp`: `pixabay_search_images`, `pixabay_search_videos`, `freesound_search`, `pexels_search_images`, `pexels_search_videos` (Missing external SaaS API secrets: `PIXABAY_API_KEY`, `FREESOUND_API_KEY`, `PEXELS_API_KEY`)

---

## 6. Embedded Models Found

Documented in detail in [`EMBEDDED_MODEL_INVENTORY.json`](file:///home/eng_Momen/Projects/%D8%A7%D9%84%D9%85%D8%B4%D8%B1%D9%88%D8%B9%20%D8%A7%D9%84%D8%AD%D8%A7%D9%84%D9%8A/Video%20maker/documentation/s28m/EMBEDDED_MODEL_INVENTORY.json).

1. **`faster-whisper` (Speech-to-Text):**
   - **Owning MCP:** `audio-tools-mcp` (`utils/voiceover_ops.py`)
   - **Invoked by:** `analyze_voiceover`
   - **Engine:** CTranslate2 (INT8 CPU quantization, CUDA check with fallback)
   - **Default Model:** `"base"`
   - **Lifecycle:** Lazy singleton managed by `WhisperModelManager`
   - **Cache:** HuggingFace Hub cache + local `.{stem}_{hash}.analysis.json`
   - **Status:** **`WORKING`** (Live verified on repository audio fixture)
2. **`Silero VAD` (Voice Activity Detection):**
   - **Owning MCP:** `audio-tools-mcp` (`utils/voiceover_ops.py`)
   - **Invoked by:** `analyze_voiceover`
   - **Engine:** ONNX Runtime (`silero_vad.onnx`)
   - **Purpose:** Segments audio into speech/silence intervals for pacing
   - **Status:** **`WORKING`** (Live verified)

---

## 7. Consumers

The graph of inbound consumers and triggers is mapped in [`MCP_DEPENDENCY_GRAPH.md`](file:///home/eng_Momen/Projects/%D8%A7%D9%84%D9%85%D8%B4%D8%B1%D9%88%D8%B9%20%D8%A7%D9%84%D8%AD%D8%A7%D9%84%D9%8A/Video%20maker/documentation/s28m/MCP_DEPENDENCY_GRAPH.md).

Primary consumers include:
1. **Agent Router:** `references/ROUTER.md` defines the decision matrix routing production tasks to `audio-tools-mcp`, `media-sources-mcp`, `video-tools-mcp`, `image-tools-mcp`, `common-tools-mcp`, and `ffmpeg-mcp-server`.
2. **Video Protocol:** `.agents/rules/video-production-protocol.md` mandates `analyze_voiceover`, `normalize_loudness`, and asset status movement.
3. **Recipes:** `recipes/*.json` (e.g. `dynamic-montage-ad.json`) declare required MCP servers in `"mcp_servers"`.
4. **AI Layer:** `ai/mcp/catalog.py` maintains an authoritative registry, while `ai/mcp/adapters/` wraps operations with validation and timeouts.
5. **Automated Tests:** `tests/ai/mcp/` and `tests/architecture/` test boundary compliance, parity, and adversarial inputs.

---

## 8. Dependencies & External Providers

- **Local System Binaries:**
  - `/usr/bin/ffmpeg` & `/usr/bin/ffprobe` (FFmpeg 8.1.3)
  - `/home/eng_Momen/.local/bin/uv` (uv 0.10.4)
  - `/home/eng_Momen/.nvm/versions/node/v26.7.0/bin/node` (Node.js v26.7.0)
- **External Web APIs:**
  - `api.iconify.design` (Public, no API key)
  - `api.pexels.com` (Requires `PEXELS_API_KEY`)
  - `pixabay.com` (Requires `PIXABAY_API_KEY`)
  - `freesound.org` (Requires `FREESOUND_API_KEY`)
- **Web Scraping:**
  - `pixabay.com/music/search/` (Playwright headless Chromium — currently missing browser binary)

---

## 9. Side Effects

1. **Filesystem Writes:**
   - Transcoded media files written directly to source or custom output directories.
   - Cache artifacts written to `assets/cache/{asset_id}_{specs_hash}.ext`.
   - Ad-hoc state persistence: `.agents/mcp_state/ffmpeg_jobs.json` and `{jobId}.log`.
   - Temporary file creation: `ffmpeg-mcp-server` writes `concat_list.txt` in the videos directory during concatenation and unlinks it upon completion.
2. **Subprocess Spawning:**
   - Unmanaged detached background FFmpeg processes spawned by `ffmpeg-mcp-server`.
   - Synchronous and asynchronous child processes spawned via `asyncio.create_subprocess_exec` by `audio-tools-mcp` and `video-tools-mcp`.
3. **Database / Storage Bypass:**
   - `media-sources-mcp::change_asset_status` moves files on disk without synchronizing with `02_asset_manifest.json` or database tables.
   - `common-tools-mcp::save_to_cache` copies files without updating `AssetV2` models.

---

## 10. Security & Tenant Observations

1. **Missing Tenant Scoping:** None of the 6 MCP servers possess tenant awareness or workspace isolation. File paths are passed as raw strings, allowing cross-tenant directory access if unsanitized.
2. **Path Traversal Defenses:**
   - `media-sources-mcp` implements `safe_resolve`, but because `SVM_DATA_DIR` defaults to Windows `c:\video\...`, on Linux it treats valid absolute paths as traversal attacks.
3. **Shell Injection Surface:** `ffmpeg-mcp-server::concatenateVideos` performs raw string concatenation into `execAsync`:
   ```javascript
   const command = `ffmpeg -f concat -safe 0 -i ${tempListFile} -c copy ${output_filename}`;
   await execAsync(command, { cwd: baseFolder });
   ```
   If `output_filename` contains shell metacharacters (e.g. `; rm -rf /`), arbitrary commands would be executed in the host shell.
4. **Secrets Handling:**
   - No secrets are hardcoded in the codebase.
   - Missing secrets are detected via `os.environ.get()` and trigger clean `ValueError` exceptions before making network calls.

---

## 11. Failures Found with Exact Reproductions

### Failure 1: FFmpeg `blackdetect` False Positive
- **Server:** `video-tools-mcp`
- **Tool:** `detect_and_trim_black_frames`
- **Reproduction:** Call `detect_and_trim_black_frames_file(video_path)` with default parameters.
- **Result:** FFmpeg filter string sets `pic_th=0.1` (requires only 10% black pixels per frame). On standard video, every frame is identified as black, raising `ValueError: Video is entirely black frames`.
- **Workaround Proved:** Calling with `threshold=0.98` accurately identifies and trims black intervals.

### Failure 2: Missing Playwright Browser Executable
- **Server:** `media-sources-mcp`
- **Tool:** `pixabay_search_audio`
- **Reproduction:** Run `search_pixabay_audio("ambient")`.
- **Result:** Fails with `RuntimeError: Failed to fetch Pixabay audio: BrowserType.launch: Executable doesn't exist at /home/eng_Momen/.cache/ms-playwright/...`.

### Failure 3: PowerShell WMI & Taskkill Failure on Linux
- **Server:** `ffmpeg-mcp-server`
- **Tools:** `speed_up_video`, `check_processing_status`, `cancel_video_processing`
- **Reproduction:** Run `ffmpeg-mcp-server` on Linux and monitor background jobs.
- **Result:** Server logs `[WMI Error] Failed to get running FFmpeg processes: Command failed: powershell ...`. Job adoption on restart fails.

### Failure 4: Argument Bypass in `save_to_cache`
- **Server:** `common-tools-mcp`
- **Tool:** `save_to_cache`
- **Reproduction:** Call `save_to_cache_file(src, asset_id, hash, custom_cache_dir)`.
- **Result:** The function ignores `custom_cache_dir` and saves to `CACHE_DIR = DATA_DIR / "assets" / "cache"`.

---

## 12. Unverified Items

Exactly 5 tools are classified as **`UNVERIFIED`**:
1. `media-sources-mcp::pixabay_search_images` (Missing `PIXABAY_API_KEY`)
2. `media-sources-mcp::pixabay_search_videos` (Missing `PIXABAY_API_KEY`)
3. `media-sources-mcp::freesound_search` (Missing `FREESOUND_API_KEY`)
4. `media-sources-mcp::pexels_search_images` (Missing `PEXELS_API_KEY`)
5. `media-sources-mcp::pexels_search_videos` (Missing `PEXELS_API_KEY`)

**Why Unverified?**
- In accordance with Section 0 and Section 13, secrets must not be guessed, forged, or leaked.
- The environment `.env` only contains `OPENROUTER_API_KEY`.
- Because these 5 tools make authenticated HTTP requests to external third-party commercial APIs, live search execution cannot succeed without valid credentials.
- In accordance with Section 12, these are **non-critical tools** (optional external asset search), so having them classified as `UNVERIFIED` does not block milestone gate passage. All core processing tools are verified.

---

## 13. Legacy Behavior Preserved

The following behaviors must be preserved during any future migration:
1. **Voiceover Processing Pipeline:** The sequential contract `analyze_voiceover` -> `split_voiceover_sentences` -> `get_voiceover_manifest` -> `build_voiceover_timeline` forms the temporal backbone for Remotion word-level kinetic captions.
2. **Loudness Standards:** Integrated loudness normalization to `-16.0` LUFS for voiceover and `-24.0` LUFS for SFX/BGM must be strictly enforced.
3. **Aspect Ratio & Fit Modes:** Video and image resizing logic supporting letterboxing, pillarboxing, and aspect-ratio preservation (`1:1`, `9:16`, `16:9`) must be maintained.
4. **Cache Filename Convention:** `{asset_id}_{specs_hash}.{ext}` must be preserved for compatibility with asset lookups.

---

## 14. Remaining Unknowns

**`0 Remaining Unknowns`**
- All 6 servers have verified source paths, startup commands, package managers, and transports.
- All 34 tools have verified runtime signatures, input/output schemas, and execution statuses.
- All embedded models are cataloged with device selection, caching, and lifecycle behaviors.

---

## 15. Tests Executed & Results

1. **Existing Unit & Adversarial Test Suite:**
   - Command: `.venv/bin/pytest tests/ai/mcp/`
   - Result: **`85 passed in 5.91s`**
2. **Live stdio Schema Discovery:**
   - Command: `python3 scratch/discover_all_mcp_schemas.py`
   - Result: **All 6 servers connected via stdio JSON-RPC; 34 tools discovered with formal schemas.**
3. **Core Processing Verification Test (Audio, Video, Image, Common):**
   - Command: `python3 scratch/run_actual_mcp_verification.py`
   - Result: **16 tools tested with live media fixtures; all happy paths and error branches verified.**
4. **Media Sources & FFmpeg Node Verification Test:**
   - Command: `python3 scratch/run_media_and_ffmpeg_verification.py`
   - Result: **17 tools tested; Iconify live network verified, Playwright failure isolated, FFmpeg Node tools verified via stdio.**

---

## 16. Files Changed

Only new audit, inventory, and evidence documentation files were created:
- `documentation/s28m/MCP_REALITY_INVENTORY.json` (New)
- `documentation/s28m/MCP_TOOL_MATRIX.md` (New)
- `documentation/s28m/MCP_DEPENDENCY_GRAPH.md` (New)
- `documentation/s28m/EMBEDDED_MODEL_INVENTORY.json` (New)
- `documentation/s28m/evidence/S28-M01_REPORT.md` (New)

Temporary test scripts and media fixtures in `/tmp` and `scratch/` were cleaned up.

---

## 17. Runtime & Production Code Changes

**`NONE`**
Zero lines of production code, scripts, templates, or configurations were modified.

---

## 18. Known Risks (Documented Only)

1. **Host Command Injection Risk:** `ffmpeg-mcp-server::concatenateVideos` uses unescaped string concatenation inside `child_process.exec()`.
2. **Windows Path Portability:** Default paths in `media-sources-mcp` and `common-tools-mcp` assume Windows drive letters (`C:/video/...`).
3. **Orphan Process Risk:** Background FFmpeg jobs in `ffmpeg-mcp-server` are detached without a bounded watchdog on Linux.
4. **Third-Party Rate Limits & Web Scraper Fragility:** `pixabay_search_audio` relies on scraping DOM/bootstrap variables from Pixabay using a headless browser, which is fragile and currently broken.

---

## 19. Final Gate Verdict

### **`S28-M01 PASS`**

- `0 unknown MCP servers` (6/6 accounted for)
- `0 unknown tools` (34/34 accounted for)
- `0 unknown embedded models` (2/2 accounted for)
- `0 unexplained side effects` (All filesystem/process/network effects verified)
- `0 critical tools = UNVERIFIED` (100% of critical processing tools verified)
- Full machine-readable inventories and human-readable matrices generated.
- `S28-M02` was **NOT** started.
- Zero capability deleted or lost.

---

## 20. Commit / PR Evidence

- Git Branch: `feature/s27-ai-platform`
- Latest Commit SHA: `c7b2f17 Merge pull request #6 from m2menqawsh-maker/remediation/s26-deliverables`
- Audit Deliverable Directory: `documentation/s28m/`
