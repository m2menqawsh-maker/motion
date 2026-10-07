# Renderer Capability Model Specification (S28-R10)

**Status**: Verified Reality Specification  
**Governing Authority**: `contracts/renderer.ts` (`CANONICAL_CAPABILITIES`, `deriveRequiredCapabilities`)  

---

## 1. Executive Summary

Milestone **S28-R10** formalizes the system-wide Renderer Capability Model. The model prevents hardcoded engine dependencies and guarantees deterministic engine dispatch across heterogeneous rendering runtimes.

Rendering requests declare or dynamically derive a required capability set. `RendererRegistry` matches these requirements against the declared capabilities of all registered adapters using strict fail-closed logic.

---

## 2. Capability Taxonomy

The canonical taxonomy is partitioned into five distinct operational domains:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL CAPABILITIES                          │
├─────────────────┬─────────────────┬──────────────────┬─────────────────┤
│ Core Visual     │ Temporal/Motion │ Advanced Graphic │ Audio Subsystem │
├─────────────────┼─────────────────┼──────────────────┼─────────────────┤
│ text            │ keyframes       │ map              │ audio           │
│ image           │ transitions     │ 3d               │ audio_voiceover │
│ video           │ alpha           │ particles        │ audio_music     │
│ shapes          │                 │ custom_shaders   │ audio_sfx       │
│ groups          │                 │ webgl            │ audio_mixing    │
│                 │                 │                  │ audio_ducking   │
│                 │                 │                  │ audio_timing    │
├─────────────────┴─────────────────┴──────────────────┴─────────────────┤
│ Execution Pipeline Modes: frame_rendering | sequence_rendering | export_video | live_preview │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Concrete Engine Capability Matrix

| Capability Identifier | Domain | `CanvasRendererAdapter` (S28-R10) | `RemotionRendererAdapter` (S28-R09) | `BrowserPreviewAdapter` (S28-R08) |
| :--- | :--- | :---: | :---: | :---: |
| `text` | Core Visual | **YES** | **YES** | **YES** |
| `image` | Core Visual | **YES** | **YES** | **YES** |
| `shapes` | Core Visual | **YES** | **YES** | **YES** |
| `groups` | Core Visual | **YES** | **YES** | **YES** |
| `video` | Core Visual | **NO** (Rejected) | **YES** | **NO** |
| `keyframes` | Temporal | **YES** | **YES** | **YES** |
| `transitions` | Temporal | **YES** | **YES** | **NO** |
| `alpha` | Temporal | **YES** | **YES** | **YES** |
| `frame_rendering` | Execution Target | **YES** | **YES** | **YES** |
| `sequence_rendering` | Execution Target | **YES** | **YES** | **NO** (Rejected) |
| `export_video` | Execution Target | **YES** (MP4) | **YES** (MP4/WebM) | **NO** (Rejected) |
| `live_preview` | Execution Target | **NO** | **NO** | **YES** |
| `audio` | Audio | **NO** | **YES** | **YES** |
| `audio_voiceover` | Audio | **NO** | **YES** | **YES** |
| `audio_music` | Audio | **NO** | **YES** | **YES** |
| `audio_ducking` | Audio | **NO** (Rejected) | **YES** | **NO** |
| `audio_mixing` | Audio | **NO** (Rejected) | **YES** | **NO** |
| `audio_timing` | Audio | **NO** | **YES** | **YES** |
| `map` | Advanced Graphics | **NO** (Fail-Closed) | **NO** (Fail-Closed) | **NO** (Fail-Closed) |
| `3d` | Advanced Graphics | **NO** (Fail-Closed) | **NO** (Fail-Closed) | **NO** (Fail-Closed) |
| `particles` | Advanced Graphics | **NO** (Fail-Closed) | **NO** (Fail-Closed) | **NO** (Fail-Closed) |
| `custom_shaders` | Advanced Graphics | **NO** (Fail-Closed) | **NO** (Fail-Closed) | **NO** (Fail-Closed) |
| `webgl` | Advanced Graphics | **NO** (Fail-Closed) | **NO** (Fail-Closed) | **NO** (Fail-Closed) |

---

## 4. Automatic Derivation Engine (`deriveRequiredCapabilities`)

When a `RenderRequest` does not specify explicit capabilities, `deriveRequiredCapabilities(document, type)` derives the exact minimal set:

1. **Pipeline Mode**: Adds `frame_rendering`, `sequence_rendering`, or `export_video`.
2. **Scenes & Layer Inspection**:
   - `text` layer -> requires `text`
   - `image` layer -> requires `image`
   - `video` layer -> requires `video`
   - `shape` layer / `scene.surface` -> requires `shapes`
   - `group` layer / `parent_id` -> requires `groups`
   - channels with keyframes -> requires `keyframes`
   - layer opacity $< 1.0$ -> requires `alpha`
   - scene transition -> requires `transitions` (if GL shader transition, adds `custom_shaders` and `webgl`)
3. **TemplateSpec Requirements**:
   - `rui-map-flight` -> requires `map`, `webgl`
   - `scene3d-element` -> requires `3d`, `webgl`
   - `particlesystem-element` -> requires `particles`
4. **Audio Subsystem Requirements**:
   - `voiceover` present -> requires `audio`, `audio_voiceover`, `audio_timing`
   - `music` present -> requires `audio`, `audio_music`, `audio_timing`
   - `music.ducking.enabled` -> requires `audio_ducking`, `audio_mixing`
   - Multiple audio streams $\ge 2$ -> requires `audio_mixing`

---

## 5. Multi-Renderer Deterministic Dispatch Rules

Selection operates through `CANONICAL_RENDERER_REGISTRY.selectRenderer(request)`:

1. **Compatibility Gate**:
   Each registered adapter evaluates `adapter.canRender(request)`. If `missingCapabilities.length > 0`, the adapter is eliminated.
2. **Deterministic Tie-Breaking**:
   - **Priority Descending**:
     - `CanvasRendererAdapter`: `110` (Preferred for lightweight 2D frame and sequence captures)
     - `RemotionRendererAdapter`: `100` (Production standard for full video and complex DOM)
     - `BrowserPreviewAdapter`: `50` (Preview interactive adapter)
   - **Supported Capability Count Descending**: Favor engines with wider capability sets when priorities match.
   - **Renderer ID Lexicographical Ascending**: Deterministic tie-breaker for identical priorities and capability counts.
3. **Fail-Closed Resolution**:
   If no adapter satisfies all requirements, throws `NoCompatibleRendererError` (`NO_COMPATIBLE_RENDERER`).
