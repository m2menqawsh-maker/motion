# True Product Journey Gap Analysis Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous edge-by-edge architectural breakdown of the ideal end-to-end product journey (from user prompt to final video streaming), classifying each transition, proving reachability or isolating breakage points, without performing code repairs.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. The Ideal Product Journey vs. Real System Topology

The intended product vision promises a seamless autonomous-to-interactive video creation pipeline:
`Prompt / Brief` $\to$ `AI Creative Planning` $\to$ `Autonomous Asset Acquisition` $\to$ `Canonical BlueprintV2 Compilation` $\to$ `Live Interactive Authoring` $\to$ `Deterministic Quality Gates` $\to$ `Human Approval` $\to$ `Multi-Engine Rendering` $\to$ `Final QC & Video Delivery`.

Forensic investigation reveals that this ideal journey is severed into two disconnected architectural hemispheres:
1. **The Disconnected AI Hemisphere** (Edges 1 through 6): Implemented in `ai/` and heavily verified in unit/eval test suites, but completely disconnected from the production HTTP API and background worker daemons.
2. **The Active Deterministic Engine Hemisphere** (Edges 7 through 12): Fully wired and proven in production, but starting exclusively from pre-existing disk files or manual structured API mutations.

---

## 2. Edge-by-Edge Journey Classification & Trace

```
========================================================================================================
                               EDGE-BY-EDGE PRODUCT JOURNEY MAP
========================================================================================================

  [1. User Prompt / Brief]
           |
           | Edge 1: Prompt -> Brief (MISSING ON API)
           v
  [2. CreativeBrief]
           |
           | Edge 2: Brief -> NarrativePlan (TEST_PROVEN_ONLY)
           v
  [3. NarrativePlan]
           |
           | Edge 3: NarrativePlan -> CreativePlan (TEST_PROVEN_ONLY)
           v
  [4. CreativePlan]
           |
           | Edge 4: Plan -> Recipe & Template Resolution (TEST_PROVEN_ONLY)
           | Edge 5: Autonomous Asset Acquisition (TEST_PROVEN_ONLY)
           v
  [5. Resolved Creative Elements]
           |
           | Edge 6: CreativePlan -> BlueprintV2 Compilation (BROKEN / UNWIRED TO PROD)
           v
======================= THE ARCHITECTURAL CHASM ========================================================
           v
  [6. Canonical VideoDocument (BlueprintV2)]
           |
           | Edge 7: Interactive Live Authoring & AST Mutation (PRODUCTION_PROVEN)
           v
  [7. Mutated Document on Disk / Storage]
           |
           | Edge 8: POST /projects/{id}/runs & Stage Gating (PRODUCTION_PROVEN)
           v
  [8. Probe QC Verification & Unlocked Studio]
           |
           | Edge 9: Human Review & Decision Bundle (PRODUCTION_PROVEN)
           v
  [9. Review Approved Authorization]
           |
           | Edge 10: Multi-Engine RenderGraph Execution (PRODUCTION_PROVEN)
           | Edge 11: Renderer Adapter (Remotion / Canvas) (PRODUCTION_PROVEN)
           v
  [10. Rendered MP4 & Final QC]
           |
           | Edge 12: Final QC & HTTP 206 Streaming Delivery (PRODUCTION_PROVEN)
           v
  [11. Client Video Playback]
========================================================================================================
```

---

### Edge 1: User Natural-Language Prompt $\to$ `CreativeBrief`
- **Intended Behavior**: A user sends a prompt (e.g., "Create a 30s SaaS product explainer for Acme") via HTTP API, creating a structured `CreativeBrief`.
- **Observed Behavior**: All 13 routers mounted in `api/main.py:57-70` operate strictly on structured DTOs (`ProjectCreateRequest`, `RunCreateRequest`, `AuthoringRequest`). No HTTP endpoint accepts a prompt or brief.
- **Classification**: **`MISSING`** on Production Runtime [`CODE_PROVEN`].
- **Production Caller**: `NONE` / `UNKNOWN`.
- **Test Reality**: Tested in `tests/ai/planning/test_creative_planner.py` where `CreativeBrief` is instantiated manually in Python memory.
- **Breakage Analysis**: Complete absence of prompt ingestion router.

---

### Edge 2: `CreativeBrief` $\to$ `NarrativePlan`
- **Intended Behavior**: `NarrativePlanner` ingests `CreativeBrief` and synthesizes archetype beats and audio modes.
- **Observed Behavior**: `ai/narrative/planner.py:35-80` implements `NarrativePlanner.plan()`. It has zero callers in `api/` or `scripts/pipeline.py`.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Executed in `tests/ai/narrative/test_narrative_planner.py` and regression runner `ai/regression/runner.py:171`.

---

### Edge 3: `NarrativePlan` $\to$ `CreativePlan`
- **Intended Behavior**: `CreativePlanner` combines `CreativeBrief` and `NarrativePlan` to produce a proposed `CreativePlan`.
- **Observed Behavior**: `ai/planning/creative_planner.py:58-115` implements `CreativePlanner.plan()`. Zero callers in production code.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Tested in `tests/ai/planning/test_creative_planner.py` and `scripts/run_creative_e2e.py:70`.

---

### Edge 4: `CreativePlan` $\to$ Recipe & Template Resolution
- **Intended Behavior**: `CreativeTierPolicy`, `ReuseEngine`, and `RecipeSelector` match beats against registered templates and recipes.
- **Observed Behavior**: Implemented in `ai/planning/recipe_selector.py` and `reuse_engine.py`. Reads `recipes/*.json` and `registry/template-registry-data.json`. Zero production callers.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Tested in `tests/ai/recipes/test_recipe_platform.py` and `tests/ai/planning/test_recipe_selector.py`.

---

### Edge 5: Autonomous Asset Acquisition & Processing
- **Intended Behavior**: AI autonomously acquires voiceover, images, and SFX via `CapabilityRouter` $\to$ `ToolGateway` $\to$ `AssetService`.
- **Observed Behavior**:
  - **Manual Path**: Fully proven. `POST /projects/{id}/assets` $\to$ `AssetService.upload_asset()` $\to$ `StorageService` $\to$ `02_asset_manifest.json` (`PRODUCTION_PROVEN`).
  - **AI Autonomous Path**: Implemented in `ai/capabilities/` and `ai/tools/gateway.py`, but has zero callers in production API.
- **Classification**: **`TEST_PROVEN_ONLY`** for AI Autonomous Path [`CODE_PROVEN`, `TEST_PROVEN`].

---

### Edge 6: `CreativePlan` $\to$ Canonical `VideoDocument` (`BlueprintV2`) Compilation
- **Intended Behavior**: `BlueprintCompiler` transforms advisory `CreativePlan` into authoritative `contracts/blueprint.ts:BlueprintV2`.
- **Observed Behavior**:
  - `BlueprintCompiler` is defined in `ai/planning/compiler.py:62-443`.
  - It is **never called** by `AuthoringService` or the production pipeline.
  - Production authoring creates documents strictly from scratch or via template instantiation (`instantiateTemplateToCanonicalDocument`).
- **Classification**: **`BROKEN / UNWIRED TO PRODUCTION`** [`CODE_PROVEN`].
- **Production Caller**: `NONE` (Callers strictly in test runners: `scripts/run_creative_e2e.py:75`).
- **Breakage Analysis**: This is the primary chasm disconnecting the AI planning stack from the authoring and rendering engine.

---

### Edge 7: Interactive Live Authoring & AST Mutation
- **Intended Behavior**: Clients view and edit canonical `VideoDocument` via atomic AST mutations.
- **Observed Behavior**:
  - `GET /projects/{id}/document` $\to$ loads `BlueprintV2`.
  - `POST /projects/{id}/mutate` or `/batch` or `/intent` $\to$ `AuthoringService.execute_authoring()`.
  - Concurrency verified with ETag / CAS.
  - Dispatched via subprocess to `scripts/execute_authoring_mutation.ts` $\to$ `UnifiedAuthoringSession`.
  - Result persisted transactionally to SQL and `StorageService`.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/api/test_authoring_router.py`, `tests/contracts/test_authoring_contracts.ts`.

---

### Edge 8: Pipeline Run Enqueue & Deterministic Stage Gating
- **Intended Behavior**: A run is enqueued and executed through the 10 sequential quality gates.
- **Observed Behavior**:
  - `POST /projects/{id}/runs` $\to$ `RunService.create_run()` $\to$ inserts `RunRecord(status=QUEUED)` in SQLite/PostgreSQL `runs` table (HTTP 202).
  - Background daemon `scripts/core/worker.py` claims run with lease and executes `python scripts/pipeline.py <project_id>`.
  - `scripts/pipeline.py` advances states: `DRAFT` $\to$ `ASSETS_READY` (`asset_gate.py`) $\to$ `PLAN_READY` (`plan_gate.py`, `taste_gate.py`) $\to$ `BLUEPRINT_READY` (`validate_blueprint.py`, `motion_validator.py`, `code_template_gate.py`) $\to$ `MATERIALIZED` (`materialize_project.py`) $\to$ `PROBE_PASSED` (`probe_qc.py`).
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/e2e/true_e2e_suite.py`, `tests/gates/*`, `tests/core/*`.

---

### Edge 9: Human Review & Approval Gate
- **Intended Behavior**: Pipeline halts after Probe QC awaiting human review; client approves or rejects.
- **Observed Behavior**:
  - `probe_qc.py` unlocks `.studio_unlocked` and creates `ReviewBundle`.
  - `GET /projects/{id}/review` returns preview bundle.
  - `POST /projects/{id}/review/approve` calls `ReviewService.approve()`, setting state to `REVIEW_APPROVED` and authorizing render.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/core/test_review_service.py`, `tests/api/test_artifacts.py`.

---

### Edge 10: Multi-Engine Render Planning & Graph Execution
- **Intended Behavior**: `scripts/render_project.py` builds render inputs and invokes `RenderPlanner`.
- **Observed Behavior**:
  - `scripts/render_project.py:130` validates authorization via `assert_render_authorized()`.
  - Invokes Priority 1: `npx tsx scripts/render_via_planner.ts <project_id>`.
  - `planner/render-planner.ts` compiles `BlueprintV2` into a Directed Acyclic Graph (DAG) executed by `ProductionRenderGraphExecutor`.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/planner/*`, `tests/e2e/test_pipeline_integration.py`.

---

### Edge 11: Renderer Adapter Execution (Remotion / Canvas)
- **Intended Behavior**: Independent renderer adapters render visual composition frames.
- **Observed Behavior**:
  - `RemotionRendererAdapter` (`remotion/remotion-renderer-adapter.ts`) mounts Remotion composition.
  - Fallback to Remotion CLI (`scripts/render_project.py:177`) if planner encounters node failures.
  - Audio and video multiplexed via `MasterCompositor` (`compositor/master-compositor.ts`).
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/remotion/*`, `tests/compositor/*`.

---

### Edge 12: Final QC & Video Delivery
- **Intended Behavior**: Final quality control checks video specs, uploads MP4 to storage, and streams to client.
- **Observed Behavior**:
  - `scripts/gates/final_qc.py` verifies duration, loudness, resolution, and encoding specs, producing `09_final_qc_report.json`.
  - Pipeline worker uploads `out.mp4` to `StorageService` and marks run `SUCCEEDED`.
  - Client retrieves video via `GET /projects/{id}/outputs/{output_id}`, which supports HTTP 206 Partial Content Range streaming.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/api/test_outputs.py`, `tests/gates/test_final_qc.py`.

---

## 3. Journey Summary Table

| Edge # | Journey Transition | Source Component | Target Component | Reality Classification | Primary Obstacle / Breakage Point |
|---|---|---|---|---|---|
| **1** | Prompt $\to$ Brief | Client User | `CreativeBrief` | **`MISSING`** | Zero prompt intake endpoints in `api/`. |
| **2** | Brief $\to$ Narrative | `CreativeBrief` | `NarrativePlan` | **`TEST_PROVEN_ONLY`** | Unimported in production API/pipeline. |
| **3** | Narrative $\to$ Plan | `NarrativePlan` | `CreativePlan` | **`TEST_PROVEN_ONLY`** | Unimported in production API/pipeline. |
| **4** | Plan $\to$ Template/Recipe | `CreativePlan` | `RecipeRegistry` / Templates | **`TEST_PROVEN_ONLY`** | Unwired to production runs. |
| **5** | Asset Acquisition | AI Agent | `StorageService` / Manifest | **`TEST_PROVEN_ONLY`** (AI) / **`PROVEN`** (Manual) | AI capability router not triggered by API. |
| **6** | Plan $\to$ Document | `CreativePlan` | `BlueprintV2` | **`BROKEN`** | `BlueprintCompiler` has 0 production callers. |
| **7** | Live Authoring | HTTP Client | `UnifiedAuthoringSession` | **`PRODUCTION_PROVEN`** | Fully functional via `/mutate`, `/intent`. |
| **8** | Pipeline Gating | `POST .../runs` | `scripts/pipeline.py` | **`PRODUCTION_PROVEN`** | Fully functional via worker daemon. |
| **9** | Human Review | `ReviewService` | `StateStore` | **`PRODUCTION_PROVEN`** | Fully functional via `/review/approve`. |
| **10** | Render Planning | `render_project.py` | `RenderPlanner` | **`PRODUCTION_PROVEN`** | Priority 1 planner execution functional. |
| **11** | Render Adapters | `RenderGraph` | `RemotionRendererAdapter` | **`PRODUCTION_PROVEN`** | Adapters render Remotion compositions. |
| **12** | QC & Delivery | `final_qc.py` | `GET .../outputs` | **`PRODUCTION_PROVEN`** | Final QC and HTTP 206 streaming proven. |
