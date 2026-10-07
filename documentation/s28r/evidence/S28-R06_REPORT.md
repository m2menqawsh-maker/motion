# S28-R06 Milestone Evidence Report: Browser Live Preview Runtime

**Milestone**: S28-R06  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Git Baseline SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Branch**: `feature/s27-ai-platform`  
**Execution Date**: 2026-10-06  
**Final Status**: **PASS (100% Verified)**  

---

## 1. Executive Summary

Milestone **S28-R06** successfully delivers the foundational **Browser Live Preview Runtime** for Clean Video. The preview runtime renders the `Canonical VideoDocument` (`BlueprintV2` and `NormalizedVideo`) directly in browser DOM/Canvas environments without making Remotion the preview authority.

Key achievements:
1. **Canonical VideoDocument Authority Preserved**: Zero competing preview documents. The runtime directly consumes canonical blueprints and normalized video structures.
2. **Deterministic Evaluator Integration**: Directly invokes R03's `evaluateVideoAtFrame()`. Zero duplicate timeline math or animation curve solvers.
3. **Complete Interactive Controls**: Full implementations of `play()`, `pause()`, `seek(frame)`, `seekToMs(ms)`, `stepForward()`, `stepBackward()`, `setPlaybackRate()`, and aspect-ratio switching (`16:9`, `9:16`, `1:1`, custom).
4. **Comprehensive Layer Rendering**: Evaluates and renders transforms, opacity, text typography, images with fit/crop, shape rectangles/ellipses/vector paths, nested groups with composed parent transforms, and basic transitions (`fade`, `slide`, `wipe`).
5. **Live Mutation Integration**: Seamlessly receives R04 mutations with `ChangeSet` invalidation metadata, enabling sub-2ms preview refresh and 60fps transient drag interactions with full Undo/Redo bijectivity.
6. **Native TemplateSpec Previewing**: Validated across 7 representative native templates (`rui-title-card`, `rui-quote-card`, `rui-media-frame`, `rui-lower-third`, `rui-stat-card`, `rui-intro`, `rui-bento-pan`).
7. **Explicit Unsupported Capabilities**: Fail-closed guards and explicit diagnostic overlays for `ENGINE_BACKED`, `HYBRID`, and `LEGACY_COMPATIBILITY` templates.
8. **Decoupled Architecture**: 0 imports from React or Remotion in core preview modules. React component (`LivePreviewPlayer.tsx`) serves strictly as an optional consumer UI shell.

---

## 2. Preview Architecture

```text
       Canonical VideoDocument (BlueprintV2 / NormalizedVideo)
                             │
                             ▼
                  evaluateVideoAtFrame()
                 (contracts/evaluator.ts)
                             │
                             ▼
                   buildVisualFrame()
                (preview/visual-frame.ts)
                             │
                             ▼
                  DOMPreviewDriver / Canvas
                 (preview/dom-driver.ts)
                             │
                             ▼
                        Visual Frame
```

### Module Breakdown:
- **`preview/types.ts`**: Pure data contracts for playback state, visual nodes, transition progression, and diagnostic reports.
- **`preview/capabilities.ts`**: Detection of required capabilities; fail-closed `UnsupportedPreviewCapabilityError`.
- **`preview/visual-frame.ts`**: Pure assembler mapping evaluated frame state to `VisualFrame` and computed CSS styles.
- **`preview/dom-driver.ts`**: DOM stage renderer with aspect-fit viewport scaling, layer element recycling, and diagnostic overlays.
- **`preview/preview-runtime.ts`**: Central `BrowserPreviewRuntime` playback orchestrator, clock loop, seeking, and mutation synchronization.
- **`preview/components/LivePreviewPlayer.tsx`**: React UI wrapper providing player controls, timecode display, and scrubber slider.

---

## 3. Supported Canonical Layers & Capabilities

| Layer Kind | Evaluated Properties | Visual DOM / Canvas Representation |
| :--- | :--- | :--- |
| **`TextLayer`** | `text`, `fontFamily`, `fontSize`, `fontWeight`, `fontStyle`, `fillColor`, `strokeColor`, `strokeWidth`, `lineHeight`, `textAlign` | `div` with absolute positioning, text-stroke, white-space wrapping |
| **`ImageLayer`** | `asset_ref`, `fit` (`contain`/`cover`/`fill`), `crop` | `img` element with `objectFit` and clipping |
| **`ShapeLayer`** | `shape_type` (`rectangle`/`ellipse`/`path`), `size`, `fillColor`, `strokeColor`, `strokeWidth`, `borderRadius`, `pathData` | Styled `div` or SVG vector `<path>` with fill/stroke |
| **`GroupLayer`** | Hierarchical `children_ids`, `parent_id`, composed transform matrix | Container `div` with nested child visual elements |
| **Transforms** | Position $(x, y)$, Scale $(s_x, s_y)$, Rotation ($\theta$), Anchor point | CSS `transform: translate(-50%, -50%) rotate() scale()` |
| **Opacity** | Layer opacity $\times$ transform opacity $\times$ keyframed opacity | CSS `opacity: [0.0, 1.0]` |
| **Keyframes** | `LINEAR`, `EASE`, `SPRING`, `CUBIC_BEZIER` channel targets | Evaluated per frame via `contracts/keyframes.ts` |
| **Transitions** | `fade`, `slide`, `wipe` with overlap timing | Alpha blending, directional offsets, discrete cuts |

---

## 4. Play/Pause/Seek Status

- **`play()`**: Starts clock loop according to canonical fps and playback rate. Verified transitions `idle -> playing`.
- **`pause()`**: Freezes playhead at exact discrete frame $N$. Verified transitions `playing -> paused`.
- **`seek(frame)`**: Clamps to $[0, \text{duration} - 1]$, evaluates frame immediately. Average latency **0.0092 ms**.
- **`seekToMs(ms)`**: Converts milliseconds using `msToFrame()` with canonical rounding policy.
- **`stepForward(n)` / `stepBackward(n)`**: Discrete frame stepping with boundary safety.
- **Continuous Playback**: Evaluates sequential playback at **59,495+ frames/second**.

---

## 5. Timeline & Evaluator Integration

- **Duration Authority**: Delegates directly to `calculateCanonicalDuration(scenes)` from `contracts/timeline.ts`.
- **Time Conversion**: Delegates directly to `frameToMs()` and `msToFrame()`.
- **Frame Evaluation**: Delegates directly to `evaluateVideoAtFrame(video, frame)` from `contracts/evaluator.ts`.
- **Zero Duplicate Math**: Verified by architecture guards `R06-AG-03`.

---

## 6. Mutation & Live Update Status

- **Mutation Ingestion**: Runtime accepts `(newBlueprint, changeSet)`.
- **Invalidation Handling**:
  - `requires_timeline_rebuild`: Recalculates duration and clamps playhead.
  - `requires_layout`: Re-scales aspect-ratio viewport.
  - `requires_render`: Triggers frame re-evaluation.
- **EditorSession Sync**: Seamlessly syncs with `EditorSession`.
  - Transient mouse drags (e.g. 60fps bounding box updates) update preview in **~1.5 ms**.
  - `undo()` and `redo()` immediately restore visual frame state.

---

## 7. TemplateSpec Preview Status

All 7 representative `NATIVE` templates from R05 instantiate and preview with 100% fidelity:
1. `rui-title-card`: Previews background shape, title typography, subtitle, and accent shape.
2. `rui-quote-card`: Previews quote typography, italic style, and author citation.
3. `rui-media-frame`: Previews image container, `asset_ref` binding, and caption.
4. `rui-lower-third`: Previews overlay plate shape, speaker name, and title.
5. `rui-stat-card`: Previews numeric metric value and description label.
6. `rui-intro`: Previews presentation backdrop, main title, and tagline.
7. `rui-bento-pan`: Previews multi-container grid panels.

---

## 8. Unsupported Capabilities (Fail-Closed & Explicit)

The preview runtime enforces explicit detection and diagnosis:
- **`ENGINE_BACKED` Templates**:
  - `rui-map-flight`: MapLibre GL WebGL vector tile rendering required.
  - `scene3d-element`: 3D WebGL mesh perspective camera engine required.
  - `particlesystem-element`: Runtime physics particle spawner simulation required.
  - *Behavior*: Throws `UnsupportedPreviewCapabilityError` in fail-closed mode (`failClosedOnUnsupported: true`); renders explicit diagnostic warning overlay in permissive mode.
- **`HYBRID` Templates**:
  - WebGL GL transitions (`film-burn`, `ripple`, `crosswarp`, etc.): Flagged with required capability `webgl_glsl_transition_shader`.
- **`LEGACY_COMPATIBILITY` Templates**:
  - Complex TSX scene templates (`rui-browser-flow`, etc.): Flagged with `remotion_tsx_runtime`.

---

## 9. Real Measured Performance Baseline

Benchmarked under real Node.js execution (`tests/remotion/s28_r06_preview_performance.test.ts`):

| Operation / Benchmark | Measured Average | Measured p50 | Measured p95 | Threshold Target | Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frame Evaluation** | **0.0336 ms** | **0.0098 ms** | **0.0851 ms** | $< 5.0\text{ ms}$ | Sub-0.1ms evaluation |
| **Preview Update (`buildVisualFrame`)** | **0.0747 ms** | **0.0203 ms** | **0.1073 ms** | $< 10.0\text{ ms}$ | Negligible UI overhead |
| **Seek Operation** | **0.0092 ms** | **0.0060 ms** | **0.0211 ms** | $< 10.0\text{ ms}$ | Instant scrubbing |
| **Continuous Playback Throughput** | **59,495 fps** | — | — | $> 120\text{ fps}$ | Massive headroom |
| **Mutation $\to$ Preview Refresh** | **1.5794 ms** | **1.3950 ms** | **3.2611 ms** | $< 15.0\text{ ms}$ | Instant live editing |
| **Representative Multi-Layer Scene** | **0.0318 ms** | **0.0181 ms** | **0.0469 ms** | $< 10.0\text{ ms}$ | Complex scenes $< 0.1$ms |

---

## 10. Test Verification & Matrix Comparison

### Test Counts Before vs After:

| Test Scope | Tests Before R06 | Tests After R06 | Net Change | Result |
| :--- | :--- | :--- | :--- | :--- |
| **S28 Combined Vitest Regression (R02–R05)** | 128 | 128 | 0 | **PASS** |
| **S28-R06 New Test Suites**: | | | | |
| `tests/architecture/test_s28_r06_architecture_guards.test.ts` | 0 | 5 | +5 | **PASS** |
| `tests/remotion/s28_r06_preview_core.test.ts` | 0 | 9 | +9 | **PASS** |
| `tests/remotion/s28_r06_templates_and_mutations.test.ts` | 0 | 13 | +13 | **PASS** |
| `tests/remotion/s28_r06_preview_performance.test.ts` | 0 | 1 | +1 | **PASS** |
| **S28 Vitest Total** | **128** | **156** | **+28** | **100% PASS** |
| **Standard Remotion Test Suite (`npm test`)** | 153 | 153 | 0 | **100% PASS** |
| **Python Architecture Guards (`pytest`)** | 105 | 105 | 0 | **100% PASS** |
| **Total Test Verification** | **386** | **414** | **+28** | **ALL PASS** |

### Critical Integration Test:
```text
TemplateSpec
  → instantiateTemplate("rui-title-card")
  → Canonical VideoDocument (BlueprintV2)
  → applyMutation(UPDATE_TEXT, UPDATE_TRANSFORM)
  → normalizeCanonicalVideo()
  → evaluateVideoAtFrame()
  → Browser Preview Representation (DOM mount & VisualFrame)
Result: PASS
```

---

## 11. Remaining Risks & Architectural Assessment

- **CRITICAL Risks**: **0**
- **HIGH Risks**: **0**
- **MEDIUM Considerations**:
  - Audio Waveform & Playback Synchronization: Auditory tracks are evaluated symbolically in R06; real-time audio playback and Web Audio waveforms are intentionally deferred to R07.
  - Video Tag Decoding: For video layers (`kind: "video"`), native browser playback relies on standard HTML5 `<video>` elements. Headless automated tests use image fallbacks or mocked media references.

---

## 12. Documentation Paths

- `documentation/s28r/BROWSER_LIVE_PREVIEW_RUNTIME.md`: Full architecture specification.
- `documentation/s28r/evidence/S28-R06_REPORT.md`: This gate closure report.
- `documentation/s28r/AUTHORITY_MATRIX.md`: System-wide authority ledger.

---

## 13. Recommended Starting Point for S28-R07

With S28-R06 closed and verified:
- **S28-R07 Focus**: **Audio Preview, Synchronization & Waveform Generation**.
- Interface `BrowserPreviewRuntime` with Web Audio API (`AudioContext`).
- Implement audio track mixing (`voiceover`, `music`, `sfx`) synchronizing playback state with the preview playhead.
- Build pure waveform peak decoders without altering canonical video authority.

---

## 14. Final Gate Decision

# **`S28-R06 PASS`**
