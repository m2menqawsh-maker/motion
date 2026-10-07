# System Authority Matrix: Reality Audit & Evolution

**Status**: Verified Reality Specification  
**Current Milestone**: S28-R13 (AI + Templates + Editor Unified Authoring)  
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
| **Unified Authoring Authority** | `authoring/unified-authoring-session.ts` (`UnifiedAuthoringSession`) & `contracts/authoring.ts` | `SINGLE_AUTHORITY` | S28-R13 unified authoring pipeline. AI, User, and Templates all mutate the exact same Canonical VideoDocument via typed Mutation Engine. |
| **AI Intent Translation** | `authoring/intent-planner.ts` (`planAuthoringIntent`) | `SINGLE_AUTHORITY` | S28-R13 pure intent-to-mutation translator targeting stable IDs (`scene_id`, `layer_id`, `clip_id`). Fails closed on ambiguity or unsupported capabilities. Zero renderer code emitted. |
| **Timeline / Timing Authority** | `contracts/canonical-video.ts` & `evaluateVideoAtFrame` (`contracts/evaluator.ts`) | `SINGLE_AUTHORITY` | S28-R03 unified timeline evaluation. Evaluator computes exact frame state deterministically without engine dependencies. |
| **Editor State & Mutations** | `contracts/mutations.ts` & `contracts/editor-session.ts` | `SINGLE_AUTHORITY` | S28-R04 established bijective mutations (`applyMutationToDocument`), granular ChangeSets, and undo/redo history. |
| **Template Identity & Instantiation** | `contracts/template-spec.ts` & `contracts/template-instantiator.ts` | `SINGLE_AUTHORITY` | S28-R05 established engine-neutral template schemas and deterministic instantiation. |
| **Preview Fidelity Resolution** | `contracts/preview-fidelity.ts` (`resolvePreviewFidelity`) | `SINGLE_AUTHORITY` | S28-R07B engine-neutral fidelity assessment classifying native, approximate, or proxy required. Zero renderer package imports. |
| **Visual Preview Playhead** | `preview/preview-runtime.ts` (`BrowserPreviewRuntime`) | `SINGLE_AUTHORITY` | S28-R06 established headless browser-neutral live preview runtime. Sole master clock for interactive playback. Consumes proxy artifacts as auxiliary visual nodes. |
| **Preview Proxy Coordinator & Cache** | `preview/proxy/` (`PreviewProxyCoordinator` & `PreviewProxyCache`) | `SUBORDINATED_AUTHORITY` | S28-R07B subordinated to canonical ChangeSets, revision guards, and RendererRegistry dispatch. Never mutates documents or asserts final render authority. |
| **Audio Playback & Preview** | `preview/audio/audio-preview-runtime.ts` | `SUBORDINATED_AUTHORITY` | S28-R07 subordinated audio playback to `BrowserPreviewRuntime`. Has zero independent clock; syncs on play, pause, seek, step, rate. |
| **Waveform Generation** | `contracts/waveform.ts` (`extractWaveformPeaks`) | `SINGLE_AUTHORITY` | S28-R07 framework-neutral pure numeric peak extractor with deterministic LRU caching. Zero Web Audio/React coupling. |
| **Effects Catalog** | `contracts/effects.ts` & `registry/effects-runtime.ts` | `SINGLE_AUTHORITY` | Governed by canonical effect schemas with type-safe parameter validation. |
| **Audio Plan Semantics** | `contracts/blueprint.ts` (`AudioPlanSchema`) | `SINGLE_AUTHORITY` | Strict contract for voiceover, music, global SFX, and ducking parameters. |
| **Renderer Registry & Selection** | `contracts/renderer.ts` (`RendererRegistry` / `CANONICAL_RENDERER_REGISTRY`) | `SINGLE_AUTHORITY` | S28-R08 single authority for registering renderers, capability declarations, and deterministic compatible adapter selection. |
| **Render Planning Authority** | `planner/render-planner.ts` (`RenderPlanner`) & `contracts/render-graph.ts` | `SINGLE_AUTHORITY` | S28-R12 single authority for decomposing Canonical VideoDocuments into deterministic RenderPlans and DAG topological levels. Queries RendererRegistry for engine capabilities. |
| **RenderGraph Execution** | `planner/render-graph-executor.ts` (`RenderGraphExecutor`) | `SUBORDINATED_AUTHORITY` | S28-R12 subordinated local execution orchestrator. Dispatches nodes across engines concurrently/sequentially and manages artifact cache. Zero canonical document mutation authority. |
| **Remotion Execution** | `RemotionRendererAdapter` (`remotion/remotion-renderer-adapter.ts`) | `SUBORDINATED_AUTHORITY` | S28-R09 production adapter. Subordinated to `RenderRequest` and `RendererRegistry` selection. Renders canonical documents via `CanonicalVideo.tsx` using `evaluateVideoAtFrame()`. Zero video semantics authority. |
| **Canvas Execution** | `CanvasRendererAdapter` (`canvas/canvas-renderer-adapter.ts`) | `SUBORDINATED_AUTHORITY` | S28-R10 second production adapter. Subordinated to `RenderRequest` and `RendererRegistry` selection. Headless 2D vector canvas engine with sub-second frame rendering. Zero video semantics authority. |
| **Master Compositor & Assembly** | `MasterCompositor` (`compositor/master-compositor.ts`) | `SUBORDINATED_AUTHORITY` | S28-R11 central engine-neutral assembly orchestrator. Subordinated to Canonical VideoDocument timeline and CompositorRequest. Zero video semantics authority, zero renderer selection authority. |
| **Output Normalization** | `compositor/output-normalizer.ts` | `SUBORDINATED_AUTHORITY` | S28-R11 deterministic normalization engine enforcing OutputProfile resolution, fps, timebase, and codec policies. |
| **Quality Control (QC)** | `scripts/gates/final_qc.py` | `SINGLE_AUTHORITY` | Authoritative post-render inspection using `ffprobe` against Blueprint V2. Integrated via `compositor/qc-adapter.ts`. |

---

## 2. Rendering, Planning & Composition Authority Hierarchy (S28-R12)

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
│   Canvas Renderer Adapter   │ │  Remotion Renderer Adapter  │
│ (Lightweight 2D / FFmpeg)   │ │ (Headless MP4/WebM Export)  │
│  Subordinated to Registry   │ │  Subordinated to Registry   │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────┐
│           Intermediate Artifacts / Outputs             │
│        (Explicit Provenance, Time Range, Format)       │
└──────────────────────────────┬─────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────┐
│                   Master Compositor                    │
│           [Engine-Neutral Assembly Authority]          │
│  • Input & Artifact Validation (Fail-Closed)           │
│  • Canonical Timeline & Scene Assembly (No new clock)  │
│  • Output Normalization (Res, FPS, Timebase, Codec)    │
│  • Audio Normalization & Ducking (R07 Semantics)       │
└──────────────────────────────┬─────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────┐
│                  Final Video Artifact                  │
│                  (CompositorResult)                    │
└──────────────────────────────┬─────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────┐
│                 Existing Final QC Gate                 │
│              (scripts/gates/final_qc.py)               │
└────────────────────────────────────────────────────────┘
```

### Architectural Guarantees:
1. **Single Selection Authority**: `CANONICAL_RENDERER_REGISTRY` is the sole authority deciding compatible renderers for any render request. Master Compositor does NOT select renderers (renderer selection & planning belongs to R12).
2. **Deterministic Multi-Renderer Assembly**: Master Compositor seamlessly unites artifacts produced by different engines (Canvas, Remotion, future engines) into a unified timeline.
3. **Canonical Timing Authority**: The Canonical VideoDocument (`BlueprintV2`) remains the single timing authority. The compositor has zero independent clock; all durations, transition overlaps, and audio cues align strictly with canonical frames.
4. **Output Normalization Enforcement**: OutputProfile strictly enforces target resolution, framerate, pixel format, audio sample rate, and container codecs. Incompatible artifacts fail closed without silent passes.
5. **Fail-Closed Composition**: Structured errors (`INCOMPATIBLE_INPUT`, `INVALID_TIMEBASE`, `MISSING_ARTIFACT`, `UNSUPPORTED_FORMAT`, `NORMALIZATION_FAILED`, `COMPOSITION_FAILED`, `AUDIO_SYNC_ERROR`) halt corrupted assembly immediately.
6. **Engine-Neutral Boundary**: Canonical contracts (`contracts/compositor.ts`, `contracts/renderer.ts`) contain zero concrete engine dependencies. Concrete FFmpeg execution remains strictly isolated within `compositor/`.
7. **Clean Lifecycle & Resource Cleanup**: Cancellation via `AbortSignal` immediately terminates FFmpeg processes and completely evicts temporary working files without orphaned disk clutter.

---

## 3. Unified Authoring Authority Hierarchy (S28-R13)

```text
┌────────────────────────────────────────────────────────┐
│                      CreativePlan                      │
│            (Transient Planning Input Only)             │
└──────────────────────────┬─────────────────────────────┘
                           │ compileCreativePlanToCanonical()
                           ▼
┌────────────────────────────────────────────────────────┐
│                Canonical VideoDocument                 │
│               [Sole Persistent Authority]              │
│                (BlueprintV2, Revision N)               │
└──────────────────────────┬─────────────────────────────┘
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
      ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌────────────────┐
│   AI Agent   │   │  Human User  │   │  TemplateSpec  │
│  (Intent)    │   │ (Direct UI)  │   │  (Parameters)  │
└──────┬───────┘   └──────┬───────┘   └───────┬────────┘
       │                  │                   │
       ▼                  │                   ▼
┌──────────────┐          │            ┌───────────────┐
│IntentPlanner │          │            │  Instantiator │
│(Pure Mapping)│          │            │  / Adapter    │
└──────┬───────┘          │            └──────┬────────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│               Typed Canonical Mutations                │
│    (UPDATE_TEXT, UPDATE_STYLE, UPDATE_TRANSFORM, etc.) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                UnifiedAuthoringSession                 │
│                 [Authoring Authority]                  │
│  • Optimistic Revision Guard (expected_revision)       │
│  • Deterministic Idempotency Cache                     │
│  • Atomic Compound Batch Execution                     │
│  • Bijective Inverse Generation (EditorSession)        │
│  • Unified Single Undo/Redo Stack                      │
│  • Provenance Metadata Audit Log                       │
└──────────────────────────┬─────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────┐                      ┌──────────────┐
│  ChangeSet   │                      │  Canonical   │
│  (Granular)  │                      │ VideoDocument│
└──────┬───────┘                      │(Revision N+1)│
       │                              └──────┬───────┘
       ▼                                     │
┌──────────────┐                             ▼
│PreviewRuntime│                      ┌──────────────┐
│(Proxy Inval) │                      │RenderPlanner │
└──────────────┘                      └──────────────┘
```

### Authoring Guarantees:
1. **Single Source of Truth**: `Canonical VideoDocument` (`BlueprintV2`) is the sole persistent authority. No competing persistent documents exist.
2. **Unified Mutation Engine**: Human users, AI agents, and Templates modify documents strictly through typed `CanonicalMutation` objects handled by `EditorSession`.
3. **Preservation of User Edits**: AI edits target specific entities by stable IDs (`scene_id`, `layer_id`, `clip_id`). Downstream AI edits never trigger whole-project re-compilations that wipe out user changes.
4. **Concurrency Conflict Protection**: Any edit submitted with a stale `base_revision` fails closed with `REVISION_CONFLICT`.
5. **Zero Renderer Code Generation**: The AI authoring layer generates typed intent/mutation structures only; it is architecturally prohibited from generating React/Remotion/Canvas/FFmpeg code.

