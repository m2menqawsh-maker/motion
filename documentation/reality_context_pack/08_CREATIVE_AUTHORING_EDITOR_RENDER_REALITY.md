# 08 — Creative Authoring, Editor & Render Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Creative Authoring Pipeline, VideoDocument Mutations, Intent Planning, Remotion Renderer Role, Render Graph Execution, and Quality Control
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Reality Verdict

The creative authoring and rendering architecture in this repository is divided into two distinct domains:

1. **A Highly Structured, Deterministic Production Runtime**: The active production path comprises FastAPI authoring services (`api/services/authoring_service.py`), a TypeScript AST mutation engine (`authoring/`, `contracts/`), a background pipeline orchestrator (`scripts/pipeline.py`), and a multi-engine render pipeline (`planner/`, `remotion/`, `compositor/`). This runtime enforces strict transactional CAS (Compare-And-Swap) revisioning, immutable review bundles, and mechanical locks.
2. **An Isolated Creative Planning Platform**: The algorithmic Creative Intelligence pipeline (Brief $\to$ Narrative $\to$ CreativePlan $\to$ Tier Selection $\to$ BlueprintCompiler) exists entirely in Python (`ai/planning/`, `ai/intent/`, `ai/narrative/`, `ai/recipes/`), but is **completely bypassed** by the production HTTP run and render execution paths.

Crucially:
- `POST /projects/{id}/runs` **never reaches Creative Intelligence**; it validates and renders pre-authored blueprints already on disk.
- `POST /projects/{id}/intent` **does not accept natural language**; it strictly requires typed discriminated-union AST intent schemas.
- `CreativePlan` is **never compiled into `VideoDocument` on the production path**; `BlueprintCompiler` is only called in test harnesses.
- Remotion is **contractually declared as a swappable adapter**, but **retains substantial operational authority and lock-in** across template code, CLI fallbacks, and visual QC probes.

---

## 2. Creative Pipeline Trace: Intended vs. Actual Production Flow

```
INTENDED ARCHITECTURE (S28 Vision):
[Raw User Prompt] ──► [CreativeBrief] ──► [NarrativePlan] ──► [CreativePlan]
                                                                     │
                                                                     ▼
[Canonical VideoDocument] ◄── [BlueprintCompiler] ◄── [REUSE/COMPOSE/CREATE]
           │
           ├─► [AuthoringIntents] ──► [CanonicalMutations] (Live Editor)
           │
           ▼
[RenderPlanner] ──► [RenderGraph DAG] ──► [Renderer Adapters (Remotion/Canvas)]
                                                         │
                                                         ▼
[Final MP4 Output] ◄── [Final QC] ◄── [MasterCompositor] ◄── [Render Chunks]


ACTUAL PROVEN PRODUCTION RUNTIME:
[Pre-Existing Disk Files] (master_plan.md, 01_manifest.json, 05_blueprint.json)
           │
           ▼
[POST /projects/{id}/runs] (api/routers/runs.py)
           │
           ▼ Enqueues RunRecord in SQLite (data/runs.db)
[PipelineWorker] (scripts/core/worker.py)
           │
           ▼ Launches Subprocess: python scripts/pipeline.py <project_id>
[scripts/pipeline.py]
   ├── 1. asset_gate.py (Validates files on disk against manifest)
   ├── 2. plan_gate.py (Checks master_plan.md structure; ad-hoc OpenAI fallback)
   ├── 3. taste_gate.py (Deterministic layout/symmetry regex lint)
   ├── 4. validate_blueprint.py (Validates 05_blueprint.json schema)
   ├── 5. motion_validator.py (Validates timing, frame counts, typography)
   ├── 6. code_template_gate.py (Verifies template imports in source code)
   ├── 7. materialize_project.py (Copies media to remotion-app/public/)
   ├── 8. probe_qc.py (npx remotion still -> Generates ReviewBundle & .studio_unlocked)
   ├── 9. [GATE: AWAITING_REVIEW] (Requires user approval -> .studio_approved)
   ├── 10. render_project.py:
   │         ├─ Priority 1: scripts/render_via_planner.ts (RenderPlanner DAG)
   │         ├─ Priority 2: scripts/render_via_adapter.ts (RemotionRendererAdapter)
   │         └─ Priority 3: npx remotion render src/index.ts (Legacy CLI)
   └── 11. final_qc.py (FFprobe verification: aspect ratio, audio/video duration, sync)
           │
           ▼
[out.mp4 Saved & Metered]
```

---

## 3. Mandatory Check C: Exact Runtime Path for `POST /projects/{id}/runs`

### 3.1 Question Statement
> **Check C**: What is the exact runtime path for `POST /projects/{id}/runs`?

### 3.2 Step-by-Step Production Call Graph
Tracing execution from incoming HTTP socket to final output:

1. **HTTP Routing & Ingestion**:
   - `api/routers/runs.py:23-56` (`create_run`):
   - Validates caller authentication and checks permission `Action.RUN_EXECUTE`.
   - Calls `RunService.create_run(project_id, idempotency_key, payload, workspace_id)`.
2. **Domain Service & Idempotency**:
   - `api/services/run_service.py:34-114`:
   - Validates `project_id` format via `validate_project_id()`.
   - Verifies project directory exists on disk (`projects/{project_id}`). If absent, raises `ProjectNotFoundError`.
   - Queries `RunRepository.find_by_idempotency(project_id, idempotency_key)` to prevent duplicate execution or payload mismatch (`IdempotencyConflictError`).
   - Reads current lifecycle state from disk via `StateStore.load(proj_dir)` to snapshot `input_revision`.
   - Instantiates `RunRecord(run_id=f"run_{uuid.uuid4().hex}", workspace_id=ws, project_id=pid, status=RunStatus.QUEUED, input_revision=input_revision)`.
   - Persists record into SQLite database (`data/runs.db`) via `RunRepository.create_run()`.
   - Emits durable event `RUN_QUEUED` via `RunRepository.record_event()`.
   - Returns HTTP `202 Accepted` with `RunResponse`.
3. **Background Worker Claim & Ephemeral Preparation**:
   - `scripts/core/worker.py:180-360` (`PipelineWorker.process_one()`):
   - Background daemon (`scripts/worker.py`) executes polling loop `run_loop()`.
   - Claims queued run using atomic CAS query `RunRepository.claim_next_run(worker_id, lease_duration=300)`. Status becomes `RUN_STARTED`.
   - Spawns background lease heartbeat thread (`_start_heartbeat`).
   - Validates tenant asset isolation against `01_manifest.json` (`ManifestValidator.validate_tenant_assets`).
   - Creates isolated ephemeral workspace (`tempfile.mkdtemp(prefix=f"ephemeral_{project_id}_")`).
   - Spawns child process (`scripts/core/worker.py:289`):
     ```bash
     python scripts/pipeline.py <project_id>
     ```
     with environment variables `AGY_RUN_ID`, `AGY_WORKER_ID`, `AGY_WORKSPACE_ID`, `AGY_INPUT_REVISION`.
4. **Pipeline Orchestrator State Machine**:
   - `scripts/pipeline.py:221-520` (`main()`):
   - Loads project state and verifies recovery engine (`RecoveryEngine.evaluate()`).
   - Sequentially advances state machine:
     - `DRAFT` $\to$ `ASSETS_READY`: runs `scripts/gates/asset_gate.py`.
     - `ASSETS_READY` $\to$ `PLAN_READY`: runs `scripts/gates/plan_gate.py` and `scripts/gates/taste_gate.py`.
     - `PLAN_READY` $\to$ `BLUEPRINT_READY`: runs `scripts/gates/validate_blueprint.py`, `scripts/gates/motion_validator.py`, `scripts/gates/code_template_gate.py`.
     - `BLUEPRINT_READY` $\to$ `MATERIALIZED`: runs `scripts/generators/materialize_project.py` (materializes media to `remotion-app/public/`).
     - `MATERIALIZED` $\to$ `PROBE_PASSED`: runs `scripts/gates/probe_qc.py` (generates contact sheets, creates HMAC-sealed `ReviewBundle`, creates `.studio_unlocked`).
     - `PROBE_PASSED` $\to$ `AWAITING_REVIEW`: pauses for human/client review decision.
     - `AWAITING_REVIEW` $\to$ `REVIEW_APPROVED`: checks for approved `ReviewDecision` in database or `.studio_approved` marker file on disk.
     - `REVIEW_APPROVED` $\to$ `RENDERED`: verifies authorization (`assert_render_authorized()`) and runs `scripts/render_project.py`.
     - `RENDERED` $\to$ `FINAL_QC_PASSED`: runs `scripts/gates/final_qc.py`.
     - `FINAL_QC_PASSED` $\to$ `COMPLETE`.
5. **Render Sub-Path Execution**:
   - `scripts/render_project.py:100-200`:
   - Builds render props (`build_render_input()` writing `.render_props.json`).
   - Executes render through prioritized ladder:
     - Priority 1: `npx tsx scripts/render_via_planner.ts <project_id> --out <tmp_out_file>`
     - Priority 2: `npx tsx scripts/render_via_adapter.ts <project_id> --out <tmp_out_file>`
     - Priority 3 (fallback): `npx remotion render src/index.ts BlueprintVideo <tmp_out_file> --props <props_file>`
   - Moves `tmp_out_file` to `out.mp4`.
6. **Worker Completion & Metering**:
   - `scripts/core/worker.py:306-350`:
   - `PipelineWorker` captures subprocess exit code 0.
   - Invokes `_upload_outputs_and_meter()` to store `out.mp4` into `StorageService` and record usage telemetry.
   - Calls `RunRepository.finish_run(run_id, status=RunStatus.SUCCEEDED)`.
   - Emits terminal event `RUN_SUCCEEDED`.

---

## 4. Mandatory Check D: Creative Intelligence Reachability from `POST /projects/{id}/runs`

### 4.1 Question Statement
> **Check D**: Does `POST /projects/{id}/runs` reach Creative Intelligence?

### 4.2 Code Audit
A line-by-line inspection of the entire execution chain for `POST /projects/{id}/runs` (`api/routers/runs.py`, `api/services/run_service.py`, `scripts/core/worker.py`, `scripts/pipeline.py`, and all 8 gate scripts):
1. **Zero AI Platform Imports**: None of the files in the execution chain import `CreativePlanner`, `NarrativePlanner`, `RecipeSelector`, `TasteEngine`, `BlueprintCompiler`, `ModelRouter`, or `ai.*` (`CODE_PROVEN`).
2. **Pre-Existing File Mandate**:
   - `scripts/pipeline.py:371` asserts: `plan_file = proj_dir / "master_plan.md"`. If absent, pipeline fails closed.
   - `scripts/pipeline.py:381` asserts: `blueprint_file = proj_dir / "05_blueprint.json"`. If absent, pipeline fails closed.
3. **Purely Validating & Rendering**: The run pipeline does not create, generate, or ideate video content. It solely validates, materializes, probes, and renders files that already exist in `projects/{id}/`.

### 4.3 Answer to Check D
**NO** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`).
`POST /projects/{id}/runs` does not reach Creative Intelligence at any point in its execution path.

---

## 5. Mandatory Check F: Nature of `/intent` Endpoint

### 5.1 Question Statement
> **Check F**: Does `/intent` accept natural language or only pre-structured typed intents?

### 5.2 Schema & Handler Inspection
In `api/routers/authoring.py:104-132`:
```python
@router.post("/{project_id}/intent", response_model=AuthoringResultDTO)
async def apply_intent(
    project_id: str,
    payload: Dict[str, Any] = Body(...),
    ...
):
    return AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="apply_intent",
        payload=payload,
        actor_id=principal.actor_id,
    )
```

In `api/services/authoring_service.py:150-176`, the payload is piped directly via JSON IPC to `scripts/execute_authoring_mutation.ts`.

In `contracts/authoring.ts:273-288`, `AuthoringIntentSchema` is defined as a discriminated union over literal field `type`:
```typescript
export const AuthoringIntentSchema = z.discriminatedUnion("type", [
  UpdateTextIntentSchema,           // type: "UPDATE_TEXT", target: { scene_id, layer_id }, text: string
  UpdateTransformIntentSchema,      // type: "UPDATE_TRANSFORM", target: ..., transform: ...
  UpdateStyleIntentSchema,          // type: "UPDATE_STYLE", target: ..., style: ...
  ReplaceMediaIntentSchema,         // type: "REPLACE_MEDIA", target: ..., asset_id: string
  ChangeTimingIntentSchema,         // type: "CHANGE_TIMING", target: ..., in_frame, out_frame
  ApplyTemplateParamIntentSchema,   // type: "APPLY_TEMPLATE_PARAM", param_name, param_value
  CompoundCommandIntentSchema,      // type: "COMPOUND_COMMAND", commands: [...]
  AddLayerIntentSchema,             // type: "ADD_LAYER", layer: CanonicalLayer
  RemoveLayerIntentSchema,          // type: "REMOVE_LAYER", target: ...
  ReorderLayerIntentSchema,         // type: "REORDER_LAYER", target: ..., new_index: number
  AddSceneIntentSchema,             // type: "ADD_SCENE", scene: BlueprintScene
  RemoveSceneIntentSchema,          // type: "REMOVE_SCENE", scene_id: string
  ReorderSceneIntentSchema,         // type: "REORDER_SCENE", scene_id: string, new_index: number
  UnsupportedIntentSchema,          // type: "UNSUPPORTED"
]);
```

In `authoring/intent-planner.ts:5-14`:
```typescript
/**
 * Invariants:
 * - Pure, deterministic, zero-AI-SDK, zero-renderer, zero-side-effects.
 * - Strict Stable-ID entity targeting (scene_id, layer_id, clip_id, keyframe_id).
 * - Fail-closed error handling with structured diagnostics.
 */
```

Passing a raw natural-language string such as `{"prompt": "Make the title bigger and red"}` results in immediate schema validation failure (`ZodError` / HTTP 422 / `AUTHORING_VALIDATION_FAILED`).

### 5.3 Answer to Check F
`/intent` accepts **ONLY pre-structured typed intents** [`CODE_PROVEN`]. It rejects arbitrary natural-language text.

---

## 6. Mandatory Check R: Compilation of `CreativePlan` to Canonical `VideoDocument`

### 6.1 Question Statement
> **Check R**: Is `CreativePlan` compiled into canonical `VideoDocument` on the production path?

### 6.2 Code Evidence
The compilation logic is housed in `BlueprintCompiler` (`ai/planning/compiler.py:62-443`). It takes a `CreativePlan`, `ResolvedTemplateDecision` mappings, a `ManifestV2`, and a `TemplateRegistryContract`, and outputs a canonical `BlueprintV2` / `VideoDocument`.

A comprehensive codebase search for callers of `BlueprintCompiler`:
- `scripts/run_creative_e2e.py:116`: Offline benchmark runner [`TEST_PROVEN`].
- `tests/ai/planning/test_compiler.py`: Unit test suite [`TEST_PROVEN`].
- `tests/ai/e2e/test_full_creative_e2e_matrix.py`: Test harness [`TEST_PROVEN`].
- `scripts/core/blueprint_compiler.py`: Re-export module with zero production callers.
- **Production API (`api/`)**: Exactly 0 callers [`CODE_PROVEN`].
- **Pipeline Worker (`scripts/core/worker.py`, `scripts/pipeline.py`)**: Exactly 0 callers [`CODE_PROVEN`].
- **Authoring Engine (`authoring/`, `api/services/authoring_service.py`)**: Exactly 0 callers [`CODE_PROVEN`].

On the production path, `VideoDocument` is generated in one of three ways:
1. Created from scratch by disk fixtures or seed generators.
2. Created via template instantiation: `POST /projects/{id}/template` $\to$ `AuthoringService.instantiate_template()` $\to$ `contracts/templates.ts:instantiateTemplateToCanonicalDocument()`.
3. Mutated incrementally via `POST /projects/{id}/mutate` or `POST /projects/{id}/batch` $\to$ `UnifiedAuthoringSession`.

### 6.3 Answer to Check R
**NO** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`).
`CreativePlan` is **never** compiled into a canonical `VideoDocument` on the production path.

---

## 7. Mandatory Check S: Runtime Role of Remotion (Adapter vs. Lingering Authority)

### 7.1 Question Statement
> **Check S**: Is Remotion strictly an adapter at runtime or does it retain authority?

### 7.2 The Dual Reality: Adapter Intent vs. Runtime Lock-In

#### Architectural / Contractual Intent (Adapter Role)
- In `remotion/remotion-renderer-adapter.ts:8-16`:
  ```typescript
  // Enforces:
  // - Remotion is strictly a rendering engine; canonical document is the sole authority
  // - Zero mutation of canonical video document
  ```
- `RemotionRendererAdapter` implements `RendererAdapter` (`contracts/renderer.ts`). It declares capabilities, bundles Remotion compositions in temporary staging directories, renders frame chunks, and returns structured `RenderResult` objects.
- In `planner/render-planner.ts`, `RemotionRendererAdapter` is registered alongside `CanvasRendererAdapter` in `CANONICAL_RENDERER_REGISTRY`. The planner decides renderer assignments dynamically based on declared node capabilities.

#### Concrete Runtime Reality (Lingering Structural Authority)
Despite the contractual adapter abstraction, Remotion retains deep operational authority and lock-in across the codebase:
1. **Component Coupling**: All 105 production video templates in `remotion-app/src/templates/` and `templates/` directly import and execute Remotion runtime primitives (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`, `spring`, `interpolate`). They cannot render on Canvas or HTML5 without Remotion.
2. **CLI Fallback Authority**: In `scripts/render_project.py:177-185`, the final fallback executes `npx remotion render src/index.ts BlueprintVideo ...` directly in `remotion-app/`.
3. **Probe QC Dependency**: `scripts/gates/probe_qc.py:180` derives contact sheets and review stills by directly invoking `npx remotion still src/index.ts BlueprintVideo ...`.
4. **Studio UI Authority**: `scripts/open_studio.py:75` launches `npx remotion studio` on port 3000 as the sole live visual inspection interface.
5. **Governance Harness**: `creative_governance/candidates/candidate_runtime_runner.py` compiles candidate templates into a Remotion `CandidateHarness.tsx` importing `registerRoot` from `remotion`.

### 7.3 Answer to Check S
Remotion is an **adapter in contract design**, but **retains substantial lingering operational authority and lock-in at runtime** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`). The system cannot execute visual preview, probe QC, or render any of the 105 production templates without Remotion.

---

## 8. VideoDocument & BlueprintV2 Authority, AST Mutations, and CAS Locking

### 8.1 Document Authority & Invariant Governance
The authoritative video representation is `BlueprintV2` / `VideoDocument` (`contracts/blueprint.ts` and `schemas/blueprint.schema.json`). It enforces:
- Strict Stable-ID targeting for every scene (`scene_id`), layer (`layer_id`), clip (`clip_id`), and keyframe (`keyframe_id`).
- Strict FPS authority (no silent defaults).
- Strict dimensions and aspect ratios (`16:9`, `9:16`, `1:1`).
- Bounded timing: every scene defines non-overlapping `start_frame` and `duration_frames`.

### 8.2 AST Mutations & Session Bridge
When an authoring request arrives at `AuthoringService`:
1. `AuthoringService` acquires a transactional CAS lock via `CanonicalDocumentRepository` (`api/services/authoring_service.py:115-147`).
2. If client `base_revision != curr_rev`, fails closed with `RevisionConflictError`.
3. Passes `(document, request)` to `scripts/execute_authoring_mutation.ts` via Node.js IPC subprocess.
4. `execute_authoring_mutation.ts` calls `UnifiedAuthoringSession` in `authoring/unified-authoring-session.ts`.
5. `IntentPlanner` translates intents into typed `CanonicalMutation` objects (`contracts/mutations.ts`).
6. Mutations are applied immutably, generating a new `BlueprintV2` and a `ChangeSet`.
7. `AuthoringService` validates the new document against `CanonicalDocumentRepository`, increments `revision = curr_rev + 1`, commits to SQL, persists to `StorageService`, and emits invalidation events.

### 8.3 Cache & Artifact Invalidation
Committing an authoring mutation automatically invalidates:
- Any pre-rendered video chunks (`out.mp4`, `.render_props.json`).
- Any active review bundle (`ReviewBundle` state reset).
- Removes `.studio_approved` and `.studio_unlocked` markers from disk, locking Remotion Studio until `probe_qc.py` is re-run.

---

## 9. RenderPlanner, MasterCompositor & Multi-Engine Graph Architecture

### 9.1 Multi-Engine RenderGraph (`planner/render-planner.ts`)
- **Role**: Compiles `BlueprintV2` into an execution DAG (`RenderGraph`) composed of `RenderNode` and `RenderEdge`.
- **Node Classification**: Nodes represent distinct timeline segments, background tracks, overlay tracks, or audio stems.
- **Renderer Assignment**: Resolves compatible renderers from `CANONICAL_RENDERER_REGISTRY` based on required capabilities (e.g., WebGL, Canvas, Remotion).

### 9.2 MasterCompositor (`compositor/master-compositor.ts`)
- **Role**: Timeline stitcher and audio normalizer.
- **Function**: Takes individual scene or layer render chunks produced by the render graph, executes FFmpeg audio mixing with ducking (-16 LUFS voiceover, -24 LUFS music), applies GL transitions, and outputs the final master MP4.

---

## 10. Quality Control Gates, Review Bundles & Mechanical Locks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GATE & LOCK PROTOCOL                               │
├───────────────────┬──────────────────────────┬──────────────────────────────┤
│ Gate / Mechanism  │ Script Location          │ Security / Enforcement Rule  │
├───────────────────┼──────────────────────────┼──────────────────────────────┤
│ Taste Gate        │ scripts/gates/taste_gate │ Layout symmetry, contrast,   │
│                   │                          │ typography overlap checks    │
│ Probe QC          │ scripts/gates/probe_qc   │ npx remotion still probes;   │
│                   │                          │ creates sealed ReviewBundle; │
│                   │                          │ unlocks .studio_unlocked     │
│ Mechanical Lock   │ scripts/open_studio.py   │ Studio UI blocked unless     │
│                   │                          │ .studio_unlocked exists      │
│ Human Review Gate │ scripts/core/review_svc  │ Rendering blocked unless     │
│                   │                          │ approved (.studio_approved)  │
│ Render Auth Gate  │ scripts/render_project   │ assert_render_authorized()   │
│                   │                          │ fails closed if unapproved   │
│ Final QC          │ scripts/gates/final_qc   │ FFprobe stream analysis;     │
│                   │                          │ AV-sync error < 200ms        │
└───────────────────┴──────────────────────────┴──────────────────────────────┘
```

1. **Probe QC (`scripts/gates/probe_qc.py`)**:
   - Computes deterministic frame probe plan (`derive_probe_frame_plan()`).
   - Renders still frames and contact sheets.
   - Seals report with HMAC-SHA256 using `.agents/secrets/.qc_salt`.
   - Touches `.studio_unlocked` on disk.
2. **Review Approval Protocol**:
   - Pipeline transitions to `AWAITING_REVIEW`.
   - Rendering is strictly forbidden until the user reviews contact sheets and approves via `POST /projects/{id}/review/approve` or manual touch of `.studio_approved`.
3. **Final QC (`scripts/gates/final_qc.py`)**:
   - Analyzes `out.mp4` streams using `ffprobe`.
   - Validates aspect ratio against `CANONICAL_ASPECT_MAP`.
   - Validates AV-sync error does not exceed `MAX_AV_SYNC_ERROR_MS = 200.0`.
   - Rejects corrupted or misaligned output files.

---

## 11. File & Symbol Evidence Index

| File Path | Symbol / Function | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `api/routers/runs.py` | `create_run` | 23-56 | Enqueues run; zero AI reachability | `CODE_PROVEN` |
| `api/services/run_service.py` | `RunService.create_run` | 34-114 | Validates project & persists RunRecord | `CODE_PROVEN` |
| `scripts/core/worker.py` | `PipelineWorker.process_one` | 180-360 | Claims run and executes pipeline.py | `CODE_PROVEN` |
| `scripts/pipeline.py` | `main` | 221-520 | 10-stage sequential pipeline orchestrator | `CODE_PROVEN` |
| `api/routers/authoring.py` | `apply_intent` | 104-132 | Accepts typed AuthoringIntentSchema | `CODE_PROVEN` |
| `contracts/authoring.ts` | `AuthoringIntentSchema` | 273-288 | Discriminated union of 14 typed AST intents | `CODE_PROVEN` |
| `authoring/intent-planner.ts` | `IntentPlanner` | 1-60 | Deterministic intent-to-mutation translator | `CODE_PROVEN` |
| `api/services/authoring_service.py` | `execute_authoring` | 81-195 | CAS revision control and Node.js bridge | `CODE_PROVEN` |
| `scripts/execute_authoring_mutation.ts`| `main` | 1-220 | IPC bridge invoking UnifiedAuthoringSession | `CODE_PROVEN` |
| `ai/planning/compiler.py` | `BlueprintCompiler` | 62-443 | Compiles CreativePlan $\to$ BlueprintV2 (0 prod callers)| `CODE_PROVEN` |
| `remotion/remotion-renderer-adapter.ts`| `RemotionRendererAdapter` | 8-50 | Implements RendererAdapter contract | `CODE_PROVEN` |
| `planner/render-planner.ts` | `RenderPlanner` | 1-60 | Multi-engine RenderGraph DAG compiler | `CODE_PROVEN` |
| `scripts/render_project.py` | `main` / render ladder | 100-200 | Executes render priority 1, 2, or 3 | `CODE_PROVEN` |
| `scripts/gates/probe_qc.py` | `main` / seal logic | 1-60 | Renders stills, seals ReviewBundle, unlocks studio | `CODE_PROVEN` |
| `scripts/open_studio.py` | `main` / mechanical lock | 49-65 | Asserts .studio_unlocked before opening studio | `CODE_PROVEN` |
| `scripts/gates/final_qc.py` | `main` / ffprobe analysis | 1-60 | Verifies aspect ratio, duration, AV-sync | `CODE_PROVEN` |

---

## 12. Strategic Recommendations

1. **Wire Creative Planning to Authoring Service**: To allow AI-generated video projects, introduce an asynchronous `POST /projects/{id}/generate` endpoint in FastAPI that calls `CreativeBriefBuilder` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` $\to$ `AuthoringService.save_document()`.
2. **Standardize on RenderPlanner**: Remove legacy Remotion CLI fallback in `scripts/render_project.py` once `scripts/render_via_planner.ts` achieves 100% soak stability in CI.
3. **Decouple Templates from Remotion**: For true renderer independence, extract template visual markup into framework-agnostic AST declarations, allowing `CanvasRendererAdapter` to render templates without the Remotion React runtime.
