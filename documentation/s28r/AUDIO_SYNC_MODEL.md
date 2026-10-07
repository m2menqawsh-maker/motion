# S28-R07: Audio Synchronization & Clock Governance Model

## 1. Single Authority & Timebase

The core architectural invariant of the audio preview subsystem is that **the canonical playhead is the sole temporal authority**. No independent audio clock, Web Audio timer, `setInterval`, or separate RAF loop is permitted to drive timeline progression.

```text
Canonical VideoDocument
       │ (fps, duration_frames)
       ▼
BrowserPreviewRuntime (Playhead Authority)
       ├── current_frame (0 .. duration_frames - 1)
       ├── fps (e.g. 30 fps)
       ├── playback_rate (e.g. 1.0x, 1.5x)
       └── is_playing (boolean)
       │
       ▼
AudioPreviewRuntime (Downstream Consumer)
       ├── AudioContext.currentTime (Hardware reference)
       └── WebAudio Source Nodes (Scheduled buffer playback)
```

### Timebase Mapping Equations
- **Timeline Frame to Seconds**:
  $$t_{\text{canonical}} = \frac{\text{frame}}{\text{fps}}$$
- **Track Local Offset (Seconds)**:
  $$\Delta t_{\text{track}} = \frac{\text{frame} - \text{startFrame}_{\text{track}}}{\text{fps}}$$
- **Active Track Condition**:
  $$\text{startFrame}_{\text{track}} \le \text{frame} < \text{startFrame}_{\text{track}} + \text{durationFrames}_{\text{track}}$$

---

## 2. Transport State Synchronization Mechanics

### 2.1 Play (`syncPlay`)
1. `BrowserPreviewRuntime.play()` sets `is_playing = true` and starts its RAF clock.
2. Invokes `AudioPreviewRuntime.syncPlay(currentFrame, playbackRate)`.
3. For each evaluated active track:
   - Computes local buffer offset: `offsetSeconds = (currentFrame - track.startFrame) / fps`.
   - Creates transient `AudioBufferSourceNode`.
   - Applies `playbackRate` to source node.
   - Connects source to track `GainNode`.
   - Calls `source.start(context.currentTime, offsetSeconds, remainingDuration)`.
4. Evaluates ducking immediately.

### 2.2 Pause (`syncPause`)
1. `BrowserPreviewRuntime.pause()` halts the RAF clock.
2. Invokes `AudioPreviewRuntime.syncPause(currentFrame)`.
3. Instantly calls `.stop(0)` on all active `AudioBufferSourceNode`s.
4. Disconnects and unlinks all source nodes to prevent memory leakage.
5. Audio and video rest at the identical logical frame: `no timeline drift`.

### 2.3 Seek (`syncSeek`)
1. `BrowserPreviewRuntime.seek(targetFrame)` bounds target frame to `[0, duration_frames - 1]`.
2. Stops all active playing audio buffer sources.
3. If preview is currently playing:
   - Immediately schedules fresh `AudioBufferSourceNode`s at the new offset `(targetFrame - track.startFrame) / fps`.
   - Re-evaluates ducking gains.
4. If preview is paused:
   - Retains silence at the target frame; no sources are scheduled.

### 2.4 Step Frame (`step(delta)`)
1. When paused, stepping +1 or -1 frame executes as a synchronous seek to `current_frame + delta`.
2. Audio remains halted; logical alignment between playhead and audio graph is preserved exactly.

### 2.5 Playback Rate (`syncPlaybackRate`)
1. Changing rate via `BrowserPreviewRuntime.setPlaybackRate(rate)` updates canonical rate.
2. `AudioPreviewRuntime.syncPlaybackRate(rate)` iterates all active source nodes and calls:
   ```typescript
   source.playbackRate.setValueAtTime(rate, context.currentTime);
   ```
3. Web Audio hardware pitch/time scaling remains synchronized with the visual RAF loop.

---

## 3. Drift Detection & Resynchronization Policy

Web Audio hardware clocks (`AudioContext.currentTime`) and browser visual animation frames (`requestAnimationFrame`) can experience minor phase variations due to CPU scheduling or frame drops.

```text
               Expected Audio Time (frame / fps)
                             │
                             ▼
              |─────────── Drift ───────────|
                             ▲
                             │
               Actual Audio Elapsed Time (context.currentTime - startTime)
```

### Policy Rules:
1. **Micro-Drift (< 40ms, ~1.2 frames at 30fps)**:
   - Tolerated transparently without intervention.
   - Prevents micro-stutters and audio crackling from excessive re-seeking.
2. **Macro-Drift (≥ 40ms)**:
   - Triggered when visual frame clock falls behind or runs ahead of audio buffer.
   - Resynchronizes by restarting active track buffer sources at `(currentFrame - track.startFrame) / fps`.
   - Records an internal resync metric event.

---

## 4. Multi-Track Mixing & Dynamic Ducking

### 4.1 Track Isolation & Mixing Graph
- Each track (`voiceover`, `music`, `global_sfx[i]`, `scene.layer[j]`) routes through an isolated track `GainNode`.
- All track GainNodes connect to `masterGainNode` which connects to `context.destination`.
- Multiple simultaneous SFX clips mix additively without clipping master gain if normalized.

### 4.2 Dynamic Voiceover Ducking
- When `voiceover` is active (`startFrame <= frame < startFrame + durationFrames`):
  - Music gain automatically transitions to `ducking_volume` (default: 0.05).
- When `voiceover` is inactive:
  - Music gain returns to configured `base_volume`.
- Evaluated both dynamically on frame transitions and immediately upon seek.
