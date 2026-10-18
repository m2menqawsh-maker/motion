# Repository Structural Inventory & Architectural Directory Taxonomy

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
