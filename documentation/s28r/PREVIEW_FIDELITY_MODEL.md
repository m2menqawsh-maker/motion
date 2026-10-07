# Preview Fidelity Model & Capability Taxonomy

**Status**: Verified Reality Specification  
**Milestone**: S28-R07B (Preview Fidelity, Cache & Proxy System)  
**Contract Source**: [`contracts/preview-fidelity.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts)  

---

## 1. Overview & Architectural Purpose

In a modern video authoring platform, interactive editing demands immediate feedback ($60\text{ fps}$ playhead scrubbing), whereas final export may involve heavy computation (motion blur, custom shaders, multi-pass compositing, engine-backed 3D/Map simulations).

The **Preview Fidelity Model** is an engine-neutral contract and evaluation system that deterministically decides how each scene, layer, and effect in a `VideoDocument` is presented within [`BrowserPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts).

```text
                     Canonical VideoDocument
                                │
                                ▼
                   resolvePreviewFidelity()
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
    LIVE_NATIVE        APPROXIMATE_PREVIEW   PROXY_RENDER_REQUIRED
         │                      │                      │
   Browser renders        Browser renders         Coordinator requests
    directly with        deterministic fast        proxy artifact from
    full fidelity          approximation            RendererRegistry
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                ▼
                      BrowserPreviewRuntime
                     (Sole Preview Authority)
```

---

## 2. Fidelity Taxonomy & Classification

The system defines three mutually exclusive preview modes for any fragment or document:

### 2.1 `LIVE_NATIVE`
- **Definition**: The feature can be rendered directly by the browser's DOM/Canvas pipeline in real time with visual parity to the final render.
- **Applicable Features**:
  - Text typography and styling
  - Static images (PNG, JPEG, WebP, SVG)
  - Basic geometric shapes (rectangles, circles, paths)
  - Hierarchical container groups
  - 2D spatial transforms (translation, scale, rotation)
  - Layer opacity and alpha blending
  - Canonical keyframe interpolation (linear, ease-in, ease-out, ease-in-out)
  - Standard linear transitions (fade, crossfade, basic slide)
  - Synchronized native audio preview via [`AudioPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/audio/audio-preview-runtime.ts)
- **Preview Quality**: `"full"`
- **Proxy Requirement**: None (`proxyRequired = false`).

### 2.2 `APPROXIMATE_PREVIEW`
- **Definition**: The feature cannot be evaluated at full render fidelity at 60 fps in the browser, but a deterministic, visually coherent approximation can be computed locally without waiting for an external render.
- **Applicable Features**:
  - Complex transitions: Zoom, wipe, iris, clock-wipe, morph transitions approximated deterministically as crossfade with direction tags.
  - Expensive visual effects: Heavy multi-pass blurs, simulated glow, basic color grading approximations.
  - High-density vector elements rendered at reduced vector tessellation.
- **Preview Quality**: `"approximate"`
- **Guarantees**:
  - **Deterministic**: The same input always produces identical visual approximations.
  - **Diagnosable**: Explicit diagnostic messages explaining why the element is approximated.
  - **Transparent**: Never masquerades as final render fidelity; UI indicators receive explicit metadata (`previewQuality = "approximate"`).
- **Proxy Requirement**: None unless user explicitly requests pre-rendered proxy (`proxyRequired = false`).

### 2.3 `PROXY_RENDER_REQUIRED`
- **Definition**: The feature cannot be faithfully or safely simulated in real time inside the browser DOM/Canvas. Attempting a naive fallback would produce a silently misleading output.
- **Applicable Features**:
  - Engine-backed templates (e.g., `rui-map-flight`, 3D scenes, particle systems)
  - Custom GLSL / WebGL shaders
  - Advanced multi-track video blending or video-codec-dependent transforms
  - Unsupported canvas/SVG filters
- **Preview Quality**: `"proxy"` (when artifact available) or `"placeholder"` (while rendering)
- **Guarantees**:
  - **Zero Silent Degradation**: The system flags the fragment fail-closed.
  - **Proxy Generation**: Dispatches a [`PreviewProxyRequest`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts) through [`RendererRegistry`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/renderer.ts).
  - **Non-blocking Preview**: Displays a diagnostic placeholder during background rendering; swaps seamlessly when ready.

---

## 3. Contract Schema & Diagnostic Surface

The preview fidelity contract is defined in [`contracts/preview-fidelity.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts):

```typescript
export type PreviewMode = "LIVE_NATIVE" | "APPROXIMATE_PREVIEW" | "PROXY_RENDER_REQUIRED";
export type PreviewQualityLevel = "full" | "approximate" | "proxy" | "placeholder";

export interface PreviewFidelityDiagnostics {
  code: string;
  message: string;
  entityId?: string;
  entityType?: "document" | "scene" | "layer" | "effect" | "transition";
  suggestedAction?: string;
}

export interface PreviewCapabilityAssessment {
  mode: PreviewMode;
  qualityLevel: PreviewQualityLevel;
  reason: string;
  requiredCapabilities: readonly CanonicalRendererCapability[];
  unsupportedCapabilities: readonly CanonicalRendererCapability[];
  approximatedCapabilities: readonly CanonicalRendererCapability[];
  affectedEntities: readonly {
    entityId: string;
    entityType: "scene" | "layer" | "effect" | "transition";
    mode: PreviewMode;
    reason: string;
  }[];
  proxyRequired: boolean;
  diagnostics: readonly PreviewFidelityDiagnostics[];
}
```

### 3.1 Evaluation Function

```typescript
export function resolvePreviewFidelity(
  doc: VideoDocument,
  options?: {
    customNativeCapabilities?: readonly CanonicalRendererCapability[];
    strictApproximations?: boolean;
  }
): PreviewCapabilityAssessment;
```

- Inspects every scene, layer, transition, and effect.
- Aggregates missing capabilities against the browser baseline:
  - If any missing capability has no registered approximation $\to$ `PROXY_RENDER_REQUIRED`.
  - If missing capabilities can be approximated $\to$ `APPROXIMATE_PREVIEW`.
  - If all capabilities are natively executable $\to$ `LIVE_NATIVE`.

---

## 4. Engine-Neutral Architecture Guard

1. Canonical contracts ([`contracts/preview-fidelity.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts), [`contracts/preview-proxy.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts)) do **not** import Remotion, Canvas, React, or FFmpeg packages.
2. All capability declarations utilize the standardized [`CanonicalRendererCapability`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/renderer.ts) union.
3. [`BrowserPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts) queries [`RendererRegistry`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/renderer.ts) via abstract interfaces, completely decoupled from concrete rendering implementations.
