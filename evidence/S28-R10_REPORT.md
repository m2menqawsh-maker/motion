# S28-R10 Closure Report: Canvas Headless Alternative Renderer Adapter

**Milestone**: S28-R10 (Canvas / FFmpeg Alternative Headless Renderer Adapter)  
**Status**: **PASS**  
**Git HEAD**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Audited Timestamp**: `2026-10-06T22:08:00+03:00`  

---

## 1. Executive Summary

Milestone **S28-R10** achieves the multi-engine milestone for the video platform. It implements a second real headless rendering engine adapter: `CanvasRendererAdapter` (`canvas/canvas-renderer-adapter.ts`), operating concurrently with `RemotionRendererAdapter` inside `CANONICAL_RENDERER_REGISTRY`.

### Architectural Truths Proven:
1. **Multi-Engine Reality**: The rendering architecture dynamically decouples canonical video documents (`BlueprintV2`) from concrete rendering packages. Zero engine-specific branching exists outside `RendererRegistry`.
2. **Canonical Authority**: Both `CanvasRendererAdapter` and `RemotionRendererAdapter` consume canonical states strictly through `evaluateVideoAtFrame()` (`contracts/evaluator.ts`). Neither engine mutates canonical documents, invents timeline math, or re-implements keyframe interpolation.
3. **Deterministic Capability Dispatch**:
   - 2D Visual Request $\to$ `CanvasRendererAdapter` (Higher priority: 110 vs 100)
   - Video / Audio-Ducking Request $\to$ `RemotionRendererAdapter` (Exclusive capability)
   - Unsupported Engine Request (e.g. Map, 3D, Particles, Shaders) $\to$ `NO_COMPATIBLE_RENDERER` (Strict fail-closed)
4. **Sub-second Frame Performance**: `CanvasRendererAdapter` delivers 11.5x–14.5x faster startup and frame capture times than Remotion, using 20x less heap memory.

---

## 2. Chosen Alternative Renderer: `CanvasRendererAdapter`

### 2.1 Technical Profile
- **Identifier**: `CANVAS_RENDERER_ID = "canvas-renderer-adapter"`
- **Module Location**: `canvas/canvas-renderer-adapter.ts` and `canvas/index.ts`
- **Engine Architecture**: Headless 2D Vector Canvas surface + FFmpeg/librsvg rasterization and encoding
- **Version**: `1.0.0`
- **Priority**: `110` (Remotion is `100`)
- **Zero Heavy Dependencies**: Leverages Node.js core and system FFmpeg (`/usr/bin/ffmpeg`) already present on the host.

### 2.2 Capability Matrix
```typescript
export const CANVAS_SUPPORTED_CAPABILITIES: readonly CanonicalRendererCapability[] = [
  "text",
  "image",
  "shapes",
  "groups",
  "keyframes",
  "transitions",
  "alpha",
  "frame_rendering",
  "sequence_rendering",
  "export_video",
];
```

### 2.3 Excluded & Fail-Closed Capabilities
- `video`: Video playback frame decoding in SVG not supported $\to$ rejected in `canRender()`, routes to Remotion.
- `map`: Requires MapLibre $\to$ rejected in `canRender()`, fails closed.
- `3d`: Requires Three.js / WebGL $\to$ rejected in `canRender()`, fails closed.
- `particles`: Requires particle simulation $\to$ rejected in `canRender()`, fails closed.
- `custom_shaders`: Requires GLSL/WebGL $\to$ rejected in `canRender()`, fails closed.
- `live_preview`: Authority of `BrowserPreviewRuntime` $\to$ rejected in `canRender()`, fails closed.

---

## 3. Operational Implementation Verification

### 3.1 `renderFrame()`
- **Status**: **VERIFIED PASS**
- **Operation**: Evaluates discrete frame via `evaluateVideoAtFrame()`, constructs center-based SVG surface, rasterizes via FFmpeg librsvg into PNG/JPEG.
- **Output**: Structured `RenderResult` with valid file path, `Uint8Array` buffer, exact pixel dimensions, and execution metrics.
- **Latency**: ~205 ms (vs ~2,370 ms in Remotion).

### 3.2 `renderSequence()`
- **Status**: **VERIFIED PASS**
- **Operation**: Renders discrete frame range `[startFrame, endFrame]` into discrete image files in target directory.
- **Cancellation**: Evaluates `context.signal.aborted` on each frame iteration, halting execution cleanly without orphaned processes.
- **Latency**: ~724 ms for 4 frames; ~5,416 ms for 30 frames.

### 3.3 `exportVideo()`
- **Status**: **VERIFIED PASS**
- **Operation**: Renders full frame sequence into temporary workspace and encodes via FFmpeg into H.264 MP4 (`libx264`, `yuv420p`, `+faststart`).
- **Output**: Valid MP4 video file verified with file size $> 1$ KB.

---

## 4. Multi-Renderer Proof (Core Milestone Gate)

Verified in `tests/remotion/s28_r10_canvas_adapter.test.ts` (suite `R10-07`):

| Test Case | Request Profile | Capabilities Required | Dispatched Engine | Verification Result |
| :--- | :--- | :--- | :--- | :--- |
| **Request A** | 2D Text + Vector Shape | `text`, `shapes`, `frame_rendering` | `canvas-renderer-adapter` | **PASS** (Priority 110 > 100) |
| **Request B** | Video Layer Background | `video`, `frame_rendering` | `remotion-engine-adapter` | **PASS** (Canvas rejected; Remotion selected) |
| **Request C** | Engine-Backed Template (`rui-map-flight`) | `map`, `webgl` | None (Throws `NO_COMPATIBLE_RENDERER`) | **PASS** (Fail-closed) |
| **Override A**| Preferred: `remotion-engine-adapter` | `text`, `shapes` | `remotion-engine-adapter` | **PASS** (Explicit preference respected) |
| **Override B**| Preferred: `canvas-renderer-adapter` | `video` | None (Throws `UNSUPPORTED_CAPABILITY`) | **PASS** (Fail-closed; zero silent fallback) |

---

## 5. Performance Comparison Baseline

Benchmark executed under identical system conditions:

| Metric | CanvasRendererAdapter | RemotionRendererAdapter | Factor |
| :--- | :--- | :--- | :--- |
| **Cold Startup** | 189 ms | 2,736 ms | **14.5x faster** |
| **Warm Startup** | 205 ms | 2,370 ms | **11.5x faster** |
| **Single Frame Render** | 205 ms | 2,370 ms | **11.5x faster** |
| **4-Frame Sequence** | 724 ms | 6,109 ms | **8.4x faster** |
| **30-Frame Sequence** | 5,416 ms | 38,079 ms | **7.0x faster** |
| **Video Export (30f MP4)**| 6,428 ms | 4,960 ms | Remotion faster on multi-threaded ffmpeg piping |
| **Heap Memory Delta** | 0.96 MB | 19.72 MB | **20.5x less heap** |
| **Process RSS** | 133.29 MB | 223.18 MB | Canvas ~90 MB lower RSS |

---

## 6. Semantic Parity Verification

Outputs compared across `evaluateVideoAtFrame()`, `BrowserPreviewRuntime`, and `CanvasRendererAdapter`:
1. **Coordinates**: Center-based transform $(cx, cy) = (W/2 + t.x, H/2 + t.y)$ with anchor $(0.5, 0.5)$ exactly matches CSS transform calculations in `preview/visual-frame.ts`.
2. **Opacity**: Net opacity $(layer.opacity \times transform.opacity)$ matches evaluator output.
3. **Keyframe Motion**: Evaluator keyframe channels (`TRANSFORM_Y`, `ROTATION`, `SCALE`) produce matching evaluated transforms at discrete frames $F_0, F_{15}, F_{30}$.
4. **Native TemplateSpecs**: Both `rui-title-card` and `rui-stat-card` render with full visual fidelity.

---

## 7. Architecture Guards & Regression Status

### 7.1 Architecture Enforcement Suites
- Pytest: `tests/architecture/test_s28_r10_architecture_guards.py` $\to$ **5 passed**
- Vitest: `tests/architecture/test_s28_r10_architecture_guards.test.ts` $\to$ **7 passed**
- Full Architecture Suite: 118 pytest tests passing.

### 7.2 Regression Tests
- Vitest: All 153 tests in `npm test` $\to$ **PASS**
- S28-R08 Core: `tests/remotion/s28_r08_renderer_core.test.ts` $\to$ **PASS**
- S28-R09 Remotion Adapter: `tests/remotion/s28_r09_remotion_adapter.test.ts` $\to$ **PASS**
- S28-R10 Canvas Adapter: `tests/remotion/s28_r10_canvas_adapter.test.ts` $\to$ **15 passed**

---

## 8. Artifact Ledger

| File Path | Nature | Purpose |
| :--- | :--- | :--- |
| `canvas/canvas-renderer-adapter.ts` | Source | Implementation of Headless Canvas Renderer Adapter |
| `canvas/index.ts` | Source | Public module exports |
| `contracts/renderer.ts` | Modified | Added `CANVAS_RENDERER_ID` engine-neutral constant |
| `tests/remotion/s28_r10_canvas_adapter.test.ts` | Test | 15 comprehensive verification and multi-renderer proof tests |
| `tests/architecture/test_s28_r10_architecture_guards.py` | Guard | Pytest boundary enforcement |
| `tests/architecture/test_s28_r10_architecture_guards.test.ts` | Guard | Vitest boundary enforcement |
| `ALTERNATIVE_RENDERER_ADAPTER.md` | Doc | Architectural specification of Canvas Renderer Adapter |
| `RENDERER_ARCHITECTURE.md` | Doc | Updated with multi-renderer selection & Canvas placement |
| `RENDERER_CAPABILITY_MODEL.md` | Doc | System-wide capability taxonomy and derivation matrix |
| `R10_COMPATIBILITY_MAP.md` | Doc | Multi-renderer dispatch resolution map & template coverage |
| `AUTHORITY_MATRIX.md` | Doc | System authority matrix updated for S28-R10 |
| `evidence/S28-R10_REPORT.md` | Evidence | Formal closure evidence report |
