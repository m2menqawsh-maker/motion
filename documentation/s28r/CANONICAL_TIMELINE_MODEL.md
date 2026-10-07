# Canonical Timeline Specification: Single Video Authority & Temporal Hierarchy

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R03  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Modules**: `contracts/timeline.ts`, `contracts/layers.ts`, `contracts/normalization.ts`  
**Audited Baseline SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Date**: 2026-10-06  

---

## 1. Executive Summary & Core Invariant

The central mandate of **S28-R03** is to provide the video platform with a **pure, engine-neutral temporal and layer editing language**, usable identically across:
- Browser Live Editor & Preview Runtime (S28-R04 through S28-R06)
- AI Autonomous Director & Story Planner
- Headless Render Engines (Remotion, FFmpeg, Canvas/WebCodecs)

### The Cardinal Rule: ZERO Duplicate Truth
Under no circumstances does S28-R03 establish a secondary persistent authority.
```text
FORBIDDEN: BlueprintV2 truth + Independent TimelineDocument truth
FORBIDDEN: Persistent Scene truth + Independently persisted Tracks truth
```

The platform maintains **ONE CANONICAL VIDEO AUTHORITY**:
- **Persistent Authority**: `BlueprintV2` (evolved additively in `contracts/blueprint.ts` and `contracts/canonical-video.ts`).
- **Normalized Derived State**: `NormalizedVideo.timeline` (`CanonicalTimeline` assembled deterministically in `contracts/normalization.ts`).
- **Compatibility Layers**: `remotion-app/src/merge.ts` and `contracts/render-input.ts` projection wrappers.

---

## 2. Temporal & Editorial Vocabulary

| Term | Scope | Definition | Persistent or Derived? |
| :--- | :--- | :--- | :--- |
| **Timeline** | Global Video | The complete temporal axis of the video. Governs total duration, timebase (`fps`), tracks, and transition sequencing. | **Derived View** (`CanonicalTimeline`) |
| **Scene** | Narrative Container | Semantic, narrative, or template-driven block of the video. Owns an editorial time range, semantic template, surface properties, and canonical layers. | **Persistent Authority** (`BlueprintScene`) |
| **Track** | Global / Layer Group | A logical lane of non-colliding clips or layers organized by purpose (e.g. `video`, `audio`, `text`, `overlay`, `caption`). | **Derived View** (`CanonicalTrack`) |
| **Clip** | Track Element | A bounded segment of time placed on a track, referencing either a scene, media source, or layer collection. | **Derived View** (`CanonicalClip`) |
| **Layer** | Spatial Element | A discrete visual or audible item evaluated at any discrete frame (text, image, video, shape, audio, group). | **Authoritative/Synthesized** (`CanonicalLayer`) |
| **Group** | Hierarchical Node | A logical container for layers that applies hierarchical transform, opacity, and timing composition without DOM/React tree. | **Canonical Layer** (`GroupLayer`) |

---

## 3. Structural Relationship & Data Flow

```mermaid
flowchart TD
    subgraph Persistent Authority [contracts/canonical-video.ts]
        BP[BlueprintV2]
        Scenes[BlueprintScene[]]
        AudioPlan[AudioPlan]
        BP --> Scenes
        BP --> AudioPlan
        Scenes -.->|Optional explicit| SceneLayers[CanonicalLayer[]]
    end

    subgraph Pure Normalizer [contracts/normalization.ts]
        Normalizer[normalizeCanonicalVideo]
        LayerSynth[Layer Synthesizer: Template/Surface -> CanonicalLayer]
        TimelineBuilder[buildCanonicalTimeline]
    end

    subgraph Normalized In-Memory State [contracts/normalization.ts]
        NormVid[NormalizedVideo]
        NormTimeline[CanonicalTimeline]
        Tracks[CanonicalTrack[]: video, audio, overlay]
        Clips[CanonicalClip[]]
        ResolvedLayers[CanonicalLayer[]: sorted & validated]
        NormVid --> NormTimeline
        NormTimeline --> Tracks
        Tracks --> Clips
        NormVid --> ResolvedLayers
    end

    subgraph Deterministic Evaluator [contracts/evaluator.ts]
        FrameEval[evaluateVideoAtFrame / evaluateTimelineAtFrame]
        FrameState[(EvaluatedFrameState: active layers, transforms, opacities)]
    end

    BP --> Normalizer
    Normalizer --> LayerSynth
    LayerSynth --> ResolvedLayers
    Normalizer --> TimelineBuilder
    TimelineBuilder --> NormTimeline
    NormVid --> FrameEval
    FrameEval --> FrameState
```

---

## 4. Scene vs Timeline Boundaries

A fundamental architectural question for the video platform is: **What is the exact relationship between Scenes and the Timeline?**

### 4.1 Is Scene a Container?
**YES.** A `Scene` is a semantic narrative unit. In AI story generation, prompts and screenplays reason in terms of scenes ("Intro", "Problem", "Feature Showcase", "Call to Action"). A Scene defines:
- A logical time window: `startFrame` and `durationFrames`.
- Editorial content: template reference, style surface, or explicit canonical layers.
- Transition out: declarative transition to the next scene.

### 4.2 Can Tracks Span Across Scenes?
**YES.** In the derived `CanonicalTimeline`:
- **Visual Tracks**: Divided into clips matching each scene's time range (`clip_sc_{scene_id}`).
- **Audio Tracks**: Span across scene boundaries. A continuous voiceover track or background music bed (`AudioPlan`) is projected into audio tracks that run uninterrupted across multiple scene clips.
- **Overlay Tracks**: Future persistent overlays (subtitles, lower thirds, persistent watermarks) project as clips spanning multiple scenes.

### 4.3 Can Layers Belong to a Scene?
**YES.** A scene can either:
1. Define explicit `layers?: CanonicalLayer[]` (e.g. authored directly in an editor or generated by advanced AI).
2. Omit `layers` and specify a template and style surface (legacy/template mode). In this case, `contracts/normalization.ts` deterministically synthesizes standard canonical layers (`TextLayer`, `ImageLayer`, `ShapeLayer`) for the scene.

---

## 5. Stable Identifiers (No Index-Based Authority)

Every editable entity in the canonical model carries an engine-neutral, persistent, unique identifier conforming to `/^[a-zA-Z0-9_\-]+$/`:

- `scene_id`: Unique identifier for each scene (e.g. `sc_intro_01`).
- `track_id`: Unique identifier for each timeline track (e.g. `track_main_video`, `track_voiceover`).
- `clip_id`: Unique identifier for each timeline clip (e.g. `clip_sc_intro_01`).
- `layer_id`: Unique identifier for each visual/audio layer (e.g. `layer_sc_intro_title`).
- `keyframe_id`: Unique identifier for each keyframe (e.g. `kf_title_fade_01`).
- `transition_id`: Unique identifier for each scene transition (e.g. `trans_intro_showcase`).
- `channel_id`: Unique identifier for each animation channel (e.g. `ch_title_x`).

**Fail-Closed Invariant**: Array indices are NEVER used as editing identities. Commits or updates referencing index numbers are strictly rejected by the validator.
