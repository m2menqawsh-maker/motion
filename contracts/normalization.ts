/**
 * contracts/normalization.ts — Canonical Video Normalizer & Domain Representation.
 * S28-R02: Pure, deterministic normalization of canonical video blueprints and render inputs.
 * ZERO Remotion or React dependencies.
 */
import {
  BlueprintScene,
  BlueprintV2,
  StyleSurface,
  StyleSurfaceSchema,
  TransitionRef,
  TransitionRefSchema,
  SUPPORTED_TRANSITION_TYPES,
  SceneOverride,
} from "./blueprint";
import { SceneContent } from "./SceneContent";
import { BrandKit } from "./brand";
import { validateStyleOverride } from "./override-validator";
import {
  resolveAssetReference,
  ASSET_ID_REGEX,
} from "./asset-resolver";
import { validateTemplatePayload } from "./template-schemas";
import {
  UnknownEffectError,
  UnknownTransitionError,
  UnknownTemplateError,
  InvalidRenderInputError,
} from "./render-input";
import {
  isKnownEffect,
  isExecutableEffect,
  SEMANTIC_EFFECTS_CATALOG,
} from "./effects";
import {
  getSemanticTemplateEntry,
  SemanticTemplateEntry,
} from "../registry/semantic-registry";
import {
  type CanonicalTimeline,
  type CanonicalTrack,
  type CanonicalClip,
  type CanonicalTransitionSpec,
  createTimeRange,
  calculateCanonicalDuration,
  msToFrame,
  frameToSeconds,
  secondsToFrame,
  localFrameToGlobal,
  globalFrameToLocal,
} from "./timeline";
import {
  type CanonicalLayer,
  defaultTransform,
} from "./layers";

export {
  msToFrame,
  frameToSeconds,
  secondsToFrame,
  localFrameToGlobal,
  globalFrameToLocal,
  calculateCanonicalDuration,
  createTimeRange,
};

// ─── 1. Canonical Normalized Representation ───────────────────────────────────

export interface NormalizedScene {
  scene_id: string;
  template: string;
  startFrame: number;
  durationFrames: number;
  surface: StyleSurface;
  media_refs: string[];
  sfx_ref: string | null;
  captions_ref: string | null;
  content: SceneContent;
  layers?: CanonicalLayer[];
  effects?: any[];
  template_props?: Record<string, any>;
  transition?: TransitionRef;
}

export interface NormalizedAudio {
  voiceover?: string;
  bgm?: string;
  bgmVolume?: number;
}

export interface NormalizedVideo {
  fps: number;
  title: string;
  totalDurationFrames: number;
  scenes: NormalizedScene[];
  audio?: NormalizedAudio;
  timeline?: CanonicalTimeline;
  aspect_ratio?: string;
  project_id?: string;
}

export interface CanonicalVideoInput {
  project?: { title?: string; fps?: number; project_id?: string; [key: string]: any };
  blueprint: { fps?: number; aspect_ratio?: string; project_id?: string; scenes: BlueprintScene[]; audio?: any; [key: string]: any };
  brand?: BrandKit;
  overrides?: { scenes: Record<string, SceneOverride> };
  asset_manifest?: any;
  media_map?: Record<string, string>;
}

// ─── 2. Deterministic Timing Helpers ──────────────────────────────────────────

export function framesToMs(frames: number, fps: number): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  return Math.round((frames / fps) * 1000);
}

export function msToFrames(ms: number, fps: number): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  return Math.round((ms / 1000) * fps);
}

export function calculateTotalDurationFrames(scenes: Array<{ startFrame: number; durationFrames: number }>): number {
  return scenes.reduce((max, s) => {
    const end = s.startFrame + s.durationFrames;
    return end > max ? end : max;
  }, 0);
}

// ─── 3. Brand Token Resolution ────────────────────────────────────────────────

export function resolveBrandToken(key: string, brand: BrandKit): string {
  if (key === "brand.primary") return brand.colors.primary;
  if (key === "brand.accent") return brand.colors.accent;
  if (key === "brand.background") return brand.colors.background;
  if (key === "brand.text") return brand.colors.text;
  if (key === "brand.surface" && brand.colors.surface) return brand.colors.surface;
  if (key === "brand.display") return brand.fonts.display;
  if (key === "brand.body") return brand.fonts.body;
  if (key === "brand.logo" && brand.logoSrc) return brand.logoSrc;
  return key;
}

export function resolveTokensDeep(obj: any, brand: BrandKit): any {
  if (Array.isArray(obj)) {
    return obj.map((val) => resolveTokensDeep(val, brand));
  } else if (obj !== null && typeof obj === "object") {
    const resolved: Record<string, any> = {};
    for (const key in obj) {
      resolved[key] = resolveTokensDeep(obj[key], brand);
    }
    return resolved;
  } else if (typeof obj === "string" && obj.startsWith("brand.")) {
    return resolveBrandToken(obj, brand);
  }
  return obj;
}

// Default Fallback Brand Kit
const DEFAULT_BRAND: BrandKit = {
  brandName: "Default",
  logoSrc: null,
  colors: {
    primary: "#00F5FF",
    accent: "#FFD700",
    background: "#1a2238",
    text: "#FFFFFF",
  },
  fonts: {
    display: "Cairo",
    body: "IBMPlexSansArabic",
  },
};

// ─── 4. Domain Scene Normalizer ───────────────────────────────────────────────

export function normalizeScene(
  scene: BlueprintScene,
  templateEntry: {
    id?: string;
    defaults?: Record<string, any>;
    schema?: any;
    contentSchema?: any;
    propsSchema?: any;
    surfaceSchema?: any;
  },
  brand: BrandKit = DEFAULT_BRAND,
  override?: SceneOverride,
  mediaMap?: Record<string, string>,
  projectId?: string
): NormalizedScene {
  // 1. Defaults from template entry
  const baseSurface = { ...(templateEntry.defaults || {}) };

  // 2. Merge scene surface or scene props over defaults
  const sceneProps = { ...((scene as any).surface || {}), ...(scene.props || {}) };
  const mergedProps = { ...baseSurface, ...sceneProps };

  // 3. Resolve brand tokens
  const resolvedProps = resolveTokensDeep(mergedProps, brand);

  // 4. Validate resolved surface against schema
  let finalValidatedSurface: StyleSurface;
  try {
    finalValidatedSurface = StyleSurfaceSchema.parse(resolvedProps);
  } catch (e) {
    throw e;
  }

  // 5. Merge override props
  let surfaceWithOverrides = { ...finalValidatedSurface };
  if (override && override.props) {
    if (override.props.styleOverride) {
      const { ok, errors } = validateStyleOverride(override.props.styleOverride);
      if (!ok) {
        const validStyleOverride: Record<string, any> = {};
        for (const [k, v] of Object.entries(override.props.styleOverride)) {
          if (validateStyleOverride({ [k]: v }).ok) {
            validStyleOverride[k] = v;
          }
        }
        override.props.styleOverride = validStyleOverride;
      }
    }

    const rawWithOverrides = {
      ...surfaceWithOverrides,
      ...resolveTokensDeep(override.props, brand),
    };
    surfaceWithOverrides = StyleSurfaceSchema.parse(rawWithOverrides);
  }

  // 6. Timing from override if present
  const startFrame = override?.timing?.startFrame ?? scene.startFrame;
  const durationFrames = override?.timing?.durationFrames ?? scene.durationFrames;

  // 7. Resolve asset references via media_map
  const resolvedMediaRefs = (scene.media_refs || []).map((ref, idx) =>
    resolveAssetReference(ref, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].media_refs[${idx}]`,
      sceneId: scene.scene_id,
      projectId,
    })
  );

  const resolvedSfxRef = scene.sfx_ref
    ? resolveAssetReference(scene.sfx_ref, mediaMap, {
        fieldPath: `scenes[${scene.scene_id}].sfx_ref`,
        sceneId: scene.scene_id,
        projectId,
      })
    : null;

  const resolvedCaptionsRef = scene.captions_ref
    ? resolveAssetReference(scene.captions_ref, mediaMap, {
        fieldPath: `scenes[${scene.scene_id}].captions_ref`,
        sceneId: scene.scene_id,
        projectId,
      })
    : null;

  if (surfaceWithOverrides.logoSrc) {
    surfaceWithOverrides.logoSrc = resolveAssetReference(surfaceWithOverrides.logoSrc, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].surface.logoSrc`,
      sceneId: scene.scene_id,
      projectId,
    });
  }

  // Content-level media refs
  const finalContent: SceneContent = { ...scene.content };

  if (finalContent.images && finalContent.images.length > 0) {
    finalContent.images = finalContent.images.map((imgRef, idx) =>
      resolveAssetReference(imgRef, mediaMap, {
        fieldPath: `scenes[${scene.scene_id}].content.images[${idx}]`,
        sceneId: scene.scene_id,
        projectId,
      })
    );
  } else if (resolvedMediaRefs.length > 0) {
    finalContent.images = [...resolvedMediaRefs];
  }

  if (finalContent.screen) {
    finalContent.screen = resolveAssetReference(finalContent.screen, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].content.screen`,
      sceneId: scene.scene_id,
      projectId,
    });
  } else if (resolvedMediaRefs.length > 0) {
    finalContent.screen = resolvedMediaRefs[0];
  }

  if (finalContent.icons && finalContent.icons.length > 0) {
    finalContent.icons = finalContent.icons.map((iconRef, idx) =>
      resolveAssetReference(iconRef, mediaMap, {
        fieldPath: `scenes[${scene.scene_id}].content.icons[${idx}]`,
        sceneId: scene.scene_id,
        projectId,
      })
    );
  }

  if (finalContent.audioRef) {
    finalContent.audioRef = resolveAssetReference(finalContent.audioRef, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].content.audioRef`,
      sceneId: scene.scene_id,
      projectId,
    });
  }

  if (
    finalContent.path &&
    typeof finalContent.path === "string" &&
    !finalContent.path.startsWith("M") &&
    !finalContent.path.startsWith("m") &&
    ASSET_ID_REGEX.test(finalContent.path)
  ) {
    finalContent.path = resolveAssetReference(finalContent.path, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].content.path`,
      sceneId: scene.scene_id,
      projectId,
    });
  }

  // Effects fail-closed check
  if (scene.effects && scene.effects.length > 0) {
    for (let eIdx = 0; eIdx < scene.effects.length; eIdx++) {
      const eff = scene.effects[eIdx];
      if (!isKnownEffect(eff.effect)) {
        throw new UnknownEffectError(eff.effect, scene.scene_id, `scenes[${scene.scene_id}].effects[${eIdx}].effect`);
      }
      if (!isExecutableEffect(eff.effect)) {
        const reason = SEMANTIC_EFFECTS_CATALOG[eff.effect]?.reason || "unbridged";
        throw new UnknownEffectError(
          `${eff.effect} (unsupported unbridged effect: ${reason})`,
          scene.scene_id,
          `scenes[${scene.scene_id}].effects[${eIdx}].effect`
        );
      }
    }
  }

  // Transition validation
  let validatedTransition: TransitionRef | undefined = undefined;
  if (scene.transition) {
    if (!SUPPORTED_TRANSITION_TYPES.includes(scene.transition.type as any)) {
      throw new UnknownTransitionError(scene.transition.type, scene.scene_id, `scenes[${scene.scene_id}].transition.type`);
    }
    validatedTransition = TransitionRefSchema.parse(scene.transition);
  }

  // Template payload validation
  validateTemplatePayload(templateEntry as any, scene);

  // Canonical Layer synthesis / normalization
  let normalizedLayers: CanonicalLayer[] = [];
  const sceneTimeRange = createTimeRange(startFrame, durationFrames);

  if ((scene as any).layers && Array.isArray((scene as any).layers) && (scene as any).layers.length > 0) {
    normalizedLayers = (scene as any).layers.map((l: CanonicalLayer) => ({ ...l }));
  } else {
    if (surfaceWithOverrides.text) {
      normalizedLayers.push({
        layer_id: `layer_${scene.scene_id}_text`,
        kind: "text",
        time_range: sceneTimeRange,
        transform: {
          position: { x: surfaceWithOverrides.position?.x ?? 0, y: surfaceWithOverrides.position?.y ?? 0 },
          scale: { x: surfaceWithOverrides.scale ?? 1, y: surfaceWithOverrides.scale ?? 1 },
          rotation: surfaceWithOverrides.rotation ?? 0,
          anchor: { x: 0.5, y: 0.5 },
          opacity: surfaceWithOverrides.opacity ?? 1,
        },
        opacity: surfaceWithOverrides.opacity ?? 1,
        visible: true,
        z_index: 1,
        text: surfaceWithOverrides.text,
        typography: {
          fontFamily: surfaceWithOverrides.fontFamily ?? "Cairo",
          fontSize: surfaceWithOverrides.fontSize ?? 48,
          textAlign: (surfaceWithOverrides.textAlign as any) ?? "center",
          fillColor: surfaceWithOverrides.color,
        },
        channels: [],
      });
    }

    if (resolvedMediaRefs.length > 0 || surfaceWithOverrides.logoSrc) {
      normalizedLayers.push({
        layer_id: `layer_${scene.scene_id}_media`,
        kind: "image",
        time_range: sceneTimeRange,
        transform: defaultTransform(),
        opacity: 1,
        visible: true,
        z_index: 0,
        asset_ref: surfaceWithOverrides.logoSrc || resolvedMediaRefs[0],
        fit: "contain",
        channels: [],
      });
    }

    if (normalizedLayers.length === 0) {
      normalizedLayers.push({
        layer_id: `layer_${scene.scene_id}_base`,
        kind: "shape",
        time_range: sceneTimeRange,
        transform: defaultTransform(),
        opacity: 1,
        visible: true,
        z_index: 0,
        shape_type: "rectangle",
        size: { width: 1920, height: 1080 },
        fillColor: surfaceWithOverrides.background ?? "#1a2238",
        channels: [],
      });
    }
  }

  return {
    scene_id: scene.scene_id,
    template: scene.template,
    startFrame,
    durationFrames,
    surface: surfaceWithOverrides,
    media_refs: resolvedMediaRefs,
    sfx_ref: resolvedSfxRef,
    captions_ref: resolvedCaptionsRef,
    content: finalContent,
    layers: normalizedLayers,
    effects: (scene as any).effects || [],
    template_props: (scene as any).template_props || {},
    transition: validatedTransition,
  };
}

// ─── 5. Timeline Assembly ────────────────────────────────────────────────────

export function buildCanonicalTimeline(video: {
  fps: number;
  totalDurationFrames: number;
  scenes: NormalizedScene[];
  audio?: NormalizedAudio;
  project_id?: string;
}): CanonicalTimeline {
  const tracks: CanonicalTrack[] = [];

  // Track 0: Main Video / Scene Track
  const videoClips: CanonicalClip[] = video.scenes.map((scene) => ({
    clip_id: `clip_sc_${scene.scene_id}`,
    track_id: "track_main_video",
    time_range: createTimeRange(scene.startFrame, scene.durationFrames),
    scene_id: scene.scene_id,
    source_ref: scene.template,
    layer_ids: scene.layers ? scene.layers.map((l) => l.layer_id) : [`layer_${scene.scene_id}_base`],
  }));

  tracks.push({
    track_id: "track_main_video",
    kind: "video",
    name: "Main Video Track",
    order: 0,
    muted: false,
    visible: true,
    clips: videoClips,
  });

  // Track 1: Audio Tracks
  if (video.audio) {
    if (video.audio.voiceover) {
      tracks.push({
        track_id: "track_voiceover",
        kind: "audio",
        name: "Voiceover Track",
        order: 1,
        muted: false,
        visible: true,
        clips: [
          {
            clip_id: "clip_voiceover",
            track_id: "track_voiceover",
            time_range: createTimeRange(0, video.totalDurationFrames),
            source_ref: video.audio.voiceover,
            layer_ids: [],
          },
        ],
      });
    }

    if (video.audio.bgm) {
      tracks.push({
        track_id: "track_bgm",
        kind: "audio",
        name: "Background Music Track",
        order: 2,
        muted: false,
        visible: true,
        clips: [
          {
            clip_id: "clip_bgm",
            track_id: "track_bgm",
            time_range: createTimeRange(0, video.totalDurationFrames),
            source_ref: video.audio.bgm,
            layer_ids: [],
          },
        ],
      });
    }
  }

  // Transitions
  const transitions: CanonicalTransitionSpec[] = [];
  video.scenes.forEach((scene, idx) => {
    if (scene.transition && idx < video.scenes.length - 1) {
      const nextScene = video.scenes[idx + 1];
      transitions.push({
        transition_id: `trans_${scene.scene_id}_${nextScene.scene_id}`,
        type: scene.transition.type as any,
        durationFrames: scene.transition.durationFrames,
        overlap_semantics: (scene.transition as any).overlap_semantics ?? "overlap",
        from_scene_id: scene.scene_id,
        to_scene_id: nextScene.scene_id,
      });
    }
  });

  return {
    timeline_id: `tl_${video.project_id || "default"}`,
    fps: video.fps,
    totalDurationFrames: video.totalDurationFrames,
    tracks,
    transitions,
  };
}

// ─── 6. Canonical Video Normalizer ───────────────────────────────────────────

export function normalizeCanonicalVideo(
  data: CanonicalVideoInput,
  options?: {
    getTemplateEntry?: (template: string) => SemanticTemplateEntry | undefined;
    mediaMap?: Record<string, string>;
    defaultBrand?: BrandKit;
  }
): NormalizedVideo {
  if (!data || typeof data !== "object") {
    throw new InvalidRenderInputError("Project data must be a non-null object");
  }
  if (!data.blueprint || !Array.isArray(data.blueprint.scenes)) {
    throw new InvalidRenderInputError("Missing or malformed blueprint.scenes in project data");
  }

  const fps = data.blueprint.fps ?? (data.project as any)?.fps;
  if (fps === undefined || fps === null) {
    throw new InvalidRenderInputError("Missing mandatory blueprint.fps in project data");
  }

  // Idempotency guarantee: if input is already normalized, preserve and return pure clone
  if ((data.blueprint as any).timeline && Array.isArray((data.blueprint as any).scenes)) {
    const bp = data.blueprint as any;
    const clonedScenes = bp.scenes.map((s: any) => ({ ...s }));
    const result: NormalizedVideo = {
      fps,
      title: data.project?.title || bp.project_id || bp.title || "Untitled",
      totalDurationFrames: bp.totalDurationFrames ?? calculateTotalDurationFrames(clonedScenes),
      scenes: clonedScenes,
      audio: bp.audio,
      aspect_ratio: bp.aspect_ratio,
      project_id: (data.project as any)?.project_id || bp.project_id || bp.title || "Untitled",
    };
    result.timeline = bp.timeline ?? buildCanonicalTimeline(result);
    return result;
  }

  const brand = data.brand || options?.defaultBrand || DEFAULT_BRAND;
  const mediaMap = data.media_map || options?.mediaMap;
  const projectId = (data.project as any)?.project_id || (data.blueprint as any)?.project_id || data.project?.title || "Untitled";
  const entryResolver = options?.getTemplateEntry || getSemanticTemplateEntry;

  const scenes = [...data.blueprint.scenes]
    .sort((a, b) => a.startFrame - b.startFrame)
    .map((scene) => {
      const entry = entryResolver(scene.template);
      if (!entry) {
        throw new UnknownTemplateError(scene.template, scene.scene_id);
      }
      const override = data.overrides?.scenes[scene.scene_id];
      return normalizeScene(scene, entry, brand, override, mediaMap, projectId);
    });

  const totalDurationFrames = calculateTotalDurationFrames(scenes);

  const rawAudio = (data as any).audio || (data.blueprint as any).audio;
  let normalizedAudio: NormalizedAudio | undefined = undefined;

  if (rawAudio) {
    const voRef = rawAudio.voiceover?.asset_ref || rawAudio.voiceover || rawAudio.voiceover_ref;
    const musicRef = rawAudio.music?.asset_ref || rawAudio.bgm || rawAudio.music_ref;
    const musicVolume = rawAudio.music?.volume ?? rawAudio.bgmVolume ?? rawAudio.volume ?? 0.15;

    const resolvedVo = voRef
      ? resolveAssetReference(voRef, mediaMap, {
          fieldPath: "audio.voiceover.asset_ref",
          projectId,
        })
      : undefined;

    const resolvedBgm = musicRef
      ? resolveAssetReference(musicRef, mediaMap, {
          fieldPath: "audio.music.asset_ref",
          projectId,
        })
      : undefined;

    normalizedAudio = {
      voiceover: resolvedVo,
      bgm: resolvedBgm,
      bgmVolume: typeof musicVolume === "number" ? musicVolume : 0.15,
    };
  }

  const result: NormalizedVideo = {
    fps,
    title: data.project?.title || (data.blueprint as any)?.project_id || "Untitled",
    totalDurationFrames,
    scenes,
    audio: normalizedAudio,
    aspect_ratio: data.blueprint.aspect_ratio,
    project_id: projectId,
  };

  result.timeline = buildCanonicalTimeline(result);
  return result;
}
