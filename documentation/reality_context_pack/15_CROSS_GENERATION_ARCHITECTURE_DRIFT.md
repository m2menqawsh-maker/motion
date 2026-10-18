# Cross-Generation Architecture Drift Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Historical breakdown of the six distinct architectural generations present in the repository, evolutionary timeline, layer responsibilities, cross-generational dependency matrix, and architectural gap analysis.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Architectural Generations Taxonomy

The codebase contains artifacts, patterns, and conventions from six distinct architectural generations. Each generation was designed to solve specific operational challenges, resulting in overlapping layers of authority, duplicate abstractions, and isolated subsystems.

```
========================================================================================================
                               EVOLUTIONARY TIMELINE & GENERATIONS
========================================================================================================

  Gen 1: Pre-S25          Gen 2: S25/S26 Core       Gen 3: S27 AI Infra       Gen 4: S28 Creative
  [Ad-hoc / Remotion]  -> [SaaS / Deterministic] -> [Context / Routing]   ->  [Planning / Taste]
  • Raw CLI scripts       • FastAPI & Workers       • ContextBuilder          • CreativePlanner
  • Direct Remotion       • CAS StateStore          • ModelRouter             • NarrativePlanner
  • Plugin MCPs           • 10 Pipeline Gates       • ProviderRegistry        • RecipeRegistry
                          • StorageService          • MemoryService           • SkillRegistry
                                 |                         |                         |
                                 +-------------------------+-------------------------+
                                                           |
                                                           v
                              Gen 5: S28-M Capability        Gen 6: S28-R Live Authoring
                              [Capability / FastMCP]     ->  [Renderer-Neutral / Editor]
                              • CapabilityRouter             • BlueprintV2 / VideoDocument
                              • ToolGateway (15 stages)      • UnifiedAuthoringSession
                              • 32 Native Capabilities       • RenderPlanner & Graph
                              • AST Provider Blockers        • Remotion & Canvas Adapters
========================================================================================================
```

---

## 2. Detailed Generation Profiles

### 2.1 Generation 1: Pre-S25 (Ad-Hoc Video Engine & Direct Remotion)
- **Primary Focus**: Prototype video generation, raw shell invocations, and agent-driven direct file editing.
- **Key Artifacts & Patterns**:
  - `scripts/deliver_project.py`, `scripts/open_studio.py`
  - `.agents/plugins/super-video-maker-plugin/tools/` (`heygen_client.py`, `elevenlabs_voice.py`, `replicate_video.py`)
  - Direct execution of `npx remotion render src/index.ts`
  - Hardcoded local paths and Windows paths (`C:/video/...` in `mcp_config.json`)
  - External MCP servers (`audio-tools-mcp`, `media-sources-mcp`, `ffmpeg-mcp-server`)
- **Current Status**: **QUARANTINED / PARTIALLY CONFINED** [`CODE_PROVEN`].
  - Direct provider scripts were actively blocked with hard exceptions (`PermissionError("DIRECT SECRET ACCESS BLOCKED...")`).
  - Direct rendering via `npm run render` in `remotion-app` exits with a hard stop (`remotion-app/package.json:9`).
  - Residual CLI fallbacks remain in `scripts/render_project.py:177`.

### 2.2 Generation 2: S25 / S26 Core (Deterministic SaaS Backend & Gate Pipeline)
- **Primary Focus**: SaaS reliability, deterministic stage gating, atomic state transitions, concurrency safety, and worker-based asynchronous execution.
- **Key Artifacts & Patterns**:
  - FastAPI application: `api/main.py`, `api/routers/projects.py`, `api/routers/runs.py`, `api/routers/assets.py`
  - State management: `scripts/core/state_store.py` (atomic CAS on `.pipeline_state.json`), `scripts/core/lifecycle_service.py`
  - Queue & persistence: `scripts/core/run_repository.py` (SQLite/PostgreSQL `runs` table), `scripts/core/worker.py` (`PipelineWorker` daemon)
  - Deterministic pipeline orchestrator: `scripts/pipeline.py` enforcing sequential gate stages (`asset_gate.py`, `plan_gate.py`, `taste_gate.py`, `validate_blueprint.py`, `probe_qc.py`, `final_qc.py`)
  - Storage abstraction: `scripts/core/storage/storage_service.py` (`LocalStorageBackend`, `S3CompatibleStorageBackend`)
  - Confinement policies: `scripts/core/security/path_policy.py`, `command_policy.py`
- **Current Status**: **ACTIVE PRODUCTION RUNTIME** [`RUNTIME_REACHABILITY_PROVEN`].
  - Powers all active HTTP requests and asynchronous render jobs.

### 2.3 Generation 3: S27 AI Platform Infrastructure
- **Primary Focus**: Structured AI context assembly, token budgeting, multi-provider model routing, and persistent semantic memory.
- **Key Artifacts & Patterns**:
  - Context engine: `ai/context/builder.py` (`ContextBuilder`), token estimation (`DeterministicTokenEstimator`), compression, ranking
  - Model routing: `ai/routing/router.py` (`ModelRouter`), ranking models by latency, cost, and quality
  - Provider management: `ai/providers/registry.py` (`ProviderRegistry`), `ai/providers/definitions.py` (`CANONICAL_PROVIDERS`)
  - Memory service: `ai/memory/service.py` (`MemoryService`), vector embeddings, temporal decay
  - Knowledge platform: `ai/knowledge/router.py` (`KnowledgeRouter`), `ai/knowledge/registry.py`
- **Current Status**: **ACTIVE DEVELOPMENT / ISOLATED SUBSYSTEM** [`CODE_PROVEN`].
  - Completely decoupled from `api/` and `scripts/pipeline.py`. Has 0 production callers.

### 2.4 Generation 4: S28 Creative Intelligence
- **Primary Focus**: High-level creative direction, narrative structuring, taste evaluation, declarative recipes, and agent skills.
- **Key Artifacts & Patterns**:
  - Creative planning: `ai/planning/creative_planner.py` (`CreativePlanner`), `CreativeBrief`, `CreativePlan`
  - Narrative planning: `ai/narrative/planner.py` (`NarrativePlanner`), archetype beat sequencing
  - AI Taste engine: `ai/taste/engine.py` (`TasteEngine`), evaluating `CANONICAL_TASTE_RULES`
  - Recipe platform: `ai/recipes/registry.py` (`RecipeRegistry`), globbing and migrating `recipes/*.json`
  - Skill platform: `ai/skills/registry.py` (`SkillRegistry`), `ai/skills/loader.py` (loading `.agents/skills/*/SKILL.md`)
  - Reuse & composition: `ai/planning/reuse_engine.py`, `ai/planning/compose_engine.py`, `ai/planning/creative_tier_policy.py`
- **Current Status**: **ACTIVE DEVELOPMENT / EVALUATION HARNESS** [`CODE_PROVEN`, `TEST_PROVEN`].
  - Extensively tested in offline benchmarks (`scripts/run_creative_e2e.py`, `scripts/run_creative_regression.py`), but completely uncalled on the production HTTP run path.

### 2.5 Generation 5: S28-M Capability & MCP Modernization
- **Primary Focus**: Eliminating raw JSON-RPC MCP calls in favor of strongly typed Python capability routing, strict AST guards, and FastMCP compatibility.
- **Key Artifacts & Patterns**:
  - Capability catalog: `ai/capabilities/catalog.py` (32 capabilities spanning Audio, Image, Video, Speech, Vision, Ingestion, System)
  - Capability router: `ai/routing/capability_router.py` (`CapabilityRouter`)
  - Tool execution gateway: `ai/tools/gateway.py` (`ToolGateway` enforcing a 15-stage pipeline: lookup, lease, auth, idempotency, execution, validation)
  - Native adapters: `NativeToolAdapter`, `DomainServiceAdapter` (`ai/tools/adapters/`)
  - MCP compatibility server: `ai/mcp/compatibility/server.py` (`CompatibilityMCPServer`) wrapping FastMCP for external clients
  - AST architecture guards: `tests/ai/audit/test_s28_m11_final_architecture_audit.py` (forbidding raw MCP and enforcing capability boundaries)
- **Current Status**: **ACTIVE TESTED SUBSYSTEM / COMPATIBILITY BOUNDARY** [`TEST_PROVEN`, `CODE_PROVEN`].
  - Successfully modernized tool interfaces for AI agents, but neither `api/main.py` nor `scripts/pipeline.py` dispatches through `CapabilityRouter`.

### 2.6 Generation 6: S28-R Renderer Independence & Live Authoring
- **Primary Focus**: Engine-neutral video document representation, interactive AST mutations, multi-engine render planning, and Remotion decoupling.
- **Key Artifacts & Patterns**:
  - Authoritative document schema: `contracts/blueprint.ts` (`BlueprintV2` / `VideoDocument`)
  - Authoring contracts: `contracts/authoring.ts` (`AuthoringIntentSchema`, `CanonicalMutationSchema`)
  - Authoring engine: `authoring/unified-authoring-session.ts`, `authoring/intent-planner.ts`
  - Live authoring API: `api/routers/authoring.py` (`/projects/{id}/document`, `/mutate`, `/batch`, `/intent`, `/template`, `/undo`, `/redo`)
  - Concurrency & persistence: `scripts/core/canonical_document_repository.py` (ETag & CAS versioning)
  - Multi-engine render planner: `planner/render-planner.ts` (`RenderPlanner`), DAG executor (`planner/production-render-graph-executor.ts`)
  - Renderer adapters: `remotion/remotion-renderer-adapter.ts`, `canvas/canvas-renderer-adapter.ts`
  - Master compositor: `compositor/master-compositor.ts` (timeline assembly, audio mixing, FFmpeg multiplexing)
- **Current Status**: **ACTIVE PRODUCT RUNTIME** [`RUNTIME_REACHABILITY_PROVEN`].
  - S28-R successfully integrated into both the HTTP authoring API and the render pipeline (`scripts/render_project.py` Priority 1).

---

## 3. Cross-Generational Dependency & Interop Matrix

The following matrix documents which generation directly calls or consumes artifacts from other generations:

| Caller Generation \ Callee Generation | Pre-S25 (Gen 1) | S25/S26 Core (Gen 2) | S27 AI Infra (Gen 3) | S28 Creative (Gen 4) | S28-M Capability (Gen 5) | S28-R Live Authoring (Gen 6) |
|---|---|---|---|---|---|---|
| **Pre-S25 (Gen 1)** | Direct scripts | **NO** | **NO** | **NO** | **NO** | **NO** |
| **S25/S26 Core (Gen 2)** | Subprocess CLI fallback (`scripts/render_project.py:177`) | Core runtime (`api/`, `worker.py`, `pipeline.py`) | **NO (0 imports)** | **NO (0 imports)** | **NO (0 imports)** | Calls S28-R RenderPlanner (`render_via_planner.ts`) |
| **S27 AI Infra (Gen 3)** | **NO** | Reads `DatabaseEngine` in tests | Self-contained (`ContextBuilder`, `ModelRouter`) | **NO** | Injected into CapabilityRouter | **NO** |
| **S28 Creative (Gen 4)** | **NO** | **NO** | Calls `KnowledgeRouter`, `ModelRouter` | Self-contained (`CreativePlanner`, `NarrativePlanner`) | Calls `CapabilityRouter` | Compiles to `BlueprintV2` schema via `compiler.py` (test only) |
| **S28-M Capability (Gen 5)** | Wraps legacy MCPs via FastMCP server | Delegates to `DomainServiceAdapter` | Calls `ModelRouter` via `ModelRouterSeam` | **NO** | Self-contained (`CapabilityRouter`, `ToolGateway`) | **NO** |
| **S28-R Live Authoring (Gen 6)**| Fallback to Remotion CLI | Uses `CanonicalDocumentRepository`, `StorageService`, CAS | **NO** | **NO** | **NO** | Self-contained (`UnifiedAuthoringSession`, `RenderPlanner`) |

---

## 4. Architectural Drift & Gap Analysis

### 4.1 The AI-to-Production Chasm (Gen 3/4/5 Disconnection)
- **The Intended Design**:
  A user submits a creative brief via API $\to$ `ContextBuilder` aggregates memory and knowledge $\to$ `NarrativePlanner` structures story beats $\to$ `CreativePlanner` resolves templates/recipes $\to$ `CapabilityRouter` acquires voiceover and imagery $\to$ `BlueprintCompiler` outputs a canonical `VideoDocument` $\to$ S28-R Live Authoring modifies the AST $\to$ S28-R RenderPlanner renders the final MP4.
- **The Actual Reality**:
  - The production pipeline (`api/` $\to$ `worker.py` $\to$ `pipeline.py`) is **100% deterministic** and requires pre-existing `master_plan.md` and `05_blueprint.json` files on disk.
  - Gen 3 (`ai/context/`, `ai/routing/`), Gen 4 (`ai/planning/`, `ai/taste/`), and Gen 5 (`ai/capabilities/`, `ai/tools/`) operate strictly as an offline library or evaluation harness.
  - There is zero HTTP or daemon wiring connecting the AI platform to the production run queue.

### 4.2 The S28-R Remotion Dual Authority Drift
- **The Intended Design**:
  Remotion is strictly an engine-neutral renderer adapter (`RemotionRendererAdapter`), equal to `CanvasRendererAdapter`. Canonical video truth resides exclusively in `BlueprintV2`.
- **The Actual Reality**:
  - All 105 production templates are implemented as React TSX components importing Remotion hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`).
  - `scripts/render_project.py` retains a hard fallback to raw `npx remotion render`.
  - `scripts/gates/probe_qc.py` invokes `npx remotion still` directly.
  - While S28-R decoupled the document format, the template asset library remains deeply bound to the Remotion React runtime.

### 4.3 The State Authority Drift (Disk `.pipeline_state.json` vs SQL `project_states`)
- **The Intended Design**:
  In S25 single-node mode, `.pipeline_state.json` was the sole authority.
  In S26 multi-tenant mode, `project_states` in SQLite/PostgreSQL became the transactional CAS store.
- **The Actual Reality**:
  - `scripts/pipeline.py` still reads and writes `.pipeline_state.json` directly on disk (`StateStore.load()`).
  - `AuthoringService` writes to `CanonicalDocumentRepository` and updates `project_states` in SQL.
  - A dual-state reality exists where disk state and SQL state must be manually synchronized.
