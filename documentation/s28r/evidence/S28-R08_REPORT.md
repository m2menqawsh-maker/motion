# S28-R08 Milestone Evidence Report: Renderer Registry & Engine Abstraction

**Milestone**: S28-R08  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Git Baseline SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Branch**: `feature/s27-ai-platform`  
**Execution Date**: 2026-10-06  
**Final Status**: **PASS (100% Verified)**  

---

## 1. Executive Summary

Milestone **S28-R08** delivers the formal rendering abstraction layer for the Clean Video platform. It establishes complete decoupling between the canonical data model (`BlueprintV2` / `evaluateVideoAtFrame`) and concrete rendering engines (Remotion, WebGL, Canvas, FFmpeg).

Key achievements:
1. **Unidirectional Rendering Pipeline**: Implemented strict architectural sequence:
   `Canonical VideoDocument → RenderRequest → RendererRegistry → Renderer Selection → RendererAdapter → RenderResult`.
2. **Authoritative Contracts**: Defined clean, engine-neutral contracts:
   - `RendererCapabilities`
   - `RenderRequest`
   - `RenderResult`
   - `RenderContext`
   - `RendererAdapter`
   - `RendererRegistry`
3. **Structured Capability Model**: Fine-grained taxonomy covering visual primitives (`text`, `image`, `video`, `shapes`, `groups`), temporal features (`keyframes`, `transitions`, `alpha`), hardware/engine-backed graphics (`webgl`, `3d`, `particles`, `map`, `custom_shaders`), and full R07 audio subsystem capabilities (`audio_voiceover`, `audio_music`, `audio_sfx`, `audio_mixing`, `audio_ducking`, `audio_timing`).
4. **Deterministic Fail-Closed Selection**: `selectRenderer()` matches requirements against candidate adapters with 100% deterministic tie-breaking (priority $\to$ capability count $\to$ lexicographical ID). Throws `NO_COMPATIBLE_RENDERER` when requirements are unfulfilled; zero silent degradation or fallback to incomplete engines.
5. **R05 & R07 System Integration**: Automatic capability derivation (`deriveRequiredCapabilities`) maps `rui-map-flight` to `map` + `webgl`, `scene3d-element` to `3d` + `webgl`, `particlesystem-element` to `particles`, GL transitions to `custom_shaders` + `webgl`, and audio plans with ducking to `audio_ducking` + `audio_mixing`.
6. **Remotion Architecture Placement**: Defined Remotion's place as an external engine behind `RemotionRendererAdapterStub` declaring standard production capabilities, ready for full execution handover in S28-R09.
7. **Preview Runtime Bridge**: Bridged `BrowserPreviewRuntime` (R06/R07) into `BrowserPreviewAdapter` without altering its single playhead authority.
8. **100% Verification**: 25 new S28-R08 tests (19 core + 6 TS architecture guards), 4 Python architecture guards, 207 full S28 vitest tests, 153 Remotion production tests (`npm test`), and 109 Pytest architecture guards pass with zero regressions.

---

## 2. Rendering Subsystem Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Canonical VideoDocument                  │
│       (BlueprintV2 / Evaluated Timeline State)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                     RenderRequest                      │
│        (Type, Document, Output, Required Caps)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   RendererRegistry                     │
│               [Sole Selection Authority]               │
│  • register / unregister / lookup                      │
│  • deriveRequiredCapabilities()                        │
│  • selectRenderer() [Fail-Closed / Deterministic]      │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│  Remotion Renderer Adapter  │ │   Browser Preview Adapter   │
│  (Headless MP4/WebM Export) │ │   (Interactive Frame / DOM) │
│  Subordinated to Registry   │ │   Subordinated to Registry  │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────┐
│                     RenderResult                       │
│           (ok, metrics, output, error)                 │
└────────────────────────────────────────────────────────┘
```

---

## 3. Core Contract Implementation Details

All contracts reside in `contracts/renderer.ts` and are re-exported via `contracts/index.ts`:

- **`RendererCapabilities`**: Class encapsulating immutable capability sets with `has()`, `hasAll()`, `getMissing()`, and format/resolution constraints.
- **`normalizeCapability(cap: string)`**: Normalizes developer and legacy aliases (`"custom shaders"`, `"audio mixing"`, `"ducking"`, `"maplibre-gl"`, `"three.js"`, `"remotion-bits"`) to canonical identifiers.
- **`deriveRequiredCapabilities(doc, type)`**: Pure numeric/structural analyzer extracting required capabilities from document scenes, templates, layer hierarchies, keyframes, transitions, and audio plans.
- **`validateRenderRequest(req)`**: Validates request parameters fail-closed, ensuring integer frames, bounded sequence time ranges, and non-empty project IDs.
- **`RendererRegistry`**: Encapsulates adapter management, preventing duplicate IDs (`DUPLICATE_RENDERER_ID`), listing capability unions, and executing deterministic selection.
- **`CANONICAL_RENDERER_REGISTRY`**: Authoritative system-wide singleton instance.
- **Structured Error Hierarchy**:
  - `RendererNotFoundError` (`RENDERER_NOT_FOUND`)
  - `NoCompatibleRendererError` (`NO_COMPATIBLE_RENDERER`)
  - `UnsupportedCapabilityError` (`UNSUPPORTED_CAPABILITY`)
  - `InvalidRenderRequestError` (`INVALID_RENDER_REQUEST`)
  - `RenderFailedError` (`RENDER_FAILED`)
  - `DuplicateRendererError` (`DUPLICATE_RENDERER_ID`)

---

## 4. R05 Template & R07 Audio Derivation Evidence

### 4.1 R05 Template Spec Verification
- `rui-map-flight`: Verified derivation of `["map", "webgl", "frame_rendering"]`.
- `scene3d-element`: Verified derivation of `["3d", "webgl", "frame_rendering"]`.
- `particlesystem-element`: Verified derivation of `["particles", "frame_rendering"]`.
- GL Transitions (`ripple`, `book-flip`, `crosswarp`): Verified derivation of `["transitions", "custom_shaders", "webgl", "sequence_rendering"]`.

### 4.2 R07 Audio Plan Verification
- Voiceover + Music + SFX + Ducking: Verified derivation of `["audio", "audio_voiceover", "audio_music", "audio_sfx", "audio_ducking", "audio_mixing", "audio_timing", "export_video"]`.

---

## 5. Critical End-to-End Pipeline Verification

Verified in `tests/remotion/s28_r08_renderer_core.test.ts`:

### 5.1 Happy Path Flow:
1. Instantiated canonical project from `rui-title-card` `TemplateSpec` with voiceover.
2. Constructed `RenderRequest` targeting frame 45 at 1080p PNG.
3. Automatically derived required capabilities (`text`, `shapes`, `audio`, `audio_voiceover`, `frame_rendering`).
4. Registered `canvas-production-adapter` declaring these capabilities.
5. Selected compatible renderer via `registry.selectRenderer(request)`.
6. Invoked `adapter.renderFrame(request)`.
7. Received valid `RenderResult` (`ok: true`, `evaluatedFrames: 1`, `width: 1920`, `height: 1080`).

### 5.2 Fail-Closed Missing Capability Flow:
1. Canonical project with `rui-map-flight` (requires `map`, `webgl`).
2. Registry contains only standard 2D canvas adapter (`text`, `image`, `shapes`).
3. Invoked `registry.selectRenderer(request)`.
4. System threw `NoCompatibleRendererError` (`NO_COMPATIBLE_RENDERER`) with detailed rejection diagnostics. Zero silent fallback to incomplete engine.

---

## 6. Architecture Guards Verification

Verified via `tests/architecture/test_s28_r08_architecture_guards.test.ts` & `tests/architecture/test_s28_r08_architecture_guards.py`:

| Guard | Invariant | Result |
| :--- | :--- | :--- |
| `R08-AG-01` | Canonical contracts in `contracts/` have ZERO imports from `remotion`, `@remotion/*`, `react`, `react-dom`, `fluent-ffmpeg`, `canvas`, `three`, `maplibre-gl`. | **PASS** |
| `R08-AG-02` | Mutation core (`mutations.ts`, `editor-session.ts`) has ZERO imports from `RendererRegistry` or adapters. | **PASS** |
| `R08-AG-03` | TemplateSpec core (`template-spec.ts`, `template-instantiator.ts`) has ZERO imports from concrete renderers or `RendererRegistry`. | **PASS** |
| `R08-AG-04` | `RendererRegistry` does NOT import or execute document mutation functions (`applyMutation`, `EditorSession`). | **PASS** |
| `R08-AG-05` | `BrowserPreviewRuntime` does NOT act as a renderer authority or define competing registries. | **PASS** |
| `R08-AG-06` | Single Renderer Authority invariant (`CANONICAL_RENDERER_REGISTRY` is the sole authority). | **PASS** |

---

## 7. Verification Test Runs

### 7.1 New S28-R08 Test Suite
- `tests/remotion/s28_r08_renderer_core.test.ts`: **19 passed (100%)**
- `tests/architecture/test_s28_r08_architecture_guards.test.ts`: **6 passed (100%)**
- `tests/architecture/test_s28_r08_architecture_guards.py`: **4 passed (100%)**

### 7.2 Full S28 Suite (27 test files, 207 tests)
- `npx vitest run tests/remotion/s28_r0*.test.ts tests/architecture/test_s28_r*.test.ts`: **207 passed (100%)**

### 7.3 Remotion Production Test Suite (13 test files, 153 tests)
- `npm test`: **153 passed (100%)**

### 7.4 Full Python Architecture Guard Suite (25 test files, 109 tests)
- `uv run pytest tests/architecture/`: **109 passed (100%)**

---

## 8. Remaining Risks & Gate Assessment

### Risks:
- **Renderer Parity (R09 Handover)**: Remotion render pipeline currently invoked via `scripts/render_project.py` must be formally adapted to implement the `RendererAdapter` contract in S28-R09.
- **Hardware Acceleration Availability**: Adapters declaring `webgl` or `custom_shaders` will require headless GL contexts (e.g. `gl` or Puppeteer WebGL flags) when running in headless CI containers.

### S28-R08 Gate Assessment:
**PASS**. All milestone criteria met without exception. Ready for S28-R09 handover.
