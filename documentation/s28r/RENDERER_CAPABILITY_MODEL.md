# Renderer Capability Model Specification (S28-R08)

## 1. Overview

The Renderer Capability Model provides a fine-grained, deterministic taxonomy of platform rendering features. It enables rendering adapters to declare what features they natively support and allows the system to derive exact technical requirements from any `BlueprintV2` document.

---

## 2. Canonical Capability Taxonomy

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      Renderer Capability Taxonomy                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ Core Visual Primitives         │ text, image, video, shapes, groups   │
├────────────────────────────────┼───────────────────────────────────────┤
│ Temporal & Motion              │ keyframes, transitions, alpha         │
├────────────────────────────────┼───────────────────────────────────────┤
│ Advanced Graphics / Hardware   │ webgl, 3d, particles, map,            │
│ Acceleration                   │ custom_shaders                        │
├────────────────────────────────┼───────────────────────────────────────┤
│ Audio Subsystem (R07)          │ audio, audio_voiceover, audio_music,  │
│                                │ audio_sfx, audio_mixing,              │
│                                │ audio_ducking, audio_timing           │
├────────────────────────────────┼───────────────────────────────────────┤
│ Pipeline Execution Modes       │ frame_rendering, sequence_rendering,  │
│                                │ export_video, live_preview            │
└────────────────────────────────┴───────────────────────────────────────┘
```

### 2.1 Capability Catalog Details

| Capability | Category | Semantics & Triggers |
| :--- | :--- | :--- |
| `text` | Visual Primitive | Rendering formatted text nodes, fonts, and typography. |
| `image` | Visual Primitive | Static bitmap decoding, aspect ratio preservation, object-fit. |
| `video` | Visual Primitive | Frame-accurate embedded video clip decoding and synchronization. |
| `shapes` | Visual Primitive | Geometric shapes (rectangles, circles, pills, borders, shadows). |
| `groups` | Visual Primitive | Layer hierarchy, nested coordinates, and container transforms. |
| `keyframes` | Temporal | Interpolating animated channels (bezier, spring, linear, hold). |
| `transitions` | Temporal | Cross-scene transitions and visual blends. |
| `alpha` | Temporal | Transparency, RGBA blending, layer opacity < 1.0. |
| `webgl` | Advanced Hardware | WebGL rendering context required for hardware shaders / 3D. |
| `3d` | Advanced Hardware | Perspective camera, 3D meshes, lighting, transformations. |
| `particles` | Advanced Hardware | Physics particle spawners, emitter lifecycles, velocities. |
| `map` | Advanced Hardware | Geospatial vector tile rendering, projection, map animations. |
| `custom_shaders` | Advanced Hardware | GLSL fragment/vertex shaders (e.g. ripple, crosswarp, film-burn). |
| `audio` | Audio | General audio decoding and playback capability. |
| `audio_voiceover` | Audio | Spoken audio timing, speech segment alignment. |
| `audio_music` | Audio | Background music playback and looping. |
| `audio_sfx` | Audio | Spot sound effects with exact start offsets. |
| `audio_mixing` | Audio | Concurrent multi-track audio bus mixing. |
| `audio_ducking` | Audio | Dynamic volume attenuation of music when voiceover is active. |
| `audio_timing` | Audio | Frame-accurate sample synchronization and seeking. |
| `frame_rendering` | Execution Mode | Rendering a single isolated frame into an image buffer. |
| `sequence_rendering`| Execution Mode | Batch rendering an interval of consecutive frames. |
| `export_video` | Execution Mode | Headless multiplexed video container export (MP4, WebM). |
| `live_preview` | Execution Mode | Low-latency interactive rendering for browser playhead. |

---

## 3. R05 Template Classification & Engine-Backed Mapping

The capability derivation engine (`deriveRequiredCapabilities`) inspects scene templates and cross-references `TemplateSpec` definitions from `registry/semantic-registry.ts`:

| Template / Entity | Template Classification | Derived Capabilities |
| :--- | :--- | :--- |
| `rui-title-card` | `NATIVE` | `text`, `shapes` |
| `rui-quote-card` | `NATIVE` | `text`, `shapes`, `alpha` |
| `rui-media-frame` | `NATIVE` | `image`, `shapes`, `groups` |
| `rui-map-flight` | `ENGINE_BACKED` | `map`, `webgl` |
| `scene3d-element` | `ENGINE_BACKED` | `3d`, `webgl` |
| `particlesystem-element` | `ENGINE_BACKED` | `particles` |
| GL Transitions (`ripple`, `clock-wipe`, `crosswarp`, etc.) | `HYBRID` | `transitions`, `custom_shaders`, `webgl` |

---

## 4. R07 Audio Subsystem Integration

Audio capability derivation extracts requirements directly from `doc.audio`:
1. `doc.audio.voiceover` present $\implies$ `audio`, `audio_voiceover`, `audio_timing`.
2. `doc.audio.music` present $\implies$ `audio`, `audio_music`, `audio_timing`.
3. `doc.audio.global_sfx` present $\implies$ `audio`, `audio_sfx`, `audio_timing`.
4. `doc.audio.music.ducking.enabled !== false` $\implies$ `audio_ducking`, `audio_mixing`.
5. Number of concurrent audio streams $\ge 2$ $\implies$ `audio_mixing`.

---

## 5. Alias Normalization Table

The system transparently normalizes common developer aliases into canonical capability keys:

```typescript
CAPABILITY_ALIASES:
  "custom shaders"   -> "custom_shaders"
  "shaders"          -> "custom_shaders"
  "audio mixing"     -> "audio_mixing"
  "mixing"           -> "audio_mixing"
  "audio ducking"    -> "audio_ducking"
  "ducking"          -> "audio_ducking"
  "audio timing"     -> "audio_timing"
  "timing"           -> "audio_timing"
  "maplibre-gl"      -> "map"
  "three.js"         -> "3d"
  "three"            -> "3d"
  "remotion-bits"    -> "particles"
```
