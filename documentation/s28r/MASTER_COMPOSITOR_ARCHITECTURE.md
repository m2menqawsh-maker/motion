# Master Compositor Architecture

**Milestone**: S28-R11  
**Status**: ACTIVE / PRODUCTION READY  
**Component**: `compositor/master-compositor.ts`  

---

## 1. Architectural Mission

The **Master Compositor** decouples final video assembly and multi-engine stitching from individual rendering engine adapters. Prior to S28-R11, rendering adapters were expected to export finished, monolithic MP4 artifacts independently. 

Under the S28 architecture, individual rendering engines (`CanvasRendererAdapter`, `RemotionRendererAdapter`, and future 3D/Map/Shader engines) act as **subordinated scene/layer producers**. The Master Compositor operates as the **engine-neutral assembly orchestrator**, accepting discrete intermediate artifacts and assembling them into a unified, normalized final artifact.

```text
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     CanvasRendererAdapter       │   │    RemotionRendererAdapter      │
│     (2D Vector / Overlays)      │   │    (Video / Complex Audio)      │
└────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │ Intermediate Artifact               │ Intermediate Artifact
                 └───────────────────┬─────────────────┘
                                     ▼
                       ┌───────────────────────────┐
                       │     Master Compositor     │
                       │ (compositor/master-compositor.ts)
                       └─────────────┬─────────────┘
                                     │
                                     ▼
                       ┌───────────────────────────┐
                       │   Output Normalization    │
                       │ (compositor/output-normalizer.ts)
                       └─────────────┬─────────────┘
                                     │
                                     ▼
                       ┌───────────────────────────┐
                       │    Final Video Artifact   │
                       │      (Single MP4)         │
                       └─────────────┬─────────────┘
                                     │
                                     ▼
                       ┌───────────────────────────┐
                       │  Existing Final QC Gate   │
                       │ (scripts/gates/final_qc.py)
                       └───────────────────────────┘
```

---

## 2. Invariant Boundaries & Authority Rules

1. **Not a Renderer**: The Master Compositor is strictly an assembly orchestrator. It does not evaluate graphics primitives, canvas elements, or WebGL shaders.
2. **Not a Renderer Planner**: The Master Compositor does not decide which engine renders which scene. Renderer selection and planning is the domain of **S28-R12 (Multi-Engine RenderGraph & Render Planner)**. In R11, inputs are explicitly matched to scenes via `canonicalSceneId` or index.
3. **Not a Canonical Authority**: The Master Compositor never invents an independent timeline clock. All durations, start frames, transitions, and audio cues are derived strictly from the **Canonical VideoDocument** (`BlueprintV2`).
4. **Zero Mutation Authority**: The Master Compositor does not mutate canonical documents. It reads canonical states and maps artifacts to canonical time ranges.
5. **Fail-Closed Execution**: If any scene artifact is missing, has an incompatible timebase, or fails normalization, execution halts immediately with structured error codes. Silent degradation or empty frames are prohibited.

---

## 3. Subsystem Breakdown

### 3.1 Input & Provenance Ingestion (`compositor/probe.ts`)
- Leverages `ffprobe` to inspect media files, extracting exact duration, fps, resolution, pixel format, audio sample rate, channels, and alpha support.
- Wraps intermediate outputs into immutable `IntermediateArtifact` instances containing `sourceRendererId`, `scope`, `timeRange`, `mediaInfo`, and a deterministic SHA-256 `contentFingerprint`.

### 3.2 Output Normalizer (`compositor/output-normalizer.ts`)
- Normalizes disparate resolutions (e.g. 720p vs 1080p, 16:9 vs 9:16) via deterministic scaling policies (`fit_pad`, `crop_fill`, `stretch`).
- Enforces framerate conversion (e.g. 60fps $\to$ 30fps) with nearest-neighbor deterministic sampling (`fps=fps=N:round=near`), guaranteeing zero duration drift.
- Unifies pixel formats to target profile (default: `yuv420p`).

### 3.3 Timeline & Scene Assembler (`compositor/timeline-assembler.ts`)
- Stitches normalized scene segments sequentially according to canonical scene ordering.
- Supports transition overlap mathematics (`xfade` filter): when Scene A transitions into Scene B with a 15-frame crossfade, total duration strictly equals `(Dur(A) + Dur(B)) - Overlap`, matching `calculateCanonicalDuration(scenes)`.

### 3.4 Audio Subsystem Normalizer (`compositor/audio-normalizer.ts`)
- Preserves full **S28-R07** audio semantics:
  - Voiceover start delay, trim, volume, and mute.
  - Background music looping, base volume, and dynamic ducking during active voiceover windows.
  - Global SFX triggering and volume.
- Resamples all audio streams to standard profile (48,000 Hz, 2-channel stereo, AAC).
- Preserves AV sync: video frame $N$ aligns with canonical audio time at frame $N$.

### 3.5 QC Gate Integration (`compositor/qc-adapter.ts`)
- Post-composition inspection verifying file integrity, canonical duration parity ($\le 150\text{ ms}$ delta), resolution compliance, framerate conformity, and AV sync.
- Bridges directly into `scripts/gates/final_qc.py`.

---

## 4. Cancellation & Working Space Lifecycle

- Master Compositor accepts an optional `AbortSignal` in `CompositorContext`.
- All FFmpeg processes terminate immediately upon signal abort.
- An isolated temporary directory (`compositor_<id>_<timestamp>_<random>/`) is used for all intermediate processing.
- A strict `finally` block evicts the temporary directory completely on success, failure, or cancellation. Zero orphaned files remain on disk.
