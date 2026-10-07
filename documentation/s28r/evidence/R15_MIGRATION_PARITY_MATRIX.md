# S28-R15 Evidence: Migration & Parity Matrix

**Milestone**: S28-R15 Verification, Fault Destruction, Fencing, Load & Soak  
**Date**: October 7, 2026  

---

## 1. Document Schema Migration Matrix

| Input Format | Adapter Function | Canonical Output | Parity Status | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **Legacy Blueprint V1** (`version: "1.0"`) | `migrateBlueprintToV2()` | `BlueprintV2` (`blueprint_version: "2.0.0"`) | **100% Deterministic** | [`R15-TS-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L250), [`R15-LEGACY-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_part3_final_campaigns.test.ts#L100) |
| **Malformed Blueprint V1** (missing scenes, bad types) | `migrateBlueprintToV2()` | Fail-Closed Error | **Rejected Fail-Closed** | [`R15-TS-02`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L295) |
| **Canonical Blueprint V2** (`2.0.0`) | Direct Validation | `BlueprintV2` | **Pass-Through Preserved** | [`R15-AG-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/architecture/test_s28_r15_architecture_guards.test.ts#L30) |

---

## 2. Rendering Engine Parity Matrix

| Scene Kind | Primary Engine | Fallback / Alternative Engine | Parity Attribute | Measured Result |
| :--- | :--- | :--- | :--- | :--- |
| **Typography / Text Scene** | `remotion` (RemotionAdapter) | `canvas` (CanvasRendererAdapter) | Duration frames & dimensions | Exact 1:1 frame count (0 drift) |
| **Shape / Vector Scene** | `canvas` (CanvasRendererAdapter) | `remotion` (RemotionAdapter) | Color, opacity, transform | Exact visual parity |
| **Headless Non-Remotion Export** | `canvas` + `ffmpeg` | Standalone CLI | Audio/Video multiplexing | Valid standalone MP4 (h264/aac) |
| **Master Compositor Normalization** | `MasterCompositor` | N/A (Engine-neutral authority) | 48kHz audio, timebase, resolution | Exact canonical timeline compliance |

---

## 3. Aspect Ratio Matrix (Campaign R15-C26)

| Target Profile | Resolution | Framerate | Audio Sample Rate | Geometry Distortion | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Landscape (16:9)** | 1920x1080 | 30.0 fps | 48,000 Hz | Zero distortion (1.0 aspect) | **PASS** ([`R15-AR-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L1215)) |
| **Portrait / Vertical (9:16)** | 1080x1920 | 30.0 fps | 48,000 Hz | Zero distortion (1.0 aspect) | **PASS** ([`R15-AR-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L1215)) |
| **Square (1:1)** | 1080x1080 | 30.0 fps | 48,000 Hz | Zero distortion (1.0 aspect) | **PASS** ([`R15-AR-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L1215)) |

---

## 4. Audio & Caption Integrity (Campaign R15-C27)

- **Voiceover Normalization**: -16 LUFS target.
- **SFX / BGM Normalization**: -24 LUFS target.
- **AV Sync Drift**: Measured drift = 0.0 ms across multi-track audio assembly (< 150 ms tolerance threshold).
- **Caption Word Alignments**: Strictly bounded within canonical scene duration `[0, durationFrames]`.
