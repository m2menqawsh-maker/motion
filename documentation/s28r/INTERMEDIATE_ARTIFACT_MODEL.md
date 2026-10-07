# Intermediate Artifact Model & Provenance

**Milestone**: S28-R11  
**Status**: ACTIVE / PRODUCTION READY  
**Component**: `contracts/compositor.ts` & `compositor/probe.ts`  

---

## 1. Architectural Philosophy

In multi-engine video architectures, intermediate render outputs (e.g., scene clips, vector sequences, rendered graphics overlays, audio stems) pass between rendering engines and compositing orchestrators.

Under S28-R11:
- An **Intermediate Artifact** is an explicit technical artifact model carrying verified provenance metadata.
- An intermediate artifact is **NOT** a copy of the `Canonical VideoDocument` (`BlueprintV2`). It contains only the technical metadata describing the rendered media, its producing engine, scope, and time range.
- An intermediate artifact has **NO canonical authority**. It cannot dictate timing, layer stacking, or style overrides back to the document.

---

## 2. Supported Input Types

```typescript
export const INTERMEDIATE_ARTIFACT_TYPES = [
  "video",            // Rendered MP4, WebM, MOV clip
  "sequence",         // Frame sequence in directory or pattern (e.g. frame_%06d.png)
  "image",            // Single static image (e.g. title card still, graphic)
  "audio",            // Standalone audio clip (MP3, WAV, AAC)
  "audio_stem",       // Specific audio role (voiceover, music stem, SFX)
  "overlay",          // Transparent graphic/video layer with alpha channel
  "scene_render",     // Intermediate rendered scene produced by Canvas or Remotion
] as const;
```

---

## 3. Intermediate Artifact Schema & Fields

```typescript
export interface IntermediateArtifact {
  readonly artifactId: string;             // Unique identifier (e.g. "art_scene_canvas_123")
  readonly sourceRendererId: string;       // Producing engine (e.g. "canvas-renderer-adapter", "remotion-engine-adapter")
  readonly canonicalRevision?: string | number; // Revision of the canonical document when rendered
  readonly scope: IntermediateArtifactScope;    // { type: "scene" | "project" | "layer" | "stem", id: string }
  readonly timeRange: {
    startFrame: number;
    durationFrames: number;
    startTimeSec?: number;
    durationSec?: number;
  };
  readonly type: IntermediateArtifactType;
  readonly filePath?: string;              // Absolute path to disk artifact
  readonly filePattern?: string;           // Image sequence pattern (e.g. "frame_%06d.png")
  readonly directoryPath?: string;         // Directory containing sequence
  readonly mediaInfo: IntermediateArtifactMediaInfo;
  readonly contentFingerprint?: string;    // Deterministic SHA-256 fingerprint
  readonly metadata?: Record<string, unknown>;
}
```

### 3.1 Explicit `mediaInfo` Technical Metadata
Every artifact carries explicit probed properties:
- `durationSec`: Duration in seconds.
- `durationFrames`: Frame count.
- `fps`: Explicit framerate (e.g. 30, 60, 24).
- `width`: Pixel width.
- `height`: Pixel height.
- `pixelFormat`: e.g. `yuv420p`, `rgba`, `yuva420p`.
- `timebase`: Rational timebase string (e.g. `1/30`, `1/60`).
- `startTimeSec`: Stream timestamp offset.
- `hasAlpha`: Explicit alpha channel support flag.
- `videoCodec`: e.g. `h264`, `png`, `vpx`.
- `audioCodec`: e.g. `aac`, `pcm_s16le`, `mp3`.
- `audioSampleRate`: e.g. `48000`, `44100`, `24000`.
- `audioChannels`: e.g. `2`, `1`.

---

## 4. Deterministic Content Fingerprinting

To detect stale cached artifacts or accidental mutations, each artifact generates a deterministic SHA-256 hash across its canonical parameters:

$$\text{Fingerprint} = \text{SHA256}(\text{SortKeys}(\{\text{renderer}, \text{scope}, \text{timeRange}, \text{mediaInfo}, \text{revision}\}))$$

Identical render parameters yield identical fingerprints. Any difference in resolution, duration, framerate, or source renderer changes the hash immediately.

---

## 5. Construction Factories

1. `createIntermediateArtifact(params)`: Engine-neutral constructor verifying schema validity and auto-computing fingerprint.
2. `createArtifactFromFile(params)`: Inspects disk files using `ffprobe` to derive `mediaInfo` automatically.
3. `createArtifactFromRenderResult(params)`: Wraps `RenderResult` produced by `CanvasRendererAdapter` or `RemotionRendererAdapter` into a fully qualified `IntermediateArtifact`.
