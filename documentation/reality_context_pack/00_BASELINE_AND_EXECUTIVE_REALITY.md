# Baseline & Executive Architectural Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Executive baseline, repository health, reachable vs disconnected architecture map, high-risk operational and architectural zones, top unknowns, and executive summary of mandatory checks A through T.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Repository Reality Overview

### 1.1 The Dual-Reality Architecture
An exhaustive software and systems architecture investigation of the repository at commit `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` on branch `main` reveals a profound architectural bifurcation:

1. **The Active Deterministic Video Engine (Generation S25/S26 + S28-R Live Authoring)**:
   - A fully functional, production-hardened SaaS backend comprising FastAPI (`api/`), PostgreSQL/SQLite storage engines with Compare-And-Swap (CAS) locking (`scripts/core/`), an asynchronous polling worker daemon (`scripts/core/worker.py`), a deterministic gate-driven pipeline state machine (`scripts/pipeline.py`, `scripts/gates/`), a TypeScript abstract syntax tree (AST) document mutation engine (`authoring/`, `contracts/`), and a multi-stage video rendering pipeline (`scripts/render_project.py`, `planner/`, `remotion-app/`).
   - This system processes structured HTTP mutations, schedules durable runs via SQLite/PostgreSQL `runs` tables, executes 10 sequential quality and verification gates on disk workspaces, and renders video compositions via Remotion and Master Compositor.
   - **Reachability Status**: `RUNTIME_REACHABILITY_PROVEN` and `CODE_PROVEN`.

2. **The Disconnected Creative Intelligence Subsystem (Generation S27/S28)**:
   - An extensive, sophisticated AI platform subsystem located in `ai/` (comprising 270 test files and thousands of lines of Python code). It implements context assembly (`ai/context/builder.py`), model routing (`ai/routing/router.py`), capability cataloging and execution gateways (`ai/capabilities/`, `ai/tools/gateway.py`), memory indexing (`ai/memory/service.py`), creative planning (`ai/planning/creative_planner.py`), narrative generation (`ai/narrative/planner.py`), and taste rule evaluation (`ai/taste/engine.py`).
   - **Critical Reality Finding**: This entire AI platform subsystem has **ZERO active production wiring** to the primary HTTP application (`api/main.py`), the background worker daemon (`scripts/core/worker.py`), or the pipeline orchestrator (`scripts/pipeline.py`). Grep across `api/` and `scripts/` reveals exactly zero imports of the `ai` module (`api/`: 0 imports; `scripts/`: 0 imports).
   - Furthermore, required GitHub Actions CI (`.github/workflows/remediation-ci.yml`) completely omits `tests/ai`, running 0 of the 270 AI test files.
   - **Reachability Status**: `UNREACHABLE_FROM_PRODUCT` [`CODE_PROVEN`].

```
========================================================================================================
                                     ARCHITECTURAL REALITY MAP
========================================================================================================

    [ CLIENTS: Browser / Studio / Automation / CLI ]
                      |
                      | HTTP REST (34 Endpoints)
                      v
    +-------------------------------------------------------------+
    |                   api/main.py (FastAPI)                     |
    |  - Projects, Runs, Assets, Artifacts, Outputs, Gates        |  ACTIVE PRODUCT
    |  - S28-R Live Authoring (/intent, /mutate, /document)       |  RUNTIME
    +-------------------------------------------------------------+  (Fully Proven)
           |                                     |
           | Async Enqueue (RunRecord)           | Stdin/Stdout IPC (safe_subprocess)
           v                                     v
    +-----------------------------+       +------------------------------------+
    |  data/runs.db (SQLite/SQL)  |       | scripts/execute_authoring_mutation |
    +-----------------------------+       +------------------------------------+
           |                                     |
           | Polling CAS Claim                   | Delegates to UnifiedAuthoringSession
           v                                     v
    +-----------------------------+       +------------------------------------+
    |  scripts/core/worker.py     |       | authoring/ & contracts/ (TS)       |
    |  (PipelineWorker Daemon)    |       | (Deterministic AST Mutations)      |
    +-----------------------------+       +------------------------------------+
           |
           | Spawns Subprocess (AGY_IS_MANAGED=1)
           v
    +-------------------------------------------------------------+
    |               scripts/pipeline.py (Orchestrator)            |
    |  Stages: DRAFT -> ASSETS_READY -> PLAN_READY ->             |
    |          BLUEPRINT_READY -> MATERIALIZED -> PROBE_PASSED -> |
    |          AWAITING_REVIEW -> REVIEW_APPROVED ->              |
    |          RENDERED -> FINAL_QC_PASSED -> COMPLETE            |
    +-------------------------------------------------------------+
           |
           | Executes Scripts
           v
    +-----------------------------+       +------------------------------------+
    | scripts/gates/ (8 Gates)    |       | scripts/render_project.py          |
    | asset, plan, taste,         |       |  Priority 1: render_via_planner.ts |
    | blueprint, motion, code,    | ----> |  Priority 2: render_via_adapter.ts |
    | probe_qc, final_qc          |       |  Priority 3: npx remotion render   |
    +-----------------------------+       +------------------------------------+
                                                         |
                                                         v
                                          +------------------------------------+
                                          | remotion-app/ & templates/ (105)   |
                                          | Produces: out.mp4 & Assets         |
                                          +------------------------------------+

 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 [ DISCONNECTED AIR-GAPPED SUBSYSTEM: ai/ (S27/S28 Creative Intelligence Platform) ]
  * Zero Production Callers in api/ or scripts/
  * Zero Invocations in GitHub Actions Required CI (.github/workflows/remediation-ci.yml)
  * Exercised Exclusively via In-Memory Unit/Integration Tests (tests/ai/) & Offline Scripts

   +-------------------------------------------------------------------------------------------------+
   |  ContextBuilder | KnowledgeRouter | SkillRegistry | RecipeRegistry | ModelRouter               |
   |  CapabilityRouter | ToolGateway | CreativePlanner | NarrativePlanner | TasteEngine | MemoryService |
   +-------------------------------------------------------------------------------------------------+
========================================================================================================
```

### 1.2 Quantitative Baseline Metrics
- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` [`CODE_PROVEN`]
- **Working Tree State**: Clean (0 modified tracked files; only `.agents/teamwork/` untracked metadata) [`CODE_PROVEN`]
- **Primary Languages**: Python 3.12 (`pyproject.toml:5`), TypeScript / React 19 (`package.json:34-36`), Shell
- **Top-Level Directories**: 36 total directories classified in Report 01 [`CODE_PROVEN`]
- **Total Test Files**: 510+ test files (Python: 461 test files; TypeScript/Remotion: 49 test files) [`TEST_PROVEN`]
- **Total AI Tests**: 270 test files located in `tests/ai/` (100% excluded from GitHub Actions CI) [`CI_PROVEN`, `CODE_PROVEN`]
- **Mounted HTTP Endpoints**: 34 distinct REST endpoints across 12 router modules in `api/main.py:57-69` [`CODE_PROVEN`]
- **Canonical Video Templates**: 105 TSX React components across `templates/elements/`, `templates/scenes/`, `templates/effects/`, and `remotion-app/src/templates/` [`CODE_PROVEN`]
- **Predefined Recipes**: 18 JSON video recipes in `recipes/` [`CODE_PROVEN`]
- **Cataloged Capabilities**: 32 distinct system capabilities registered in `ai/capabilities/catalog.py` [`CODE_PROVEN`]

---

## 2. Primary Entrypoints Reality Map

Every entrypoint in the repository was classified by entrypoint category, caller, callee, execution model, and verified reachability.

| Entrypoint Identifier | File & Symbol | Category | Caller / Protocol | Downstream Callee / Subsystems | Verified Reachability | Evidence Standard |
|---|---|---|---|---|---|---|
| **API Web Application** | `api/main.py:app` (lines 45-70) | Production Runtime | Uvicorn / ASGI (`uvicorn api.main:app`) | Mounts 12 router modules; executes startup environment audit (`EnvironmentPolicyAuditor.audit_environment`) | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/main.py:28-70`) |
| **Run Creation Endpoint** | `api/routers/runs.py:create_run` (line 23) | Production Runtime | HTTP `POST /projects/{id}/runs` | `RunService.create_run()` -> `RunRepository.create_run()` inserting `QUEUED` record into SQLite/MySQL `runs` table | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/runs.py:23-56`) |
| **Live Authoring Mutation** | `api/routers/authoring.py:apply_mutation` (line 65) | Production Runtime | HTTP `POST /projects/{id}/mutate` | `AuthoringService.execute_authoring()` -> subprocess `scripts/execute_authoring_mutation.ts` -> `UnifiedAuthoringSession` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/authoring.py:65-90`) |
| **Typed Intent Translation** | `api/routers/authoring.py:apply_intent` (line 104) | Production Runtime | HTTP `POST /projects/{id}/intent` | `AuthoringService` -> `execute_authoring_mutation.ts` -> `authoring/intent-planner.ts` (Validates `AuthoringIntentSchema`) | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/authoring.py:104-131`) |
| **Asset Ingestion Endpoint** | `api/routers/assets.py:upload_asset` (line 35) | Production Runtime | HTTP `POST /projects/{id}/assets` | `AssetService.upload_asset()` -> writes to `projects/{id}/assets/ready/` -> uploads to `StorageService` -> updates `02_asset_manifest.json` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/assets.py:35-80`) |
| **Media Stream Output** | `api/routers/outputs.py:get_output_media` (line 30) | Production Runtime | HTTP `GET /projects/{id}/outputs/{id}` | `OutputService.stream_media()` -> reads `projects/{id}/out.mp4` supporting HTTP 206 Partial Content byte ranges | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/outputs.py:30-75`) |
| **Worker Background Daemon** | `scripts/worker.py:main` / `scripts/core/worker.py:PipelineWorker.run_loop` (lines 180-360) | Production Runtime | Systemd / Docker CLI (`python scripts/worker.py`) | Polls `RunRepository.claim_next_run()` using atomic CAS lease -> spawns subprocess `python scripts/pipeline.py <project_id>` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`scripts/core/worker.py:180-360`) |
| **Pipeline Orchestrator** | `scripts/pipeline.py:main` (lines 221-520) | Production Runtime | Invoked by Worker or CLI (`python scripts/pipeline.py <project_id>`) | Sequentially executes gates (`scripts/gates/*`), `materialize_project.py`, `probe_qc.py`, `ReviewService`, `render_project.py`, `final_qc.py` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`scripts/pipeline.py:221-520`) |
| **Project Renderer** | `scripts/render_project.py:main` (lines 120-220) | Production Runtime | Invoked by `pipeline.py` at `REVIEW_APPROVED` | Asserts `assert_render_authorized()` -> executes `render_via_planner.ts` -> falls back to `render_via_adapter.ts` -> falls back to `remotion render` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`scripts/render_project.py:120-220`) |
| **Interactive Studio Preview** | `scripts/open_studio.py:main` | Development / Authoring | Developer CLI (`python scripts/open_studio.py <project_id>`) | Verifies `.studio_unlocked` mechanical lock -> launches `npx remotion studio` on port 3000 with environment overrides | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`scripts/open_studio.py:1-60`) |
| **Candidate Review API** | `api/routers/candidate_reviews.py:open_review` (line 35) | Production Governance | HTTP `POST /candidates/{id}/reviews/open` | `CandidateReviewService` -> evaluates template governance lifecycle in SQLite/PostgreSQL | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/candidate_reviews.py:35-70`) |
| **Candidate Promotion API** | `api/routers/candidate_promotions.py:promote_candidate` (line 30) | Production Governance | HTTP `POST /candidates/{id}/promote` | `CandidatePromotionService` -> `TemplateRegistryPublisher.publish()` -> modifies `registry/template-registry-data.json` | `RUNTIME_REACHABILITY_PROVEN` | `CODE_PROVEN` (`api/routers/candidate_promotions.py:30-80`) |
| **FastMCP Compatibility Server** | `ai/mcp/compatibility/server.py:create_compatibility_mcp_app` | Compatibility Boundary | FastMCP CLI / Subprocess | Maps legacy MCP tool requests into `ToolGateway.execute()` | `COMPATIBILITY_ONLY` | `CODE_PROVEN` (`ai/mcp/compatibility/server.py:1-50`) |
| **Plugin MCP Servers** | `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/*` | Legacy Compatibility | External Agent MCP clients | `audio-tools-mcp`, `media-sources-mcp`, `video-tools-mcp`, `image-tools-mcp`, `common-tools-mcp`, `ffmpeg-mcp-server` | `DEV_ONLY` / `COMPATIBILITY_ONLY` | `CODE_PROVEN` (`.agents/.../mcp_config.json`) |
| **Offline Creative Benchmarks** | `scripts/run_creative_e2e.py:main` | Test / Diagnostic | Manual CLI (`python scripts/run_creative_e2e.py`) | Directly instantiates `CreativePlanner`, `NarrativePlanner`, `BlueprintCompiler` across 42 matrix combinations | `TEST_ONLY` | `CODE_PROVEN` (`scripts/run_creative_e2e.py:1-95`) |
| **OpenRouter Smoke Runner** | `scripts/smoke_openrouter.py:main` | Test / Diagnostic | Manual CLI (`python scripts/smoke_openrouter.py`) | Standalone LLM integration harness; logs traces to `data/openrouter_smoke_traces.db` | `TEST_ONLY` | `CODE_PROVEN` (`scripts/smoke_openrouter.py:1-120`) |
| **Strict CI E2E Runner** | `tests/e2e/true_e2e_suite.py:main` | CI / Verification | Invoked by GitHub CI `strict-e2e` job | Synthesizes project fixtures using `create_canonical_e2e_project` -> executes `python scripts/pipeline.py` CLI | `TEST_ONLY` / `CI_PROVEN` | `CODE_PROVEN` (`tests/e2e/true_e2e_suite.py:32-75`) |

---

## 3. Subsystem Reachability & Reality Topology Map

### 3.1 Proven Reachable Subsystems in Production Runtime
The following subsystems have complete, verified, executable call chains initiating from public production entrypoints:

1. **HTTP Routing & API Security (`api/`)**:
   - `FastAPI` instance with `DynamicCORSMiddleware` (`api/main.py:49-55`).
   - `EnvironmentPolicyAuditor` enforcing variable safety at lifespan boot (`api/main.py:30-40`).
   - Tenant authentication and authorization context via `TenantContext` (`api/core/dependencies.py`).
   - Exception handlers mapping domain conflicts (`StateConflictError`, `LifecycleError`) to HTTP 409/422/500 (`api/main.py:71-75`).

2. **Run Lifecycle & Durable Queue Engine (`scripts/core/run_repository.py`, `api/services/run_service.py`)**:
   - `RunService.create_run()` creates durable `RunRecord` entries with SHA-256 idempotency hashing.
   - `RunRepository` executes transactional atomic lease acquisition (`claim_next_run`) with TTL timeouts and status transitions (`QUEUED -> RUN_STARTED -> SUCCEEDED | FAILED`).

3. **Pipeline Worker Daemon (`scripts/core/worker.py`)**:
   - Polling loop claiming runs from `RunRepository`.
   - Spawns isolated subprocess execution of `scripts/pipeline.py` with process-group separation (`start_new_session=True`).
   - Heartbeat thread renewing database leases while pipeline runs execute (`scripts/core/worker.py:230-245`).

4. **Pipeline Orchestrator & Deterministic Gate Engine (`scripts/pipeline.py`, `scripts/gates/*`)**:
   - Enforces strict unidirectional lifecycle state machine across 10 stages (`scripts/pipeline.py:356-512`).
   - Gates executed in order:
     - `gates/asset_gate.py`: Validates asset directory structure and manifest presence.
     - `gates/plan_gate.py`: Validates `master_plan.md` formatting and duration constraints.
     - `gates/taste_gate.py`: Verifies taste rules against `master_plan.md`.
     - `gates/validate_blueprint.py`: Enforces JSON schema validity for `05_blueprint.json`.
     - `gates/motion_validator.py`: Analyzes animation timing curves and layout metrics.
     - `gates/code_template_gate.py`: Verifies template parameters match registered contracts.
     - `generators/materialize_project.py`: Generates Remotion public directory symlinks and `media_map.json`.
     - `gates/probe_qc.py`: Generates contact sheet still frames via Remotion and unlocks `.studio_unlocked`.
     - `gates/final_qc.py`: Validates output `out.mp4` video duration, container format, and audio LUFS levels.

5. **Human Review Governance Subsystem (`scripts/core/review_service.py`)**:
   - Generates immutable snapshot `ReviewBundle` capturing current blueprint and asset hashes (`ReviewService.create_review_bundle()`).
   - Prevents unauthorized rendering by checking `assert_render_authorized(proj_dir)` before `render_project.py` can execute.
   - Supports dual approval: formal `ReviewService.approve()` decision record or local `.studio_approved` marker file (`scripts/pipeline.py:449-465`).

6. **S28-R Live Authoring Subsystem (`authoring/`, `contracts/`, `api/services/authoring_service.py`)**:
   - Dispatches HTTP `/intent`, `/mutate`, and `/batch` requests from `api/routers/authoring.py`.
   - Executes `scripts/execute_authoring_mutation.ts` via safe Node subprocess IPC.
   - Validates typed AST mutations using Zod contracts (`contracts/authoring.ts`).
   - Delegates mutation logic to `UnifiedAuthoringSession` (`authoring/unified-authoring-session.ts`).
   - Persists updated canonical `BlueprintV2` / `VideoDocument` into `CanonicalDocumentRepository` with CAS revision checks.

7. **Storage & Multi-Backend Object Storage Subsystem (`scripts/core/storage/storage_service.py`)**:
   - Abstract `StorageService` interface backed by `LocalStorageBackend` or `S3CompatibleStorageBackend`.
   - Enforces strict scoped path keys: `workspaces/{ws_id}/projects/{proj_id}/{category}/{item_id}/{filename}`.
   - Used actively by `AssetService`, `CanonicalDocumentRepository`, and `OutputService`.

8. **Multi-Engine Renderer & Master Compositor (`scripts/render_project.py`, `planner/`, `compositor/`)**:
   - `RenderPlanner` decomposes canonical blueprint into render graph DAG nodes.
   - Dispatches rendering to `RemotionRendererAdapter` or `CanvasRendererAdapter`.
   - Passes rendered video/audio clips to `MasterCompositor` (`compositor/master-compositor.ts`) for normalization and final multiplexing into `out.mp4`.

---

### 3.2 Disconnected / Unreachable Subsystems (The Air-Gapped AI Platform)
The following 14 core subsystems in `ai/` are **completely unreachable from the production runtime**:

| Subsystem Name | Source File | Registered / Intended Purpose | Production Callers | Why Unreachable | Evidence Citation |
|---|---|---|---|---|---|
| `ContextBuilder` | `ai/context/builder.py:47` | Assembles prompt context budgets, policies, project facts, memory, and knowledge | **NONE** (`0 callers in api/ & scripts/`) | Never imported or instantiated outside `tests/ai/context/` | `ai/context/builder.py:47-91` [`CODE_PROVEN`] |
| `KnowledgeRouter` | `ai/knowledge/router.py:34` | Routes queries across indexed knowledge documents and playbooks | **NONE** (`0 callers in api/ & scripts/`) | Never invoked during API lifespan or pipeline stages | `ai/knowledge/router.py:34-68` [`CODE_PROVEN`] |
| `KnowledgeRegistry` | `ai/knowledge/registry.py:34` | In-memory registry of validated `KnowledgeDescriptor` objects | **NONE** (`0 callers in api/ & scripts/`) | Initialized only within offline eval tests | `ai/knowledge/registry.py:34-100` [`CODE_PROVEN`] |
| `SkillRegistry` | `ai/skills/registry.py:34` | Registry of active video generation skills (remocn, snapcn, etc.) | **NONE** (`0 callers in api/ & scripts/`) | No HTTP or worker endpoint queries skill registry | `ai/skills/registry.py:34-100` [`CODE_PROVEN`] |
| `SkillLoader` | `ai/skills/loader.py:62` | Loads skills from typed code and markdown frontmatter | **NONE** (`0 callers in api/ & scripts/`) | Invoked only in unit tests | `ai/skills/loader.py:62-120` [`CODE_PROVEN`] |
| `RecipeRegistry` | `ai/recipes/registry.py:99` | Globs and loads 18 recipes from `recipes/*.json` | **NONE** (`0 callers in api/ & scripts/`) | Production pipeline does not query recipes | `ai/recipes/registry.py:99-150` [`CODE_PROVEN`] |
| `ModelRouter` | `ai/routing/router.py:67` | Deterministically ranks and selects LLM providers and models | **NONE** (`0 callers in api/ & scripts/`) | Production pipeline makes zero LLM calls | `ai/routing/router.py:67-130` [`CODE_PROVEN`] |
| `ProviderRegistry` | `ai/providers/registry.py:32` | Registry of configured AI providers (OpenAI, Anthropic, Fal, etc.) | **NONE** (`0 callers in api/ & scripts/`) | Zero calls from API or worker | `ai/providers/registry.py:32-94` [`CODE_PROVEN`] |
| `CapabilityRouter` | `ai/routing/capability_router.py:69` | Central capability router dispatching model vs tool execution | **NONE** (`0 callers in api/ & scripts/`) | No production service calls `dispatch_capability()` | `ai/routing/capability_router.py:69-120` [`CODE_PROVEN`] |
| `ToolGateway` | `ai/tools/gateway.py:231` | 15-stage execution pipeline enforcing idempotency and safety for tools | **NONE** (`0 callers in api/ & scripts/`) | Only invoked in `tests/ai/tools/` | `ai/tools/gateway.py:231-310` [`CODE_PROVEN`] |
| `ToolRegistry` | `ai/tools/registry.py:44` | In-memory registry of native tool implementations | **NONE** (`0 callers in api/ & scripts/`) | Uncalled by production services | `ai/tools/registry.py:44-110` [`CODE_PROVEN`] |
| `CreativePlanner` | `ai/planning/creative_planner.py:58` | Plans multi-scene video structure from `CreativeBrief` | **NONE** (`0 callers in api/ & scripts/`) | Pipeline requires `master_plan.md` to pre-exist | `ai/planning/creative_planner.py:58-115` [`CODE_PROVEN`] |
| `NarrativePlanner` | `ai/narrative/planner.py:35` | Generates narrative story arcs, archetypes, and script beats | **NONE** (`0 callers in api/ & scripts/`) | Uncalled by production services | `ai/narrative/planner.py:35-80` [`CODE_PROVEN`] |
| `TasteEngine` | `ai/taste/engine.py:26` | Evaluates AI creative proposals against typography and pacing rules | **NONE** (`0 callers in api/ & scripts/`) | Pipeline uses regex heuristics in `gates/taste_gate.py` | `ai/taste/engine.py:26-85` [`CODE_PROVEN`] |
| `MemoryService` | `ai/memory/service.py:49` | Stores and retrieves episodic and project memory via embeddings | **NONE** (`0 callers in api/ & scripts/`) | Tested only with in-memory SQLite mocks | `ai/memory/service.py:49-115` [`CODE_PROVEN`] |
| `BlueprintCompiler` | `ai/planning/compiler.py:62` | Compiles `CreativePlan` into canonical `VideoDocument` / `BlueprintV2` | **NONE** (`0 callers in api/ & scripts/`) | Authoring engine mutates AST directly without planner | `ai/planning/compiler.py:62-443` [`CODE_PROVEN`] |

---

## 4. Architectural Divergence Analysis: The 4 Quadrants

The repository exhibits significant divergence across four architectural dimensions:
- **Quadrant 1 (Intended Architecture)**: Defined by high-level architecture decision records, PRDs, and vision documents (`ARCHITECTURE_TRUTH.md`, S28-M specs).
- **Quadrant 2 (Documented / Agent Architecture)**: Defined by developer playbooks, SOPs, and agent rules (`.agents/AGENTS.md`, `references/`).
- **Quadrant 3 (Tested Architecture)**: Defined by what is actively executed and enforced in automated test suites and CI.
- **Quadrant 4 (Reachable Production Architecture)**: Defined strictly by what executable code can be invoked by real production entrypoints.

### 4.1 Detailed Divergence Matrix

| Architectural Subsystem | Quadrant 1: Intended | Quadrant 2: Documented / Agent Rules | Quadrant 3: Tested | Quadrant 4: Reachable Runtime | Divergence Classification & Impact |
|---|---|---|---|---|---|
| **AI Creative Video Generation** | Natural language brief accepted via API; automatically plans narrative, selects recipes, routes models, and generates video. | Agents instructed to coordinate AI models and follow SOPs in `references/`. | Tested heavily via synthetic in-memory unit tests (`tests/ai/e2e/`), but **omitted from GitHub Actions CI**. | **NON-EXISTENT**. Zero API endpoints accept prompts. Pipeline requires pre-written `master_plan.md` on disk. | **CRITICAL ARCHITECTURAL DIVERGENCE**. AI platform is completely disconnected from SaaS production runtime. |
| **CI Governance & Test Enforcement** | All code changes gated by comprehensive automated test coverage in required CI. | All 510+ tests must pass before merging. | GitHub CI runs 240 tests (core, gates, contracts, fault_injection). Local script runs 490 tests (includes `tests/ai`). | CI completely ignores `tests/ai` (270 files) and 36 S28-R Remotion tests. | **HIGH GOVERNANCE DIVERGENCE**. Broken CI mirror; developers believe `tests/ai` is gated when it is not. |
| **Template Authority** | `registry/template-registry-data.json` is single machine-readable authority. | Agent rules cite `ground-truth/template_catalog.json` and `TEMPLATE_INDEX.md`. | Verified by `scripts/validators/check_ground_truth_sync.py --check` in CI. | `registry/template-registry.tsx` is loaded at runtime by Remotion and Authoring engine. | **MODERATE METADATA DIVERGENCE**. Documentation treats derivative catalog as authority; code treats registry as authority. |
| **Renderer Engine Independence** | Engine-neutral renderer abstraction allowing seamless switching between Remotion, Canvas, and HTML5. | Documentation describes Remotion and Canvas as interchangeable peer adapters. | Contract tests verify `RendererAdapter` interface for both Remotion and Canvas. | All 105 canonical templates are Remotion TSX components. Fallback directly calls `npx remotion render`. Probe QC calls `remotion still`. | **SIGNIFICANT DIVERGENCE**. Architectural abstraction exists, but runtime is 100% hard-locked to Remotion. |
| **Authoring Intent API (`/intent`)** | Natural-language intent translator taking human requests and applying smart edits. | Documented as an intent-based authoring bridge for live video manipulation. | Tested in `tests/remotion/` using pre-structured JSON fixtures. | Strictly accepts Zod-validated `AuthoringRequestSchema` with discriminated union mutations. Rejects natural text. | **SUBSTANTIAL CONTRACT DIVERGENCE**. Name implies NLP/AI, but runtime is 100% deterministic AST compiler. |
| **Tool Execution & MCP** | Capabilities execute through unified 15-stage `ToolGateway` without raw MCP access. | Agents instructed to call tools via approved MCP servers (`audio-tools-mcp`, etc.). | AST guards verify internal AI code has 0 raw MCP dependencies. | FastMCP server exists for external compatibility, but internal capability requests never reach `ToolGateway` in production. | **DUAL-ECOSYSTEM DIVERGENCE**. Plugin MCP configs have hardcoded Windows paths; modern FastMCP is isolated. |

---

## 5. High-Risk Operational & Architectural Areas

### 5.1 High-Risk Zone 1: Complete Exclusion of `tests/ai` from GitHub Actions CI
- **Nature of Risk**: Severe regression blindness.
- **Evidence**: `.github/workflows/remediation-ci.yml:125-126` explicitly passes test directories to pytest and omits `tests/ai`.
- **Impact**: Any change made to the repository can break any of the 270 test files in `tests/ai` without causing CI failure. A developer or pull request can break the entire AI subsystem without detection.

### 5.2 High-Risk Zone 2: Disconnected AI Subsystem Masks Missing SaaS Functionality
- **Nature of Risk**: Illusion of completion.
- **Evidence**: `api/main.py:57-69` mounts 12 routers, none of which connect to `ai/`. Grep across `api/` and `scripts/` yields zero imports of `ai`.
- **Impact**: The repository cannot fulfill the end-to-end user promise of "AI-driven video generation from text" via its HTTP API. External users cannot submit a prompt and receive a video without manually creating `master_plan.md` and `05_blueprint.json` on disk first.

### 5.3 High-Risk Zone 3: Remotion Lock-In Despite Abstraction Layer
- **Nature of Risk**: Technical debt and vendor lock-in.
- **Evidence**: While `contracts/renderer.ts` and `planner/render-planner.ts` define an engine-agnostic DAG, all 105 templates in `templates/` and `remotion-app/src/templates/` directly import React and Remotion hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`). Furthermore, `scripts/render_project.py:177` falls back to `npx remotion render`, `scripts/gates/probe_qc.py` invokes `npx remotion still`, and `scripts/open_studio.py` invokes `npx remotion studio`.
- **Impact**: The system cannot render videos using the Canvas renderer without rewriting all 105 templates.

### 5.4 High-Risk Zone 4: Dual State Tracking and Concurrency Collisions
- **Nature of Risk**: Inconsistent state and data corruption.
- **Evidence**: Project lifecycle state is tracked simultaneously in two competing locations:
  1. The filesystem file `projects/{project_id}/.pipeline_state.json` managed by `StateStore` (`scripts/core/state_store.py`).
  2. The SQL database table `project_states` with CAS revision numbers managed by `DatabaseEngine` (`scripts/core/database.py:96-120`).
- **Impact**: If a pipeline worker crashes or if concurrent updates occur between direct filesystem scripts and HTTP API requests, the database revision and the disk file become desynchronized, leading to `StateConflictError` (HTTP 409) or lock timeouts.

### 5.5 High-Risk Zone 5: Legacy Plugin MCP Server Path Incompatibility
- **Nature of Risk**: Immediate execution failure on non-Windows environments.
- **Evidence**: In `.agents/plugins/super-video-maker-plugin/mcp_config.json`, the command arguments for `audio-tools-mcp`, `video-tools-mcp`, and `media-sources-mcp` contain hardcoded Windows filepaths (e.g., `C:/video/clean-video-workspace/...`).
- **Impact**: Any agent or tool client attempting to spawn these plugin MCP servers on a Linux or macOS host will fail immediately with `FileNotFoundError`.

### 5.6 High-Risk Zone 6: Direct Provider Execution Blockers
- **Nature of Risk**: Intentional runtime blockage without production fallback.
- **Evidence**: In `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py:60-85`, the code raises an intentional `RuntimeError("DIRECT PROVIDER EXECUTION BLOCKED... Use canonical S27 speech capability adapters and ModelRouter")`.
- **Impact**: Legacy tools cannot execute directly, but because the production API does not route to `ModelRouter`, speech generation cannot be performed via either path in production.

---

## 6. Top Unknowns & Unproven Claims

| ID | Domain | Unproven Claim / Unknown Question | Current Repository Evidence | Why Unproven / Risk | Required Follow-Up Probe |
|---|---|---|---|---|---|
| **UNK-001** | Production Architecture | How did the authors intend `POST /projects/{id}/runs` to connect to `CreativePlanner`? | `api/routers/runs.py` and `scripts/pipeline.py` contain zero AI references. | It is unknown whether an intermediate "compiler" worker was planned or if AI generation was intended to run strictly as an offline CLI step. | Inspect feature branches or author PR discussions regarding `feature/s27-ai-platform`. |
| **UNK-002** | Storage & Scalability | Does SQLite concurrency hold up under high worker concurrency in production? | SQLite WAL mode is configured in `scripts/core/database.py:40`, and PostgreSQL is supported via environment variable. | Under high concurrency with 10+ worker threads, SQLite busy timeouts may trigger CAS retry exhaustion. | Execute high-concurrency worker load benchmark using `scripts/testing/s28_r15_soak_and_load_runner.py`. |
| **UNK-003** | Multi-Engine Rendering | Can the Canvas renderer (`canvas/canvas-renderer-adapter.ts`) actually render canonical templates? | Unit tests test dummy canvas nodes. Canonical templates are all React TSX components. | It is unproven whether any non-trivial canonical template can execute in Canvas without React. | Run `scripts/render_via_planner.ts` with canvas engine flag against a canonical scene. |
| **UNK-004** | Vitest Test Suite | Why are 36 of 49 Remotion tests in `tests/remotion/` excluded from `npm run test`? | Root `package.json:10` defines `test: vitest run tests/contracts`. `vitest.config.ts` targets only `tests/contracts`. | S28-R authoring and preview tests are never executed in CI or default npm test. | Update `vitest.config.ts` or add dedicated npm test script and measure pass rate. |
| **UNK-005** | Real Provider Latency | What is the real-world latency and cost of running the full 42-combination creative matrix? | Offline script `scripts/run_creative_e2e.py` runs with mock providers by default. | Real API calls against OpenRouter/Fal have unknown cost and failure rates. | Run `scripts/smoke_openrouter.py` with valid credentials under budget cap. |

---

## 7. Executive Summary of Answers to Mandatory Checks (A through T)

Below is the authoritative executive summary answering all 20 mandatory check questions (A through T) with direct answers, evidence tags, and exact code citations:

| Check | Mandatory Question | Direct Answer | Evidence Standard | Concrete Code / CI Citation | Impact Summary |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **A** | Does required GitHub CI run `tests/ai` in its entirety? | **NO** | `CI_PROVEN` & `CODE_PROVEN` | `.github/workflows/remediation-ci.yml:125-126` explicitly lists tested folders and omits `tests/ai`. Grep for `tests/ai` across `.github/` yields 0 matches. | 270 AI test files are completely unverified in CI, risking silent regressions. |
| **B** | Does local `run_required_checks.sh` match actual GitHub required checks? | **NO** | `CI_PROVEN` & `CODE_PROVEN` | `scripts/ci/run_required_checks.sh:50` runs `tests/ai` and contract generators, but omits `tests/fault_injection`, Ruff linting, Trivy CVE scanning, and Docker acceptance tests. | Local script creates a false sense of alignment with GitHub Actions CI. |
| **C** | What is the exact runtime path for `POST /projects/{id}/runs`? | **Documented in detail** | `CODE_PROVEN` & `RUNTIME_REACHABILITY_PROVEN` | `api/routers/runs.py:23-56` -> `RunService.create_run()` -> SQLite `runs` table (`QUEUED`) -> worker `scripts/core/worker.py:289` claims via CAS lease -> spawns `python scripts/pipeline.py <id>` -> 10 stages -> `render_project.py` -> `final_qc.py` -> `RunRepository.finish_run()`. | Asynchronous durable run processing completely decoupled from AI. |
| **D** | Does `POST /projects/{id}/runs` reach Creative Intelligence? | **NO** | `CODE_PROVEN` | Zero calls to `ai/`, `CreativePlanner`, `NarrativePlanner`, or models exist in `runs.py`, `RunService`, `worker.py`, or `pipeline.py`. Pre-authored `master_plan.md` and `05_blueprint.json` are strictly required on disk (`pipeline.py:371, 381`). | The execution pipeline only validates and renders existing files; it generates no creative content. |
| **E** | Does the Production API have a natural-language AI generation entrypoint? | **NO** | `CODE_PROVEN` | All 34 endpoints in `api/main.py:57-69` operate strictly on structured DTOs (`RunCreateRequest`, `AuthoringRequest`, etc.). Zero endpoints accept text prompts or briefs. | System cannot be invoked by end users via natural language through HTTP API. |
| **F** | Does `/intent` accept natural language or only pre-structured typed intents? | **Only pre-structured typed intents** | `CODE_PROVEN` | `api/routers/authoring.py:104-131` delegates to `scripts/execute_authoring_mutation.ts:206`, which validates against Zod schema `AuthoringRequestSchema` from `contracts/authoring.ts:273-304`. Freeform text fails validation. | The `/intent` endpoint is a typed AST mutation compiler, not a natural-language bridge. |
| **G** | Who instantiates `ContextBuilder` in Production? | **NO ONE** (`NONE`) | `CODE_PROVEN` | `ai/context/builder.py:47`. Zero occurrences of `ContextBuilder` or `ai.context` exist in `api/` or `scripts/`. Callers exist solely in `tests/ai/context/` (`test_builder.py:64, 141`, etc.). | Context assembly is completely unreachable in production runtime. |
| **H** | Who injects `KnowledgeRouter` into `ContextBuilder`? | **NO ONE** | `CODE_PROVEN` | `ContextBuilder.__init__` accepts `knowledge_retriever: Optional[KnowledgeRetriever]`, defaulting to `DeterministicKnowledgeRetriever()` (`ai/context/builder.py:77`). `KnowledgeRouter` does not implement this protocol and is never injected. | The knowledge router is not connected to context building in code or tests. |
| **I** | Does `initialize_canonical_catalog()` execute in Production? | **NO** | `CODE_PROVEN` | `initialize_canonical_catalog()` in `ai/knowledge/router.py:58-68` is called only in offline eval runners (`ai/regression/runner.py:162`, `scripts/run_creative_regression.py:90`) and 4 test files. Never in `api/` or `scripts/`. | Knowledge catalog indexing is not initialized during application startup. |
| **J** | What is the exact function of root `/ground-truth/`? | **Derivative index & documentation cache** | `CODE_PROVEN` & `CI_PROVEN` | Generated by `scripts/generators/build_ground_truth.py:1-4` from disk scan; verified against drift in CI via `scripts/validators/check_ground_truth_sync.py:35-45`. Not an ML dataset or runtime authority. | Serves as human/agent reference navigation, not runtime authority. |
| **K** | Which files in `/ground-truth/` have active Production consumers? | **ZERO** | `CODE_PROVEN` | Audit of all 13 files in `ground-truth/` shows 0 imports or reads in `api/` or `scripts/pipeline.py`. (Only offline test beds read `template_catalog.json`, and legacy MCP reads `ASSET_INDEX.json`). | `/ground-truth/` can be deleted from production runtime without impacting execution. |
| **L** | Is `template_catalog.json` an authority or metadata input? | **Metadata input / compatibility derivative** | `CODE_PROVEN` | `scripts/core/template_registry_publisher.py:6-11` explicitly declares `registry/template-registry-data.json` as the canonical authority. `template_catalog.json` is a downstream derivative published for compatibility. | Template changes must be made in `registry/`, not in `ground-truth/`. |
| **M** | Does `RecipeRegistry` consume `recipes/*.json` in practice? | **YES** | `CODE_PROVEN` & `TEST_PROVEN` | `RecipeRegistry.__init__` (`ai/recipes/registry.py:105-125`) defaults `auto_load=True`, globs `recipes/*.json` (skipping `schema.json`), migrates legacy schemas, and loads all 18 recipe definitions. | Recipe definitions on disk are actively consumed by the AI registry. |
| **N** | Does Skills runtime load from typed definitions, markdown, or both? | **BOTH** | `CODE_PROVEN` | `ai/skills/loader.py:62-112` implements `load_from_markdown()` for `SKILL.md` files with YAML frontmatter, and lines 114-302 implement `get_canonical_skills()` for typed Python definitions. | Skills platform supports both declarative markdown and typed Python definitions. |
| **O** | Is raw MCP required for Internal Product AI? | **NO** | `CODE_PROVEN` & `TEST_PROVEN` | Internal capabilities route strictly through `CapabilityRouter` and `ToolGateway` to native adapters. Direct raw MCP imports are strictly forbidden by static AST guards (`tests/ai/audit/test_s28_m11_final_architecture_audit.py:47-81`). | Raw MCP is quarantined as an external compatibility adapter. |
| **P** | Do `CapabilityRouter` and `ToolGateway` receive real product requests? | **NO** | `CODE_PROVEN` | Zero call sites in `api/` or `scripts/pipeline.py` dispatch to `CapabilityRouter` or `ToolGateway`. All invocations occur strictly in `tests/ai/` suites. | Modern capability architecture is isolated from production traffic. |
| **Q** | Does `ModelRouter` receive real product requests? | **NO** | `CODE_PROVEN` | Neither `api/` nor `scripts/pipeline.py` routes to `ModelRouter`. Legacy tool scripts raise blockers demanding `ModelRouter`, but no production caller invokes it. | Model ranking and routing receives zero production workload. |
| **R** | Is `CreativePlan` compiled into canonical `VideoDocument` on the production path? | **NO** | `CODE_PROVEN` | `BlueprintCompiler` (`ai/planning/compiler.py:62-443`) has zero callers in `api/`, `scripts/pipeline.py`, `scripts/core/worker.py`, or `authoring/`. Production authoring directly creates and updates `BlueprintV2` AST. | Creative planning outputs do not feed into production authoring. |
| **S** | Is Remotion strictly an adapter at runtime or does it retain authority? | **Contractually an adapter, practically a lingering authority** | `CODE_PROVEN` & `DOCUMENTATION_ONLY` | Contractually an adapter (`contracts/renderer.ts`, `remotion/remotion-renderer-adapter.ts`). Practically an authority because all 105 templates are Remotion TSX, fallback executes `npx remotion render`, and QC calls `remotion still`. | System is not truly renderer-agnostic in production runtime. |
| **T** | Do tests named "E2E" enter through real Production entrypoints? | **NO** | `CODE_PROVEN` & `TEST_PROVEN` | AI "E2E" tests (`tests/ai/e2e/*`) chain in-memory classes without HTTP or CLI. `tests/e2e/true_e2e_suite.py` creates disk fixtures and calls CLI directly (skipping HTTP API and worker). SaaS multi-tenant test mocks worker execution. | No test exercises the full end-to-end production path from API to delivery. |

---

## 8. Conclusion & Architectural Recommendation

1. **Reality Verdict**: The repository contains a battle-tested, deterministic video rendering pipeline and a sophisticated S28-R AST mutation authoring engine. However, the S27/S28 Creative Intelligence platform (`ai/`) exists in an air-gapped state, completely disconnected from the SaaS production API and worker daemon, and completely omitted from GitHub Actions CI.
2. **Immediate Remediation Priority 1 (CI Governance)**: Add `tests/ai` and the remaining 36 Remotion tests into `.github/workflows/remediation-ci.yml` to close the regression gap.
3. **Immediate Remediation Priority 2 (Production Wiring)**: Author an explicit bridge router in `api/routers/` (e.g., `POST /projects/{id}/generate`) that connects `ProjectService` to `CreativePlanner`, `ModelRouter`, and `BlueprintCompiler`, closing the gap between user intent and video execution.
