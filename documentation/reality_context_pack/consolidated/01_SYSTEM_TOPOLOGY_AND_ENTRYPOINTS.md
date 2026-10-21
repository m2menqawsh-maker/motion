# PILLAR 1: System Baseline, Structural Inventory & Production Call Graph

> **Consolidated Master Pillar** — Comprehensive integration of Reports 00, 01, and 02

> **Baseline SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` | **Branch**: `main`

> **Evidence Standard**: Strictly Preserved (`CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`)


---

## Table of Contents

1. [Part 1: Executive Baseline & Reality Freeze](#part-1-executive-baseline--reality-freeze) *(Source: `00_BASELINE_AND_EXECUTIVE_REALITY.md`)*
2. [Part 2: Repository Structural Directory Inventory](#part-2-repository-structural-directory-inventory) *(Source: `01_REPOSITORY_STRUCTURAL_INVENTORY.md`)*
3. [Part 3: Entrypoints & Production Call Graphs](#part-3-entrypoints--production-call-graphs) *(Source: `02_ENTRYPOINTS_AND_PRODUCTION_CALL_GRAPH.md`)*

---


<a name='part-1-executive-baseline--reality-freeze'></a>

## Part 1: Executive Baseline & Reality Freeze


> *Original Source: `documentation/reality_context_pack/00_BASELINE_AND_EXECUTIVE_REALITY.md`*


### Sub-Report Title: Baseline & Executive Architectural Reality Report


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


---


<a name='part-2-repository-structural-directory-inventory'></a>

## Part 2: Repository Structural Directory Inventory


> *Original Source: `documentation/reality_context_pack/01_REPOSITORY_STRUCTURAL_INVENTORY.md`*


### Sub-Report Title: Repository Structural Inventory & Architectural Directory Taxonomy


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive architectural directory inventory of all 36 top-level directories, functional script subdirectories, root configuration files, structural taxonomy, language, runtime relevance, consumers, and evidence.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Structural Taxonomy Summary

The repository represents a polyglot system (Python 3.12 and TypeScript / React 19) structured across 36 top-level directories and configuration roots. Each directory has been evaluated against its actual executable participation in the production runtime, build pipelines, development tooling, or historical preservation.

### 1.1 Structural Taxonomy Definitions
- `ACTIVE_PRODUCT_RUNTIME`: Essential production code executing in user-facing HTTP request paths, background worker jobs, or video rendering pipelines.
- `ACTIVE_PRODUCT_DATA`: Production data, persistent storage, templates, recipes, or static assets consumed directly by runtime execution.
- `ACTIVE_DEVELOPMENT`: Active source code, toolsets, or experimental features currently in development, isolated or air-gapped from production runtime paths.
- `ACTIVE_COMPATIBILITY`: Compatibility bridges, legacy adapters, or derivative catalogs maintained for backward compatibility or cross-ecosystem interop.
- `GENERATED_DIAGNOSTIC`: Automatically generated logs, caches, profiling outputs, or runtime diagnostic traces.
- `MIGRATION_ONLY`: Code or tools used solely for migrating schemas, data, or project configurations across architectural generations.
- `HISTORICAL_EVIDENCE`: Static documentation, decision records, developer guides, audit reports, or learning summaries preserved for historical lineage.
- `DEPRECATED_BUT_CONSUMED`: Legacy code or assets formally deprecated but still actively referenced or imported by active runtime code.
- `DEPRECATED_UNCONSUMED`: Legacy code, scripts, or assets with zero active callers or importers across the repository.
- `TEST_ONLY`: Test suites, test harnesses, mocks, fixtures, and benchmarking tools not deployed to production.
- `UNKNOWN`: Directories whose architectural role, consumers, or provenance cannot be proven from current repository state.

### 1.2 Taxonomy Distribution Table

| Classification Category | Directory Count | Top-Level Paths Included | Core Architectural Role |
|---|---|---|---|
| `ACTIVE_PRODUCT_RUNTIME` | 13 | `api/`, `authoring/`, `contracts/`, `compositor/`, `planner/`, `preview/`, `registry/`, `remotion/`, `remotion-app/`, `templates/`, `creative_governance/`, `schemas/`, `config/` (plus `scripts/core/`, `scripts/gates/`, `scripts/generators/`, `node_modules/`, `.github/`) | Public HTTP API, deterministic state machine, AST authoring engine, multi-engine planner, and Remotion rendering pipeline. |
| `ACTIVE_PRODUCT_DATA` | 5 | `assets/`, `data/`, `projects/`, `public/`, `recipes/` | Project workspaces, SQLite databases, object storage, media assets, and 18 video recipes. |
| `ACTIVE_DEVELOPMENT` | 6 | `ai/`, `canvas/`, `.agents/`, `.githooks/`, `.venv/`, `scratch/` (plus `.git/`) | Air-gapped AI platform (S27/S28), experimental Canvas adapter, agent plugin tooling, and developer workspaces. |
| `ACTIVE_COMPATIBILITY` | 1 | `ground-truth/` | Auto-generated derivative metadata catalogs and indices validated in CI via drift checks. |
| `GENERATED_DIAGNOSTIC` | 3 | `logs/`, `.pytest_cache/`, `.ruff_cache/` | Runtime logs, test caches, and linter analysis artifacts. |
| `HISTORICAL_EVIDENCE` | 4 | `documentation/`, `references/`, `التعلم/`, `.git/` | Architecture decision records, remediation history, playbooks, Arabic learning notes, and Git lineage. |
| `DEPRECATED_UNCONSUMED` | 1 | `scripts/archive/` (functional sub-root) | Historical migration scripts from early development stages. |
| `TEST_ONLY` | 1 | `tests/` | 510+ test files spanning unit, integration, architecture guard, and simulated E2E test suites. |
| `UNKNOWN` | 0 | None | All 36 directories definitively resolved through code inspection and AST scanning. |

---

## 2. Comprehensive Directory Inventory (All 36 Top-Level Directories)

Below is the exhaustive, systematic audit of every top-level directory in alphabetical order (including hidden directories and non-ASCII paths).

```
========================================================================================================
                                36 TOP-LEVEL DIRECTORIES INVENTORY
========================================================================================================
```

### 2.1 `.agents/`
- **Path**: `.agents/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: Python, TypeScript, Shell, JSON, Dockerfiles
- **Purpose & Architectural Role**: Contains agent orchestration plugin bundles (`super-video-maker-plugin`), Docker container build configurations (`.agents/docker/Dockerfile.remotion`), guardian scripts, and agent skills (`prompt-engineering-expert`, `remocn`, `snapcn`).
- **Runtime Relevance**: Indirect / Agent Authoring. Not imported or executed by `api/main.py` or `scripts/pipeline.py`. Serves external AI agents interacting via MCP or terminal.
- **Consumers**: External AI developer agents, Docker build step in GitHub Actions (`.github/workflows/remediation-ci.yml:195-200`), Teamwork framework (`.agents/teamwork/`).
- **Dependencies**: FastMCP, Python 3.12, Docker.
- **Key Architectural Observations**:
  - `mcp_config.json` contains hardcoded Windows paths (`C:/video/clean-video-workspace/...`) for tool arguments, causing immediate failure if spawned directly on Linux hosts [`CODE_PROVEN`].
  - Contains tool implementations (`elevenlabs_voice.py`) with hardcoded execution blocks (`raise RuntimeError("DIRECT PROVIDER EXECUTION BLOCKED...")`).
- **Evidence Citation**: `.agents/plugins/super-video-maker-plugin/mcp_config.json:1-35` [`CODE_PROVEN`].

---

### 2.2 `.git/`
- **Path**: `.git/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT` / `HISTORICAL_EVIDENCE`
- **Primary Language / Form**: Git object database, packfiles, references
- **Purpose & Architectural Role**: Git version control system repository metadata, tracking commit lineage back to initial commits through 26 remediation branches (`remediation/s00` to `remediation/s26`) and feature branches.
- **Runtime Relevance**: Build & Tooling. Consumed by `scripts/validators/check_ground_truth_sync.py` via `git status --porcelain`.
- **Consumers**: Git CLI, CI runners, `check_ground_truth_sync.py`.
- **Dependencies**: Git binary.
- **Key Architectural Observations**: Clean working tree on `main` at commit `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`.
- **Evidence Citation**: `git rev-parse HEAD` -> `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` [`CODE_PROVEN`].

---

### 2.3 `.githooks/`
- **Path**: `.githooks/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: Bash Shell scripts
- **Purpose & Architectural Role**: Workstation Git hooks for developers, enforcing secret detection, formatting checks, and lockfile synchronization prior to commit.
- **Runtime Relevance**: Local Workstation Tooling. Zero production runtime execution.
- **Consumers**: Local Git commits when configured via `git config core.hooksPath .githooks`.
- **Dependencies**: Bash, Python, UV.
- **Key Architectural Observations**: Protects repository from leaking API keys or committing broken lockfiles.
- **Evidence Citation**: `.githooks/` directory listing [`CODE_PROVEN`].

---

### 2.4 `.github/`
- **Path**: `.github/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME` (CI Governance)
- **Primary Language / Form**: YAML (`remediation-ci.yml`), Markdown
- **Purpose & Architectural Role**: CI/CD automation workflow definitions and PR/issue templates. The file `.github/workflows/remediation-ci.yml` defines the canonical 7-job automated pull-request gate.
- **Runtime Relevance**: CI Governance Gatekeeper. Enforces test execution, linting, Docker builds, and security audits.
- **Consumers**: GitHub Actions runner environment.
- **Dependencies**: Ubuntu-latest, GitHub Actions, Docker, Node 20, Python 3.12.
- **Key Architectural Observations**:
  - Defines 7 jobs: `python-quality`, `contracts-ts`, `ground-truth`, `python-tests`, `strict-e2e`, `docker-render`, `security-audit`.
  - Line 125-126 explicitly excludes `tests/ai/` from pytest testpaths [`CI_PROVEN`].
- **Evidence Citation**: `.github/workflows/remediation-ci.yml:14-265` [`CI_PROVEN`].

---

### 2.5 `.pytest_cache/`
- **Path**: `.pytest_cache/`
- **Structural Classification**: `GENERATED_DIAGNOSTIC`
- **Primary Language / Form**: JSON, Python cache metadata
- **Purpose & Architectural Role**: Local cache directory generated by pytest, recording test node IDs, step timings, and failure statuses for `--lf` (last-failed) reruns.
- **Runtime Relevance**: Diagnostic / Test Cache. Zero runtime or production relevance.
- **Consumers**: Pytest CLI.
- **Dependencies**: Pytest.
- **Key Architectural Observations**: Ephemeral local development artifact; ignored in Git via `.gitignore`.
- **Evidence Citation**: `.gitignore:22` [`CODE_PROVEN`].

---

### 2.6 `.ruff_cache/`
- **Path**: `.ruff_cache/`
- **Structural Classification**: `GENERATED_DIAGNOSTIC`
- **Primary Language / Form**: Binary index cache
- **Purpose & Architectural Role**: Incremental file hashing and AST cache used by the Ruff Python linter to accelerate subsequent lint runs.
- **Runtime Relevance**: Diagnostic / Linter Cache. Zero production relevance.
- **Consumers**: Ruff CLI.
- **Dependencies**: Ruff.
- **Key Architectural Observations**: Ephemeral local artifact; ignored in Git via `.gitignore`.
- **Evidence Citation**: `.gitignore:25` [`CODE_PROVEN`].

---

### 2.7 `.venv/`
- **Path**: `.venv/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: Python binaries, shared libraries, installed site-packages
- **Purpose & Architectural Role**: Python 3.12 virtual environment containing installed dependencies generated by `uv sync`.
- **Runtime Relevance**: Local execution environment. Zero production deployment relevance.
- **Consumers**: Local developer terminal, local pytest, local uvicorn.
- **Dependencies**: Python 3.12, UV.
- **Key Architectural Observations**: Houses pinned versions of FastAPI, Pydantic, Boto3, Pytest, Librosa, FFmpeg-python, etc.
- **Evidence Citation**: `pyproject.toml:5` [`CODE_PROVEN`].

---

### 2.8 `ai/`
- **Path**: `ai/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT` (Disconnected AI Subsystem)
- **Primary Language / Form**: Python 3.12
- **Purpose & Architectural Role**: Complete Creative Intelligence Platform (Generations S27/S28). Contains context building (`ai/context/`), model ranking and routing (`ai/routing/`), capability cataloging and tool gateways (`ai/capabilities/`, `ai/tools/`), episodic memory (`ai/memory/`), creative planning (`ai/planning/`), narrative script generation (`ai/narrative/`), taste rules (`ai/taste/`), vision analysis (`ai/vision/`), speech synthesis (`ai/speech/`), and audio design (`ai/audio/`).
- **Runtime Relevance**: **ZERO PRODUCTION REACHABILITY**. Disconnected from production HTTP routes (`api/main.py`) and worker pipeline (`scripts/pipeline.py`).
- **Consumers**: Tested exclusively by `tests/ai/` unit/integration test suites, offline evaluation benchmarks (`scripts/run_creative_e2e.py`, `scripts/run_creative_regression.py`), and FastMCP compatibility server.
- **Dependencies**: Pydantic v2, OpenAI SDK, Boto3, Numpy.
- **Key Architectural Observations**:
  - Air-gapped from production: zero imports in `api/` or `scripts/pipeline.py` [`CODE_PROVEN`].
  - Completely omitted from GitHub Actions required CI (`.github/workflows/remediation-ci.yml`) [`CI_PROVEN`].
  - Implements rigorous internal domain boundaries and AST-enforced isolation from raw MCP [`TEST_PROVEN`].
- **Evidence Citation**: `ai/context/builder.py:47-91`, `ai/routing/router.py:67-130`, `ai/capabilities/gateway.py` [`CODE_PROVEN`].

---

### 2.9 `api/`
- **Path**: `api/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: Python (FastAPI, Pydantic v2)
- **Purpose & Architectural Role**: Authoritative REST API backend for the SaaS video generation platform. Exposes 34 endpoints mounted across 12 routers (`projects`, `runs`, `assets`, `artifacts`, `outputs`, `gates`, `render`, `brand`, `blueprint`, `authoring`, `candidate_reviews`, `candidate_promotions`, `health`).
- **Runtime Relevance**: Primary Production Entrypoint (`uvicorn api.main:app`). Handles client traffic, authentication, CAS locking, run enqueuing, and live authoring mutations.
- **Consumers**: Web frontend, Studio preview, external REST API clients, `tests/e2e/test_saas_multi_tenant_e2e.py`.
- **Dependencies**: FastAPI, Pydantic v2, `scripts/core/` domain services, `scripts/execute_authoring_mutation.ts`.
- **Key Architectural Observations**:
  - Enforces startup environment policy via `EnvironmentPolicyAuditor` (`api/main.py:30-40`) [`CODE_PROVEN`].
  - Contains zero natural language generation entrypoints; requires structured JSON DTOs [`CODE_PROVEN`].
  - Dispatches authoring mutations to TypeScript via Node subprocess IPC [`CODE_PROVEN`].
- **Evidence Citation**: `api/main.py:45-75`, `api/routers/runs.py:23-56`, `api/routers/authoring.py:104-131` [`CODE_PROVEN`].

---

### 2.10 `assets/`
- **Path**: `assets/`
- **Structural Classification**: `ACTIVE_PRODUCT_DATA`
- **Primary Language / Form**: Binary media, PNG, MP4, TTF fonts, JSON
- **Purpose & Architectural Role**: Static assets repository housing default brand typography fonts (`assets/fonts/Inter-*.ttf`), fallback audio tracks, sound effects, and test fixtures.
- **Runtime Relevance**: Production Data. Symlinked or copied into project workspaces by `scripts/generators/materialize_project.py`.
- **Consumers**: Remotion templates, `materialize_project.py`, test runners.
- **Dependencies**: Filesystem.
- **Key Architectural Observations**: Indexed by `scripts/generators/build_ground_truth.py` into `ground-truth/ASSET_INDEX.json`.
- **Evidence Citation**: `scripts/generators/materialize_project.py:45-70` [`CODE_PROVEN`].

---

### 2.11 `authoring/`
- **Path**: `authoring/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript (ES2022)
- **Purpose & Architectural Role**: The S28-R Live Authoring Engine. Houses `UnifiedAuthoringSession`, `IntentPlanner`, and AST mutation transformers. Manages in-memory transactional edits to canonical `VideoDocument` / `BlueprintV2` structures.
- **Runtime Relevance**: Core Production Runtime. Invoked via `scripts/execute_authoring_mutation.ts` during HTTP `POST /projects/{id}/mutate`, `/batch`, and `/intent`.
- **Consumers**: `scripts/execute_authoring_mutation.ts`, `api/services/authoring_service.py`.
- **Dependencies**: `contracts/authoring.ts`, `contracts/blueprint.ts`, Zod.
- **Key Architectural Observations**:
  - Pure, deterministic, zero-AI-SDK, zero-renderer AST engine [`CODE_PROVEN`].
  - Enforces strict entity targeting by Stable-ID (`scene_id`, `layer_id`, `clip_id`) [`CODE_PROVEN`].
- **Evidence Citation**: `authoring/unified-authoring-session.ts:1-50`, `authoring/intent-planner.ts:5-14` [`CODE_PROVEN`].

---

### 2.12 `canvas/`
- **Path**: `canvas/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: TypeScript
- **Purpose & Architectural Role**: Level 1/0 multi-engine renderer adapter implementation for HTML5 Canvas (`canvas-renderer-adapter.ts`). Implements the `RendererAdapter` contract from `contracts/renderer.ts`.
- **Runtime Relevance**: Development / Experimental. Registered in `CANONICAL_RENDERER_REGISTRY` alongside Remotion, but not exercised in default production rendering.
- **Consumers**: `planner/render-planner.ts` (when canvas engine requested), contract tests in `tests/contracts/`.
- **Dependencies**: `contracts/renderer.ts`, Node-canvas.
- **Key Architectural Observations**: Proves multi-engine contract feasibility, but canonical templates are written in React TSX and cannot render on Canvas without transpilation.
- **Evidence Citation**: `canvas/canvas-renderer-adapter.ts:1-40`, `scripts/render_via_planner.ts:114-121` [`CODE_PROVEN`].

---

### 2.13 `compositor/`
- **Path**: `compositor/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript, FFmpeg CLI bindings
- **Purpose & Architectural Role**: The Master Compositor (`master-compositor.ts`). Assembles heterogeneous video and audio rendered chunks, performs timeline interleaving, loudness normalization (-16 LUFS voice, -24 LUFS SFX), and final multiplexing into `out.mp4`.
- **Runtime Relevance**: Core Production Runtime. Executed by `scripts/render_via_planner.ts` at the final stage of rendering.
- **Consumers**: `scripts/render_via_planner.ts`, `planner/production-render-graph-executor.ts`.
- **Dependencies**: FFmpeg binary, `contracts/compositor.ts`.
- **Key Architectural Observations**: Acts as the engine-neutral compositor merging outputs from Remotion, Canvas, or external media sources.
- **Evidence Citation**: `compositor/master-compositor.ts:1-50` [`CODE_PROVEN`].

---

### 2.14 `config/`
- **Path**: `config/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: JSON
- **Purpose & Architectural Role**: Static configuration rules, containing `violations_config.json` used by `scripts/validators/check_violations.py` and quality audit scripts.
- **Runtime Relevance**: Verification / Governance. Consumed during CI and pipeline gate validation.
- **Consumers**: `scripts/validators/check_violations.py`.
- **Dependencies**: JSON parser.
- **Key Architectural Observations**: Defines rule codes and severities for code violations and style constraints.
- **Evidence Citation**: `config/violations_config.json:1-30` [`CODE_PROVEN`].

---

### 2.15 `contracts/`
- **Path**: `contracts/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript (Zod schemas, TypeScript types), JSON
- **Purpose & Architectural Role**: Single source of truth for runtime contracts across the TypeScript domain: `blueprint.ts` (BlueprintV2 schema), `authoring.ts` (AuthoringRequest, AuthoringIntent), `renderer.ts` (RendererAdapter), `compositor.ts`, and `template-runtime-contract.json`.
- **Runtime Relevance**: Core Production Runtime. Imported by `authoring/`, `planner/`, `remotion/`, `canvas/`, and tested in CI.
- **Consumers**: All TypeScript subsystems, Python contract generators (`scripts/generate_ai_contracts.py`).
- **Dependencies**: Zod 3.25.76.
- **Key Architectural Observations**:
  - Gated in CI via `npm run test:contracts` and `npm run check:template-contract` [`CI_PROVEN`].
  - Versioned schemas guarantee forward/backward compatibility of blueprints.
- **Evidence Citation**: `contracts/index.ts`, `contracts/blueprint.ts:1-50`, `contracts/authoring.ts:1-60` [`CODE_PROVEN`].

---

### 2.16 `creative_governance/`
- **Path**: `creative_governance/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: Python 3.12
- **Purpose & Architectural Role**: Template candidate review and promotion domain subsystem. Implements candidate lifecycle state machines (`DRAFT -> REVIEW_PENDING -> APPROVED -> PROMOTED`), sandbox test execution, and governance storage.
- **Runtime Relevance**: Production Runtime. Mounted in `api/main.py:67-68` via `candidate_reviews.router` and `candidate_promotions.router`.
- **Consumers**: `api/routers/candidate_reviews.py`, `api/routers/candidate_promotions.py`, `scripts/core/template_registry_publisher.py`.
- **Dependencies**: `scripts/core/database.py`, `scripts/core/storage/storage_service.py`.
- **Key Architectural Observations**: Provides safe human/agent review workflow before promoting newly created templates into the canonical template registry.
- **Evidence Citation**: `creative_governance/candidates/service.py:1-50`, `api/routers/candidate_promotions.py:30-45` [`CODE_PROVEN`].

---

### 2.17 `data/`
- **Path**: `data/`
- **Structural Classification**: `ACTIVE_PRODUCT_DATA`
- **Primary Language / Form**: SQLite (`.db`), Local object storage files
- **Purpose & Architectural Role**: Persistent local state storage:
  - `data/runs.db`: Persistent run records and run event log (`runs`, `run_events`).
  - `data/motion.db`: Persistent project states, workspaces, users, reviews, and candidate records.
  - `data/openrouter_smoke_traces.db`: Traces of OpenRouter LLM test calls.
  - `data/storage/`: Local object storage bucket root used by `LocalStorageBackend`.
- **Runtime Relevance**: Production Database & Storage. Actively queried and written to by `RunRepository`, `TenantRepository`, `StorageService`.
- **Consumers**: `scripts/core/database.py`, `scripts/core/run_repository.py`, `api/services/*`.
- **Dependencies**: SQLite3, `StorageService`.
- **Key Architectural Observations**: Configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) for concurrent access safety [`CODE_PROVEN`].
- **Evidence Citation**: `scripts/core/database.py:35-45`, `scripts/core/run_repository.py:37-60` [`CODE_PROVEN`].

---

### 2.18 `documentation/`
- **Path**: `documentation/`
- **Structural Classification**: `HISTORICAL_EVIDENCE` / `ACTIVE_PRODUCT_DATA` (Post-Audit Context Pack)
- **Primary Language / Form**: Markdown, JSON
- **Purpose & Architectural Role**: Repository documentation archive housing architecture decision records, guides, remediation milestone reports (`documentation/remediation/`), and the authoritative reality audit reports in `documentation/reality_context_pack/`.
- **Runtime Relevance**: Documentation & Governance. Read-only context for developers, auditors, and agents.
- **Consumers**: Development team, agents, forensic auditors.
- **Dependencies**: Markdown viewer.
- **Key Architectural Observations**: Contains chronological documentation of 26 remediation milestones (`s00` to `s26`), S28, S28-M, S28-R.
- **Evidence Citation**: `documentation/remediation/` listing, `documentation/reality_context_pack/` [`DOCUMENTATION_ONLY`].

---

### 2.19 `ground-truth/`
- **Path**: `ground-truth/`
- **Structural Classification**: `ACTIVE_COMPATIBILITY`
- **Primary Language / Form**: JSON, Markdown
- **Purpose & Architectural Role**: Auto-generated derivative documentation, indexing, and compatibility metadata cache directory. Contains `template_catalog.json`, `ASSET_INDEX.json`, `TEMPLATE_INDEX.md`, `CANONICAL_PATHS.json`, and collections.
- **Runtime Relevance**: Compatibility / CI Gate. Has **ZERO active production consumers** in `api/` or `scripts/pipeline.py`. Gated in CI via `scripts/validators/check_ground_truth_sync.py --check`.
- **Consumers**: `scripts/validators/check_ground_truth_sync.py`, offline eval test harnesses (`ai/planning/reuse_engine.py:49`), legacy agent playbooks.
- **Dependencies**: `scripts/generators/build_ground_truth.py`.
- **Key Architectural Observations**:
  - Strictly derivative; regenerated from disk scan of `registry/` and `assets/` [`CODE_PROVEN`].
  - `template_catalog.json` is a downstream metadata compatibility catalog, NOT the authority [`CODE_PROVEN`].
- **Evidence Citation**: `scripts/validators/check_ground_truth_sync.py:19-25`, `scripts/core/template_registry_publisher.py:6-11` [`CI_PROVEN`, `CODE_PROVEN`].

---

### 2.20 `logs/`
- **Path**: `logs/`
- **Structural Classification**: `GENERATED_DIAGNOSTIC`
- **Primary Language / Form**: Text log files
- **Purpose & Architectural Role**: Runtime and diagnostic execution logs produced by pipeline scripts, guardian checks, and test harnesses.
- **Runtime Relevance**: Diagnostic / Auditing.
- **Consumers**: Developers and operators inspecting failure stack traces.
- **Dependencies**: Python logging.
- **Key Architectural Observations**: Git-ignored runtime output directory.
- **Evidence Citation**: `scripts/pipeline.py:120-135` [`CODE_PROVEN`].

---

### 2.21 `node_modules/`
- **Path**: `node_modules/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME` (Dependencies)
- **Primary Language / Form**: JavaScript, TypeScript, Native binaries
- **Purpose & Architectural Role**: Installed Node.js dependencies for root workspace and Remotion (Remotion CLI, React 19, Zod, ts-morph, Vitest).
- **Runtime Relevance**: Build & Execution Runtime. Required for executing `tsx` scripts, Remotion rendering, and Vitest.
- **Consumers**: Node runtime, `npx tsx`, Remotion CLI.
- **Dependencies**: `package.json`, `package-lock.json`.
- **Key Architectural Observations**: Installed and verified in CI via `npm ci` (`.github/workflows/remediation-ci.yml:45`).
- **Evidence Citation**: `package.json:30-45` [`CODE_PROVEN`].

---

### 2.22 `planner/`
- **Path**: `planner/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript
- **Purpose & Architectural Role**: The Multi-Engine Render Planner (`render-planner.ts`) and DAG executor (`production-render-graph-executor.ts`). Analyzes canonical `BlueprintV2`, builds a DAG of independent scene/layer render tasks, and coordinates multi-engine execution.
- **Runtime Relevance**: Core Production Runtime. Priority 1 render path in `scripts/render_project.py` via `scripts/render_via_planner.ts`.
- **Consumers**: `scripts/render_via_planner.ts`, `scripts/render_project.py`.
- **Dependencies**: `contracts/renderer.ts`, `contracts/blueprint.ts`.
- **Key Architectural Observations**: Core component of the S28-R multi-engine rendering architecture.
- **Evidence Citation**: `planner/render-planner.ts:1-50`, `scripts/render_via_planner.ts:33-40` [`CODE_PROVEN`].

---

### 2.23 `preview/`
- **Path**: `preview/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript
- **Purpose & Architectural Role**: Real-time video preview runtime (`preview-runtime.ts`). Provides DOM drivers and frame rendering projection for live editing previews in browser clients without invoking full video renderers.
- **Runtime Relevance**: Authoring / Studio Preview. Consumed by web studio interfaces and live preview clients.
- **Consumers**: Studio web interfaces, `tests/remotion/`.
- **Dependencies**: `contracts/blueprint.ts`, `authoring/`.
- **Key Architectural Observations**: Enables sub-50ms visual updates during live document mutation.
- **Evidence Citation**: `preview/preview-runtime.ts:1-50` [`CODE_PROVEN`].

---

### 2.24 `projects/`
- **Path**: `projects/`
- **Structural Classification**: `ACTIVE_PRODUCT_DATA`
- **Primary Language / Form**: JSON, Markdown, PNG, MP4, Symlinks
- **Purpose & Architectural Role**: File workspaces for individual video projects (`projects/<project_id>/`). Contains canonical files:
  - `01_manifest.json` / `02_asset_manifest.json`: Asset specifications and hashes.
  - `master_plan.md`: Human/agent narrative plan and timings.
  - `05_blueprint.json`: Canonical `BlueprintV2` AST.
  - `.pipeline_state.json`: State machine tracker and stage artifact hashes.
  - `contact_sheet.png`: Probe QC verification stills.
  - `out.mp4`: Final rendered video output.
- **Runtime Relevance**: Core Production Workspaces. Read and mutated by `scripts/pipeline.py`, `scripts/gates/*`, `AssetService`.
- **Consumers**: Pipeline orchestrator, worker, API services.
- **Dependencies**: Filesystem, CAS locks.
- **Key Architectural Observations**: The project folder acts as the physical workspace for all gate validations and rendering jobs.
- **Evidence Citation**: `scripts/pipeline.py:230-260`, `api/services/run_service.py:45-55` [`CODE_PROVEN`].

---

### 2.25 `public/`
- **Path**: `public/`
- **Structural Classification**: `ACTIVE_PRODUCT_DATA`
- **Primary Language / Form**: Static web media, fonts, audio
- **Purpose & Architectural Role**: Public web assets mounted into FastAPI and served to Remotion during rendering.
- **Runtime Relevance**: Web Serving & Rendering. Mounted by FastAPI and referenced by Remotion web server.
- **Consumers**: Remotion rendering server, browser clients.
- **Dependencies**: Web server.
- **Key Architectural Observations**: Used by `materialize_project.py` to expose local media to Remotion Chromium renderer.
- **Evidence Citation**: `scripts/generators/materialize_project.py:75-110` [`CODE_PROVEN`].

---

### 2.26 `recipes/`
- **Path**: `recipes/`
- **Structural Classification**: `ACTIVE_PRODUCT_DATA`
- **Primary Language / Form**: JSON
- **Purpose & Architectural Role**: Houses 18 declarative video recipe definitions (`avatar-explainer.json`, `living-canvas-explainer.json`, `captioned-talking-head.json`, `motion-graphics.json`, `ugc-ai-ad.json`, etc.) plus `schema.json`.
- **Runtime Relevance**: Product Data (Consumed by `RecipeRegistry`). Loaded dynamically by `RecipeRegistry.load_from_directory()` during construction.
- **Consumers**: `ai/recipes/registry.py:105-125`, `ai/planning/recipe_selector.py`.
- **Dependencies**: JSON schema.
- **Key Architectural Observations**: All 18 recipes are actively parsed, migrated, and registered in memory by `RecipeRegistry` [`CODE_PROVEN`, `TEST_PROVEN`].
- **Evidence Citation**: `ai/recipes/registry.py:105-140` [`CODE_PROVEN`].

---

### 2.27 `references/`
- **Path**: `references/`
- **Structural Classification**: `HISTORICAL_EVIDENCE` / `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: Markdown
- **Purpose & Architectural Role**: Developer SOPs, reference playbooks, taste engine matrices (`SFX_BINDING_MATRIX.md`), and legacy router documentation (`ROUTER.md`).
- **Runtime Relevance**: Documentation & Guidance. Zero executable production runtime callers. Indexed as knowledge by `KnowledgeLoader` in test beds.
- **Consumers**: Developers, AI agents, `ai/knowledge/loader.py` (in tests).
- **Dependencies**: Markdown reader.
- **Key Architectural Observations**: Provides normative guidelines for video creation and sound design.
- **Evidence Citation**: `references/README.md`, `references/ROUTER.md` [`DOCUMENTATION_ONLY`].

---

### 2.28 `registry/`
- **Path**: `registry/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript (React TSX), JSON
- **Purpose & Architectural Role**: The Canonical Template Registry:
  - `template-registry-data.json`: Canonical machine-readable authority.
  - `template-registry.tsx`: Concrete React component binding registry.
  - `template-aliases.ts`: Canonical component alias definitions.
- **Runtime Relevance**: Core Production Runtime. Loaded by Remotion runtime, authoring session, and candidate promotion services.
- **Consumers**: `templates/brand-resolver.ts`, `scripts/core/template_registry_publisher.py`, Remotion Studio.
- **Dependencies**: React 19, `contracts/`.
- **Key Architectural Observations**: Declared as the Single Source of Truth for template identities and props contracts [`CODE_PROVEN`].
- **Evidence Citation**: `scripts/core/template_registry_publisher.py:6-11`, `registry/template-registry.tsx:1-40` [`CODE_PROVEN`].

---

### 2.29 `remotion/`
- **Path**: `remotion/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript
- **Purpose & Architectural Role**: The Remotion Renderer Adapter (`remotion-renderer-adapter.ts`). Wraps the Remotion rendering engine to conform to the `RendererAdapter` contract defined in `contracts/renderer.ts`.
- **Runtime Relevance**: Core Production Runtime. Executed by `scripts/render_via_adapter.ts` and `planner/render-planner.ts`.
- **Consumers**: `scripts/render_project.py`, `planner/production-render-graph-executor.ts`.
- **Dependencies**: Remotion CLI, `contracts/renderer.ts`.
- **Key Architectural Observations**: Wraps Remotion as an engine-neutral adapter without letting Remotion mutate the canonical document [`CODE_PROVEN`].
- **Evidence Citation**: `remotion/remotion-renderer-adapter.ts:1-50` [`CODE_PROVEN`].

---

### 2.30 `remotion-app/`
- **Path**: `remotion-app/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript (React 19), JSON
- **Purpose & Architectural Role**: Standalone Remotion React application root:
  - `src/index.ts`: Remotion entrypoint (`registerRoot`).
  - `src/Composition.tsx`: Top-level composition renderer mounting `BlueprintVideo`.
  - `remotion.config.ts`: Remotion Chromium and Webpack configuration.
  - `package.json`: Pinned Remotion 4.0.525 and React 19.3.0 dependencies.
- **Runtime Relevance**: Core Production Runtime. Executed during video rendering and interactive studio sessions.
- **Consumers**: Remotion CLI, Chromium headless renderer, `scripts/open_studio.py`.
- **Dependencies**: Remotion, React 19.
- **Key Architectural Observations**:
  - `remotion-app/package.json:9` bans direct rendering (`echo ❌ HARD STOP: Direct rendering is banned`) to force execution through canonical scripts [`CODE_PROVEN`].
  - Pinned to Zod 4.5.4 (overriding root's 3.25.76) [`CODE_PROVEN`].
- **Evidence Citation**: `remotion-app/package.json:1-46`, `remotion-app/src/index.ts:1-30` [`CODE_PROVEN`].

---

### 2.31 `schemas/`
- **Path**: `schemas/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: JSON Schema (Draft 7 / Draft 2020-12)
- **Purpose & Architectural Role**: Canonical JSON Schemas validating system interchange files:
  - `manifest.v2.schema.json`: Validates `02_asset_manifest.json`.
  - `blueprint.schema.json`: Validates `05_blueprint.json`.
  - `pipeline_state.schema.json`: Validates `.pipeline_state.json`.
  - `brand.schema.json`, `overrides.schema.json`, `creative_brief.schema.json`.
- **Runtime Relevance**: Core Production Runtime. Invoked by pipeline gates (`validate_blueprint.py`, `asset_gate.py`) and API routers.
- **Consumers**: `scripts/gates/validate_blueprint.py`, `scripts/core/state_store.py`, `scripts/generators/manifest_compiler.py`.
- **Dependencies**: `jsonschema` Python package.
- **Key Architectural Observations**: Fails closed if any project JSON artifact violates the corresponding schema.
- **Evidence Citation**: `scripts/gates/validate_blueprint.py:25-45`, `schemas/blueprint.schema.json` [`CODE_PROVEN`].

---

### 2.32 `scratch/`
- **Path**: `scratch/`
- **Structural Classification**: `ACTIVE_DEVELOPMENT`
- **Primary Language / Form**: Python, TypeScript, Shell
- **Purpose & Architectural Role**: Developer scratchpad directory for exploratory prototypes, one-off scripts, and experimental benchmarks.
- **Runtime Relevance**: Developer Workspace. Zero production runtime relevance.
- **Consumers**: Individual developers during local experimentation.
- **Dependencies**: None.
- **Key Architectural Observations**: Excluded from linting and CI enforcement.
- **Evidence Citation**: `scratch/` listing [`CODE_PROVEN`].

---

### 2.33 `scripts/`
- **Path**: `scripts/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME` (See Section 3 for functional breakdown)
- **Primary Language / Form**: Python 3.12, TypeScript
- **Purpose & Architectural Role**: Domain execution core, pipeline orchestrators, verification gates, generators, maintenance utilities, and test runners.
- **Runtime Relevance**: Core Production Runtime. Houses `pipeline.py`, `worker.py`, `render_project.py`, `open_studio.py`.
- **Consumers**: Worker daemon, CLI operators, CI workflows.
- **Dependencies**: Python 3.12, UV, FFmpeg.
- **Key Architectural Observations**: The nerve center of the deterministic video production engine.
- **Evidence Citation**: `scripts/pipeline.py:1-520`, `scripts/worker.py:1-40` [`CODE_PROVEN`].

---

### 2.34 `templates/`
- **Path**: `templates/`
- **Structural Classification**: `ACTIVE_PRODUCT_RUNTIME`
- **Primary Language / Form**: TypeScript (React TSX)
- **Purpose & Architectural Role**: Canonical library of 105 video template components categorized into:
  - `templates/elements/`: Typography, title cards, badges, statistics, subtitles, callouts.
  - `templates/scenes/`: High-level multi-layer scene compositions (intros, outros, split-screens, product showcases).
  - `templates/effects/`: Visual shaders, kinetic typography, transitions, brand resolver (`brand-resolver.ts`), engine bridge (`engine-bridge.tsx`).
- **Runtime Relevance**: Core Production Runtime. Dynamically instantiated and rendered by Remotion into video frames.
- **Consumers**: Remotion Chromium renderer, Studio preview, `UnifiedAuthoringSession`.
- **Dependencies**: React 19, Remotion hooks.
- **Key Architectural Observations**: Strictly validated by `scripts/validators/template_lint.py` to ensure compliance with property contracts and font rules.
- **Evidence Citation**: `templates/brand-resolver.ts:1-40`, `registry/template-registry-data.json` [`CODE_PROVEN`].

---

### 2.35 `tests/`
- **Path**: `tests/`
- **Structural Classification**: `TEST_ONLY`
- **Primary Language / Form**: Python, TypeScript
- **Purpose & Architectural Role**: Complete automated verification suite containing 510+ test files:
  - `tests/core/`: Unit tests for StateStore, RunRepository, CAS locking, StorageService.
  - `tests/gates/`: Unit tests for pipeline gates.
  - `tests/generators/`: Unit tests for materialize_project and manifest compiler.
  - `tests/validators/`: Unit tests for dependency lock and ground truth validators.
  - `tests/architecture/`: Static AST guards enforcing architectural boundaries.
  - `tests/contracts/`: Zod and TypeScript contract tests.
  - `tests/fault_injection/`: Chaos testing and crash recovery tests.
  - `tests/e2e/`: Standalone E2E suites (`true_e2e_suite.py`, `test_saas_multi_tenant_e2e.py`).
  - `tests/ai/`: 270 test files verifying AI platform (excluded from GitHub CI).
  - `tests/remotion/`: 49 Vitest tests for S28-R Live Authoring and Remotion.
- **Runtime Relevance**: Verification / CI. Executed by pytest and vitest.
- **Consumers**: CI runners, local test commands.
- **Dependencies**: Pytest, Pytest-asyncio, Vitest.
- **Key Architectural Observations**: Discrepancy observed: GitHub Actions executes ~240 tests, while local test command executes ~490 tests [`CI_PROVEN`].
- **Evidence Citation**: `tests/` directory tree [`TEST_PROVEN`].

---

### 2.36 `التعلم/`
- **Path**: `التعلم/`
- **Structural Classification**: `HISTORICAL_EVIDENCE`
- **Primary Language / Form**: Markdown, Arabic text
- **Purpose & Architectural Role**: Arabic learning and documentation archive:
  - `التعلم/الاصلاح/`: Remediation summaries and fix notes.
  - `التعلم/التقارير/`: Progress reports and architectural milestones.
- **Runtime Relevance**: Historical / Documentation. Zero executable runtime callers.
- **Consumers**: Arabic-speaking engineering stakeholders and historical auditors.
- **Dependencies**: Markdown reader.
- **Key Architectural Observations**: Preserves historical remediation context from earlier phases of the project.
- **Evidence Citation**: `التعلم/` directory listing [`DOCUMENTATION_ONLY`].

---

## 3. Functional Script Subdirectories Inventory (`scripts/`)

Because `scripts/` contains over 100 files spanning disparate architectural concerns, its functional subdirectories have been classified individually:

| Subdirectory / File | Structural Classification | Primary Language | Purpose & Runtime Relevance | Consumers & Evidence |
|---|---|---|---|---|
| `scripts/core/` | `ACTIVE_PRODUCT_RUNTIME` | Python | Domain core services: `StateStore`, `RunRepository`, `LifecycleService`, `StorageService`, `ReviewService`, `PipelineWorker`, `CanonicalDocumentRepository`. | Imported directly by `api/` and `scripts/pipeline.py` [`CODE_PROVEN`]. |
| `scripts/gates/` | `ACTIVE_PRODUCT_RUNTIME` | Python | Deterministic pipeline gates: `asset_gate.py`, `plan_gate.py`, `taste_gate.py`, `validate_blueprint.py`, `motion_validator.py`, `code_template_gate.py`, `probe_qc.py`, `final_qc.py`. | Executed sequentially by `scripts/pipeline.py:356-512` [`CODE_PROVEN`]. |
| `scripts/generators/` | `ACTIVE_PRODUCT_RUNTIME` | Python / TS | Project materialization (`materialize_project.py`), catalog builders (`build_ground_truth.py`), manifest compilers. | Executed by `pipeline.py` at `BLUEPRINT_READY -> MATERIALIZED` [`CODE_PROVEN`]. |
| `scripts/maintenance/` | `ACTIVE_PRODUCT_RUNTIME` | Python | Maintenance tools: `sync_templates.py`, `cleanup_assets.py`, `check_orphans.py`, `auto_backup.py`. | Executed via npm scripts (`package.json:6`) and cron jobs [`CODE_PROVEN`]. |
| `scripts/validators/` | `ACTIVE_PRODUCT_RUNTIME` | Python / JS | Validation utilities: `check_ground_truth_sync.py`, `check_dependencies_lock.py`, `check_secrets.py`, `template_lint.py`. | Executed in CI (`.github/workflows/remediation-ci.yml:65-85`) [`CI_PROVEN`]. |
| `scripts/archive/` | `DEPRECATED_UNCONSUMED` | Python | Historical migration scripts: `migrate_legacy_projects.py`, `migrate_state.py`, `classify_templates.py`. | 0 active callers in production or CI [`DOCUMENTATION_ONLY`]. |
| `scripts/pipeline.py` | `ACTIVE_PRODUCT_RUNTIME` | Python | Master pipeline orchestrator advancing projects through 10 lifecycle stages. | Spawned by `worker.py` or run directly via CLI [`CODE_PROVEN`]. |
| `scripts/render_project.py` | `ACTIVE_PRODUCT_RUNTIME` | Python | Master rendering dispatcher coordinating RenderPlanner, adapter, and Remotion CLI. | Executed by `pipeline.py` at `REVIEW_APPROVED -> RENDERED` [`CODE_PROVEN`]. |
| `scripts/worker.py` | `ACTIVE_PRODUCT_RUNTIME` | Python | CLI entrypoint spawning `PipelineWorker.run_loop()`. | Executed as background daemon in Docker / Systemd [`CODE_PROVEN`]. |
| `scripts/open_studio.py` | `ACTIVE_PRODUCT_RUNTIME` | Python | CLI entrypoint unlocking Remotion Studio UI with gate verification. | Executed by developers via `python scripts/open_studio.py` [`CODE_PROVEN`]. |
| `scripts/execute_authoring_mutation.ts`| `ACTIVE_PRODUCT_RUNTIME` | TypeScript | Node subprocess bridge executing `UnifiedAuthoringSession` mutations. | Spawned via safe subprocess from `api/services/authoring_service.py:150` [`CODE_PROVEN`]. |

---

## 4. Root Configuration Manifests & Lockfiles Inventory

The repository enforces strict hermetic lockfile policies verified by automated CI checks:

| Configuration File | Structural Classification | Format / Type | Purpose & Governance Role | Evidence Citation |
|---|---|---|---|---|
| `pyproject.toml` | `ACTIVE_PRODUCT_RUNTIME` | TOML (PEP 621) | Python package metadata (`name = "motion"`, Python `>=3.12`), dependencies, pytest configuration, ruff lint rules. | `pyproject.toml:1-70` [`CODE_PROVEN`] |
| `uv.lock` | `ACTIVE_PRODUCT_RUNTIME` | Lockfile (UV) | Fully resolved dependency graph for all Python runtime and development packages (405 KB). | `uv.lock` [`CODE_PROVEN`] |
| `requirements.txt` | `ACTIVE_PRODUCT_RUNTIME` | Pinned Text | Production Python dependencies generated by `uv export --no-dev` with full SHA-256 integrity hashes (1,325 lines). | `requirements.txt:1-1325` [`CODE_PROVEN`] |
| `requirements-dev.txt` | `ACTIVE_DEVELOPMENT` | Pinned Text | Developer dependencies (pytest, pytest-cov, ruff, bandit, pip-audit). | `requirements-dev.txt:1-150` [`CODE_PROVEN`] |
| `package.json` | `ACTIVE_PRODUCT_RUNTIME` | JSON | Root Node.js workspace manifest: Remotion 4.0.525, React 19.3.0, Zod 3.25.76, Vitest, npm scripts. | `package.json:1-45` [`CODE_PROVEN`] |
| `package-lock.json` | `ACTIVE_PRODUCT_RUNTIME` | Lockfile (npm v3) | Fully resolved npm dependency tree with SHA-512 integrity hashes (287 KB). | `package-lock.json` [`CODE_PROVEN`] |
| `tsconfig.json` | `ACTIVE_PRODUCT_RUNTIME` | JSON with Comments | Root TypeScript compiler options: Target `ES2022`, Module `ESNext`, `moduleResolution: bundler`. | `tsconfig.json:1-25` [`CODE_PROVEN`] |
| `vitest.config.ts` | `ACTIVE_PRODUCT_RUNTIME` | TypeScript | Vitest test runner configuration targeting `tests/contracts`. | `vitest.config.ts:1-20` [`CODE_PROVEN`] |
| `.blueprint_lock.json` | `ACTIVE_PRODUCT_RUNTIME` | JSON | Cryptographic lock pinning canonical blueprint schema hashes. | `.blueprint_lock.json:1-15` [`CODE_PROVEN`] |
| `skills-lock.json` | `ACTIVE_PRODUCT_RUNTIME` | JSON | Integrity hash lock pinning installed agent skill versions. | `skills-lock.json:1-20` [`CODE_PROVEN`] |
| `hooks.json` | `ACTIVE_PRODUCT_RUNTIME` | JSON | Agent hook event definitions for tooling automation. | `hooks.json:1-35` [`CODE_PROVEN`] |
| `.env.example` | `ACTIVE_PRODUCT_RUNTIME` | Environment Spec | Documented environment variables for LLMs, storage, media APIs, and runtime modes. | `.env.example:1-45` [`CODE_PROVEN`] |
| `.dockerignore` | `ACTIVE_PRODUCT_RUNTIME` | Ignore Spec | Excludes tests, node_modules, and cache files from Docker image builds. | `.dockerignore:1-25` [`CODE_PROVEN`] |
| `.trivyignore` | `ACTIVE_PRODUCT_RUNTIME` | Security Policy | Ignored CVE vulnerability exceptions audited by security scanning. | `.trivyignore:1-10` [`CODE_PROVEN`] |

---

## 5. Cross-Cutting Structural Realities

### 5.1 Polyglot Boundary: Python and TypeScript IPC Interop
The repository avoids shared-memory polyglot runtimes in favor of explicit inter-process communication:
1. **Live Authoring Bridge**: `api/services/authoring_service.py:150` communicates with `authoring/` via `subprocess.Popen([npx, tsx, "scripts/execute_authoring_mutation.ts"])` using JSON over stdin and stdout.
2. **Rendering Bridge**: `scripts/render_project.py:130` dispatches to `planner/render-planner.ts` via `subprocess.run([npx, tsx, "scripts/render_via_planner.ts", project_id])`.
3. **Contract Synchronization**: `scripts/generate_ai_contracts.py` parses TypeScript contracts in `contracts/` and compiles corresponding Pydantic models in Python, validated against drift in CI.

### 5.2 Data Tier vs. Compute Tier Isolation
- **Data Tier (`ACTIVE_PRODUCT_DATA`)**: The repository maintains strict data separation. All persistent writes must pass through `DatabaseEngine` (`data/motion.db`, `data/runs.db`) or `StorageService` (`data/storage/` or S3). Direct writes to `projects/` are restricted to the active pipeline worker possessing the CAS lease.
- **Compute Tier (`ACTIVE_PRODUCT_RUNTIME`)**: The FastAPI application is completely stateless, permitting horizontal scaling behind a load balancer, with state coordinate synchronization managed via database CAS revisions.

### 5.3 Generational Stratification & Architectural Hygiene
- **Generations S25/S26**: Deterministic pipeline state machine, gates, and Remotion CLI. Fully functional and mature.
- **Generation S27/S28**: AI routing, capabilities, memory, and creative planning in `ai/`. Fully developed and tested in isolation, but currently air-gapped from production HTTP entrypoints.
- **Generation S28-R**: S28-R Live Authoring engine (`authoring/`, `contracts/authoring.ts`), Multi-Engine Render Planner (`planner/`), and Master Compositor (`compositor/`). Fully integrated into both FastAPI (`/mutate`, `/intent`) and rendering (`render_via_planner.ts`).

---

## 6. Verification Method

To independently verify this structural inventory:
1. **Verify Top-Level Directory Count (Exactly 36)**:
   ```bash
   find . -maxdepth 1 -type d | grep -v "^\.$" | wc -l
   # Returns: 36
   ```
2. **Verify Lockfile Integrity Check**:
   ```bash
   python scripts/validators/check_dependencies_lock.py --check
   # Returns exit code 0
   ```
3. **Verify Ground Truth Synchronization Check**:
   ```bash
   python scripts/validators/check_ground_truth_sync.py --check
   # Returns exit code 0
   ```
4. **Verify TypeScript Contract Compilation**:
   ```bash
   npm run test:contracts
   # Runs vitest and passes
   ```


---


<a name='part-3-entrypoints--production-call-graphs'></a>

## Part 3: Entrypoints & Production Call Graphs


> *Original Source: `documentation/reality_context_pack/02_ENTRYPOINTS_AND_PRODUCTION_CALL_GRAPH.md`*


### Sub-Report Title: Entrypoints and Production Call Graph Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive inventory of all HTTP/WebSocket endpoints, background worker daemons, pipeline orchestrators, rendering scripts, authoring bridges, MCP tools, and test/maintenance entrypoints with concrete call graph tracing.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Entrypoint Topology

The repository exhibits a multi-generation architecture where execution entrypoints are partitioned into distinct operational tiers:
1. **Production HTTP/WebSocket API**: Powered by FastAPI (`api/main.py`), exposing 13 router modules with 53 routed HTTP/WS operations handling projects, runs, assets, artifacts, outputs, gates, render, brand, blueprints, live authoring, and template candidate governance.
2. **Background Worker Daemon**: Decoupled asynchronous polling daemon (`scripts/worker.py` -> `scripts/core/worker.py:PipelineWorker`) implementing lease acquisition, orphan recovery, heartbeat renewal, and process-group pipeline execution.
3. **Pipeline Orchestrator & Gate State Machine**: Linear deterministic CLI orchestrator (`scripts/pipeline.py`) validating hashes and running discrete gate scripts (`scripts/gates/*`) through a 10-stage lifecycle.
4. **Multi-Engine Rendering Pipeline**: Tiered render execution (`scripts/render_project.py`) attempting Multi-Engine RenderPlanner & MasterCompositor (`scripts/render_via_planner.ts`), falling back to RemotionRendererAdapter (`scripts/render_via_adapter.ts`), and falling back to legacy Remotion CLI (`remotion render`).
5. **Live Video Authoring Bridge**: Inter-process Node/TypeScript bridge (`scripts/execute_authoring_mutation.ts`) executing deterministic AST mutations (`UnifiedAuthoringSession`) under optimistic concurrency control (CAS) via `AuthoringService`.
6. **Isolated Development & Compatibility Entrypoints**: Remotion Studio preview (`scripts/open_studio.py`), FastMCP compatibility server (`ai/mcp/compatibility/server.py`), legacy plugin MCP servers (`.agents/plugins/.../mcp-servers/`), and offline regression/benchmark runners (`scripts/run_creative_e2e.py`, `scripts/smoke_openrouter.py`).

Crucially, **zero production entrypoints invoke the AI subsystem (`ai/`)**. Production video rendering operates exclusively on pre-authored project files (`master_plan.md`, `05_blueprint.json`) or pre-structured typed JSON mutations.

---

## 2. Production HTTP & WebSocket Route Catalog (13 Router Modules, 53 Operations)

FastAPI application root is declared in `api/main.py:45` (`app = FastAPI(...)`). Routers are mounted at lines 57–69 with strict CORS middleware (`DynamicCORSMiddleware:49`) and an environment policy lifespan auditor (`lifespan:28-40`).

### 2.1 Complete Route Inventory Table

| # | HTTP Method | Path Pattern | Router Module | Handler Function (Symbol & Line) | Action / Authorization | Request DTO / Payload | Response DTO / Output | Evidence Standard |
|---|---|---|---|---|---|---|---|---|
| 1 | `POST` | `/projects/` | `api/routers/projects.py` | `create:26` | `Action.PROJECT_CREATE` | `ProjectCreateRequest` | `ProjectSummaryDTO` (201) | `CODE_PROVEN` |
| 2 | `GET` | `/projects/` | `api/routers/projects.py` | `list_projects:35` | `Action.PROJECT_READ` | Query params | `List[ProjectSummaryDTO]` | `CODE_PROVEN` |
| 3 | `GET` | `/projects/{project_id}/state` | `api/routers/projects.py` | `get_project_state:43` | `Action.PROJECT_READ` | Path: `project_id` | `LifecycleDTO` (state JSON) | `CODE_PROVEN` |
| 4 | `GET` | `/projects/{project_id}` | `api/routers/projects.py` | `get_project:54` | `Action.PROJECT_READ` | Path: `project_id` | `ProjectSummaryDTO` | `CODE_PROVEN` |
| 5 | `POST` | `/projects/{project_id}/runs` | `api/routers/runs.py` | `create_run:23` | `Action.RUN_EXECUTE` | `RunCreateRequest`, Idempotency Key | `RunResponse` (202 Accepted) | `CODE_PROVEN` & `RUNTIME_REACHABILITY_PROVEN` |
| 6 | `GET` | `/projects/{project_id}/runs/{run_id}` | `api/routers/runs.py` | `get_run:58` | `Action.RUN_READ` | Path: `project_id`, `run_id` | `RunResponse` | `CODE_PROVEN` |
| 7 | `GET` | `/projects/{project_id}/runs` | `api/routers/runs.py` | `list_runs:77` | `Action.RUN_READ` | Query: `limit`, `offset` | `List[RunResponse]` | `CODE_PROVEN` |
| 8 | `POST` | `/projects/{project_id}/runs/{run_id}/cancel` | `api/routers/runs.py` | `cancel_run:97` | `Action.RUN_CANCEL` | Path: `project_id`, `run_id` | `RunResponse` | `CODE_PROVEN` |
| 9 | `GET` | `/projects/{project_id}/runs/{run_id}/events` | `api/routers/runs.py` | `get_run_events:120` | `Action.RUN_READ` | Query: `stream: bool` | SSE stream (`text/event-stream`) or `List[RunEventResponse]` | `CODE_PROVEN` |
| 10 | `GET` | `/projects/{project_id}/assets` | `api/routers/assets.py` | `list_assets:20` | `Action.PROJECT_READ` | Path: `project_id` | `List[AssetDTO]` | `CODE_PROVEN` |
| 11 | `GET` | `/projects/{project_id}/assets/{asset_id}` | `api/routers/assets.py` | `get_asset:35` | `Action.PROJECT_READ` | Path: `project_id`, `asset_id` | `AssetDTO` | `CODE_PROVEN` |
| 12 | `POST` | `/projects/{project_id}/assets` | `api/routers/assets.py` | `upload_asset:50` | `Action.PROJECT_WRITE` | `UploadFile`, Form: `asset_id`, `media_type` | `AssetDTO` (201 Created) | `CODE_PROVEN` |
| 13 | `DELETE` | `/projects/{project_id}/assets/{asset_id}` | `api/routers/assets.py` | `delete_asset:78` | `Action.PROJECT_WRITE` | Path: `project_id`, `asset_id` | `{ok: True}` | `CODE_PROVEN` |
| 14 | `GET` | `/projects/{project_id}/artifacts` | `api/routers/artifacts.py` | `list_artifacts:23` | `Action.PROJECT_READ` | Path: `project_id` | `List[ArtifactMetadataDTO]` | `CODE_PROVEN` |
| 15 | `GET` | `/projects/{project_id}/artifacts/{artifact_type}` | `api/routers/artifacts.py` | `get_artifact:38` | `Action.PROJECT_READ` | Path: `project_id`, `artifact_type` | File streaming / JSON | `CODE_PROVEN` |
| 16 | `GET` | `/projects/{project_id}/review` | `api/routers/artifacts.py` | `get_review:65` | `Action.PROJECT_READ` | Path: `project_id` | `ReviewBundleDTO` | `CODE_PROVEN` |
| 17 | `POST` | `/projects/{project_id}/review/approve` | `api/routers/artifacts.py` | `approve_review:82` | `Action.STAGE_APPROVE` | `ReviewDecisionRequest` | `ReviewDecisionDTO` | `CODE_PROVEN` |
| 18 | `POST` | `/projects/{project_id}/review/reject` | `api/routers/artifacts.py` | `reject_review:113` | `Action.STAGE_APPROVE` | `ReviewDecisionRequest` | `ReviewDecisionDTO` | `CODE_PROVEN` |
| 19 | `GET` | `/projects/{project_id}/outputs/{output_id}` | `api/routers/outputs.py` | `get_output:21` | `Action.PROJECT_READ` | Header: `Range`, Path: `output_id` | `StreamingResponse` (206 Partial Content / 200) | `CODE_PROVEN` |
| 20 | `GET` | `/gates/{project_id}/status` | `api/routers/gates.py` | `status:13` | `Action.STAGE_READ` | Path: `project_id` | `GateStatusDTO` | `CODE_PROVEN` |
| 21 | `POST` | `/gates/{project_id}/start/{stage}` | `api/routers/gates.py` | `start:26` | `Action.STAGE_START` | Path: `stage` | `GateTransitionDTO` | `CODE_PROVEN` |
| 22 | `POST` | `/gates/{project_id}/finish/{stage}` | `api/routers/gates.py` | `finish:37` | `Action.STAGE_FINISH` | Path: `stage` | `GateTransitionDTO` | `CODE_PROVEN` |
| 23 | `POST` | `/gates/{project_id}/approve/{gate}` | `api/routers/gates.py` | `approve:48` | `Action.STAGE_APPROVE` | Path: `gate` | `GateTransitionDTO` | `CODE_PROVEN` |
| 24 | `POST` | `/gates/{project_id}/reject/{gate}` | `api/routers/gates.py` | `reject:60` | `Action.STAGE_APPROVE` | Path: `gate` | `GateTransitionDTO` | `CODE_PROVEN` |
| 25 | `GET` | `/gates/{project_id}/review/status` | `api/routers/gates.py` | `review_status:73` | `Action.STAGE_READ` | Path: `project_id` | `ReviewStatusDTO` | `CODE_PROVEN` |
| 26 | `WEBSOCKET` | `/render/{project_id}/ws` | `api/routers/render.py` | `websocket_endpoint:21` | WebSocket Auth | WebSocket Frames | Streamed Progress JSON | `CODE_PROVEN` |
| 27 | `POST` | `/render/{project_id}` | `api/routers/render.py` | `render:32` | `Action.RUN_EXECUTE` | `RenderRequest` | `RenderResponse` (Deprecated wrapper -> `RunService`) | `CODE_PROVEN` |
| 28 | `GET` | `/brand/{project_id}` | `api/routers/brand.py` | `get_brand:18` | `Action.PROJECT_READ` | Path: `project_id` | `BrandConfigDTO` | `CODE_PROVEN` |
| 29 | `PUT` | `/brand/{project_id}` | `api/routers/brand.py` | `update_brand:29` | `Action.PROJECT_WRITE` | `BrandConfigDTO` | `BrandConfigDTO` | `CODE_PROVEN` |
| 30 | `POST` | `/brand/{project_id}` | `api/routers/brand.py` | `update_brand:29` | `Action.PROJECT_WRITE` | `BrandConfigDTO` | `BrandConfigDTO` | `CODE_PROVEN` |
| 31 | `GET` | `/blueprint/{project_id}` | `api/routers/blueprint.py` | `get_blueprint:21` | `Action.PROJECT_READ` | Path: `project_id` | `BlueprintDTO` | `CODE_PROVEN` |
| 32 | `POST` | `/blueprint/{project_id}/blueprint` | `api/routers/blueprint.py` | `update_blueprint:43` | `Action.PROJECT_WRITE` | `BlueprintDTO` | `BlueprintDTO` | `CODE_PROVEN` |
| 33 | `PUT` | `/blueprint/{project_id}/overrides` | `api/routers/blueprint.py` | `update_overrides:60` | `Action.PROJECT_WRITE` | `OverridesDTO` | `OverridesDTO` | `CODE_PROVEN` |
| 34 | `POST` | `/blueprint/{project_id}/overrides` | `api/routers/blueprint.py` | `update_overrides:60` | `Action.PROJECT_WRITE` | `OverridesDTO` | `OverridesDTO` | `CODE_PROVEN` |
| 35 | `GET` | `/projects/{project_id}/document` | `api/routers/authoring.py` | `get_canonical_document:23` | `Action.PROJECT_READ` | Header: `If-None-Match` | `BlueprintV2` (ETag: revision) | `CODE_PROVEN` |
| 36 | `POST` | `/projects/{project_id}/mutate` | `api/routers/authoring.py` | `apply_mutation:44` | `Action.PROJECT_WRITE` | `AuthoringRequest` (single mutation) | `AuthoringResult` | `CODE_PROVEN` |
| 37 | `POST` | `/projects/{project_id}/batch` | `api/routers/authoring.py` | `apply_batch:74` | `Action.PROJECT_WRITE` | `AuthoringRequest` (mutation array) | `AuthoringResult` | `CODE_PROVEN` |
| 38 | `POST` | `/projects/{project_id}/intent` | `api/routers/authoring.py` | `apply_intent:104` | `Action.PROJECT_WRITE` | `AuthoringRequest` (discriminated union) | `AuthoringResult` | `CODE_PROVEN` |
| 39 | `POST` | `/projects/{project_id}/template` | `api/routers/authoring.py` | `instantiate_template:134` | `Action.PROJECT_WRITE` | Template spec JSON | `AuthoringResult` | `CODE_PROVEN` |
| 40 | `POST` | `/projects/{project_id}/undo` | `api/routers/authoring.py` | `undo:164` | `Action.PROJECT_WRITE` | Empty / operation ID | `AuthoringResult` | `CODE_PROVEN` |
| 41 | `POST` | `/projects/{project_id}/redo` | `api/routers/authoring.py` | `redo:194` | `Action.PROJECT_WRITE` | Empty / operation ID | `AuthoringResult` | `CODE_PROVEN` |
| 42 | `POST` | `/candidates/{candidate_id}/reviews/open` | `api/routers/candidate_reviews.py` | `open_review:69` | `Action.STAGE_START` | Path: `candidate_id` | `ReviewBundleDTO` (201 Created) | `CODE_PROVEN` |
| 43 | `GET` | `/candidates/{candidate_id}/reviews/bundle/active` | `api/routers/candidate_reviews.py` | `get_active_review_bundle:97` | `Action.STAGE_READ` | Path: `candidate_id` | `ReviewBundleDTO` | `CODE_PROVEN` |
| 44 | `GET` | `/candidates/{candidate_id}/reviews/{review_bundle_id}` | `api/routers/candidate_reviews.py` | `get_review_bundle:117` | `Action.STAGE_READ` | Path: `candidate_id`, `bundle_id` | `ReviewBundleDTO` | `CODE_PROVEN` |
| 45 | `POST` | `/candidates/{candidate_id}/reviews/{review_bundle_id}/approve` | `api/routers/candidate_reviews.py` | `approve_candidate:137` | `Action.STAGE_APPROVE` | `ReviewDecisionRequest` | `ReviewDecisionDTO` | `CODE_PROVEN` |
| 46 | `POST` | `/candidates/{candidate_id}/reviews/{review_bundle_id}/reject` | `api/routers/candidate_reviews.py` | `reject_candidate:170` | `Action.STAGE_APPROVE` | `ReviewDecisionRequest` | `ReviewDecisionDTO` | `CODE_PROVEN` |
| 47 | `GET` | `/candidates/{candidate_id}/decisions` | `api/routers/candidate_reviews.py` | `list_decisions:201` | `Action.STAGE_READ` | Path: `candidate_id` | `List[ReviewDecisionDTO]` | `CODE_PROVEN` |
| 48 | `GET` | `/candidates/{candidate_id}/decisions/{decision_id}` | `api/routers/candidate_reviews.py` | `get_decision:215` | `Action.STAGE_READ` | Path: `decision_id` | `ReviewDecisionDTO` | `CODE_PROVEN` |
| 49 | `POST` | `/candidates/{candidate_id}/promote` | `api/routers/candidate_promotions.py` | `promote_candidate:58` | Role: `ADMIN` / `LEAD` | `PromotionRequestDTO` | `PromotionResultDTO` | `CODE_PROVEN` |
| 50 | `GET` | `/candidates/{candidate_id}/promotion` | `api/routers/candidate_promotions.py` | `get_candidate_promotion:96` | `Action.STAGE_READ` | Path: `candidate_id` | `PromotionRecordDTO` | `CODE_PROVEN` |
| 51 | `GET` | `/candidates/promotions/{promotion_id}` | `api/routers/candidate_promotions.py` | `get_promotion_by_id:116` | `Action.STAGE_READ` | Path: `promotion_id` | `PromotionRecordDTO` | `CODE_PROVEN` |
| 52 | `GET` | `/candidates/promotions` | `api/routers/candidate_promotions.py` | `list_promotions:136` | `Action.STAGE_READ` | Query params | `List[PromotionRecordDTO]` | `CODE_PROVEN` |
| 53 | `GET` | `/health/live` | `api/routers/health.py` | `liveness_probe:16` | Unauthenticated | None | `{status: "live", timestamp: ...}` | `CODE_PROVEN` |
| 54 | `GET` | `/health/ready` | `api/routers/health.py` | `readiness_probe:29` | Unauthenticated | None | `{status: "ready", checks: {...}}` | `CODE_PROVEN` |
| 55 | `GET` | `/health` | `api/routers/health.py` | `legacy_health_adapter:46` | Unauthenticated | None | `{status: "ok", mode: "legacy_adapter"}` | `CODE_PROVEN` |

*(Note: Endpoints 28/29/30 and 33/34 share handler functions with multiple HTTP method decorators).*

---

## 3. Background Worker Daemons & Schedulers

### 3.1 Worker Process: `scripts/worker.py` -> `scripts/core/worker.py`
- **Entrypoint**: `python scripts/worker.py` (`scripts/worker.py:24-38`).
- **Daemon Class**: `scripts.core.worker.PipelineWorker` (`scripts/core/worker.py:29-523`).
- **Execution Mechanism**:
  1. `run_loop()` polls `RunRepository` at configurable intervals (default: 1.0s).
  2. Runs orphan recovery (`recover_orphans()`): scans expired leases, resets to `QUEUED` with incremented `attempt` count up to `max_attempts`.
  3. Claims next queued run via `RunRepository.claim_next_run(worker_id, lease_duration)` using atomic database CAS (`UPDATE runs SET status='RUNNING', worker_id=?, lease_expires_at=? WHERE status='QUEUED'`).
  4. Emits `RUN_STARTED` event into `run_events` table.
  5. Spawns background thread `_start_heartbeat(run)` renewing lease every 5.0 seconds.
  6. Validates tenant asset confinement via `ManifestValidator.validate_tenant_assets()`.
  7. Creates ephemeral workspace `tempfile.mkdtemp(prefix=f"ephemeral_{project_id}_{run_id}_")`.
  8. Executes child subprocess in its own process group (`start_new_session=True`):
     ```bash
     python scripts/pipeline.py <project_id>
     ```
     with injected environment: `AGY_RUN_ID`, `AGY_WORKER_ID`, `AGY_WORKSPACE_ID`, `AGY_IS_MANAGED=1`, `AGY_INPUT_REVISION`, `AGY_EPHEMERAL_WORKSPACE`.
  9. Streams stdout/stderr, parsing `[STAGE_START]` and `[STAGE_FINISH]` markers and updating `run_events`.
  10. Upon completion (exit code 0): invokes `_upload_outputs_and_meter()` uploading `out.mp4` to `StorageService` key `workspaces/{ws}/projects/{project_id}/outputs/{run_id}/out.mp4`, records usage in `usage_events`, updates `RunRecord(status=SUCCEEDED)`, emits `RUN_SUCCEEDED`.

---

## 4. Pipeline & Render Execution Call Graphs

### 4.1 Production End-to-End Call Graph: Video Creation & Rendering

```
[HTTP Request] POST /projects/{project_id}/runs
  │
  ▼
api/routers/runs.py : create_run()
  │
  ▼
api/services/run_service.py : RunService.create_run()
  │  ├── validate_project_id(project_id)
  │  ├── RunRepository.find_by_idempotency() [Idempotency Guard]
  │  ├── StateStore.load(proj_dir) [Captures input_revision]
  │  ├── RunRecord(status=QUEUED)
  │  └── RunRepository.create_run() -> SQLite/PostgreSQL `runs` table (HTTP 202 Accepted)
  │
═════════════════════════════════════════════════════════════════════════════
[Asynchronous Worker Boundary]
  │
  ▼
scripts/core/worker.py : PipelineWorker.process_one()
  │  ├── RunRepository.claim_next_run() [Atomic Lease CAS]
  │  ├── RunRepository.record_event("RUN_STARTED")
  │  ├── Heartbeat Thread Spawned
  │  └── Subprocess: python scripts/pipeline.py <project_id>
  │
  ▼
scripts/pipeline.py : main() [Deterministic Gate State Machine]
  │
  ├── [Stage 1: DRAFT -> ASSETS_READY]
  │   └── scripts/gates/asset_gate.py (validates 02_asset_manifest.json)
  │
  ├── [Stage 2: ASSETS_READY -> PLAN_READY]
  │   ├── scripts/gates/plan_gate.py (validates master_plan.md structure & line count)
  │   └── scripts/gates/taste_gate.py (validates typography, pacing, SFX heuristics)
  │
  ├── [Stage 3: PLAN_READY -> BLUEPRINT_READY]
  │   ├── scripts/gates/validate_blueprint.py (validates 05_blueprint.json schema)
  │   ├── scripts/gates/motion_validator.py (validates animation curves & FPS)
  │   └── scripts/gates/code_template_gate.py (validates template AST & forbidden APIs)
  │
  ├── [Stage 4: BLUEPRINT_READY -> MATERIALIZED]
  │   └── scripts/generators/materialize_project.py (copies assets to remotion-app/public)
  │
  ├── [Stage 5: MATERIALIZED -> PROBE_PASSED]
  │   └── scripts/gates/probe_qc.py (renders still frames via Remotion CLI, generates contact sheet)
  │
  ├── [Stage 6: PROBE_PASSED -> AWAITING_REVIEW]
  │   └── ReviewService.create_review_bundle() (persists ReviewBundle in DB & state)
  │
  ├── [Stage 7: AWAITING_REVIEW -> REVIEW_APPROVED]
  │   └── Asserts ReviewDecision == APPROVED or .studio_approved marker exists
  │
  ├── [Stage 8: REVIEW_APPROVED -> RENDERED]
  │   ├── scripts/core/review_service.py : assert_render_authorized()
  │   ├── scripts/core/render_input.py : build_render_input()
  │   └── scripts/render_project.py : main()
  │         │
  │         ├── Priority 1: scripts/render_via_planner.ts (Multi-Engine Planner)
  │         │   ├── planner/render-planner.ts : RenderPlanner.plan()
  │         │   ├── planner/production-render-graph-executor.ts : ProductionRenderGraphExecutor
  │         │   ├── remotion/remotion-renderer-adapter.ts : RemotionRendererAdapter
  │         │   ├── canvas/canvas-renderer-adapter.ts : CanvasRendererAdapter
  │         │   └── compositor/master-compositor.ts : MasterCompositor (FFmpeg stream mux)
  │         │
  │         ├── Priority 2 (Fallback): scripts/render_via_adapter.ts
  │         │   └── remotion/remotion-renderer-adapter.ts
  │         │
  │         └── Priority 3 (Fallback): npx remotion render src/index.ts BlueprintVideo
  │             └── remotion-app/src/index.ts (Direct Remotion CLI execution)
  │
  ├── [Stage 9: RENDERED -> FINAL_QC_PASSED]
  │   └── scripts/gates/final_qc.py (validates audio LUFS, black frames, freeze frames)
  │
  └── [Stage 10: FINAL_QC_PASSED -> COMPLETE]
      └── StateStore.save(LifecycleState.COMPLETE)
  │
═════════════════════════════════════════════════════════════════════════════
[Post-Execution Delivery & Metering]
  │
  ▼
scripts/core/worker.py : _upload_outputs_and_meter()
  ├── scripts/core/storage/storage_service.py : put(out.mp4) -> StorageService
  ├── TenantRepository.record_usage() -> SQLite/PostgreSQL `usage_events` table
  └── RunRepository.finish_run(status=SUCCEEDED)
  │
  ▼
[HTTP Delivery] GET /projects/{project_id}/outputs/{output_id}
  └── api/services/output_service.py : HTTP 206 Partial Content Stream
```

---

### 4.2 Production Live Authoring & Intent Call Graph

```
[HTTP Request] POST /projects/{project_id}/intent
  │
  ▼
api/routers/authoring.py : apply_intent()
  │
  ▼
api/services/authoring_service.py : AuthoringService.execute_authoring()
  ├── validate_project_id(project_id)
  ├── IdempotencyRepository.try_claim_leader() [Checks authoring_idempotency_records]
  ├── CanonicalDocumentRepository.get_document() [Loads current revision from SQL/Storage]
  ├── Optimistic Concurrency Check: base_revision == current_revision
  │
  ▼ [Inter-Process IPC Bridge via Stdin/Stdout JSON]
scripts/execute_authoring_mutation.ts : main()
  ├── Zod validation: AuthoringRequestSchema / AuthoringIntentSchema
  ├── authoring/unified-authoring-session.ts : UnifiedAuthoringSession
  ├── authoring/intent-planner.ts : IntentPlanner.plan() [Deterministic AST mapping]
  └── Emits: updated BlueprintV2, AuthoringChangeSet, applied_mutation_ids
  │
  ▼ [Commit Protocol]
api/services/authoring_service.py :
  ├── CanonicalDocumentRepository.save_document()
  │   ├── StorageService.put(blueprints/rev_{next_rev}_{hash}/blueprint.json)
  │   ├── CAS UPDATE project_states SET revision = next_rev
  │   ├── INSERT INTO project_artifact_versions
  │   └── Syncs local projects/{project_id}/05_blueprint.json
  └── IdempotencyRepository.mark_completed() -> Returns AuthoringResult
```

---

## 5. Other Entrypoint Categories

### 5.1 Development & Studio Entrypoints
- **`scripts/open_studio.py`**:
  - Purpose: Launches local Remotion Studio UI with port management and mechanical safety checks.
  - Verifications: Checks `projects/{project_id}/.studio_unlocked` (written by `probe_qc.py`). Fails closed if mechanical lock is closed.
  - Execution: Executes `npx remotion studio src/index.ts --port 3000` inside `remotion-app/`.
  - Classification: `ACTIVE_PRODUCT_RUNTIME` / `ACTIVE_DEVELOPMENT`.

### 5.2 Candidate Governance Entrypoints
- **`api/routers/candidate_reviews.py` & `candidate_promotions.py`**:
  - Domain Service: `creative_governance/candidates/service.py:TemplateCandidateService`.
  - Promotion Engine: `scripts/core/template_registry_publisher.py:TemplateRegistryPublisher`.
  - Mutation Target: Atomically updates `registry/template-registry-data.json`, `registry/template-registry.tsx`, `contracts/template-runtime-contract.json`, and compatibility catalog `ground-truth/template_catalog.json`.

### 5.3 MCP Entrypoints (Plugin MCP vs FastMCP Compatibility)
1. **Plugin MCP Tools** (`.agents/plugins/super-video-maker-plugin/tools/mcp-servers/`):
   - Entrypoints: `audio-tools-mcp/server.py`, `media-sources-mcp/server.py`, `video-tools-mcp/server.py`, `image-tools-mcp/server.py`, `common-tools-mcp/server.py`, `ffmpeg-mcp-server/server.js`.
   - Classification: `ACTIVE_DEVELOPMENT` / `COMPATIBILITY_ONLY`.
   - Note: Hardcoded Windows paths in `mcp_config.json` require host translation. Direct execution blocked for S27 capabilities.
2. **FastMCP Compatibility Server** (`ai/mcp/compatibility/server.py`):
   - Entrypoint: `CompatibilityMCPServer.run()` exposing tools backed by `ToolGateway`.
   - Classification: `COMPATIBILITY_ONLY`. Zero production routes dispatch through it.

### 5.4 Test Runners & Evaluators
- **`tests/e2e/true_e2e_suite.py`**: Invoked in GitHub Actions CI `strict-e2e` job. Executes pipeline via CLI on synthetic project fixtures.
- **`scripts/smoke_openrouter.py`**: Standalone OpenRouter LLM diagnostic utility.
- **`scripts/run_creative_e2e.py`**: Offline Creative Intelligence evaluation matrix.
- **`scripts/run_creative_regression.py`**: Regression runner across 13 creative quality categories.
- **`scripts/testing/s28_r15_soak_and_load_runner.py`**: High-concurrency database and storage soak tester.

---

## 6. The AI Disconnection Reality

An exhaustive code search across all 13 production router modules in `api/` and all execution scripts in `scripts/` reveals:
- **Total imports of `ai` in `api/`**: **0** (`CODE_PROVEN`).
- **Total imports of `ai` in `scripts/pipeline.py`**: **0** (`CODE_PROVEN`).
- **Total imports of `ai` in `scripts/worker.py`**: **0** (`CODE_PROVEN`).
- **Total imports of `ai` in `scripts/render_project.py`**: **0** (`CODE_PROVEN`).

The entire AI subsystem (`ai/planning`, `ai/routing`, `ai/capabilities`, `ai/context`, `ai/providers`, `ai/tools`, `ai/narrative`, `ai/taste`, `ai/recipes`, `ai/skills`) operates as an isolated evaluation and research framework. The production video engine is 100% deterministic, taking structured JSON or existing disk files, with zero runtime calls to LLMs or AI planning agents during user requests or pipeline runs.


---

