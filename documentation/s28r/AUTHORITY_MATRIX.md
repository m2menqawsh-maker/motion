# System Authority Matrix: Reality Audit & Evolution

**Status**: Verified Reality Specification  
**Current Milestone**: S28-R09 (Remotion Renderer Adapter & Engine Abstraction)  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Global Concern vs Authority Matrix

This matrix maps every foundational architectural concern in the video system to its authoritative subsystem, classifying each as:
- `SINGLE_AUTHORITY`: A clean, unambiguous source of truth.
- `DUPLICATED_AUTHORITY`: Two or more subsystems calculate or assert truth, creating drift risks.
- `SUBORDINATED_AUTHORITY`: An execution runtime strictly governed by a single upstream canonical authority.

| Concern | Authoritative Subsystem | Status | Evolution & Architecture Invariants |
| :--- | :--- | :--- | :--- |
| **Video Structure** | `contracts/blueprint.ts` (`BlueprintV2Schema`) & `contracts/canonical-video.ts` | `SINGLE_AUTHORITY` | Strict Zod schemas enforce project ID, aspect ratio, fps, scenes, tracks fail-closed. |
| **Timeline / Timing Authority** | `contracts/canonical-video.ts` & `evaluateVideoAtFrame` (`contracts/evaluator.ts`) | `SINGLE_AUTHORITY` | S28-R03 unified timeline evaluation. Evaluator computes exact frame state deterministically without engine dependencies. |
| **Editor State & Mutations** | `contracts/mutations.ts` & `contracts/editor-session.ts` | `SINGLE_AUTHORITY` | S28-R04 established bijective mutations (`applyMutationToDocument`), granular ChangeSets, and undo/redo history. |
| **Template Identity & Instantiation** | `contracts/template-spec.ts` & `contracts/template-instantiator.ts` | `SINGLE_AUTHORITY` | S28-R05 established engine-neutral template schemas and deterministic instantiation. |
| **Visual Preview Playhead** | `preview/preview-runtime.ts` (`BrowserPreviewRuntime`) | `SINGLE_AUTHORITY` | S28-R06 established headless browser-neutral live preview runtime. Sole master clock for interactive playback. Not a renderer authority. |
| **Audio Playback & Preview** | `preview/audio/audio-preview-runtime.ts` | `SUBORDINATED_AUTHORITY` | S28-R07 subordinated audio playback to `BrowserPreviewRuntime`. Has zero independent clock; syncs on play, pause, seek, step, rate. |
| **Waveform Generation** | `contracts/waveform.ts` (`extractWaveformPeaks`) | `SINGLE_AUTHORITY` | S28-R07 framework-neutral pure numeric peak extractor with deterministic LRU caching. Zero Web Audio/React coupling. |
| **Effects Catalog** | `contracts/effects.ts` & `registry/effects-runtime.ts` | `SINGLE_AUTHORITY` | Governed by canonical effect schemas with type-safe parameter validation. |
| **Audio Plan Semantics** | `contracts/blueprint.ts` (`AudioPlanSchema`) | `SINGLE_AUTHORITY` | Strict contract for voiceover, music, global SFX, and ducking parameters. |
| **Renderer Registry & Selection** | `contracts/renderer.ts` (`RendererRegistry` / `CANONICAL_RENDERER_REGISTRY`) | `SINGLE_AUTHORITY` | S28-R08 single authority for registering renderers, capability declarations, and deterministic compatible adapter selection. |
| **Renderer Execution** | `RemotionRendererAdapter` (`remotion/remotion-renderer-adapter.ts`) | `SUBORDINATED_AUTHORITY` | S28-R09 production adapter replacing stub. Subordinated to `RenderRequest` and `RendererRegistry` selection. Renders canonical documents via `CanonicalVideo.tsx` using `evaluateVideoAtFrame()`. Zero video semantics authority. |
| **Quality Control (QC)** | `scripts/gates/final_qc.py` | `SINGLE_AUTHORITY` | Authoritative post-render inspection using `ffprobe` against Blueprint V2. |

---

## 2. Rendering & Engine Decoupling Authority Hierarchy (S28-R08)

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

### Architectural Guarantees:
1. **Single Selection Authority**: `CANONICAL_RENDERER_REGISTRY` is the sole authority deciding compatible renderers for any render request. No external scripts or components make ad-hoc renderer decisions.
2. **Fail-Closed Selection**: If required capabilities are missing from all registered adapters, `selectRenderer()` raises `NO_COMPATIBLE_RENDERER`. Silent degradation or fallback to incomplete engines is strictly forbidden.
3. **Engine-Neutral Core**: `contracts/renderer.ts` and all canonical contracts contain zero imports from concrete rendering engines (`remotion`, `@remotion/*`, `react`, `ffmpeg`, `canvas`, `webgl`).
4. **Preview Independence**: `BrowserPreviewRuntime` remains an interactive playhead driver and does NOT usurp rendering authority.
