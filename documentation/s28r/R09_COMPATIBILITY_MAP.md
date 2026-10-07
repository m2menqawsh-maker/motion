# R09 Compatibility & Render Path Migration Map

**Status**: Verified Reality Specification  
**Milestone**: S28-R09 (Remotion Renderer Adapter & Engine Abstraction)  

---

## 1. Overview & Migration Architecture

Prior to S28-R09, project rendering relied on `scripts/render_project.py` directly executing the Remotion CLI with raw JSON props files, coupling the rendering lifecycle directly to Remotion's internal composition model.

S28-R09 introduces a structured, backwards-compatible migration that routes render invocations through the canonical registry abstraction while preserving uninterrupted operation for existing scripts and production pipelines.

```text
                               Legacy Invocation Path
                               (scripts/render_project.py)
                                           │
                                           ▼
                     Does project contain canonical BlueprintV2?
                                           │
                   ┌───────────────────────┴───────────────────────┐
                   │ YES                                           │ NO (Legacy Format)
                   ▼                                               ▼
         scripts/render_via_adapter.ts                 Legacy Remotion CLI Fallback
                   │                                     (npx remotion render)
                   ▼
             RenderRequest
                   │
                   ▼
     CANONICAL_RENDERER_REGISTRY
                   │
                   ▼
        RemotionRendererAdapter
                   │
                   ▼
        @remotion/renderer (renderMedia)
                   │
                   ▼
             RenderResult
```

---

## 2. Compatibility Bridges

### 2.1 CLI Adapter Bridge (`scripts/render_via_adapter.ts`)
A dedicated Node.js CLI bridge that:
- Reads the target project JSON / BlueprintV2.
- Normalizes input into a canonical `BlueprintV2` video document.
- Constructs a strongly-typed `RenderRequest`.
- Automatically registers `RemotionRendererAdapter` into `CANONICAL_RENDERER_REGISTRY`.
- Dispatches the request through `CANONICAL_RENDERER_REGISTRY.selectRenderer(request).exportVideo(request)`.
- Writes out structured execution metrics (`renderTimeMs`, `evaluatedFrames`, output file size).

### 2.2 Python Orchestrator Bridge (`scripts/render_project.py`)
`scripts/render_project.py` updated to execute `render_via_adapter.ts` by default:
1. Validates the existence of the adapter bridge script.
2. Invokes `scripts/render_via_adapter.ts` with output path, props, and concurrency settings.
3. If the project utilizes unmigrated legacy props formats or the adapter encounters unsupported capabilities, gracefully falls back to the legacy Remotion CLI execution path.

### 2.3 Remotion App Root Compositions (`remotion-app/src/Root.tsx`)
Both composition trees coexist within Remotion's root catalog:
- `<Composition id="CanonicalVideo" ... />`: Consumes pure canonical `BlueprintV2` evaluated per frame via `evaluateVideoAtFrame()`.
- `<Composition id="BlueprintVideo" ... />`: Retained for 100% backwards compatibility with legacy production render jobs.

---

## 3. Template Compatibility Matrix

| Template ID | Family | S28-R09 Remotion Adapter Status | Execution Composition | Capabilities Required |
| :--- | :--- | :--- | :--- | :--- |
| `rui-title-card` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `typography`, `vector_shapes`, `keyframe_transforms` |
| `rui-quote-card` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `typography`, `vector_shapes`, `keyframe_transforms` |
| `rui-media-frame` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `multi_layer_compositing`, `typography`, `vector_shapes` |
| `rui-lower-third` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `typography`, `vector_shapes`, `transitions_basic` |
| `rui-stat-card` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `typography`, `vector_shapes`, `keyframe_transforms` |
| `rui-intro` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `typography`, `vector_shapes`, `transitions_basic` |
| `rui-bento-pan` | Native (R05) | **Supported & Verified** | `CanonicalVideo` | `multi_layer_compositing`, `typography`, `vector_shapes` |
| `rui-map-flight` | Engine-Backed | **Rejected (Fail-Closed)** | N/A | Requires `map` capability |
| `scene3d-element` | Engine-Backed | **Rejected (Fail-Closed)** | N/A | Requires `3d` capability |
| `particlesystem-element`| Engine-Backed | **Rejected (Fail-Closed)** | N/A | Requires `particles` capability |
| Legacy Compositions | Legacy | **Supported via Bridge** | `BlueprintVideo` | Legacy Remotion CLI path |

---

## 4. Audio Parity Mapping

Canonical audio definitions in `document.audio` (voiceover, music, global SFX, and ducking rules) are evaluated with strict semantic parity:

| Audio Feature | Canonical Evaluator / Browser Preview | Remotion Adapter Implementation | Parity Status |
| :--- | :--- | :--- | :--- |
| **Voiceover Timing** | `startFrame`, `durationFrames`, `volume` | Remotion `<Audio src={resolveMediaSrc(vo.asset_ref)} />` inside `<Sequence from={vo.startFrame} durationInFrames={vo.durationFrames}>` | **Exact Parity** |
| **Music Background** | Looping/trimmed track, base volume | Remotion `<Audio src={resolveMediaSrc(music.asset_ref)} loop={music.loop} />` | **Exact Parity** |
| **Dynamic Ducking** | Attenuates music to `ducking_volume` when voiceover active | Dynamic callback `volume={(frame) => duckedVolume(frame)}` querying `evaluateVideoAtFrame(doc, frame)` | **Exact Parity** |
| **SFX Mixing** | Discrete cues with individual volumes | Remotion `<Audio src={resolveMediaSrc(sfx.asset_ref)} />` inside cue sequences | **Exact Parity** |
| **Track Mute** | `mute: true` zeroes gain | Evaluated to `0.0` volume | **Exact Parity** |

---

## 5. Preview Independence Guarantee

The browser preview system (`preview/preview-runtime.ts` and `preview/audio/audio-preview-runtime.ts`) maintains **zero imports** and **zero runtime dependency** on Remotion, `@remotion/renderer`, or `RemotionRendererAdapter`. 

The preview runtime operates purely in the DOM/Canvas/Web Audio domain, verifying that Remotion is strictly an export engine and not a prerequisite for authoring, editing, or previewing video.
