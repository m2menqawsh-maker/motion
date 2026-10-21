# 09 — Capability, Model, Provider & Tool Execution Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Capability Catalog Architecture, Tool Gateway Pipeline, MCP Isolation, Model/Provider Routing, and Repository-Wide Bypass Sweep
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Architectural Verdict

The Capability and Tool Execution subsystem in this repository represents a mature, hardened abstraction designed during the S28-M modernization initiative. It introduces a unified catalog of 43 canonical capabilities (`documentation/s28m/CAPABILITY_CATALOG.json`), an authoritative 15-stage execution pipeline in `ToolGateway` (`ai/tools/gateway.py`), and a strict isolation layer that severs internal AI from raw MCP protocols.

Key architectural realities proven from the codebase:

1. **Internal Product AI Does NOT Require Raw MCP (Check O)**: Internal AI platforms (planning, narrative, intent, recipes, skills) have zero dependency on raw MCP transports. AST architecture guards enforce zero MCP calls in creative planning, recipes, and domain services (`CODE_PROVEN`, `TEST_PROVEN`). MCP servers are relegated to legacy external compatibility facades.
2. **Hardened 15-Stage Tool Gateway**: `ToolGateway` enforces complete tenant isolation, server-side RBAC, SSRF egress validation, storage path confinement, CAS idempotency leasing, and compound `side_effects[]` evaluation before invoking any tool adapter.
3. **Blocked Security Implementations**: `CONCATENATE_VIDEOS` is explicitly hard-blocked inside `MCPToolAdapter` (`ai/tools/adapters/mcp.py:83`) due to a verified shell injection finding in legacy scripts, failing closed with `ImplementationSecurityBlockedError`.
4. **Clean Shell Security Invariant**: A repository-wide audit reveals **zero** instances of `shell=True` in production code. All subprocess invocations use explicit argument vectors via `safe_subprocess` or `asyncio.create_subprocess_exec`.
5. **Provider Execution Boundary**: Production LLM routing remains unwired; the only active LLM provider adapter in `ai/providers/` is `OpenRouterProvider` (flagged `environment="development"`, `production_default=False`). Native provider adapters (OpenAI, Anthropic, Gemini, ElevenLabs, Fal.ai) exist only as metadata descriptors or test fakes.

---

## 2. Capability Catalog & Execution Matrix (All 43 Capabilities)

The authoritative runtime repository is `documentation/s28m/CAPABILITY_CATALOG.json`, loaded by `CapabilityCatalog` (`ai/capabilities/catalog.py`).

| # | Capability ID | Category | Family | Execution Mode | Tenant Scope | Required Perms | Side Effects | Target Storage Boundary | Primary Implementation | Reachability |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | `SPEECH_TO_TEXT` | `MODEL` | `SPEECH_INTELLIGENCE` | `MODEL` | `PROJECT` | `viewer`, `editor` | `LOCAL_TEMP_WRITE` | Transient Analysis Cache | `local_stt_provider` (faster-whisper) | `DEV_ONLY` |
| 02 | `SEGMENT_SPEECH_AUDIO` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Audio Slices | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 03 | `GENERATE_SPEECH_MANIFEST` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | ArtifactService / Speech Manifest | `canonical_speech_manifest_builder` | `DEV_ONLY` |
| 04 | `BUILD_SPEECH_TIMELINE` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | ArtifactService / Speech Timeline | `canonical_speech_timeline_builder` | `DEV_ONLY` |
| 05 | `TRIM_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 06 | `EXTEND_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 07 | `NORMALIZE_AUDIO_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 08 | `TRIM_AUDIO_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 09 | `TRIM_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 10 | `EXTEND_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 11 | `RESIZE_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 12 | `TRIM_BLACK_FRAMES` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 13 | `CHANGE_VIDEO_SPEED` | `TOOL` | `VIDEO_PROCESSING` | `WORKER` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS`, `BACKGROUND_JOB`| StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 14 | `ENFORCE_KEYFRAME_INTERVAL`| `TOOL` | `VIDEO_PROCESSING` | `WORKER` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 15 | `CONCATENATE_VIDEOS` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `SECURITY_BLOCKED` |
| 16 | `RESIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_resize_image` | `DEV_ONLY` |
| 17 | `CROP_IMAGE_TO_RATIO` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_crop_image_ratio` | `DEV_ONLY` |
| 18 | `AUTO_CROP_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_auto_crop_image` | `DEV_ONLY` |
| 19 | `DOWNLOAD_REMOTE_MEDIA` | `TOOL` | `MEDIA_ACQUISITION` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Ingestion Hierarchy | `canonical_acquisition_download_remote_media` | `DEV_ONLY` |
| 20 | `EXTRACT_MEDIA_PAGE` | `TOOL` | `MEDIA_ACQUISITION` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Ingestion Hierarchy | `canonical_acquisition_extract_media_page` | `DEV_ONLY` |
| 21 | `SEARCH_ICONS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_icons` | `DEV_ONLY` |
| 22 | `DOWNLOAD_ICON` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Project Icons | `canonical_acquisition_download_icon` | `DEV_ONLY` |
| 23 | `SEARCH_STOCK_IMAGES` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_images` | `DEV_ONLY` |
| 24 | `SEARCH_STOCK_VIDEOS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_videos` | `DEV_ONLY` |
| 25 | `SEARCH_STOCK_AUDIO` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_audio` | `DEV_ONLY` |
| 26 | `SEARCH_SOUND_EFFECTS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_sound_effects` | `DEV_ONLY` |
| 27 | `INSPECT_MEDIA` | `TOOL` | `MEDIA_INSPECTION` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | StorageService / Read-Only Probe | `canonical_media_processing_service` | `DEV_ONLY` |
| 28 | `MUTATE_ASSET_STATUS` | `DOMAIN_SERVICE`| `ASSET_DOMAIN_OPERATIONS`| `LOCAL` | `PROJECT` | `editor`, `admin` | `DOMAIN_MUTATION`, `PERSISTENT_WRITE` | AssetService / ManifestV2 Authority | `legacy_media_sources_mcp_change_asset_status` | `COMPATIBILITY_ONLY` |
| 29 | `CHECK_MEDIA_CACHE` | `DOMAIN_SERVICE`| `CACHE_MANAGEMENT` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | AssetService / Managed Cache | `legacy_common_tools_mcp_check_cache` | `COMPATIBILITY_ONLY` |
| 30 | `STORE_MEDIA_CACHE` | `DOMAIN_SERVICE`| `CACHE_MANAGEMENT` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | AssetService / Managed Cache | `legacy_common_tools_mcp_save_to_cache` | `COMPATIBILITY_ONLY` |
| 31 | `GET_JOB_STATUS` | `DOMAIN_SERVICE`| `JOB_MANAGEMENT` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | RunService / Durable Job Record | `legacy_ffmpeg_mcp_server_check_processing_status`| `COMPATIBILITY_ONLY` |
| 32 | `CANCEL_PROCESSING_JOB` | `DOMAIN_SERVICE`| `JOB_MANAGEMENT` | `LOCAL` | `PROJECT` | `editor`, `admin` | `DOMAIN_MUTATION`, `SUBPROCESS` | RunService / Durable Job Record | `legacy_ffmpeg_mcp_server_cancel_video_processing`| `COMPATIBILITY_ONLY` |
| 33 | `NORMALIZE_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 34 | `ANALYZE_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | In-Memory (Read-Only Analysis) | `canonical_media_processing_service` | `DEV_ONLY` |
| 35 | `DETECT_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | In-Memory (Read-Only Analysis) | `canonical_media_processing_service` | `DEV_ONLY` |
| 36 | `SPLIT_SPEECH_TEXT` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 37 | `PREPARE_VO_SEGMENTS` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 38 | `ALIGN_AUDIO_METADATA` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 39 | `PROBE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `READ_ONLY` | StorageService / Read Only | `canonical_image_processing_service_probe_image` | `DEV_ONLY` |
| 40 | `CONVERT_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_convert_image` | `DEV_ONLY` |
| 41 | `OPTIMIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_optimize_image` | `DEV_ONLY` |
| 42 | `PREPARE_IMAGE_ASSET` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | StorageService / AssetService Manifest | `canonical_image_processing_service_prepare_image_asset`| `DEV_ONLY` |
| 43 | `THUMBNAIL` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Cache | `canonical_image_processing_service_generate_thumbnail`| `DEV_ONLY` |

---

## 3. Mandatory Check O: Raw MCP Requirement for Internal Product AI

### 3.1 Question Statement
> **Check O**: Is raw MCP required for Internal Product AI?

### 3.2 Architectural Proof & AST Guard Enforcement
In `tests/ai/audit/test_s28_m11_final_architecture_audit.py:46-81`:
- **Guard 1 (`test_guard_01_no_raw_mcp_in_creative_planner`)**:
  ```python
  def test_guard_01_no_raw_mcp_in_creative_planner(self):
      """CreativePlanner and planning modules must have zero imports or calls to raw MCP servers."""
      for py_file in (AI_ROOT / "planning").rglob("*.py"):
          content = py_file.read_text(encoding="utf-8")
          assert "ai.mcp" not in content and "mcp_servers" not in content
  ```
- **Guard 3 (`test_guard_03_no_raw_mcp_transport_in_skills`)**:
  ```python
  def test_guard_03_no_raw_mcp_transport_in_skills(self):
      """Skills must resolve through CapabilityRouter or SkillRegistry, never direct raw MCP."""
      for py_file in (AI_ROOT / "skills").rglob("*.py"):
          content = py_file.read_text(encoding="utf-8")
          assert "ai.mcp" not in content and "mcp-servers" not in content
  ```
- **Guard 9 (`test_guard_09_domain_services_do_not_depend_on_compatibility_mcp`)**:
  Verifies that `scripts/core/`, `api/services/`, `ai/media_processing/`, `ai/image_processing/`, `ai/speech/`, and `ai/acquisition/` have zero import dependencies on `ai.mcp.compatibility`.

Furthermore:
- In `ai/tools/adapters/domain_service.py:8`:
  ```
  "ZERO raw MCP invocations for state mutations. Every domain operation routes through the authoritative 15-stage ToolGateway pipeline into DomainServiceAdapter."
  ```
- All internal tool invocations dispatch via `CapabilityRouter` $\to$ `ToolGateway` $\to$ Python domain adapters (`LocalMediaProcessingService`, `LocalSpeechPreparationService`, `DomainServiceAdapter`).
- Raw MCP servers (`.agents/plugins/.../tools/mcp-servers/`) are wrapped behind `FastMCP` compatibility facades (`ai/mcp/compatibility/server.py`) for external developer/agent tools only.

### 3.3 Answer to Check O
**NO** (`CODE_PROVEN`, `TEST_PROVEN`).
Raw MCP is **not required** and is **strictly forbidden** for Internal Product AI. All internal operations execute via strongly typed in-process Python services and `ToolGateway`.

---

## 4. The 15-Stage Tool Gateway Pipeline (`ai/tools/gateway.py`)

`ToolGateway.execute()` (`ai/tools/gateway.py:258-525`) is the single authoritative gateway for capability execution:

```
[Incoming CapabilityRequest]
              │
              ▼
    Stage 1: Capability Lookup (Resolves CapabilityDefinition from CapabilityCatalog)
              │
    Stage 2: Input Contract Resolution (Resolves canonical Pydantic model)
              │
    Stage 3: Input Contract Validation (Strict Pydantic model_validate)
              │
    Stage 4: TenantContext Validation (Enforces workspace_id match; validates PROJECT/SYSTEM scope)
              │
    Stage 5: Authorization Enforcement (Verifies required_permissions against actor roles)
              │
    Stage 6: Resource Ownership / Confinement (Prevents directory traversal outside projects/)
              │
    Stage 7: Side-Effects Policy Enforcement (Evaluates full side_effects[] array: SSRF, storage, subprocess)
              │
    Stage 8: Budget & Spending Ceiling Policy (Enforces max cost & quota limits)
              │
    Stage 9: Idempotency Enforcement (CAS leadership claim & in-flight replay)
              │
    Stage 10: Timeout & Deadline Policy (Sets asyncio.wait_for bounded deadline)
              │
    Stage 11: Adapter Selection (Resolves adapter from AdapterRegistry; checks security blocks)
              │
    Stage 12: Adapter Execution (Async execution within isolated process/thread)
              │
    Stage 13: Output Contract Validation (Validates raw output against output_contract Pydantic schema)
              │
    Stage 14: Storage & Integrity Verification (Validates output storage keys against path traversal)
              │
    Stage 15: Telemetry & Structured Result (Emits CapabilityResult with latency, cost, and metadata)
              │
              ▼
[Outgoing CapabilityResult]
```

### 4.1 Security Invariants Enforced by the Gateway
1. **SSRF Guardrail (`FORBIDDEN_SCHEMES`)**:
   - Blocks non-HTTP/HTTPS schemes (`file://`, `ftp://`, `gopher://`, `data://`).
   - Resolves DNS and blocks loopback (`127.0.0.1`), private RFC1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS/GCP cloud metadata endpoints (`169.254.169.254`).
2. **Security-Blocked Implementations**:
   - `CONCATENATE_VIDEOS` is explicitly hard-blocked (`MCPToolAdapter.STATIC_CAPABILITY_BINDINGS:83`) due to a verified shell injection finding in the legacy implementation. Attempts to invoke it fail closed with `ImplementationSecurityBlockedError`.
3. **Compound `side_effects[]` Processing**:
   - The gateway parses the full `side_effects` array (not just the scalar fallback), simultaneously applying network egress guards, storage confinement, and subprocess constraints for compound capabilities.

---

## 5. Comprehensive Repository-Wide Bypass Sweep

An exhaustive static sweep across the entire repository evaluates five common architectural bypass vectors:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BYPASS AUDIT SUMMARY                              │
├──────────────────────────┬──────────────┬───────────────────────────────────┤
│ Bypass Vector            │ Status       │ Findings & Evidence               │
├──────────────────────────┼──────────────┼───────────────────────────────────┤
│ 1. AI Directly to Model  │ BYPASS FOUND │ plan_gate.py:26 calls OpenAI()    │
│                          │ (Legacy Gate)│ directly, bypassing ModelRouter.  │
│ 2. Raw MCP Bypass        │ CLEAN        │ Zero raw MCP calls in ai/. AST    │
│                          │              │ guards prevent regressions.       │
│ 3. Arbitrary Shell Exec  │ CLEAN        │ Zero shell=True in production.    │
│                          │              │ All subprocesses use argv lists.  │
│ 4. Filesystem Direct CAS │ PARTIAL      │ Core and authoring enforce CAS.   │
│                          │ BYPASS       │ Maintenance scripts write direct. │
│ 5. Domain Service Bypass │ BYPASS FOUND │ pipeline.py advances state via    │
│                          │ (Pipeline)   │ save_state() instead of service.  │
└──────────────────────────┴──────────────┴───────────────────────────────────┘
```

### 5.1 Bypass Vector 1: AI Directly to Upstream Provider (Bypass Found)
- **Violation**: `scripts/gates/plan_gate.py:26-53` imports `from openai import OpenAI` and calls `client.chat.completions.create(model="gpt-4o", ...)` directly.
- **Architectural Impact**: Bypasses `ModelRouter`, `ProviderRegistry`, `CapabilityRouter`, `AITracer`, and OpenRouter development gateway. Furthermore, if `OPENAI_API_KEY` is absent or the API fails, it silently returns `True, []`, skipping the check.

### 5.2 Bypass Vector 2: Raw MCP Protocol Bypass (Clean)
- **Status**: **CLEAN** in modern architecture (`CODE_PROVEN`, `TEST_PROVEN`).
- **Evidence**: `tests/ai/audit/test_s28_m11_final_architecture_audit.py` (Guards 1, 3, 9) rigorously scan the codebase and verify that no creative planning, narrative, skill, recipe, or domain service imports or calls raw MCP servers.

### 5.3 Bypass Vector 3: Arbitrary Shell Execution (`shell=True`) (Clean)
- **Status**: **CLEAN** across the entire repository (`CODE_PROVEN`).
- **Evidence**: Repository-wide AST search confirms zero instances of `shell=True` in production code. All calls execute via `safe_subprocess` (`scripts/security/security.py`) or `asyncio.create_subprocess_exec` using explicit argument lists.

### 5.4 Bypass Vector 4: Direct Filesystem Writes Bypassing Storage CAS (Partial Bypass)
- **Status**: Enforced in product authoring; bypassed in maintenance/legacy scripts.
- **Evidence**: `AuthoringService` and `CanonicalDocumentRepository` strictly enforce CAS locks on video documents. However, legacy scripts (`scripts/maintenance/sync_templates.py`, `scripts/archive/migrate_state.py`) write files directly to disk without revision checking or CAS.

### 5.5 Bypass Vector 5: State Machine Domain Service Bypass (Bypass Found)
- **Violation**: `scripts/pipeline.py:427` directly writes lifecycle state via local `save_state(LifecycleState.AWAITING_REVIEW, [])` rather than invoking `LifecycleService` (`scripts/core/lifecycle_service.py`).
- **Architectural Impact**: Circumvents lifecycle precondition checks and transition validation guards codified in `LifecycleService`.

---

## 6. Production vs. Dev/Test Reachability Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SUBSYSTEM REACHABILITY SUMMARY                        │
├───────────────────────────────┬──────────────────────────┬──────────────────┤
│ Subsystem                     │ Production Reachability  │ Status           │
├───────────────────────────────┼──────────────────────────┼──────────────────┤
│ FastAPI REST Routes (api/)    │ PRODUCTION_REACHABLE     │ Active HTTP      │
│ Pipeline Worker (worker.py)   │ PRODUCTION_REACHABLE     │ Active Daemon    │
│ State Machine (pipeline.py)   │ PRODUCTION_REACHABLE     │ Subprocess       │
│ Authoring Engine (authoring/) │ PRODUCTION_REACHABLE     │ Subprocess IPC   │
│ Remotion Adapter (remotion/)  │ PRODUCTION_REACHABLE     │ Primary Render   │
│ Master Compositor             │ PRODUCTION_REACHABLE     │ Primary Render   │
│ CapabilityRouter              │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ ToolGateway                   │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ ModelRouter                   │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ OpenRouterProvider           │ DEV_ONLY                 │ Benchmark Only   │
│ LocalSTTProvider              │ DEV_ONLY                 │ Benchmark Only   │
│ FastMCP Compatibility Server  │ COMPATIBILITY_ONLY       │ External Tools   │
└───────────────────────────────┴──────────────────────────┴──────────────────┤
```

Neither `CapabilityRouter`, `ToolGateway`, nor `ModelRouter` receive real customer traffic from `api/` or `scripts/pipeline.py`. They operate as an active development platform exercised by unit, integration, and evaluation suites (`tests/ai/`).

---

## 7. File & Symbol Evidence Index

| File Path | Symbol / Function | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `documentation/s28m/CAPABILITY_CATALOG.json` | `capabilities` array | 1-43 | Authoritative 43 capability definitions | `CODE_PROVEN` |
| `ai/capabilities/catalog.py` | `CapabilityCatalog` | 34-110 | In-memory catalog loader and lookup | `CODE_PROVEN` |
| `ai/routing/capability_router.py` | `CapabilityRouter` | 69-140 | Routes MODEL $\to$ ModelRouter, TOOL $\to$ Gateway | `CODE_PROVEN` |
| `ai/tools/gateway.py` | `ToolGateway.execute` | 258-525 | Authoritative 15-stage execution pipeline | `CODE_PROVEN` |
| `ai/tools/gateway.py` | `validate_safe_url` | 79-115 | SSRF and network egress validation | `CODE_PROVEN` |
| `ai/tools/adapters/mcp.py` | `STATIC_CAPABILITY_BINDINGS` | 70-91 | Hardened static MCP bindings map | `CODE_PROVEN` |
| `ai/tools/adapters/mcp.py` | Blocked `CONCATENATE_VIDEOS`| 83 | Explicit security block for shell injection | `CODE_PROVEN` |
| `ai/mcp/compatibility/server.py` | `CompatibilityMCPServer` | 35-110 | FastMCP wrapper delegating to ToolGateway | `CODE_PROVEN` |
| `tests/ai/audit/test_s28_m11_final_architecture_audit.py`| `TestS28M11ArchitectureAudit` | 43-180 | AST architecture guard test suite | `TEST_PROVEN` |
| `scripts/gates/plan_gate.py` | `ask_llm_judge` | 16-64 | Ad-hoc OpenAI client bypass | `CODE_PROVEN` |
| `ai/providers/openrouter.py` | `OpenRouterProvider` | 57-70 | Development-only OpenRouter provider | `CODE_PROVEN` |
| `scripts/security/security.py` | `safe_subprocess` | 15-50 | Hermetic subprocess runner (zero shell=True) | `CODE_PROVEN` |

---

## 8. Strategic Remediation Direction

1. **Eliminate `plan_gate.py` Direct Provider Bypass**: Refactor `ask_llm_judge` in `scripts/gates/plan_gate.py` to route through `CapabilityRouter` using a typed `CRITIQUE_PLAN` capability, removing direct `OpenAI` client instantiation and unifying telemetry with `AITracer`.
2. **Expose Capability Gateway to API**: Wire `ToolGateway` directly into FastAPI under a managed administrative router (e.g. `POST /api/v1/capabilities/execute`), allowing authenticated clients to invoke media tools securely.
3. **Graduate Modern Concatenation**: Replace the blocked legacy `CONCATENATE_VIDEOS` MCP tool with the hardened, memory-safe `LocalMediaProcessingService.concatenate()` in `ai/media_processing/`.
