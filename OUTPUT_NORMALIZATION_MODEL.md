# Output Normalization Model

**Milestone**: S28-R11  
**Status**: ACTIVE / PRODUCTION READY  
**Component**: `contracts/compositor.ts` & `compositor/output-normalizer.ts`  

---

## 1. Normalization Purpose & Policy

When multiple rendering engines produce intermediate artifacts, those artifacts frequently exhibit differing technical profiles:
- **Resolution**: 1280x720 (Canvas draft), 1920x1080 (Remotion 1080p), 1080x1920 (9:16 mobile render).
- **Framerate**: 24 fps (cinematic B-roll), 30 fps (standard broadcast), 60 fps (fluid animation).
- **Pixel Formats**: `rgba` (canvas output with alpha), `yuv420p` (standard H.264), `yuva420p` (video overlay).
- **Audio Channels & Rates**: 22,050 Hz mono (legacy voiceover), 44,100 Hz stereo (music), 48,000 Hz (broadcast master).

The **Output Normalization Model** establishes deterministic policies ensuring that disparate intermediate artifacts conform strictly to a target `OutputProfile`.

---

## 2. Target `OutputProfile` Contract

```typescript
export interface OutputProfile {
  width: number;               // Default: 1920
  height: number;              // Default: 1080
  fps: number;                 // Default: 30
  aspectRatio?: string;        // "16:9", "9:16", "1:1", etc.
  videoCodec: string;          // Default: "libx264"
  pixelFormat: string;         // Default: "yuv420p"
  container: string;           // Default: "mp4"
  audioCodec: string;          // Default: "aac"
  sampleRate: number;          // Default: 48000
  channels: number;            // Default: 2
  channelLayout: string;       // Default: "stereo"
  videoBitrate: string;        // Default: "8M"
  audioBitrate: string;        // Default: "192k"
  scalingPolicy: "fit_pad" | "crop_fill" | "stretch"; // Default: "fit_pad"
  backgroundColor: string;     // Default: "black"
}
```

---

## 3. Video Normalization Pipeline

### 3.1 Scaling & Aspect Ratio Preservation
1. **`fit_pad` (Default)**: Scales the input artifact preserving its native aspect ratio so that it fits entirely within the target bounding box. Any letterbox or pillarbox areas are filled with `backgroundColor` (`black`). No geometric distortion or stretching occurs.
   ```text
   scale=w={tw}:h={th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black
   ```
2. **`crop_fill`**: Scales the artifact to completely cover the target box and crops excess pixels centered.
3. **`stretch`**: Forces non-uniform scaling to exact target dimensions.

### 3.2 Framerate & Timebase Normalization
- Inputs at arbitrary framerates (e.g. 60 fps or 24 fps) are resampled to target fps (e.g. 30 fps) using nearest-neighbor timestamp matching:
  ```text
  fps=fps={targetFps}:round=near
  ```
- Guaranteed **zero duration drift**: an artifact of duration $T$ seconds maintains exactly $T$ seconds of playback and $\text{round}(T \times \text{fps})$ discrete frames.

### 3.3 Color & Pixel Format Unification
- All incoming color spaces are converted to `yuv420p` (`format=yuv420p`), ensuring broad hardware decoder compatibility on web browsers, mobile devices, and desktop players.

---

## 4. Audio Normalization Pipeline

### 4.1 Sample Rate & Resampling
- All audio tracks are resampled to standard broadcast rate: `48,000 Hz` using FFmpeg's asynchronous resampler:
  ```text
  aresample=48000:async=1
  ```

### 4.2 Channel Layout Normalization
- Mono or multi-channel audio is mapped to standard 2-channel stereo:
  ```text
  pan=stereo|c0=c0|c1=c1
  ```

### 4.3 Lossless Intermediate Packaging
- Intermediate audio tracks are encoded as pristine PCM WAV (`pcm_s16le`) to avoid generational loss during mixing. Final packaging encodes to high-fidelity AAC at 192 kbps.

---

## 5. Fail-Closed Error Enforcement

The normalizer rejects non-conforming or corrupted assets:
- `INCOMPATIBLE_INPUT`: Missing required dimensions or framerate metadata.
- `UNSUPPORTED_FORMAT`: Input stream format unrecognizable by ffprobe.
- `NORMALIZATION_FAILED`: Filtergraph execution error during FFmpeg transcode.
- `AUDIO_SYNC_ERROR`: Output artifact duration deviates by $> 150\text{ ms}$ from canonical duration.
