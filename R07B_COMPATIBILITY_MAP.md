# R07B Compatibility & Subsystem Integration Map

**Status**: Verified Reality Specification  
**Milestone**: S28-R07B (Preview Fidelity, Cache & Proxy System)  
**Contract Sources**:
- [`contracts/preview-fidelity.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts)
- [`contracts/preview-proxy.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts)
- [`preview/proxy/proxy-cache.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-cache.ts)
- [`preview/proxy/proxy-coordinator.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-coordinator.ts)

---

## 1. Multi-Milestone Architectural Integration

Milestone **S28-R07B** closes the original fidelity, cache, and proxy scope by weaving together the foundational milestones of the video platform:

```text
               ┌────────────────────────────────────────────────────────┐
               │              S28-R04 Editor Session                    │
               │   Bijective Mutations & Granular ChangeSet Emitted     │
               └──────────────────────────┬─────────────────────────────┘
                                          │ ChangeSet
                                          ▼
┌────────────────────────────────┐ ┌────────────────────────────────┐
│      S28-R06 Preview           │ │    S28-R07B Invalidation       │
│   BrowserPreviewRuntime        │ │    PreviewProxyCache           │
│   (Sole Master Playhead Clock) │ │    (Selective Dependency Evict)│
└──────────────┬─────────────────┘ └────────────────┬───────────────┘
               │                                    │
               │ Synchronized                       │ Active Proxies
               ▼                                    ▼
┌────────────────────────────────┐ ┌────────────────────────────────┐
│      S28-R07 Audio             │ │    S28-R07B Visual Frame       │
│   AudioPreviewRuntime          │ │    buildVisualFrame()          │
│   (Subordinated Master Clock)  │ │    (Injects Proxy Visual Nodes)│
└────────────────────────────────┘ └────────────────┬───────────────┘
                                                    │
                                                    ▼
                                   ┌────────────────────────────────┐
                                   │  S28-R08 / R09 / R10 Dispatch  │
                                   │  RendererRegistry (Selection)  │
                                   │  Canvas (110) / Remotion (100) │
                                   └────────────────────────────────┘
```

---

## 2. Fidelity Resolution Matrix

The following table details how project elements are classified by [`resolvePreviewFidelity()`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts) and executed:

| Document Element | Feature / Capability | Preview Mode | Quality Level | Execution Mechanism | Proxy Required |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Text Layer** | `typography`, `styling`, `transforms` | `LIVE_NATIVE` | `full` | Browser DOM/Canvas | **NO** |
| **Image Layer** | Static PNG, JPEG, SVG | `LIVE_NATIVE` | `full` | Browser `<img>` / canvas drawing | **NO** |
| **Shape Layer** | Rectangles, circles, paths | `LIVE_NATIVE` | `full` | Browser vector rendering | **NO** |
| **Linear Transition** | `fade`, `crossfade`, `slide` | `LIVE_NATIVE` | `full` | Real-time CSS / Canvas interpolation | **NO** |
| **Native Audio** | Voiceover, music, sound effects | `LIVE_NATIVE` | `full` | [`AudioPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/audio/audio-preview-runtime.ts) Web Audio | **NO** |
| **Complex Transition**| `zoom`, `wipe`, `iris`, `morph` | `APPROXIMATE_PREVIEW` | `approximate` | Deterministic crossfade approximation | **NO** |
| **Visual Blur Effect**| Gaussian blur, heavy dropshadow | `APPROXIMATE_PREVIEW` | `approximate` | CSS filter / fast canvas box blur | **NO** |
| **Engine-Backed Template**| `rui-map-flight`, 3D scenes | `PROXY_RENDER_REQUIRED` | `proxy` / `placeholder` | Asynchronous render via `RendererRegistry` | **YES** |
| **Custom Shader** | GLSL post-processing | `PROXY_RENDER_REQUIRED` | `proxy` / `placeholder` | Asynchronous render via `RendererRegistry` | **YES** |
| **Advanced Video Composite**| Multi-track alpha / video blending | `PROXY_RENDER_REQUIRED` | `proxy` / `placeholder` | Asynchronous render via `RendererRegistry` | **YES** |

---

## 3. Proxy Generation & Renderer Dispatch Resolution

When `PROXY_RENDER_REQUIRED` triggers a [`PreviewProxyRequest`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts), the coordinator dispatches through [`RendererRegistry`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/renderer.ts):

| Proxy Fragment Profile | Capabilities Required | Selected Adapter | Selection Rationale |
| :--- | :--- | :--- | :--- |
| **2D Vector / Static Card** | `text`, `shapes`, `frame_rendering` | `CanvasRendererAdapter` | Canvas priority 110 > Remotion 100 ($14\times$ faster generation) |
| **Video Background Sequence**| `video`, `sequence_rendering` | `RemotionRendererAdapter` | Canvas lacks `video`; Remotion is sole compatible adapter |
| **Audio-Synced Fragment** | `audio_mixing`, `export_video` | `RemotionRendererAdapter` | Canvas lacks multi-track mixing; Remotion is sole compatible adapter |
| **Unsupported Engine (3D/Map)**| `map`, `webgl`, `3d` | **FAILS CLOSED** | `NO_COMPATIBLE_RENDERER` diagnostic emitted; zero broken fallback |

---

## 4. Mutation & Invalidation Matrix

Integration with S28-R04 [`ChangeSet`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/mutations.ts):

| Mutation Operation | ChangeSet Footprint | Target Proxies Affected | Unrelated Proxies |
| :--- | :--- | :--- | :--- |
| **`UPDATE_LAYER` (Text in Scene 1)** | `scenesUpdated: ["scene-1"]`, `layersUpdated: ["layer-1"]` | Scene 1 proxies evicted | **Scene 2 & Scene 3 preserved** |
| **`ADD_LAYER` (Shape in Scene 2)** | `scenesUpdated: ["scene-2"]`, `layersAdded: ["layer-shape"]` | Scene 2 proxies evicted | **Scene 1 & Scene 3 preserved** |
| **`DELETE_SCENE` (Scene 3)** | `scenesRemoved: ["scene-3"]` | Scene 3 proxies evicted | **Scene 1 & Scene 2 preserved** |
| **`UPDATE_TIME_RANGE` (Scene 1)** | `affectedTimeRange: [0, 90]` | Proxies overlapping `[0, 90]` evicted | Proxies outside range preserved |
| **`SET_ASSET` (Image replaced)** | `assetsUpdated: ["asset-bg"]` | Proxies depending on `asset-bg` evicted | Other assets preserved |
| **`UNDO` / `REDO`** | Bijective ChangeSet restoring revision | Matched revision cache hit retrieved | Stale revisions discarded |

---

## 5. Architectural Guardrails Verified

- **Sole Playhead Authority**: [`BrowserPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts) remains the single master clock. The proxy subsystem does not spawn parallel players or clocks.
- **Audio Synchronization**: Visual proxy swapping does not interrupt or desynchronize [`AudioPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/audio/audio-preview-runtime.ts). Audio playback continues uninterrupted across proxy background generation.
- **Fail-Closed Diagnostics**: Any feature lacking browser support and lacking a registered renderer produces explicit diagnostics and never silently degrades to broken visual output.
