# S27 — Baseline Inventory: AI, Agents, Providers & MCPs

## Metadata
- **Audit Date:** 2026-09-30
- **Stage:** S27.0 Architecture Freeze + Bootstrap
- **Auditor:** Strategic Planner & Pipeline Architect (AI-01)
- **Status:** BASELINE FROZEN (S27.0 PASS Gate)
- **Target Subsystem:** `ai/`, `.agents/`, `api/services/`, `scripts/core/`

---

## 1. Executive Summary

As part of **S27.0 (Architecture Freeze + Bootstrap)** of the *AI & Media Intelligence Platform*, this inventory establishes an exhaustive, empirical baseline of all existing AI-related, agentic, provider, and MCP components in `clean-video-workspace`.

### Fundamental Boundary Rule (ADR-004)
```text
AI Orchestrator / Platform (`ai/*`)
       ↓
Tool Layer / Capability Adapters
       ↓
Domain Services (`api/services/*`, `scripts/core/*`)
       ↓
Existing Deterministic Core (CAS, StateStore, Lifecycle, ReviewService)
       ↓
Render / Probe / QC (Remotion, FFmpeg, SmartQC)
```

**Core Invariant:**
AI may request actions through authorized tool interfaces. AI never becomes:
1. Source of Truth
2. Authorization Authority
3. Lifecycle Authority
4. QC Authority
5. Filesystem Authority
6. Template Registry Authority

---

## 2. Component Inventory & Classification

Each component is classified into exactly one of:
- `KEEP`: Retain in current place/role without modification in S27.
- `MIGRATE`: Migrate into canonical `ai/` subsystem (providers, capabilities, contracts) in subsequent S27 stages.
- `WRAP`: Wrap behind a typed Domain Service or Capability Adapter.
- `REPLACE`: Replace with existing canonical core service (e.g., StorageService, AssetService).
- `DELETE`: Redundant or obsolete legacy code to be safely phased out.
- `DEFER_TO_S28`: Advanced operational capability deferred to S28.

For MCPs, an additional architectural classification is assigned:
- `DOMAIN MCP`: Deals with business domain logic or entities.
- `PROCESSING MCP`: Local media computation, encoding, analysis, or transformation.
- `EXTERNAL INTEGRATION MCP`: Integrates with external 3rd-party cloud services or APIs.

---

### 2.1 Model Context Protocol (MCP) Servers

| MCP Server | Location | Current Function | Callers | Callees | Touches | Domain / Processing / Integration | MCP Architecture Classification | Action Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **audio-tools-mcp** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp` | Voiceover analysis (`faster-whisper`, Silero VAD), silence detection, sentence splitting, audio trimming/extension, LUFS normalization (`-16` LUFS for VO, `-24` LUFS for SFX), voiceover manifest & timeline builder. | AI Agent / Claude / Antigravity IDE via stdio MCP | Local FFmpeg, `faster-whisper`, Silero VAD, filesystem. | Raw filesystem paths (reads audio, writes chunks, manifests, timelines). | Processing + STT Analysis | **PROCESSING MCP** | `WRAP` (Wrap into STT Capability Adapter & Media Worker in S27/S28) |
| **video-tools-mcp** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp` | Video trimming, looping/extending (`loop` or `freeze_last_frame`), aspect ratio resizing (letterbox/pillarbox/stretch), black frame detection. | AI Agent / recipes via stdio MCP | Local FFmpeg/ffprobe via subprocess. | Raw filesystem paths (reads/writes video files). | Processing | **PROCESSING MCP** | `WRAP` (Wrap into video processing worker capability in S27/S28) |
| **image-tools-mcp** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp` | Image upscaling (Lanczos resampling), center crop to aspect ratio (`9:16`, `1:1`, `16:9`), auto border/content cropping. | AI Agent via stdio MCP | Python Pillow (`PIL`) library. | Raw filesystem paths (reads/writes image files). | Processing | **PROCESSING MCP** | `WRAP` (Wrap into image worker capability in S27/S28) |
| **common-tools-mcp** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp` | Cache lookup (`check_cache`) and saving (`save_to_cache`) for processed assets based on `asset_id` and `specs_hash`. | AI Agent during Phase 1 Media Package. | Local filesystem (`os.path.exists`, `shutil.copy2`). | Raw filesystem cache directory. | Domain Storage Logic | **DOMAIN MCP** | `REPLACE` (Replace with canonical `StorageService` / `AssetCache` in core) |
| **ffmpeg-mcp-server** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server` | Node.js MCP server managing background FFmpeg jobs, transcode, probe, trim, state persistence in `.agents/mcp_state/ffmpeg_jobs.json`. | AI Agent via stdio MCP | Node.js `child_process`, FFmpeg, Windows PowerShell WMI. | Raw filesystem, ad-hoc state file `.agents/mcp_state/ffmpeg_jobs.json`. | Processing | **PROCESSING MCP** | `WRAP` (Wrap / absorb into Python worker queue; eliminate ad-hoc Node state file) |
| **media-sources-mcp** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp` | Search & download media from Pixabay (images, video, audio via Playwright), Pexels, Freesound, Iconify; direct HTTP downloads; `change_asset_status`. | AI Agent via stdio MCP | External HTTP APIs, Playwright, yt-dlp, filesystem. | External web services, raw filesystem folders (`assets/incoming/`, etc.). | External Integration + Filesystem Mutation | **EXTERNAL INTEGRATION MCP** | `KEEP` (Keep for external search, but remove raw status mutation in favor of `AssetService`) |

---

### 2.2 Provider & AI Helper Scripts

| Script / Tool | Location | Current Function | Callers | Callees | Touches | Type | Action Classification | S27 Target Mapping |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **elevenlabs_voice.py** | `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py` | Dynamic language-aware voice picker from ElevenLabs shared voice library; TTS synthesis via `eleven_v3` / `eleven_multilingual_v2`. | External Agent, recipes via CLI | ElevenLabs REST API via `urllib.request`. | External API, `.env`, writes MP3 files locally. | External Integration | `MIGRATE` | Migrates to `ai/providers/elevenlabs_provider.py` (`TEXT_TO_SPEECH` capability adapter in S27.3). |
| **fal_seedance_video.py** | `.agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py` | CLI wrapper for Fal.ai Seedance 2.5 / 2.0 (text-to-video, image-to-video, reference-to-video). | External Agent, recipes via CLI | `fal_client` SDK, Fal.ai API. | External API, `.env`, writes MP4 to `output_videos/`. | External Integration | `MIGRATE` | Migrates to `ai/providers/fal_provider.py` (`VIDEO_GENERATION` capability adapter in S27.3). |
| **heygen_client.py** | `.agents/plugins/super-video-maker-plugin/tools/heygen_client.py` | HeyGen API client: avatar listing, voice selection, avatar video generation with green-screen background, status polling, MP4 download. | External Agent, recipes via CLI | HeyGen v2 REST API via `requests`. | External API, `.env`, writes MP4 locally. | External Integration | `MIGRATE` | Migrates to `ai/providers/heygen_provider.py` (`AVATAR_GENERATION` / `LIP_SYNC` adapter in S27.3). |
| **image_provider.py** | `.agents/plugins/super-video-maker-plugin/tools/image_provider.py` | OpenAI DALL-E / GPT image generation & editing with reference masks. Emits single RESULT JSON. | External Agent, recipes via CLI | OpenAI SDK (`from openai import OpenAI`). | External API, `.env`, writes PNG/JPG to `output_images/`. | External Integration | `MIGRATE` | Migrates to `ai/providers/openai_provider.py` (`IMAGE_GENERATION` adapter in S27.3). |
| **music_provider.py** | `.agents/plugins/super-video-maker-plugin/tools/music_provider.py` | CLI adapter stub: validates ElevenLabs music plan arguments or verifies local music file path. | External Agent, recipes via CLI | Local filesystem, `.env`. | Filesystem. | Integration / Stub | `REPLACE` | Replaced by `MUSIC_GENERATION` capability adapter & `AssetService` in S27.3. |
| **replicate_video.py** | `.agents/plugins/super-video-maker-plugin/tools/replicate_video.py` | CLI wrapper around Replicate's `bytedance/seedance-2.0` model. Emits RESULT JSON. | External Agent, recipes via CLI | `replicate` SDK, Replicate API. | External API, `.env`, writes MP4 to `output_videos/`. | External Integration | `MIGRATE` | Migrates to `ai/providers/replicate_provider.py` (`VIDEO_GENERATION` adapter in S27.3). |
| **video_captioner.py** | `.agents/plugins/super-video-maker-plugin/tools/video_captioner.py` | Extracts audio, calls OpenAI Whisper API (`whisper-1`) for word timestamps, generates ASS subtitles, burns into video via FFmpeg. | External Agent, recipes via CLI | Local FFmpeg, OpenAI Whisper API. | External API, local FFmpeg, temp audio/subtitle/video files. | Processing + Integration | `MIGRATE` | Split into `SPEECH_TO_TEXT` capability adapter and Remotion/FFmpeg caption renderer. |
| **media_pipeline.py** | `.agents/plugins/super-video-maker-plugin/tools/media_pipeline.py` | Legacy `MediaPipelineOrchestrator` handling asset ingestion, hashing, caching, atomic moves between folder tiers, and `.transactions.jsonl`. | Legacy scripts, docs | Filesystem, `filelock`, `scripts.core.asset_cache`. | Raw directories (`assets/`, `processed/`, `storage/`). | Domain Logic (Legacy) | `REPLACE` | Superseded by canonical `StorageService`, `AssetLifecycle`, and `AssetService`. |
| **ffmpeg_qc.py** | `.agents/plugins/super-video-maker-plugin/tools/ffmpeg_qc.py` | Basic ffprobe stream validation and black frame detection. | Recipes, legacy docs | FFmpeg/ffprobe subprocess. | Filesystem. | Processing / QC | `REPLACE` | Superseded by canonical `SmartQC`, `ProbePlanner`, `FinalQC` in `scripts/gates/`. |
| **screen_recorder.py** | `.agents/plugins/super-video-maker-plugin/tools/screen_recorder.py` | Screencast recorder using Xvfb + FFmpeg or Playwright fallback with event logging. | Recipes (`screencast-demo.json`) | Xvfb, FFmpeg, Playwright. | Virtual display, subprocesses, `screen_recordings/`. | Processing / Tool | `DEFER_TO_S28` | Complex screen capture deferred to S28 platform enhancements. |

---

### 2.3 Agent Governance, Guards & Skills

| Component | Location | Current Function | Callers | Callees | Touches | Action Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AGENTS.md** | `.agents/AGENTS.md` | Primary agent instructions: hierarchy of truth, taste gates, lock protocol, asset normalization. | Antigravity IDE Agent / System | N/A (Markdown instructions) | N/A | `KEEP` |
| **Guardian Hooks** | `.agents/guardian/` (`command_guard.py`, `write_guard.py`, `behavior_guard.py`, `post_executor.py`, `utils.py`, `circuit_breaker.json`) | Intercepts commands, file writes, and agent execution in the IDE. Blocks dangerous commands (`rm -rf`, raw npm studio) and unauthorized writes. | IDE Agent Tool Execution Hooks | JSON configs, filesystem, audit logs. | Logs to `.agents/logs/guardrails.log`, updates `circuit_breaker.json`. | `KEEP` |
| **video-production-protocol.md** | `.agents/rules/video-production-protocol.md` | Phased protocol (Phase 0 Pre-Flight, Phase 1 Media Package, Phase 2 Plan, Phase 3 Build/Render). | IDE Agent / System Prompt | N/A | N/A | `KEEP` |
| **prompt-engineering-expert** | `.agents/skills/prompt-engineering-expert/` | Advanced guidance for prompt design, few-shot examples, optimization, and system prompt craft. | IDE Agent / Human | N/A | N/A | `KEEP` |
| **remocn & snapcn skills** | `.agents/plugins/super-video-maker-plugin/skills/` | Guides agent in selecting Remotion components, compiling blueprints, and authoring custom React components. | IDE Agent | `inspect_template.py`, `validate_template.py`, `custom_code_validator.py`. | Guides blueprint and TSX generation. | `KEEP` |
| **transcript_cleaner.py** | `scripts/maintenance/transcript_cleaner.py` | Inspects and cleans Antigravity IDE agent session transcript JSONL files in user brain directory. | Operator / CLI | Filesystem, `safe_subprocess`. | User home directory (`~/.gemini/antigravity-ide/brain/...`). | `KEEP` |

---

## 3. Existing Domain Services & Core Gateways

The existing system possesses robust, server-verified domain services and state authorities developed across S00–S26. Future AI tools must interface exclusively through these services:

1. **`ProjectService` (`api/services/project_service.py`)**
   - *Authority:* Scoped project creation, project listing, and canonical LifecycleDTO projection.
   - *AI Boundary Role:* AI queries project existence, metadata, and stage status. AI never scans `projects/` directly.

2. **`PipelineService` (`api/services/pipeline_service.py`)**
   - *Authority:* Stage execution, gate verification, pipeline status, execution concurrency locking.
   - *AI Boundary Role:* AI requests pipeline stage triggers. AI cannot bypass gate requirements.

3. **`GateService` (`api/services/gate_service.py`)**
   - *Authority:* Approval, evidence checking, and status querying for pipeline gates (`asset_gate`, `plan_gate`, `taste_gate`, `qc_gate`).
   - *AI Boundary Role:* AI provides artifacts for gates. AI can NEVER approve gates or create `.studio_approved`.

4. **`AssetService` (`api/services/asset_service.py`)**
   - *Authority:* Tenant-aware asset registration, ingestion, status queries, and metadata tracking.
   - *AI Boundary Role:* AI registers generated or downloaded media through `AssetService`. Direct raw folder dumping is banned.

5. **`DomainArtifactService` & `ArtifactService` (`api/services/domain_artifact_service.py`, `scripts/core/artifact_service.py`)**
   - *Authority:* Manifest, blueprint, probe, and render artifact queries.
   - *AI Boundary Role:* AI reads and proposes blueprint/manifest structures through typed contracts.

6. **`ReviewService` (`scripts/core/review_service.py`)**
   - *Authority:* Sole authority for `ReviewBundle` generation, recording human `ReviewDecision`, and issuing render authorization.
   - *AI Boundary Role:* AI cannot forge review approvals or authorize video rendering.

7. **`LifecycleService` (`scripts/core/lifecycle_service.py`)**
   - *Authority:* Sole canonical authority for project `LifecycleState` transitions via atomic CAS mutations.
   - *AI Boundary Role:* AI cannot mutate `lifecycle_state` directly.

8. **`RenderService` & `Worker` (`api/services/render_service.py`, `scripts/core/worker.py`)**
   - *Authority:* Render job creation, durable worker queueing, Remotion execution in isolated ephemeral workspaces.
   - *AI Boundary Role:* AI requests rendering via jobs; never invokes `npx remotion` or Node directly.

9. **`RunRepository` (`scripts/core/run_repository.py`)**
   - *Authority:* Durable tracking of runs, step leasing, heartbeat, and execution history.
   - *AI Boundary Role:* Foundation for future `AIRun` and `AIStep` durable orchestration in S27.10.

10. **`StorageService` (`scripts/core/storage/storage_service.py`)**
    - *Authority:* Abstracted binary payload storage (`LocalStorageBackend`, `S3CompatibleStorageBackend`).
    - *AI Boundary Role:* AI stores large artifacts, transcripts, and media files via `StorageService`.

---

## 4. Discovered Architectural Gaps

1. **Unstructured File Generation:**
   - Existing tools (`fal_seedance_video.py`, `image_provider.py`, `replicate_video.py`, `heygen_client.py`) write outputs directly into root folders (`output_videos/`, `output_images/`, `temp_audio_*.mp3`) rather than mediating storage through `StorageService` or registering them in `AssetService`.
2. **Path-Based MCP Interfaces:**
   - Existing MCP tools (`audio-tools-mcp`, `video-tools-mcp`, `image-tools-mcp`) accept and return raw filesystem paths. They have zero awareness of `TenantContext`, `workspace_id`, or `StorageService`.
3. **Direct Filesystem Mutation in MCP:**
   - `media-sources-mcp` exposes `change_asset_status` which directly moves files across filesystem folders (`assets/incoming` -> `assets/ready`), completely bypassing `AssetLifecycle` and `StateStore`.
4. **Ad-Hoc State File in Node MCP:**
   - `ffmpeg-mcp-server` writes its own background job state to `.agents/mcp_state/ffmpeg_jobs.json`, violating the single-source-of-truth database architecture.
5. **Decentralized API Key Handling:**
   - Standalone provider scripts each read `.env` directly using `os.getenv` without centralized secret management or quota governance.
6. **Absence of AI Domain Service:**
   - No formal service currently coordinates AI workflows, resulting in human/agent reliance on unmetered, un-audited CLI scripts.

---

## 5. Architectural Boundaries Enforced in S27.0

To guarantee that future AI development does not violate the system's core invariants, the following mechanical boundaries are enforced starting in S27.0 via `tests/ai/test_ai_architecture_guards.py`:
- ❌ **No Raw Project Filesystem Access:** `ai/*` cannot open, read, or write project files directly via raw path strings or `Path("projects/...")`.
- ❌ **No Raw SQL Bypass:** `ai/*` cannot import raw database drivers (`sqlite3`, `psycopg2`, `mysql.connector`) or invoke raw `.execute()` outside approved repositories.
- ❌ **No Direct Lifecycle Mutation:** `ai/*` cannot mutate `state.lifecycle_state`.
- ❌ **No Direct Template Registry Mutation:** `ai/*` cannot directly write to `templates/` or `registry/`.
- ❌ **No Direct QC / Approval Authority:** `ai/*` cannot generate approval markers (`.studio_approved`, `.qc_passed`) or forge `ReviewDecision`.
- ❌ **Strict Domain Service Mediation:** All operations modifying system state must pass through the typed Tool Layer and Domain Services.
