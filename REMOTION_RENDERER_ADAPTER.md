# Remotion Renderer Adapter Specification (S28-R09)

**Status**: Production Implemented & Verified  
**Milestone**: S28-R09 (Remotion Renderer Adapter & Engine Abstraction)  
**Authority Level**: `SUBORDINATED_AUTHORITY` (Engine Execution Runtime)  
**Governing Authority**: `CANONICAL_RENDERER_REGISTRY` (`contracts/renderer.ts`)  

---

## 1. Executive Summary

Milestone **S28-R09** implements the production-grade `RemotionRendererAdapter`, replacing the `RemotionRendererAdapterStub` established in S28-R08. 

Under this architecture:
1. **Remotion is strictly an execution engine**: Remotion possesses **zero authority** over video semantics, duration math, layer models, keyframe interpolation, audio ducking formulas, or editor mutations.
2. **Canonical VideoDocument is the sole video authority**: All rendering operations consume a canonical `BlueprintV2` (or `NormalizedVideo`) evaluated via `evaluateVideoAtFrame` (`contracts/evaluator.ts`).
3. **RendererRegistry is the sole selection authority**: Requests are routed through `CANONICAL_RENDERER_REGISTRY.selectRenderer(request)`. Remotion never self-selects.
4. **Strict Fail-Closed Capabilities**: If a project requires engines or features outside Remotion's declared capability matrix (e.g., `map`, `3d`, `particles`, `custom_shaders`), the adapter immediately rejects rendering with `UnsupportedCapabilityError`, and the registry throws `NoCompatibleRendererError`.

---

## 2. Unidirectional Execution Pipeline

```text
       Canonical VideoDocument (BlueprintV2 / NormalizedVideo)
                                 │
                                 ▼
                     RenderRequest (contracts/renderer.ts)
                                 │
                                 ▼
            CANONICAL_RENDERER_REGISTRY (contracts/renderer.ts)
                                 │
                   selectRenderer(request) [Fail-Closed]
                                 │
                                 ▼
         RemotionRendererAdapter (remotion/remotion-renderer-adapter.ts)
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
      Frame / Sequence                         Video Export
        (renderStill)                          (renderMedia)
              │                                     │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
        CanonicalVideo Composition (remotion-app/src/CanonicalVideo.tsx)
             Evaluated per-frame via evaluateVideoAtFrame()
                                 │
                                 ▼
             RenderResult (Standardized R08 Output Model)
```

---

## 3. Canonical → Remotion Mapping

The adapter maps canonical state into Remotion's render tree through `CanonicalVideo.tsx` without changing canonical authority:

| Canonical Entity | Remotion Rendering Representation | Authority Source |
| :--- | :--- | :--- |
| **Document Dimensions & FPS** | Dynamically calculated via `calculateMetadata` | `document.aspect_ratio`, `document.fps`, `document.totalDurationFrames` |
| **TextLayer** | `<div>` / `<span>` with typography styles and exact CSS positioning | `layer.transform`, `layer.typography`, evaluator keyframes |
| **ImageLayer** | `<img>` tag with object-fit, opacity, transforms | `layer.transform`, `resolveMediaSrc(layer.asset_ref)` |
| **VideoLayer** | `<Video>` / `OffthreadVideo` with startOffset, volume | `layer.media_start_time`, `layer.playback_rate` |
| **ShapeLayer** | SVG / Canvas container for rectangle, circle, line | `layer.shape_type`, `layer.size`, `layer.fillColor` |
| **GroupLayer** | Hierarchical CSS transformed `<div>` container | Nested children layer evaluation |
| **Keyframe Interpolation** | Evaluated via `evaluateVideoAtFrame(doc, frame)` | Pure TypeScript canonical evaluator (`contracts/evaluator.ts`) |
| **Transitions** | Opacity and translation transitions evaluated per frame | Canonical transition curves |
| **Voiceover Audio** | Remotion `<Audio src={resolveMediaSrc(vo.asset_ref)} volume={...} />` | Evaluator voiceover tracks and timing |
| **Music Audio** | Remotion `<Audio src={resolveMediaSrc(music.asset_ref)} volume={(f) => duckedVolume(f)} />` | Evaluator dynamic ducking calculations |
| **Global SFX** | Remotion `<Audio src={resolveMediaSrc(sfx.asset_ref)} volume={...} />` | Evaluator SFX track timing and volume |

### Invariant: Zero Re-invention of Math
The adapter imports `evaluateVideoAtFrame` from `contracts/evaluator.ts`. It does **NOT** maintain its own timeline math, keyframe easing algorithms, duration rounding rules, or ducking arithmetic.

---

## 4. Declared Capabilities & Fail-Closed Boundaries

`RemotionRendererAdapter` accurately advertises only capabilities supported in production:

```typescript
export const REMOTION_SUPPORTED_CAPABILITIES: CanonicalRendererCapability[] = [
  "video_export_mp4",
  "video_export_webm",
  "frame_png",
  "frame_jpeg",
  "sequence_frames",
  "audio_voiceover",
  "audio_music",
  "audio_sfx",
  "audio_ducking",
  "typography",
  "vector_shapes",
  "keyframe_transforms",
  "transitions_basic",
  "multi_layer_compositing",
];
```

### Strictly Excluded Capabilities:
- `map` (Reserved for MapLibre / Vector Tile engines)
- `3d` (Reserved for Three.js / WebGL engines)
- `particles` (Reserved for Canvas / GPU particle engines)
- `custom_shaders` (Reserved for GLSL / WebGPU engines)
- `live_preview` (Authority of `BrowserPreviewRuntime`)

If any request requires excluded capabilities:
- `canRender()` returns `{ canRender: false, missingCapabilities: [...] }`
- Calling `renderFrame()`, `renderSequence()`, or `exportVideo()` directly throws `UnsupportedCapabilityError`
- Calling via `CANONICAL_RENDERER_REGISTRY.selectRenderer()` throws `NoCompatibleRendererError`

---

## 5. Method Specifications

### 5.1 `canRender(request: RenderRequest): RendererCanRenderResult`
Evaluates request type and canonical document requirements against `REMOTION_SUPPORTED_CAPABILITIES`. Fails closed if any requirement is unsupported or if output formats are incompatible.

### 5.2 `renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult>`
Invokes `@remotion/renderer`'s `renderStill` targeting the composition `CanonicalVideo`.
- Returns structured `RenderResult` with image buffer, output file path, dimensions, and milliseconds elapsed.
- Propagates cancellation signals cleanly.

### 5.3 `renderSequence(request: RenderRequest, context?: RenderContext): Promise<RenderResult>`
Renders a discrete range of frames (`timeRange.startFrame` to `timeRange.endFrame`) into image files in the target directory using concurrent `renderStill` operations.
- Respects abort signal on every frame iteration.
- Returns sequence directory path and evaluated frame count.

### 5.4 `exportVideo(request: RenderRequest, context?: RenderContext): Promise<RenderResult>`
Invokes `@remotion/renderer`'s `renderMedia` to export full MP4 or WebM video.
- Respects full audio plan (voiceover, music, SFX, dynamic ducking).
- Integrates `makeCancelSignal()` connected to `context.signal`.
- Returns output file path, byte size, duration, and frame metrics.

---

## 6. Bundle Optimization & Caching Strategy

WebPack bundling for Remotion takes ~20 seconds from scratch. To provide sub-second frame and video rendering in continuous workflows:
1. **In-Memory Cache**: `globalCachedBundlePath` caches the bundle in memory during long-running server/worker processes.
2. **Filesystem Cache**: The compiled bundle directory path is persisted to `/tmp/clean-video-remotion-bundle-path.txt`.
3. **Cross-Process Reuse**: Subsequent Node/Vitest worker invocations immediately verify the directory's existence and reuse the cached Webpack bundle in **0 ms**.

---

## 7. Migration & Legacy Compatibility

- **CLI Compatibility**: `scripts/render_project.py` is updated to delegate rendering through `RenderRequest` $\to$ `CANONICAL_RENDERER_REGISTRY` $\to$ `RemotionRendererAdapter` via `scripts/render_via_adapter.ts`.
- **Legacy Fallback**: If the adapter encountered legacy project types requiring raw CLI flags, `render_project.py` gracefully invokes the legacy CLI fallback.
- **Root Composition**: `remotion-app/src/Root.tsx` registers both `CanonicalVideo` and legacy `BlueprintVideo` compositions side by side.
