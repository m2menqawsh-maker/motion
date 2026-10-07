# S28-R01 Audit Report: Render / Editor Reality Baseline

**Audit Identifier**: `S28-R01-AUDIT-FINAL`  
**Milestone**: `S28-R01 — Render / Editor Reality Audit & Remotion Coupling Baseline`  
**Date**: October 6, 2026  
**Auditor**: Antigravity S28-R Reality Auditor  
**Gate Decision**: **`S28-R01 PASS`**  

---

## 1. Repository Baseline & Inspection Scope

- **Repository Root**: `/home/eng_Momen/Projects/المشروع الحالي/Video maker`
- **Git Branch**: `feature/s27-ai-platform`
- **Git SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`
- **Working Tree State**: Clean relative to S28-R scope; contains uncommitted S28-M modernization files for audio/media processing.
- **Runtime Toolchains Verified**:
  - Python: `3.14.7`
  - Node.js: `v26.7.0`
  - npm: `11.19.0`
  - uv: `0.12.17`
  - FFmpeg / FFprobe: `8.1.3`
  - Docker: `5.8.7`
- **Scope Inspected**:
  - `contracts/` (Blueprint V2, animations, asset resolver, render input gate, template schemas)
  - `registry/` (Metadata data JSON, runtime registry TSX, effects catalog, types)
  - `templates/` (70+ scene and element wrappers, effects)
  - `remotion-app/` (`Root.tsx`, `BlueprintVideo.tsx`, `merge.ts`, `loadProjectData.ts`, `remotion.config.ts`, `src/engine/`, `src/compositions/`, `src/remotion/`)
  - `scripts/` (`pipeline.py`, `render_project.py`, `open_studio.py`, `worker.py`, `core/`, `gates/`, `generators/`, `validators/`)
  - `creative_governance/` and `ai/` (`creative_planner.py`, `compiler.py`, candidate validation gates)
  - `api/` (routers, services, health check, WebSockets)
  - `tests/` (`tests/remotion/`, `tests/architecture/`, `tests/ai/`)
  - `projects/` (sample project fixtures and run records)

---

## 2. Answers to the 24 Mandated Architecture Questions

### 1. ما هو Source of Truth الحالي للفيديو؟
The runtime single source of truth for video composition is `05_blueprint.json` (canonical format `BlueprintV2`), assembled alongside `project.json`, `brand.json`, `overrides.json`, `02_asset_manifest.json`, and `media_map.json` by `scripts/core/render_input.py` into `render_props.json`. In the Remotion runtime, `Root.tsx` passes `render_props.json` through `parseRenderInput()` (the canonical parse gate in `contracts/render-input.ts`), and `mergeProject()` in `remotion-app/src/merge.ts` produces the in-memory `MergedProject` data structure.

### 2. هل Blueprint الحالية قابلة نظريًا أن تعيش بدون Remotion؟
**YES**, at the structural schema level (`BlueprintV2Schema` in `contracts/blueprint.ts` defines project metadata, fps, aspect_ratio, scenes with startFrame/durationFrames, style surface, layout, audio tracks, and asset references).
**HOWEVER**, it currently leaks implementation dependencies:
1. `contracts/blueprint.ts` imports from `registry/effects-runtime.ts` which imports React components from `templates/effects/engine-bridge.tsx` which imports Remotion components from `remotion-app/src/engine/`.
2. `contracts/animations.ts` directly imports `interpolate` and `spring` from `remotion`.
3. `contracts/render-input.ts` imports `SceneOverride` from `remotion-app/src/merge.ts`.
4. Scene `template` property refers to IDs in `registry/template-registry-data.json`, but `template-registry.tsx` binds these IDs directly to React TSX components that call `@remotion/*`.

### 3. أي fields فيها Remotion-specific فعلًا؟
In `BlueprintV2`:
- **ENGINE_NEUTRAL**: `fps`, `aspect_ratio`, `project_id`, `scenes.scene_id`, `scenes.startFrame`, `scenes.durationFrames`, `scenes.layout`, `scenes.surface`, `scenes.content`, `audio.*`.
- **AMBIGUOUS**: `scenes.template` (conceptually a semantic template ID, but currently tied 1:1 to a Remotion React TSX component).
- **AMBIGUOUS / REMOTION_COUPLED**: `scenes.transition` (types `fade`, `slide`, `wipe`, `flip`, `zoom`, `cross-zoom`, `film-burn`, `dissolve`, `iris` map directly to `@remotion/transitions` presentation functions; timing semantics depend on Remotion `TransitionSeries` overlapping sequences).
- **REMOTION_COUPLED**: `scenes.effects` (validated against `EFFECTS_RUNTIME` which requires concrete React/Remotion component bindings from `templates/effects/engine-bridge.tsx`).
- **REMOTION_COUPLED**: `scenes.surface.animation` (enum values resolve to `contracts/animations.ts` which evaluates Remotion's `interpolate` and `spring`).
- **AMBIGUOUS**: `scenes.template_props` / `scenes.props` (contains arbitrary unmodeled template-specific parameters interpreted only by the internal TSX code of each template).

### 4. أين يعيش التوقيت؟
- Timeline structure authority: `05_blueprint.json` (authoritative `fps`, `startFrame`, `durationFrames` per scene).
- Composition duration authority: `merge.ts` and `probe_planner.py` calculate `totalDurationFrames = max(startFrame + durationFrames)`.
- Runtime execution authority: `TransitionSeries` in `BlueprintVideo.tsx`. **Critical conflict**: Remotion's `TransitionSeries` shortens overall sequence duration by overlapping transition frames, creating a drift between Blueprint's `max(startFrame + durationFrames)` and the actual rendered frames.
- Word/Caption timing: `startMs` and `endMs` in `CaptionWordSchema` (milliseconds, scene-relative).
- Component internal animation timing: Hardcoded inside TSX files (e.g. `Intro` has `RAIL_AT = 46`, `FADE_AT = 120`).

### 5. أين تعيش animations؟
Two distinct tiers:
1. **Surface animations**: Defined as contract IDs (`fade_in`, `slide_up`, etc.) in `contracts/blueprint.ts`, but executed via `contracts/animations.ts` using Remotion's `interpolate()` and `spring()`.
2. **Template-internal animations**: Hardcoded inside 100+ TSX components in `remotion-app/src/compositions/` and `remotion-app/src/remotion/` using `useCurrentFrame()`, `interpolate()`, and `spring()`. These animations are pure React/TSX code, NOT serializable, NOT editable without modifying code, and unknown to any external renderer or editor.

### 6. ما الذي يجعل Template "Template" حاليًا؟
It is a hybrid:
- Semantically: An entry in `registry/template-registry-data.json` specifying `canonical_id`, `category`, `schema`, `defaults`, and `default_duration_frames`.
- Physically & Executively: A TSX wrapper in `templates/<category>/<Wrapper>.tsx` importing an underlying Remotion component in `remotion-app/src/`, registered in `registry/template-registry.tsx` inside `COMPONENT_BINDINGS`.
- Without the TSX React component, the template crashes at registry load time (`throw new Error("Template component binding missing...")`) and at render pre-mount validation.

### 7. هل Template identity منفصلة عن TSX implementation؟
**NO**. At runtime, Template identity is tightly coupled to TSX. `registry/template-registry.tsx` validates that every template in `template-registry-data.json` has a concrete entry in `COMPONENT_BINDINGS`. If the TSX component is missing, the system throws a fatal error.

### 8. هل يمكن تعديل الفيديو بدون تعديل TSX؟
**Partially**: As long as edits only change properties exposed in the Blueprint (`surface`, `content`, `template_props`, `startFrame`, `durationFrames`, `transition`, `audio`), the video can be edited without modifying TSX.
**BUT**: Any layout change, animation retiming, styling not in `StyleSurface`, or structural variation outside what the specific TSX component author hardcoded **requires** modifying the TSX component code.

### 9. هل يوجد interactive preview حاليًا؟
**NO**. No interactive Live Editor canvas exists (`NOT_IMPLEMENTED`). The only interactive preview is `remotion studio` (opened via `python scripts/open_studio.py <project_id>`), which runs the full Remotion development server on port 3000 in a browser. It is human-review inspection, not an editor.

### 10. كيف تعمل preview الحالية؟
Two paths:
1. **Headless Probe Preview**: `scripts/gates/probe_qc.py` invokes `remotion still` for selected frames, generates `contact_sheet.png` and individual frame PNGs, and writes `probe_qc_report.json`.
2. **Interactive Studio Preview**: `scripts/open_studio.py` builds `render_props.json` and runs `npx remotion studio --props <render_props.json>`.
Both paths require pre-validation: `open_studio.py` enforces that `probe_qc.py` has passed and `.studio_unlocked` exists.

### 11. هل preview وfinal render يستخدمان نفس truth؟
**YES**. Both `scripts/open_studio.py`, `scripts/gates/probe_qc.py`, and `scripts/render_project.py` use the exact same builder: `scripts/core/render_input.py:build_render_input()`, producing the identical `render_props.json` envelope which passes through `parseRenderInput()` and `mergeProject()`.

### 12. أين يبدأ Remotion في pipeline؟
- In asset layout: When `materializer.py` copies files into `remotion-app/public/`.
- In verification: When `probe_qc.py` calls `npx remotion still`.
- In candidate creation: When `scripts/validators/candidate_runtime_runner.py` uses Remotion CLI to render still frames of candidates.
- In final rendering: When `scripts/render_project.py` calls `npx remotion render`.

### 13. أين ينتهي؟
Remotion ends immediately when `remotion render` writes `out.attempt-{attempt}.tmp.mp4` and it is renamed to `out.mp4`. All downstream steps (Stage 10 `gates/final_qc.py`, ReviewService, Worker upload to StorageService, API status updates) are 100% independent of Remotion and operate on the MP4 container and canonical metadata.

### 14. هل Probe/QC مستقلان عن Remotion؟
- `final_qc.py`: **100% independent** of Remotion (uses `ffprobe` / `ffmpeg.probe` on `out.mp4`, compares with `BlueprintV2`).
- `probe_qc.py`: **COUPLED** to Remotion (uses `npx remotion still` to produce the probe PNGs and contact sheet). Once images are on disk, image verification is neutral, but frame generation requires Remotion.

### 15. هل API تكشف Remotion concepts؟
- Public / Router API: Mostly decoupled! `api/routers/render.py` and `api/routers/runs.py` expose project runs, lifecycle status, gate status.
- Leakage:
  1. `api/services/health_service.py` explicitly probes `remotion-app` presence, `package.json`, and `src/index.ts`.
  2. `api/services/pipeline_service.py` mentions `remotion` component in failure logs and invokes `render_project.py`.
  3. WebSocket logs broadcast lines directly from the Remotion build/render CLI.

### 16. هل AI تنتج Remotion-specific output؟
- Creative Planning Layer (`ai/planning/creative_planner.py`): Completely free of Remotion (produces `CreativePlan` with `SceneIntent`, zero frame counts, zero TSX components).
- Compilation Layer (`ai/planning/compiler.py`): Produces `BlueprintV2`. It references template IDs and aspect ratios, but does NOT write TSX or call Remotion APIs.
- CREATE / Candidate Layer: Highly coupled! When creating a new template, AI generates TSX code targeting React and Remotion primitives (`useCurrentFrame`, `interpolate`, `AbsoluteFill`, etc.).

### 17. هل CREATE تنتج semantic templates أم Remotion code؟
**Both, tightly bound**: It produces a TSX component (`CandidateComponent.tsx`) AND metadata schema. But validation gates (`static_code_gate`, `typescript_gate`, `render_smoke_gate`, `probe_gate`) validate the TSX code by compiling and rendering it through an isolated Remotion harness (`CandidateHarness.tsx`) with `remotion still`!

### 18. هل Worker/Storage مرتبطان بالمحرك؟
**NO**. Both `scripts/core/worker.py` and `scripts/core/storage/storage_service.py` are 100% decoupled from Remotion. The worker manages job leasing and runs the pipeline as a subprocess. StorageService handles raw file uploads (S3/local).

### 19. ماذا يتوقف لو حذفنا Remotion dependency نظريًا اليوم؟
What breaks:
1. `remotion-app/` rendering and studio: `remotion render`, `remotion still`, `remotion studio`.
2. Probe QC (`scripts/gates/probe_qc.py`): cannot render still frames or contact sheets.
3. All 105 template implementations (they are TSX components importing `@remotion/*`).
4. `contracts/animations.ts` (imports `interpolate`, `spring` from `remotion`).
5. `contracts/blueprint.ts` and `contracts/render-input.ts` (transitively break via imports from `registry/effects-runtime.ts` and `templates/effects/engine-bridge.tsx`).
6. Template Candidate validation (`candidate_runtime_runner.py`).
7. `BlueprintVideo.tsx` and `Root.tsx`.

### 20. ماذا سيظل يعمل؟
What survives:
1. AI Creative Intelligence (`CreativePlanner`, `NarrativePlanner`, Recipes, Briefs, Taste decisions, Director recommendations).
2. Blueprint Compiler (`ai/planning/compiler.py` - compiles CreativePlan to Blueprint JSON).
3. Canonical Blueprint Data Model (`BlueprintV2` data structure, once import cycle is cut).
4. Asset Manifest, Asset Resolver, and Media Management (`manifest.ts`, `asset-resolver.ts`, `scripts/core/manifest_loader.py`).
5. Final QC Gate (`scripts/gates/final_qc.py` - pure ffprobe/ffmpeg).
6. Pipeline Worker & Storage Service (`scripts/core/worker.py`, `scripts/core/storage/`).
7. REST API & Lifecycle State Machine (`api/`, `scripts/core/state_store.py`, `scripts/core/review_service.py`).
8. Security, RBAC, Principal & Permissions subsystem (`scripts/core/security/`).

### 21. ما أقل مجموعة تغييرات مطلوبة في R02-R09 لفصل القلب؟
Order:
1. **Cut Transitive Leaks from Contracts (R02 - R03)**:
   - Clean `contracts/blueprint.ts`: Remove import of `EFFECTS_RUNTIME` from `registry/effects-runtime.ts`. Make effect validation purely declarative in contracts.
   - Clean `contracts/animations.ts`: Replace `interpolate` and `spring` from Remotion with portable mathematical functions.
   - Move `SceneOverride` interface from `remotion-app/src/merge.ts` to `contracts/render-input.ts` or `contracts/blueprint.ts`.
   - Move `merge.ts` from `remotion-app/src/merge.ts` to `contracts/` or `scripts/core/` (it has no remotion imports!).
2. **Separate Template Semantic Identity from Runtime Component (R04)**:
   - Decouple `TemplateEntry` in `registry/types.ts` from `React.ComponentType`.
   - Split registry into `SemanticTemplateCatalog` (pure JSON/TS data) and `RemotionComponentBindings` (in remotion adapter).
3. **Decouple Asset Materialization from `remotion-app/public` (R06)**:
   - Stop copying assets to `remotion-app/public/projects/...`. Allow the renderer adapter to resolve assets via local file URLs, HTTP URLs, or a dedicated static asset server.
4. **Abstract Still Rendering for Probe QC (R07)**:
   - Introduce a Renderer Still Interface so `probe_qc.py` calls `renderer.render_still(...)` rather than hardcoding `npx remotion still`.
5. **Package Remotion as `RemotionRendererAdapter` (R05 / R09)**:
   - Encapsulate `remotion-app` behind a unified `VideoRenderer` contract.

### 22. ما الذي يجب الحفاظ عليه 100% لضمان parity؟
- The mathematical output of animations and transitions.
- All 105 template visual schemas, props, and default values in `registry/template-registry-data.json`.
- Arabic text styling, RTL support, and Google Font loading (`contracts/fonts.ts`).
- The fail-closed pre-mount validation rules (LED-043, LED-044, LED-045, LED-046).
- The exact aspect ratio resolutions (1080x1920, 1920x1080, 1080x1080, etc.).
- Audio mixing logic (voiceover volume, BGM volume, ducking at 0.05).
- Probe frame sampling plan determinism (`scripts/core/probe_planner.py`).
- Final QC criteria (aspect ratio, duration threshold 0.5s, fps tolerance 0.2, AV sync < 200ms).

### 23. ما المسارات القديمة/dead التي قد تربك migration؟
- `remotion-app/src/compositions/` vs `remotion-app/src/remotion/scenes/` vs `templates/` (duplicate or unreferenced scenes).
- `templates/` vs `remotion-app/src/templates/` (divergence noted in `SplitScreenWrapper.tsx`).
- 34 unbridged effects in `registry/effects-runtime.ts` with broken relative imports pointing to `.agents/plugins/...`.
- Legacy Blueprint V1 formats (`version: "1.0"`, `audio.voiceover_ref`, etc.) still present in sample project fixtures.
- Deprecated endpoints in `api/routers/render.py` (`POST /render/{project_id}`).
- Static JSON fixtures in `contracts/fixtures/` and `remotion-app/projects/test_still_diag/`.

### 24. هل هناك أي dependency مخفية تجعل فصل Remotion أصعب مما تبدو عليه architecture docs؟
**YES**:
1. **Contract-to-React Leak**: `contracts/blueprint.ts` imports `registry/effects-runtime.ts` $\to$ imports `templates/effects/engine-bridge.tsx` $\to$ imports `@/engine/*` (React + Remotion).
2. **Contract Animation Leak**: `contracts/animations.ts` directly imports `remotion`.
3. **Asset Materialization Coupling**: `materializer.py` writes to `remotion-app/public/` because `staticFile()` in Remotion requires assets in its webpack public dir.
4. **Mechanical QC Lock in Webpack**: `remotion.config.ts` intercepts CLI invocations and crashes if `.studio_unlocked` does not exist on disk.
5. **Probe QC Still Render**: `probe_qc.py` invokes `npx remotion still` directly, making probe verification depend on Remotion CLI.
6. **CREATE / Candidate Runner**: `candidate_runtime_runner.py` generates dynamic `CandidateHarness.tsx` using `Composition` and `registerRoot` from Remotion.
7. **TransitionSeries Overlap Duration Drift**: Remotion `TransitionSeries` shortens timeline duration by overlapping scenes, while Blueprint and QC treat duration as sum/max of scene frames.

---

## 3. Risk Ranking Matrix

| Risk ID | Risk Name | Severity | Likelihood | Impact on S28-R | Mitigation Strategy |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **RSK-01** | TransitionSeries Timing Drift | **CRITICAL** | High | Potential duration mismatch in QC between Blueprint and Render | Decouple timeline calculation in RenderPlanner |
| **RSK-02** | Template Component Hard Stop | **CRITICAL** | High | Inability to add non-React templates without crashing registry | Split Semantic Registry from Component Bindings (R04) |
| **RSK-03** | Transitive Contract Import Leaks | **HIGH** | High | Core models fail in non-Node or pure Python/WASM environments | Remove React imports from contracts (R02) |
| **RSK-04** | Asset Staging Directory Lockdown | **HIGH** | Medium | Multi-tenant or cloud runners cannot share public dir | Abstract asset locator via URL/provider (R06) |
| **RSK-05** | Unbridged Broken Effects (34/44) | **MEDIUM** | High | Unhandled exceptions if users pick catalog effects | Deprecate unbridged entries or supply bridges (R04) |
| **RSK-06** | Template Source Divergence | **MEDIUM** | Medium | Inconsistent rendering between tools | Reconcile root `templates/` and `src/templates/` (R05) |

---

## 4. Recommended Migration Ordering for R02 - R15

```text
Phase 1: Contract Purification & Core Extraction (R02 - R03)
  ├── R02: Canonical Editable Video Contract (Purify BlueprintV2, isolate SceneOverride)
  └── R03: Animation & Math Modernization (Decouple contracts/animations.ts from Remotion)

Phase 2: Registry & Asset Architecture (R04 - R06)
  ├── R04: Semantic Template Catalog & Independent Component Bindings
  ├── R05: Remotion Package Encapsulation (Consolidate remotion-app behind packages/renderer-remotion)
  └── R06: Abstract Asset Materialization & Storage Provider

Phase 3: Renderer Abstraction & QC Neutralization (R07 - R09)
  ├── R07: Renderer Still Interface & Neutral Probe QC (Refactor probe_qc.py)
  ├── R08: Preview Runtime Foundation & Canvas Architecture
  └── R09: VideoRenderer Interface & RemotionRendererAdapter

Phase 4: Live Editor & Multi-Renderer Modernization (R10 - R15)
  ├── R10: Live Editor State Core & Interactive Scrubbing
  ├── R11: High-Performance Canvas Renderer (WebCodecs / Canvas2D / WebGL)
  ├── R12: Multi-Target CREATE & Candidate Verification
  ├── R13: Master Compositor & Multi-Track Audio Engine
  ├── R14: Workspace & Monorepo Package Isolation
  └── R15: Final Parity, Governance Guards & Deprecation Closeout
```

---

## 5. Verification Commands Executed

1. `npm test`: Executed 13 test files (`tests/remotion/contracts.test.ts`, `merge.test.ts`, `template_runtime_resolution.test.ts`, etc.) $\to$ **153/153 PASSED**.
2. `npx vitest run tests/remotion/s28_06_render_smoke.test.ts`: Executed COMPOSE and REUSE render smoke tests $\to$ **6/6 PASSED**.
3. `uv run pytest tests/architecture/test_adapter_layer_rules.py`: Architecture guard validation $\to$ **1/1 PASSED**.
4. Python AST & Regex Scan: Scanned all TypeScript, Python, and JSON files across the codebase for 16 Remotion keywords.
5. Directory Diff: Compared `templates/` against `remotion-app/src/templates/` identifying the `SplitScreenWrapper.tsx` divergence.

---

## 6. Audit Closeout & Gate Sign-off

- **0 Unknown Critical Remotion Dependencies**
- **0 Unknown Production Render Paths**
- **0 Unknown Template Runtime Authorities**
- **0 Unknown Preview Paths**
- **0 Unknown AI $\to$ Renderer Coupling Paths**
- **All Critical Findings Backed by Physical Code Evidence**
- **Zero Production Code Modified (Audit Only Guard Maintained)**

**GATE STATUS: `S28-R01 PASS`**
