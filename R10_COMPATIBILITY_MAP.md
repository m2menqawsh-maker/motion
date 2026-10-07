# R10 Compatibility & Multi-Renderer Dispatch Map

**Status**: Verified Reality Specification  
**Milestone**: S28-R10 (Canvas / FFmpeg Alternative Headless Renderer Adapter)  

---

## 1. Overview & Multi-Engine Architecture

Milestone **S28-R10** expands the single-engine Remotion platform (S28-R09) into a true multi-engine rendering subsystem.

The system now operates with two concrete production rendering engines:
1. `CanvasRendererAdapter` (`canvas-renderer-adapter`): Lightweight, headless 2D vector canvas engine with sub-second frame rendering.
2. `RemotionRendererAdapter` (`remotion-engine-adapter`): Full-featured headless video engine with complete React DOM and audio graph capabilities.

```text
                           RenderRequest (contracts/renderer.ts)
                                            │
                                            ▼
                           CANONICAL_RENDERER_REGISTRY
                                            │
                                            ▼
                           selectRenderer(request) [Fail-Closed]
                                            │
            ┌───────────────────────────────┴───────────────────────────────┐
            │                                                               │
  Request Requirements:                                           Request Requirements:
  • 2D Visuals (text, shape, image)                               • Video Layer (`video`)
  • Keyframes, transitions, alpha                                 • Audio Ducking (`audio_ducking`)
  • Frame, sequence, or video export                              • Multi-track mixing (`audio_mixing`)
            │                                                               │
            ▼                                                               ▼
   CanvasRendererAdapter                                           RemotionRendererAdapter
     (Priority: 110)                                                 (Priority: 100)
            │                                                               │
            ▼                                                               ▼
     Output: Sub-second PNG/MP4                                      Output: Full DOM Video/MP4
```

---

## 2. Dispatch Resolution Map

| Request Profile | Key Required Capabilities | Selected Engine | Selection Mechanism |
| :--- | :--- | :--- | :--- |
| **Simple 2D Frame** | `text`, `shapes`, `frame_rendering` | `CanvasRendererAdapter` | Both compatible; Canvas wins by higher priority (110 vs 100) |
| **Animated 2D Sequence** | `text`, `shapes`, `keyframes`, `sequence_rendering` | `CanvasRendererAdapter` | Both compatible; Canvas wins by higher priority (110 vs 100) |
| **Video Background Project** | `text`, `video`, `frame_rendering` | `RemotionRendererAdapter` | Canvas lacks `video`; Remotion is sole compatible engine |
| **Audio-Ducked Project** | `text`, `audio_ducking`, `export_video` | `RemotionRendererAdapter` | Canvas lacks `audio_ducking`; Remotion is sole compatible engine |
| **Explicit Preferred Canvas** | `text`, `shapes` (preferred: `canvas-renderer-adapter`) | `CanvasRendererAdapter` | Explicit request satisfied without fallback |
| **Explicit Preferred Remotion**| `text`, `shapes` (preferred: `remotion-engine-adapter`) | `RemotionRendererAdapter` | Explicit request satisfied without fallback |
| **Invalid Engine Preference** | `video` (preferred: `canvas-renderer-adapter`) | **FAILS CLOSED** | `UnsupportedCapabilityError` thrown; zero silent fallback |
| **Advanced 3D Project** | `3d`, `webgl` | **FAILS CLOSED** | `NoCompatibleRendererError` thrown |
| **Interactive Map Project** | `map`, `webgl` (`rui-map-flight`) | **FAILS CLOSED** | `NoCompatibleRendererError` thrown |

---

## 3. Native TemplateSpec Coverage Matrix

| TemplateSpec ID | Classification | `CanvasRendererAdapter` Status | `RemotionRendererAdapter` Status | Preferred Dispatch |
| :--- | :--- | :---: | :---: | :---: |
| `rui-title-card` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-quote-card` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-stat-card` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-lower-third` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-intro` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-media-frame` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-bento-pan` | Native 2D (R05) | **VERIFIED PASS** | **VERIFIED PASS** | `CanvasRendererAdapter` (14x faster) |
| `rui-map-flight` | Engine-Backed | **REJECTED (Fail-Closed)** | **REJECTED (Fail-Closed)** | `NO_COMPATIBLE_RENDERER` |
| `scene3d-element` | Engine-Backed | **REJECTED (Fail-Closed)** | **REJECTED (Fail-Closed)** | `NO_COMPATIBLE_RENDERER` |
| `particlesystem-element`| Engine-Backed | **REJECTED (Fail-Closed)** | **REJECTED (Fail-Closed)** | `NO_COMPATIBLE_RENDERER` |

---

## 4. Performance & Operational Profile

```text
┌─────────────────────────────────┬──────────────────────────────────┐
│ CanvasRendererAdapter           │ RemotionRendererAdapter          │
├─────────────────────────────────┼──────────────────────────────────┤
│ • Cold startup: 189 ms          │ • Cold startup: 2,736 ms         │
│ • Single frame: 205 ms          │ • Single frame: 2,370 ms         │
│ • 4-frame seq: 724 ms           │ • 4-frame seq: 6,109 ms          │
│ • 30-frame seq: 5,416 ms        │ • 30-frame seq: 38,079 ms        │
│ • Heap footprint: 0.96 MB       │ • Heap footprint: 19.72 MB       │
│ • Best for: Fast frame captures,│ • Best for: Full video exports,  │
│   preview thumbnails, discrete  │   HTML5/DOM compositions,        │
│   motion sequences.             │   multi-track audio ducking.     │
└─────────────────────────────────┴──────────────────────────────────┘
```
