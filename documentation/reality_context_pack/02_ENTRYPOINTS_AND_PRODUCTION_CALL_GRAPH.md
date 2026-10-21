# Entrypoints and Production Call Graph Reality Report

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
