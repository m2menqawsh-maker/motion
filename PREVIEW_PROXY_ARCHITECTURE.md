# Preview Proxy System Architecture

**Status**: Verified Reality Specification  
**Milestone**: S28-R07B (Preview Fidelity, Cache & Proxy System)  
**Contract Sources**:
- [`contracts/preview-proxy.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts)
- [`preview/proxy/proxy-coordinator.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-coordinator.ts)
- [`preview/proxy/proxy-cache.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-cache.ts)

---

## 1. Architectural Pipeline

When the [Preview Fidelity Model](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/PREVIEW_FIDELITY_MODEL.md) determines that a document fragment requires an external render (`PROXY_RENDER_REQUIRED`), the proxy subsystem executes the following pipeline:

```text
┌────────────────────────────────────────────────────────┐
│               Canonical VideoDocument                  │
│             (or discrete scene/layer)                  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 PreviewProxyRequest                    │
│    (project, revision, range, caps, dimensions, policy)│
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             PreviewProxyCoordinator                    │
│        (In-Process Async Job Lifecycle)                │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
        [Cache Hit]                 [Cache Miss]
               │                          │
               │                          ▼
               │                ┌──────────────────┐
               │                │ RendererRegistry │
               │                └─────────┬────────┘
               │                          │
               │                          ▼
               │                ┌──────────────────┐
               │                │ RendererAdapter  │
               │                │ (Canvas/Remotion)│
               │                └─────────┬────────┘
               │                          │
               │                          ▼
               │                ┌──────────────────┐
               │                │  Proxy Artifact  │
               │                └─────────┬────────┘
               │                          │
               │                          ▼
               │                ┌──────────────────┐
               │                │ PreviewProxyCache│
               │                └─────────┬────────┘
               │                          │
               └──────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               BrowserPreviewRuntime                    │
│   (Consumes proxy visual node; sole playhead clock)    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Contracts & Data Structures

### 2.1 `PreviewProxyRequest`
Specifies an engine-neutral request to generate a proxy artifact:

```typescript
export interface PreviewProxyRequest {
  readonly projectId: string;
  readonly canonicalRevision: number;
  readonly sceneId?: string;
  readonly layerId?: string;
  readonly timeRange?: TimeRange;
  readonly requiredCapabilities: readonly CanonicalRendererCapability[];
  readonly width: number;
  readonly height: number;
  readonly fps: number;
  readonly quality: ProxyQualityLevel; // "low" | "balanced" | "high"
  readonly format: ProxyFormat;        // "png" | "jpeg" | "webp" | "mp4"
  readonly documentFragment: VideoDocument;
}
```

### 2.2 `PreviewProxyArtifact`
The immutable rendered output cached and consumed by the preview player:

```typescript
export interface PreviewProxyArtifact {
  readonly id: string;
  readonly cacheKey: string;
  readonly projectId: string;
  readonly canonicalRevision: number;
  readonly sceneId?: string;
  readonly layerId?: string;
  readonly timeRange?: TimeRange;
  readonly width: number;
  readonly height: number;
  readonly fps: number;
  readonly format: ProxyFormat;
  readonly uri: string;
  readonly buffer?: Uint8Array;
  readonly rendererId: string;
  readonly generatedAt: number;
  readonly byteLength: number;
  readonly dependencies: ProxyDependencies;
}
```

---

## 3. Configurable Quality Policies

Proxies are generated exclusively for interactive editor preview, not final export. The system avoids ad-hoc quality parameters by providing deterministic, configurable policies:

| Policy Level | Default Resolution | Default FPS | Preferred Format | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **`low`** | $640 \times 360$ ($360\text{p}$) | $15\text{ fps}$ | WebP / JPEG | Fast scrubbing, responsive typing, constrained CPU |
| **`balanced`** (default) | $1280 \times 720$ ($720\text{p}$) | $30\text{ fps}$ | WebP / MP4 | General timeline playback and visual preview |
| **`high`** | $1920 \times 1080$ ($1080\text{p}$) | $30\text{ fps}$ | MP4 / PNG | Pixel-critical detail verification |

Dimensions are calculated proportionally via `resolveProxyDimensions()`, maintaining exact project aspect ratio with even-dimension pixel rounding.

---

## 4. Background Job Lifecycle & Coordinator

[`PreviewProxyCoordinator`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-coordinator.ts) coordinates asynchronous generation without blocking the UI thread or running a heavy background queue.

### 4.1 State Machine
```text
         ┌─────────┐
         │ Queued  │
         └────┬────┘
              │ (dispatch)
              ▼
         ┌─────────┐
         │ Running │
         └────┬────┘
      ┌───────┼─────────────────────────┐
      │       │                         │
      ▼       ▼                         ▼
   [Ready] [Failed]    [Cancelled / Stale Revision]
```

### 4.2 Architectural Guarantees:
1. **Registry Selection**: The coordinator selects adapters exclusively via `registry.selectRenderer()`. No `if (isRemotion)` or `if (isCanvas)` checks exist.
2. **Fail-Closed**: If required capabilities cannot be fulfilled by any registered engine, `NO_COMPATIBLE_RENDERER` diagnostics are emitted.
3. **Abortion & Stale Detection**: In-flight jobs can be aborted on demand or cancelled automatically when a document revision supersedes them.

---

## 5. Live Runtime Integration & Proxy Replacement

1. **Initial Assessment**: [`BrowserPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts) evaluates document fidelity on load and on every mutation via `resolvePreviewFidelity()`.
2. **Placeholder Phase**: If an entity is `PROXY_RENDER_REQUIRED` and no cached artifact is active, [`buildVisualFrame()`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/visual-frame.ts) generates an explicit placeholder node (`visual_type = "proxy_placeholder"`). Native and approximate layers continue rendering simultaneously.
3. **Artifact Arrival**: When the background coordinator finishes generating the artifact and verifies its revision, it invokes `runtime.applyProxyArtifact(artifact)`.
4. **Seamless Swap**: The runtime attaches the artifact to its internal `activeProxies` Map and triggers an immediate visual frame rebuild. The placeholder is replaced with `visual_type = "proxy_layer"`, consuming the rendered buffer or URI directly.
5. **No Full Reload**: The playhead position, playback state, and other scene elements are undisturbed.
