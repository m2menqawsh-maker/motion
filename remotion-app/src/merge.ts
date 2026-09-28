import { BrandKit } from "../../contracts/brand";
import { StyleSurface, StyleSurfaceSchema, TransitionRef, TransitionRefSchema, SUPPORTED_TRANSITION_TYPES } from "../../contracts/blueprint";
import { SceneContent } from "../../contracts/SceneContent";
import { TemplateEntry } from "../../registry/types";
import { validateStyleOverride } from "../../contracts/override-validator";
import { resolveBrandToken } from "../../templates/brand-resolver";
import { BlueprintScene } from "../../contracts/blueprint";
export type { BlueprintScene } from "../../contracts/blueprint";
import {
  resolveAssetReference,
  ASSET_ID_REGEX,
  UnknownAssetReferenceError,
  MalformedAssetRefError,
} from "../../contracts/asset-resolver";
import { validateTemplatePayload } from "../../contracts/template-schemas";
import { UnknownEffectError, UnknownTransitionError, UnknownTemplateError, InvalidRenderInputError } from "../../contracts/render-input";
import { isKnownEffect } from "../../registry/effects-runtime";

export interface SceneOverride {
  props?: Record<string, any>;
  timing?: {
    startFrame?: number;
    durationFrames?: number;
  };
}

export interface ProjectData {
  project: { title: string; fps?: number; [key: string]: any };
  blueprint: { fps?: number; aspect_ratio?: string; scenes: BlueprintScene[]; [key: string]: any };
  brand: BrandKit;
  overrides?: { scenes: Record<string, SceneOverride> };
  asset_manifest?: any;
  media_map?: Record<string, string>;
}

export interface MergedScene {
  scene_id: string;
  template: string;
  startFrame: number;
  durationFrames: number;
  surface: StyleSurface;
  media_refs: string[];
  sfx_ref: string | null;
  captions_ref: string | null;
  content: SceneContent;
  effects?: any[];
  template_props?: Record<string, any>;
  transition?: TransitionRef;
}

export interface MergedProject {
  fps: number;
  title: string;
  totalDurationFrames: number;
  scenes: MergedScene[];
  audio?: {
    voiceover?: string;
    bgm?: string;
    bgmVolume?: number;
  };
}

/**
 * دالة استبدال القيم التي تبدأ بـ brand. بقيمتها الفعلية من الهوية البصرية
 */
function resolveTokensDeep(obj: any, brand: BrandKit): any {
  if (Array.isArray(obj)) {
    return obj.map(val => resolveTokensDeep(val, brand));
  } else if (obj !== null && typeof obj === 'object') {
    const resolved: Record<string, any> = {};
    for (const key in obj) {
      resolved[key] = resolveTokensDeep(obj[key], brand);
    }
    return resolved;
  } else if (typeof obj === 'string' && obj.startsWith('brand.')) {
    return resolveBrandToken(obj, brand);
  }
  return obj;
}

export function mergeScene(
  scene: BlueprintScene,
  registryEntry: TemplateEntry,
  brand: BrandKit,
  override?: SceneOverride,
  mediaMap?: Record<string, string>,
  projectId?: string
): MergedScene {
  // 1. يبدأ من registryEntry.defaults
  const baseSurface = { ...registryEntry.defaults };

  // 2. يدمج scene.surface أو scene.props فوقها
  const sceneProps = { ...((scene as any).surface || {}), ...(scene.props || {}) };
  const mergedProps = { ...baseSurface, ...sceneProps };

  // 3. يحل كل قيمة تبدأ بـ "brand."
  const resolvedProps = resolveTokensDeep(mergedProps, brand);

  // 4. Validate resolved props strictly against StyleSurfaceSchema (Runtime Validation - Fixes Flaw 8)
  let finalValidatedSurface;
  try {
    finalValidatedSurface = StyleSurfaceSchema.parse(resolvedProps);
  } catch (e) {
    console.error("Zod Validation Failed!");
    console.error("Input Object:", JSON.stringify(resolvedProps, null, 2));
    throw e;
  }

  // 5. يدمج override.props (مع الفحص)
  let surfaceWithOverrides = { ...finalValidatedSurface };
  if (override && override.props) {
    if (override.props.styleOverride) {
      const { ok, errors } = validateStyleOverride(override.props.styleOverride);
      if (!ok) {
        console.warn(`[${scene.scene_id}] Invalid styleOverride keys removed:`, errors);
        const validStyleOverride: Record<string, any> = {};
        for (const [k, v] of Object.entries(override.props.styleOverride)) {
          if (validateStyleOverride({ [k]: v }).ok) {
            validStyleOverride[k] = v;
          }
        }
        override.props.styleOverride = validStyleOverride;
      }
    }
    
    // Merge overrides and re-validate to ensure overrides don't break the schema
    const rawWithOverrides = { ...surfaceWithOverrides, ...resolveTokensDeep(override.props, brand) };
    surfaceWithOverrides = StyleSurfaceSchema.parse(rawWithOverrides);
  }

  // 6. التوقيت من override.timing إن وجد وإلا من scene
  const startFrame = override?.timing?.startFrame ?? scene.startFrame;
  const durationFrames = override?.timing?.durationFrames ?? scene.durationFrames;

  // Resolve Asset IDs via media_map.json (FAIL-CLOSED ASSET-012)
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

  // Resolve Content-level media surfaces (ASSET-005)
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

  if (finalContent.path && typeof finalContent.path === "string" && !finalContent.path.startsWith("M") && !finalContent.path.startsWith("m") && ASSET_ID_REGEX.test(finalContent.path)) {
    finalContent.path = resolveAssetReference(finalContent.path, mediaMap, {
      fieldPath: `scenes[${scene.scene_id}].content.path`,
      sceneId: scene.scene_id,
      projectId,
    });
  }
  
  // Validate effects fail-closed (S16 - LED-046)
  if (scene.effects && scene.effects.length > 0) {
    for (let eIdx = 0; eIdx < scene.effects.length; eIdx++) {
      const eff = scene.effects[eIdx];
      if (!isKnownEffect(eff.effect)) {
        throw new UnknownEffectError(eff.effect, scene.scene_id, `scenes[${scene.scene_id}].effects[${eIdx}].effect`);
      }
    }
  }

  // Validate transition fail-closed (S16 - LED-043)
  let validatedTransition: TransitionRef | undefined = undefined;
  if (scene.transition) {
    if (!SUPPORTED_TRANSITION_TYPES.includes(scene.transition.type as any)) {
      throw new UnknownTransitionError(scene.transition.type, scene.scene_id, `scenes[${scene.scene_id}].transition.type`);
    }
    validatedTransition = TransitionRefSchema.parse(scene.transition);
  }

  // Validate template payload fail-closed (S16 - LED-045)
  validateTemplatePayload(registryEntry, scene);

  // 7. يرجع surface نهائية مع الانتقال المعتمد
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
    effects: (scene as any).effects || [],
    template_props: (scene as any).template_props || {},
    transition: validatedTransition,
  };
}

export function mergeProject(
  data: ProjectData,
  getRegistryEntry: (template: string) => TemplateEntry | undefined
): MergedProject {
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

  const projectId = (data.project as any)?.project_id || (data.blueprint as any)?.project_id || data.project?.title || "Untitled";
  const scenes = [...data.blueprint.scenes]
    .sort((a, b) => a.startFrame - b.startFrame)
    .map(scene => {
      const entry = getRegistryEntry(scene.template);
      if (!entry) {
        throw new UnknownTemplateError(scene.template, scene.scene_id);
      }
      const override = data.overrides?.scenes[scene.scene_id];
      return mergeScene(scene, entry, data.brand, override, data.media_map, projectId);
    });

  const totalDurationFrames = scenes.reduce((max, s) => {
    const end = s.startFrame + s.durationFrames;
    return end > max ? end : max;
  }, 0);

  const rawAudio = (data as any).audio || (data.blueprint as any).audio;
  let normalizedAudio: { voiceover?: string; bgm?: string; bgmVolume?: number } | undefined = undefined;

  if (rawAudio) {
    const voRef = rawAudio.voiceover?.asset_ref || rawAudio.voiceover || rawAudio.voiceover_ref;
    const musicRef = rawAudio.music?.asset_ref || rawAudio.bgm || rawAudio.music_ref;
    const musicVolume = rawAudio.music?.volume ?? rawAudio.bgmVolume ?? rawAudio.volume ?? 0.15;

    const resolvedVo = voRef
      ? resolveAssetReference(voRef, data.media_map, {
          fieldPath: "audio.voiceover.asset_ref",
          projectId,
        })
      : undefined;

    const resolvedBgm = musicRef
      ? resolveAssetReference(musicRef, data.media_map, {
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

  return {
    fps,
    title: data.project.title,
    totalDurationFrames,
    scenes,
    audio: normalizedAudio,
  };
}
