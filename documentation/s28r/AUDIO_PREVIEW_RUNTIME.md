# S28-R07: Audio Preview Runtime Specification

## 1. Architectural Overview

The **Audio Preview Runtime** (`preview/audio/audio-preview-runtime.ts`) provides engine-independent, real-time auditory playback synchronized with the **Canonical VideoDocument** and the **Browser Live Preview Runtime** (`preview/preview-runtime.ts`).

```text
Canonical VideoDocument (BlueprintV2 / NormalizedVideo)
                          │
                          ▼
            evaluateVideoAtFrame()
           (contracts/evaluator.ts)
                          │
                          ▼
              BrowserPreviewRuntime
             (preview/preview-runtime.ts)
                    [Playhead Authority]
                          │
                          ▼
             AudioPreviewRuntime
         (preview/audio/audio-preview-runtime.ts)
                          │
                          ▼
                Web Audio API Boundary
          (preview/audio/web-audio-adapter.ts)
```

### Core Invariants:
1. **Single Playhead Authority**: The Audio Preview Runtime has **no independent clock**, no `setInterval`, and no `requestAnimationFrame`. All playback advancement, seeking, pausing, and stepping are driven strictly by the canonical playhead in `BrowserPreviewRuntime`.
2. **Canonical Contracts Decoupled from Web Audio**: All data contracts (`contracts/blueprint.ts`, `contracts/evaluator.ts`, `contracts/waveform.ts`) contain **zero references** to `AudioContext`, `GainNode`, or Web Audio globals.
3. **Engine Neutrality**: Zero imports from React or Remotion across the entire audio preview subsystem.
4. **Deterministic Multi-Track Mixing**: Direct graph mixing for voiceover, background music, sound effects (SFX), and scene-level audio layers.

---

## 2. Audio Graph Architecture

```text
[Track: Voiceover] ──────► [GainNode (VO)] ────────┐
                                                   │
[Track: Music]     ──────► [GainNode (Music)] ─────┼──► [Master GainNode] ──► [Destination]
                                (Ducked by VO)     │
[Track: SFX 0..N]  ──────► [GainNode (SFX)] ───────┤
                                                   │
[Track: Scene Audio] ────► [GainNode (Layer)] ─────┘
```

### Node Lifecycle:
- **Master Gain**: Connects directly to `context.destination`. Governs global preview volume and master mute.
- **Track GainNode**: Dedicated per canonical track (`audio_voiceover`, `audio_music`, `audio_sfx_N`, layer IDs). Updates gain smoothly via `setValueAtTime()` without destroying or restarting sources.
- **AudioBufferSourceNode**: Transient buffer player instantiated when a track is active during playback or seek. Instantly stopped and unlinked on pause or seek.

---

## 3. Supported Audio Tracks & Mixing

| Track Kind | Canonical Source | Properties Governed | Runtime Behavior |
| :--- | :--- | :--- | :--- |
| **`voiceover`** | `blueprint.audio.voiceover` | `asset_ref`, `startFrame`, `durationFrames`, `volume`, `mute` | Starts at `startFrame`, drives dynamic ducking on active playback. |
| **`music`** | `blueprint.audio.music` | `asset_ref`, `startFrame`, `durationFrames`, `volume`, `loop`, `mute`, `ducking` | Plays with optional loop; ducks to `ducking_volume` whenever voiceover is active. |
| **`global_sfx`** | `blueprint.audio.global_sfx[]` | `asset_ref`, `startFrame`, `durationFrames`, `volume`, `mute` | Multiple simultaneous overlapping sound effect clips. |
| **`layer`** | `scene.layers[kind="audio"]` | `asset_ref`, `time_range`, `volume`, `muted` | Scene-scoped audio layers aligned with scene timing. |

---

## 4. Mutation & Partial Update Integration

Mutations emitted by R04 or the `EditorSession` integrate through the canonical `ChangeSet` invalidation contract:

```text
Mutation (SET_AUDIO_LEVEL / UPDATE_AUDIO)
  │
  ▼
ChangeSet
  ├── requires_audio_remix: true
  └── requires_timeline_rebuild: false
  │
  ▼
BrowserPreviewRuntime.updateDocument()
  │
  ▼
AudioPreviewRuntime.applyPartialVolumeMuteUpdates()
  │
  ▼
Track GainNode.gain.setValueAtTime()
(Source nodes continue playing uninterrupted!)
```

- **Partial Updates (`requires_timeline_rebuild: false`)**:
  - `SET_AUDIO_LEVEL`: Updates volume or mute on individual tracks.
  - `UPDATE_AUDIO` (volume/mute only): Updates GainNodes in-place.
  - Zero audible glitches; audio sources continue playing seamlessly.
- **Full Rebuild (`requires_timeline_rebuild: true`)**:
  - Track timing changes (`startFrame`, `durationFrames`) or asset reference changes.
  - Safely stops current sources, re-computes active tracks, and reschedules buffer offsets.

---

## 5. Fail-Closed Error Handling & Diagnostics

The runtime emits structured `AudioDiagnosticError` instances with explicit codes:

| Error Code | Trigger Condition | Fail-Closed Behavior |
| :--- | :--- | :--- |
| **`MISSING_ASSET`** | Asset ref not found in cache or resolver returned null. | Throws in `failClosedOnMissingAsset: true`; logs structured diagnostic. |
| **`DECODE_FAILURE`** | Corrupted audio data or invalid header stream. | Rejects buffer decoding promise and records diagnostic event. |
| **`AUDIO_CONTEXT_UNAVAILABLE`** | Web Audio API not supported in host environment. | Throws explicit diagnostic error with root cause details. |
| **`INVALID_AUDIO_TIMING`** | Negative duration or invalid frame range. | Rejects track scheduling and records diagnostic error. |
