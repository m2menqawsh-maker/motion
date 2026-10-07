/**
 * contracts/evaluator.ts — Pure Framework-Neutral Deterministic Frame Evaluator.
 * S28-R03: Evaluates canonical videos, timelines, layers, keyframes, and audio states at any discrete frame.
 * ZERO React, Remotion, Canvas, DOM or wall-clock dependencies.
 */
import {
  type CanonicalTimeline,
  type CanonicalTrack,
  frameToMs,
} from "./timeline";
import {
  type CanonicalLayer,
  type Transform,
  composeTransform,
  sortLayersByZIndex,
} from "./layers";
import {
  evaluateChannelAtFrame,
  type ChannelTarget,
} from "./keyframes";
import type { BlueprintV2, BlueprintScene } from "./blueprint";
import type { NormalizedVideo, NormalizedScene } from "./normalization";

// ────────────────────────────────────────────────────────────────────────────
// 1. Evaluated Frame State Types
// ────────────────────────────────────────────────────────────────────────────

export interface EvaluatedTransform {
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  rotation: number;
  opacity: number;
}

export interface EvaluatedLayerState {
  layer_id: string;
  kind: string;
  visible: boolean;
  localFrame: number;
  transform: EvaluatedTransform;
  opacity: number;
  properties: Record<string, any>;
  scene_id?: string;
  parent_id?: string;
}

export interface EvaluatedAudioTrackState {
  track_id: string;
  volume: number;
  base_volume?: number;
  muted: boolean;
  active: boolean;
  asset_ref?: string;
  kind?: "voiceover" | "music" | "sfx" | "layer";
  startFrame?: number;
  durationFrames?: number;
  localFrame?: number;
}

export interface EvaluatedAudioState {
  tracks: EvaluatedAudioTrackState[];
}

export interface EvaluatedFrameState {
  frame: number;
  fps: number;
  timeMs: number;
  active_scenes: string[];
  layers: EvaluatedLayerState[];
  audio: EvaluatedAudioState;
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Layer Evaluation Mathematics
// ────────────────────────────────────────────────────────────────────────────

function evaluateLayerTransform(
  layer: CanonicalLayer,
  localFrame: number,
  fps: number
): EvaluatedTransform {
  let x = layer.transform.position.x;
  let y = layer.transform.position.y;
  let scaleX = layer.transform.scale.x;
  let scaleY = layer.transform.scale.y;
  let rotation = layer.transform.rotation;
  let opacity = layer.opacity * layer.transform.opacity;

  if (layer.channels && layer.channels.length > 0) {
    for (const ch of layer.channels) {
      if (ch.keyframes.length === 0) continue;
      const val = evaluateChannelAtFrame(ch, localFrame, fps);

      switch (ch.target) {
        case "TRANSFORM_X":
          x = val;
          break;
        case "TRANSFORM_Y":
          y = val;
          break;
        case "SCALE":
          scaleX = val;
          scaleY = val;
          break;
        case "SCALE_X":
          scaleX = val;
          break;
        case "SCALE_Y":
          scaleY = val;
          break;
        case "ROTATION":
          rotation = val;
          break;
        case "OPACITY":
          opacity = Math.max(0, Math.min(1, opacity * val));
          break;
      }
    }
  }

  return { x, y, scaleX, scaleY, rotation, opacity };
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Frame Evaluator Implementations
// ────────────────────────────────────────────────────────────────────────────

export function evaluateTimelineAtFrame(
  timeline: CanonicalTimeline,
  layers: CanonicalLayer[],
  frame: number
): EvaluatedFrameState {
  const fps = timeline.fps;
  const timeMs = frameToMs(frame, fps);

  const sortedLayers = sortLayersByZIndex(layers);
  const layerMap = new Map<string, CanonicalLayer>();
  for (const l of sortedLayers) layerMap.set(l.layer_id, l);

  const evaluatedMap = new Map<string, EvaluatedLayerState>();

  function resolveEvaluated(layer: CanonicalLayer): EvaluatedLayerState | null {
    if (evaluatedMap.has(layer.layer_id)) {
      return evaluatedMap.get(layer.layer_id)!;
    }

    const { startFrame, endFrame } = layer.time_range;
    const isWithinTime = frame >= startFrame && frame < endFrame;
    const localFrame = frame - startFrame;

    let evalTransform = evaluateLayerTransform(layer, localFrame, fps);

    // Parent composition
    if (layer.parent_id && layerMap.has(layer.parent_id)) {
      const parentLayer = layerMap.get(layer.parent_id)!;
      const evaluatedParent = resolveEvaluated(parentLayer);
      if (evaluatedParent) {
        const parentT: Transform = {
          position: { x: evaluatedParent.transform.x, y: evaluatedParent.transform.y },
          scale: { x: evaluatedParent.transform.scaleX, y: evaluatedParent.transform.scaleY },
          rotation: evaluatedParent.transform.rotation,
          anchor: { x: 0.5, y: 0.5 },
          opacity: evaluatedParent.transform.opacity,
        };
        const childT: Transform = {
          position: { x: evalTransform.x, y: evalTransform.y },
          scale: { x: evalTransform.scaleX, y: evalTransform.scaleY },
          rotation: evalTransform.rotation,
          anchor: { x: 0.5, y: 0.5 },
          opacity: evalTransform.opacity,
        };
        const composed = composeTransform(parentT, childT);
        evalTransform = {
          x: composed.position.x,
          y: composed.position.y,
          scaleX: composed.scale.x,
          scaleY: composed.scale.y,
          rotation: composed.rotation,
          opacity: composed.opacity,
        };
      }
    }

    const properties: Record<string, any> = {};
    if (layer.kind === "text") {
      properties.text = layer.text;
      properties.typography = layer.typography;
    } else if (layer.kind === "image" || layer.kind === "video") {
      properties.asset_ref = layer.asset_ref;
      properties.fit = layer.fit;
      if ((layer as any).crop) properties.crop = (layer as any).crop;
    } else if (layer.kind === "shape") {
      properties.shape_type = layer.shape_type;
      properties.size = layer.size;
      if (layer.fillColor !== undefined) properties.fillColor = layer.fillColor;
      if (layer.strokeColor !== undefined) properties.strokeColor = layer.strokeColor;
      if (layer.strokeWidth !== undefined) properties.strokeWidth = layer.strokeWidth;
      if (layer.borderRadius !== undefined) properties.borderRadius = layer.borderRadius;
      if (layer.pathData !== undefined) properties.pathData = layer.pathData;
    } else if (layer.kind === "group") {
      properties.children_ids = layer.children_ids;
    }

    const evaluated: EvaluatedLayerState = {
      layer_id: layer.layer_id,
      kind: layer.kind,
      visible: layer.visible && isWithinTime,
      localFrame,
      transform: evalTransform,
      opacity: isWithinTime ? evalTransform.opacity : 0,
      properties,
      parent_id: layer.parent_id,
    };

    evaluatedMap.set(layer.layer_id, evaluated);
    return evaluated;
  }

  const evaluatedLayers: EvaluatedLayerState[] = [];
  for (const layer of sortedLayers) {
    const res = resolveEvaluated(layer);
    if (res) evaluatedLayers.push(res);
  }

  // Audio tracks evaluation
  const evaluatedAudioTracks: EvaluatedAudioTrackState[] = [];
  for (const track of timeline.tracks) {
    if (track.kind === "audio") {
      let trackActive = false;
      let trackVol = 1.0;
      for (const clip of track.clips) {
        if (frame >= clip.time_range.startFrame && frame < clip.time_range.endFrame) {
          trackActive = true;
          break;
        }
      }
      evaluatedAudioTracks.push({
        track_id: track.track_id,
        volume: track.muted ? 0 : trackVol,
        muted: track.muted,
        active: trackActive,
      });
    }
  }

  return {
    frame,
    fps,
    timeMs,
    active_scenes: [],
    layers: evaluatedLayers,
    audio: { tracks: evaluatedAudioTracks },
  };
}

/**
 * Pure evaluator for canonical video projects (either BlueprintV2 or NormalizedVideo).
 */
export function evaluateVideoAtFrame(
  video: BlueprintV2 | NormalizedVideo | any,
  frame: number
): EvaluatedFrameState {
  const fps = video.fps ?? 30;
  const timeMs = frameToMs(frame, fps);

  // If video already has an assembled timeline with explicit layers
  if (video.timeline && Array.isArray((video as any).layers) && (video as any).layers.length > 0) {
    const res = evaluateTimelineAtFrame(video.timeline, (video as any).layers, frame);
    // Determine active scenes
    const activeScenes: string[] = [];
    if (Array.isArray(video.scenes)) {
      for (const s of video.scenes) {
        const start = s.startFrame ?? 0;
        const dur = s.durationFrames ?? 1;
        if (frame >= start && frame < start + dur) {
          activeScenes.push(s.scene_id);
        }
      }
    }
    return { ...res, active_scenes: activeScenes };
  }

  // Evaluate from scenes
  const scenes: Array<BlueprintScene | NormalizedScene> = video.scenes ?? [];
  const activeScenes: string[] = [];
  const evaluatedLayers: EvaluatedLayerState[] = [];

  for (const scene of scenes) {
    const start = scene.startFrame ?? 0;
    const dur = scene.durationFrames ?? 1;
    const end = start + dur;
    const isActive = frame >= start && frame < end;
    const localFrame = frame - start;

    if (isActive) {
      activeScenes.push(scene.scene_id);
    }

    // If scene has explicit layers
    if ((scene as any).layers && Array.isArray((scene as any).layers) && (scene as any).layers.length > 0) {
      for (const layer of (scene as any).layers as CanonicalLayer[]) {
        const lStart = layer.time_range?.startFrame ?? start;
        const lDur = layer.time_range?.durationFrames ?? dur;
        const lEnd = lStart + lDur;
        const lActive = frame >= lStart && frame < lEnd;
        const lLocal = frame - lStart;

        let evalT = evaluateLayerTransform(layer, lLocal, fps);

        if (layer.parent_id) {
          const parentLayer = ((scene as any).layers as CanonicalLayer[]).find(
            (p) => p.layer_id === layer.parent_id
          );
          if (parentLayer) {
            const pStart = parentLayer.time_range?.startFrame ?? start;
            const pLocal = frame - pStart;
            const parentEvalT = evaluateLayerTransform(parentLayer, pLocal, fps);
            const parentT: Transform = {
              position: { x: parentEvalT.x, y: parentEvalT.y },
              scale: { x: parentEvalT.scaleX, y: parentEvalT.scaleY },
              rotation: parentEvalT.rotation,
              anchor: { x: 0.5, y: 0.5 },
              opacity: parentEvalT.opacity,
            };
            const childT: Transform = {
              position: { x: evalT.x, y: evalT.y },
              scale: { x: evalT.scaleX, y: evalT.scaleY },
              rotation: evalT.rotation,
              anchor: { x: 0.5, y: 0.5 },
              opacity: evalT.opacity,
            };
            const composed = composeTransform(parentT, childT);
            evalT = {
              x: composed.position.x,
              y: composed.position.y,
              scaleX: composed.scale.x,
              scaleY: composed.scale.y,
              rotation: composed.rotation,
              opacity: composed.opacity,
            };
          }
        }

        const props: Record<string, any> = {};
        if (layer.kind === "text") {
          props.text = (layer as any).text;
          props.typography = (layer as any).typography;
        } else if (layer.kind === "image" || layer.kind === "video") {
          props.asset_ref = (layer as any).asset_ref;
          props.fit = (layer as any).fit;
          if ((layer as any).crop) props.crop = (layer as any).crop;
        } else if (layer.kind === "shape") {
          props.shape_type = (layer as any).shape_type;
          props.size = (layer as any).size;
          if ((layer as any).fillColor !== undefined) props.fillColor = (layer as any).fillColor;
          if ((layer as any).strokeColor !== undefined) props.strokeColor = (layer as any).strokeColor;
          if ((layer as any).strokeWidth !== undefined) props.strokeWidth = (layer as any).strokeWidth;
          if ((layer as any).borderRadius !== undefined) props.borderRadius = (layer as any).borderRadius;
          if ((layer as any).pathData !== undefined) props.pathData = (layer as any).pathData;
        } else if (layer.kind === "group") {
          props.children_ids = (layer as any).children_ids;
        }

        evaluatedLayers.push({
          layer_id: layer.layer_id,
          scene_id: scene.scene_id,
          parent_id: layer.parent_id,
          kind: layer.kind,
          visible: layer.visible && lActive,
          localFrame: lLocal,
          transform: evalT,
          opacity: lActive ? evalT.opacity : 0,
          properties: props,
        });
      }
    } else {
      // Synthesize standard canonical layers from scene surface/content
      const surface = (scene as any).surface ?? {};
      const content = (scene as any).content ?? {};

      // 1. Text Layer if text present
      if (surface.text || content.lines || content.words) {
        const textVal = surface.text || (content.lines ? content.lines.join(" ") : "");
        evaluatedLayers.push({
          layer_id: `layer_${scene.scene_id}_text`,
          scene_id: scene.scene_id,
          kind: "text",
          visible: isActive,
          localFrame,
          transform: {
            x: surface.position?.x ?? 0,
            y: surface.position?.y ?? 0,
            scaleX: surface.scale ?? 1,
            scaleY: surface.scale ?? 1,
            rotation: surface.rotation ?? 0,
            opacity: isActive ? (surface.opacity ?? 1) : 0,
          },
          opacity: isActive ? (surface.opacity ?? 1) : 0,
          properties: {
            text: textVal,
            fontFamily: surface.fontFamily ?? "Cairo",
            fontSize: surface.fontSize ?? 48,
          },
        });
      }

      // 2. Media Layer if image/screen present
      if (surface.logoSrc || content.screen || (content.images && content.images.length > 0)) {
        const assetRef = surface.logoSrc || content.screen || (content.images ? content.images[0] : "");
        evaluatedLayers.push({
          layer_id: `layer_${scene.scene_id}_media`,
          scene_id: scene.scene_id,
          kind: "image",
          visible: isActive,
          localFrame,
          transform: {
            x: 0,
            y: 0,
            scaleX: 1,
            scaleY: 1,
            rotation: 0,
            opacity: isActive ? 1 : 0,
          },
          opacity: isActive ? 1 : 0,
          properties: { asset_ref: assetRef },
        });
      }

      // 3. Fallback background/container layer if nothing else
      if (!surface.text && !surface.logoSrc && (!content.images || content.images.length === 0)) {
        evaluatedLayers.push({
          layer_id: `layer_${scene.scene_id}_base`,
          scene_id: scene.scene_id,
          kind: "shape",
          visible: isActive,
          localFrame,
          transform: { x: 0, y: 0, scaleX: 1, scaleY: 1, rotation: 0, opacity: isActive ? 1 : 0 },
          opacity: isActive ? 1 : 0,
          properties: { template: scene.template },
        });
      }
    }
  }

  // Audio evaluation
  const evaluatedAudioTracks: EvaluatedAudioTrackState[] = [];
  const rawAudio = video.audio;

  let voActive = false;
  if (rawAudio?.voiceover) {
    const vo = rawAudio.voiceover;
    const voStart = vo.startFrame ?? 0;
    const voDur = vo.durationFrames;
    voActive = voDur !== undefined ? (frame >= voStart && frame < voStart + voDur) : (frame >= voStart);
    const localVoFrame = Math.max(0, frame - voStart);
    evaluatedAudioTracks.push({
      track_id: "audio_voiceover",
      kind: "voiceover",
      asset_ref: typeof vo.asset_ref === "string" ? vo.asset_ref : (vo.asset_ref as any)?.asset_id,
      volume: vo.volume ?? 1.0,
      muted: vo.mute ?? false,
      active: voActive,
      startFrame: voStart,
      durationFrames: voDur,
      localFrame: localVoFrame,
    });
  }

  if (rawAudio?.music) {
    const bgm = rawAudio.music;
    const bgmStart = bgm.startFrame ?? 0;
    const bgmDur = bgm.durationFrames;
    const bgmActive = bgmDur !== undefined ? (frame >= bgmStart && frame < bgmStart + bgmDur) : (frame >= bgmStart);
    const localBgmFrame = Math.max(0, frame - bgmStart);

    let effectiveVolume = bgm.volume ?? 0.15;
    // Ducking rule: duck music when voiceover is actively speaking
    if (bgm.ducking && bgm.ducking.enabled !== false && voActive) {
      effectiveVolume = bgm.ducking.ducking_volume ?? 0.05;
    }

    evaluatedAudioTracks.push({
      track_id: "audio_music",
      kind: "music",
      asset_ref: typeof bgm.asset_ref === "string" ? bgm.asset_ref : (bgm.asset_ref as any)?.asset_id,
      volume: effectiveVolume,
      base_volume: bgm.volume ?? 0.15,
      muted: bgm.mute ?? false,
      active: bgmActive,
      startFrame: bgmStart,
      durationFrames: bgmDur,
      localFrame: localBgmFrame,
    });
  }

  if (rawAudio?.global_sfx && Array.isArray(rawAudio.global_sfx)) {
    rawAudio.global_sfx.forEach((sfx: any, idx: number) => {
      const sfxStart = sfx.startFrame ?? 0;
      const sfxDur = sfx.durationFrames;
      const sfxActive = sfxDur !== undefined ? (frame >= sfxStart && frame < sfxStart + sfxDur) : (frame >= sfxStart);
      const localSfxFrame = Math.max(0, frame - sfxStart);

      evaluatedAudioTracks.push({
        track_id: sfx.track_id ?? `audio_sfx_${idx}`,
        kind: "sfx",
        asset_ref: typeof sfx.asset_ref === "string" ? sfx.asset_ref : (sfx.asset_ref as any)?.asset_id,
        volume: sfx.volume ?? 1.0,
        muted: sfx.mute ?? false,
        active: sfxActive,
        startFrame: sfxStart,
        durationFrames: sfxDur,
        localFrame: localSfxFrame,
      });
    });
  }

  // Scene audio layers
  for (const scene of scenes) {
    if ((scene as any).layers && Array.isArray((scene as any).layers)) {
      for (const layer of (scene as any).layers as CanonicalLayer[]) {
        if (layer.kind === "audio") {
          const lStart = layer.time_range?.startFrame ?? scene.startFrame ?? 0;
          const lDur = layer.time_range?.durationFrames ?? scene.durationFrames ?? 1;
          const lActive = frame >= lStart && frame < lStart + lDur;
          const localLFrame = Math.max(0, frame - lStart);

          evaluatedAudioTracks.push({
            track_id: layer.layer_id,
            kind: "layer",
            asset_ref: typeof (layer as any).asset_ref === "string" ? (layer as any).asset_ref : (layer as any).asset_ref?.asset_id,
            volume: (layer as any).volume ?? 1.0,
            muted: (layer as any).muted ?? false,
            active: lActive,
            startFrame: lStart,
            durationFrames: lDur,
            localFrame: localLFrame,
          });
        }
      }
    }
  }

  return {
    frame,
    fps,
    timeMs,
    active_scenes: activeScenes,
    layers: evaluatedLayers,
    audio: { tracks: evaluatedAudioTracks },
  };
}
