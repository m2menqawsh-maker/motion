import { BrandKit } from "../../contracts/brand";
import { StyleSurface, StyleSurfaceSchema } from "../../contracts/blueprint";
import { SceneContent } from "../../contracts/SceneContent";
import { TemplateEntry } from "../../registry/types";
import { validateStyleOverride } from "../../contracts/override-validator";
import { resolveBrandToken } from "../../templates/brand-resolver";
import { BlueprintScene } from "../../contracts/blueprint";

export interface SceneOverride {
  props?: Record<string, any>;
  timing?: {
    startFrame?: number;
    durationFrames?: number;
  };
}

export interface ProjectData {
  project: { fps: number; title: string };
  blueprint: { scenes: BlueprintScene[] };
  brand: BrandKit;
  overrides?: { scenes: Record<string, SceneOverride> };
  manifest?: any;
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
  override?: SceneOverride
): MergedScene {
  // 1. يبدأ من registryEntry.defaults
  const baseSurface = { ...registryEntry.defaults };

  // 2. يدمج scene.surface أو scene.props فوقها
  const sceneProps = { ...((scene as any).surface || {}), ...(scene.props || {}) };
  const mergedProps = { ...baseSurface, ...sceneProps };

  // 3. يحل كل قيمة تبدأ بـ "brand."
  const resolvedProps = resolveTokensDeep(mergedProps, brand);

  // 4. Validate resolved props strictly against StyleSurfaceSchema (Runtime Validation - Fixes Flaw 8)
  const finalValidatedSurface = StyleSurfaceSchema.parse(resolvedProps);

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

  const finalContent: SceneContent = { ...scene.content };
  
  if (!finalContent.images && scene.media_refs && scene.media_refs.length > 0) {
    finalContent.images = [...scene.media_refs];
  }
  
  if (!finalContent.screen && scene.media_refs && scene.media_refs.length > 0) {
    finalContent.screen = scene.media_refs[0];
  }
  
  // 7. يرجع surface نهائية
  return {
    scene_id: scene.scene_id,
    template: scene.template,
    startFrame,
    durationFrames,
    surface: surfaceWithOverrides,
    media_refs: scene.media_refs || [],
    sfx_ref: scene.sfx_ref || null,
    captions_ref: scene.captions_ref || null,
    content: finalContent,
    effects: (scene as any).effects || [],
    template_props: (scene as any).template_props || {},
  };
}

export function mergeProject(
  data: ProjectData,
  getRegistryEntry: (template: string) => TemplateEntry | undefined
): MergedProject {
  const scenes = [...data.blueprint.scenes]
    .sort((a, b) => a.startFrame - b.startFrame)
    .map(scene => {
      const entry = getRegistryEntry(scene.template);
      if (!entry) {
        throw new Error(`Template not found in registry: ${scene.template}`);
      }
      const override = data.overrides?.scenes[scene.scene_id];
      return mergeScene(scene, entry, data.brand, override);
    });

  const totalDurationFrames = scenes.reduce((max, s) => {
    const end = s.startFrame + s.durationFrames;
    return end > max ? end : max;
  }, 0);

  return {
    fps: data.project.fps,
    title: data.project.title,
    totalDurationFrames,
    scenes,
    audio: (data as any).audio || (data.blueprint as any).audio,
  };
}
