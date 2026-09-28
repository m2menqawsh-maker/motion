import { z } from "zod";
import { AssetKind, ManifestV2 } from "./manifest";
import {
  AssetRefSchema,
  type AssetRef,
  collectAssetReferences,
} from "./asset-resolver";
import { isKnownEffect } from "../registry/effects-runtime";

export { AssetRefSchema, type AssetRef } from "./asset-resolver";

// ==========================================
// 1. Primitive Tokens & Enumerations
// ==========================================

export const AnimationIdSchema = z.enum([
  "none",
  "fade_in",
  "fade_in_up",
  "fade_out",
  "zoom_in",
  "zoom_in_bounce",
  "slide_up",
  "slide_down",
  "slide_right",
  "slide_left",
  "typewriter",
  "word_flip",
  "text_swell",
]);
export type AnimationId = z.infer<typeof AnimationIdSchema>;

export const FontKeySchema = z.enum([
  "Cairo",
  "Tajawal",
  "Almarai",
  "IBMPlexSansArabic",
  "NotoKufiArabic",
  "Inter",
  "Manrope",
  "Fraunces",
  "JetBrainsMono",
]);
export type FontKey = z.infer<typeof FontKeySchema>;

export const AnchorIdSchema = z.enum([
  "top-left",
  "top-center",
  "top-right",
  "center-left",
  "center",
  "center-right",
  "bottom-left",
  "bottom-center",
  "bottom-right",
]);
export type AnchorId = z.infer<typeof AnchorIdSchema>;

export const HexColorSchema = z.string().regex(/^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$|^brand\.[a-zA-Z0-9_]+$/, "Must be valid HEX color or brand token");

export const GradientSchema = z.object({
  from: HexColorSchema,
  to: HexColorSchema,
  angle: z.number().optional(),
});
export type Gradient = z.infer<typeof GradientSchema>;

export const PositionSchema = z.object({
  anchor: AnchorIdSchema,
  x: z.number().optional(),
  y: z.number().optional(),
});
export type Position = z.infer<typeof PositionSchema>;

export const StyleOverrideSchema = z.object({
  borderRadius: z.union([z.string(), z.number()]).optional(),
  boxShadow: z.union([z.string(), z.number()]).optional(),
  textShadow: z.union([z.string(), z.number()]).optional(),
  filter: z.union([z.string(), z.number()]).optional(),
  backdropFilter: z.union([z.string(), z.number()]).optional(),
  border: z.union([z.string(), z.number()]).optional(),
  borderColor: z.union([z.string(), z.number()]).optional(),
  borderWidth: z.union([z.string(), z.number()]).optional(),
  textStroke: z.union([z.string(), z.number()]).optional(),
  textStrokeWidth: z.union([z.string(), z.number()]).optional(),
  padding: z.union([z.string(), z.number()]).optional(),
  gap: z.union([z.string(), z.number()]).optional(),
});
export type StyleOverride = z.infer<typeof StyleOverrideSchema>;

// ==========================================
// 2. Style Surface
// ==========================================

export const StyleSurfaceSchema = z.object({
  text: z.string().optional(),
  subtext: z.string().optional(),
  emphasis: z.string().optional(),
  fontSize: z.number().min(8).max(400).optional(),
  fontWeight: z.union([z.number(), z.string()]).optional(),
  fontFamily: FontKeySchema.optional(),
  letterSpacing: z.string().optional(),
  textAlign: z.enum(["right", "center", "left", "start", "end"]).optional(),
  lineHeight: z.number().min(0.5).max(4).optional(),
  color: HexColorSchema.optional(),
  background: HexColorSchema.optional(),
  gradient: GradientSchema.optional(),
  opacity: z.number().min(0).max(1).optional(),
  position: PositionSchema.optional(),
  scale: z.number().min(0.1).max(10).optional(),
  rotation: z.number().min(-360).max(360).optional(),
  width: z.number().min(1).optional(),
  height: z.number().min(1).optional(),
  animation: AnimationIdSchema.optional(),
  speed: z.number().min(0.1).max(5).optional(),
  delay: z.number().min(0).optional(),
  mode: z.enum(["light", "dark"]).optional(),
  logoSrc: z.string().optional(),
  brandName: z.string().optional(),
  styleOverride: StyleOverrideSchema.optional(),
  coverage_pct: z.number().min(0).max(100).optional(),
  layer: z.number().min(1).max(5).optional(),
}).passthrough();
export type StyleSurface = z.infer<typeof StyleSurfaceSchema>;

// ==========================================
// 3. Scene Content
// ==========================================

export const CaptionWordSchema = z.object({
  word: z.string(),
  startMs: z.number().min(0),
  endMs: z.number().min(0),
});
export type CaptionWord = z.infer<typeof CaptionWordSchema>;

export const SceneContentSchema = z.object({
  lines: z.array(z.string()).optional(),
  words: z.array(CaptionWordSchema).optional(),
  images: z.array(AssetRefSchema).optional(),
  screen: AssetRefSchema.optional(),
  numbers: z.array(z.number()).optional(),
  range: z.object({ from: z.number(), to: z.number() }).optional(),
  path: z.string().optional(),
  icons: z.array(AssetRefSchema).optional(),
  audioRef: AssetRefSchema.optional(),
  spectrum: z.array(z.array(z.number())).optional(),
});
export type SceneContent = z.infer<typeof SceneContentSchema>;

// ==========================================
// 4. Transitions & Effects (S16 - LED-043, LED-046)
// ==========================================

export const SUPPORTED_TRANSITION_TYPES = [
  "fade",
  "slide",
  "wipe",
  "flip",
  "zoom",
  "cross-zoom",
  "film-burn",
  "dissolve",
  "iris",
  "none",
] as const;

export const TransitionTypeSchema = z.enum(SUPPORTED_TRANSITION_TYPES);
export type TransitionType = z.infer<typeof TransitionTypeSchema>;

export const TransitionRefSchema = z.object({
  type: TransitionTypeSchema.default("fade"),
  durationFrames: z.number().int().min(1).default(15),
  timing: z.enum(["linear", "ease-in-out"]).optional(),
});
export type TransitionRef = z.infer<typeof TransitionRefSchema>;

export const EffectRefSchema = z.object({
  effect: z.string().min(1).refine(isKnownEffect, (val) => ({
    message: `Unknown effect '${val}'. Must be registered in EFFECTS_RUNTIME.`,
  })),
  apply: z.enum(["scene", "overlay"]).optional().default("scene"),
  params: z.record(z.string(), z.any()).optional().default({}),
});
export type EffectRef = z.infer<typeof EffectRefSchema>;

// ==========================================
// 5. Canonical AudioPlan Contract (S12)
// ==========================================

export const VoiceoverTrackSchema = z.object({
  asset_ref: AssetRefSchema,
  volume: z.number().min(0.0).max(1.0).default(1.0),
  startFrame: z.number().int().min(0).default(0),
  durationFrames: z.number().int().min(1).optional(),
  mute: z.boolean().default(false),
});
export type VoiceoverTrack = z.infer<typeof VoiceoverTrackSchema>;

export const AudioDuckingSchema = z.object({
  enabled: z.boolean().default(true),
  ducking_volume: z.number().min(0.0).max(1.0).default(0.05),
  duck_under: z.array(z.string()).default(["voiceover"]),
});
export type AudioDucking = z.infer<typeof AudioDuckingSchema>;

export const MusicTrackSchema = z.object({
  asset_ref: AssetRefSchema,
  volume: z.number().min(0.0).max(1.0).default(0.15),
  startFrame: z.number().int().min(0).default(0),
  durationFrames: z.number().int().min(1).optional(),
  loop: z.boolean().default(true),
  mute: z.boolean().default(false),
  ducking: AudioDuckingSchema.optional(),
});
export type MusicTrack = z.infer<typeof MusicTrackSchema>;

export const GlobalSfxTrackSchema = z.object({
  asset_ref: AssetRefSchema,
  startFrame: z.number().int().min(0).default(0),
  durationFrames: z.number().int().min(1).optional(),
  volume: z.number().min(0.0).max(1.0).default(1.0),
});
export type GlobalSfxTrack = z.infer<typeof GlobalSfxTrackSchema>;

export const AudioPlanSchema = z.object({
  voiceover: VoiceoverTrackSchema.optional(),
  music: MusicTrackSchema.optional(),
  global_sfx: z.array(GlobalSfxTrackSchema).default([]),
});
export type AudioPlan = z.infer<typeof AudioPlanSchema>;

// ==========================================
// 6. Scenes & Layout
// ==========================================

export const LayoutSchema = z.object({
  layer: z.number().min(1).max(5).optional(),
  coverage_pct: z.number().min(0).max(100).optional(),
});
export type Layout = z.infer<typeof LayoutSchema>;

export const BlueprintSceneSchema = z.object({
  scene_id: z.string().regex(/^[a-zA-Z0-9_\-]+$/, "Invalid scene_id format"),
  template: z.string().min(1),
  startFrame: z.number().int().min(0),
  durationFrames: z.number().int().min(1),
  content: SceneContentSchema.optional(),
  template_props: z.record(z.string(), z.any()).optional(),
  props: z.record(z.string(), z.any()).optional(),
  surface: z.record(z.string(), z.any()).optional(),
  layout: LayoutSchema.optional(),
  media_refs: z.array(AssetRefSchema).optional(),
  sfx_ref: AssetRefSchema.nullable().optional(),
  captions_ref: AssetRefSchema.nullable().optional(),
  transition: TransitionRefSchema.optional(),
  effects: z.array(EffectRefSchema).optional(),
});
export type BlueprintScene = z.infer<typeof BlueprintSceneSchema>;
export type BlueprintSceneV2 = BlueprintScene;

// ==========================================
// 7. Canonical Blueprint V2 Schema
// ==========================================

export const MetaSchema = z.object({
  motion_personality: z.enum(["Cinematic", "Energetic", "Playful", "Technical"]).optional(),
  timings_path: z.string().optional(),
}).passthrough();
export type Meta = z.infer<typeof MetaSchema>;

export const BlueprintV2Schema = z.object({
  blueprint_version: z.enum(["2.0.0", "2.0"]),
  project_id: z.string().regex(/^[a-zA-Z0-9_\-]+$/, "Invalid project_id format"),
  fps: z.number().int().min(1).max(120),
  aspect_ratio: z.enum(["9:16", "16:9", "1:1", "4:5", "21:9"]),
  scenes: z.array(BlueprintSceneSchema),
  audio: AudioPlanSchema.optional(),
  meta: MetaSchema.optional().default({}),
});
export type BlueprintV2 = z.infer<typeof BlueprintV2Schema>;

export const BlueprintSchema = BlueprintV2Schema;
export type Blueprint = BlueprintV2;

// ==========================================
// 9. Validation Interface & Semantic Checks
// ==========================================

export interface BlueprintValidationResult {
  ok: boolean;
  errors: string[];
  blueprint?: BlueprintV2;
}

export function validateBlueprintV2(
  data: unknown,
  options?: {
    expectedProjectId?: string;
    manifest?: ManifestV2;
  }
): BlueprintValidationResult {
  const parseResult = BlueprintV2Schema.safeParse(data);
  if (!parseResult.success) {
    return {
      ok: false,
      errors: parseResult.error.issues.map(
        (e: z.ZodIssue) => `[${e.path.join(".")}] ${e.message}`
      ),
    };
  }

  const bp = parseResult.data;
  const errors: string[] = [];

  // 1. Project ID Match
  if (options?.expectedProjectId && bp.project_id !== options.expectedProjectId) {
    errors.push(
      `Project ID mismatch: blueprint contains '${bp.project_id}' but expected '${options.expectedProjectId}'`
    );
  }

  if (options?.manifest && bp.project_id !== options.manifest.project_id) {
    errors.push(
      `Project ID mismatch with Manifest: blueprint contains '${bp.project_id}' but manifest has '${options.manifest.project_id}'`
    );
  }

  // 2. Scene Uniqueness and Timing Invariants
  const seenSceneIds = new Set<string>();
  const manifestAssets = new Map<string, AssetKind>();
  if (options?.manifest) {
    for (const a of options.manifest.assets) {
      manifestAssets.set(a.asset_id, a.kind);
    }
  }

  for (let idx = 0; idx < bp.scenes.length; idx++) {
    const s = bp.scenes[idx];

    if (seenSceneIds.has(s.scene_id)) {
      errors.push(`scenes[${idx}]: duplicate scene_id '${s.scene_id}'`);
    }
    seenSceneIds.add(s.scene_id);

    if (s.startFrame < 0) {
      errors.push(`scenes[${idx}] ('${s.scene_id}'): startFrame must be >= 0`);
    }
    if (s.durationFrames <= 0) {
      errors.push(`scenes[${idx}] ('${s.scene_id}'): durationFrames must be >= 1`);
    }

    if (s.transition && s.transition.durationFrames >= s.durationFrames) {
      errors.push(
        `scenes[${idx}] ('${s.scene_id}'): transition durationFrames (${s.transition.durationFrames}) must be strictly less than scene durationFrames (${s.durationFrames})`
      );
    }

  }

  // 3. Audio Plan Volume Checks
  if (bp.audio) {
    if (bp.audio.voiceover) {
      const vo = bp.audio.voiceover;
      if (vo.volume < 0.0 || vo.volume > 1.0) {
        errors.push(`audio.voiceover: volume must be between 0.0 and 1.0`);
      }
    }

    if (bp.audio.music) {
      const bgm = bp.audio.music;
      if (bgm.volume < 0.0 || bgm.volume > 1.0) {
        errors.push(`audio.music: volume must be between 0.0 and 1.0`);
      }
      if (bgm.ducking && (bgm.ducking.ducking_volume < 0.0 || bgm.ducking.ducking_volume > 1.0)) {
        errors.push(`audio.music.ducking: ducking_volume must be between 0.0 and 1.0`);
      }
    }

    for (let sIdx = 0; sIdx < bp.audio.global_sfx.length; sIdx++) {
      const sfx = bp.audio.global_sfx[sIdx];
      if (sfx.volume < 0.0 || sfx.volume > 1.0) {
        errors.push(`audio.global_sfx[${sIdx}]: volume must be between 0.0 and 1.0`);
      }
    }
  }

  // 4. Authoritative Declarative Manifest Reference Checks (ASSET-005)
  if (options?.manifest) {
    const occurrences = collectAssetReferences(bp);
    for (const occ of occurrences) {
      if (occ.parsed.isLogical && occ.parsed.assetId) {
        const aid = occ.parsed.assetId;
        const kind = manifestAssets.get(aid);
        if (!kind) {
          if (occ.sceneId) {
            const sIdx = bp.scenes.findIndex(s => s.scene_id === occ.sceneId);
            const slotName = occ.slot.includes(".") ? occ.slot.split(".").slice(1).join(".") : occ.slot;
            errors.push(`scenes[${sIdx}] ('${occ.sceneId}'): referenced ${slotName} '${aid}' not found in manifest`);
          } else {
            const trackName = occ.fieldPath.split(".")[1] || occ.slot;
            errors.push(`audio.${trackName}: referenced asset '${aid}' not found in manifest`);
          }
        } else if (occ.expectedKinds && occ.expectedKinds.length > 0) {
          const isMatch = occ.expectedKinds.includes(kind) || occ.expectedKinds.includes(String(kind).toLowerCase());
          if (!isMatch) {
            const expectedStr = occ.expectedKinds.map(k => `'${k}'`).join(" or ");
            if (occ.sceneId) {
              const sIdx = bp.scenes.findIndex(s => s.scene_id === occ.sceneId);
              const slotName = occ.slot.includes(".") ? occ.slot.split(".").slice(1).join(".") : occ.slot;
              errors.push(`scenes[${sIdx}] ('${occ.sceneId}'): ${slotName} '${aid}' has kind '${kind}', expected ${expectedStr}`);
            } else {
              const trackName = occ.fieldPath.split(".")[1] || occ.slot;
              errors.push(`audio.${trackName}: asset '${aid}' has kind '${kind}', expected ${expectedStr}`);
            }
          }
        }
      }
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return { ok: true, errors: [], blueprint: bp };
}

// ==========================================
// 10. Centralized Migration & Compatibility Adapters
// ==========================================

export const SUPPORTED_V2_VERSIONS = ["2.0.0", "2.0"] as const;
export const SUPPORTED_LEGACY_VERSIONS = ["1.0", "1", 1] as const;

export function isLegacyBlueprintV1(raw: unknown): boolean {
  if (!raw || typeof raw !== "object") return false;
  const d = raw as Record<string, any>;
  if (d.blueprint_version === "2.0.0" || d.blueprint_version === "2.0") {
    return false;
  }
  const v = d.version;
  return v === "1.0" || v === "1" || v === 1 || (Array.isArray(d.scenes) && d.blueprint_version === undefined);
}

export function migrateBlueprintToV2(raw: unknown, expectedProjectId?: string): any {
  if (!raw || typeof raw !== "object") {
    throw new Error("Blueprint payload must be an object");
  }
  const data = JSON.parse(JSON.stringify(raw)) as Record<string, any>;

  if (data.blueprint_version === "2.0.0" || data.blueprint_version === "2.0") {
    return data;
  }

  // Version check
  const v = data.version;
  if (v !== undefined && v !== "1.0" && v !== "1" && v !== 1) {
    throw new Error(`Unsupported blueprint version: ${v}. Supported versions: 2.0.0, 2.0, 1.0`);
  }

  if (!data.project_id && expectedProjectId) {
    data.project_id = expectedProjectId;
  }

  const meta = (typeof data.meta === "object" && data.meta !== null) ? data.meta : {};
  if (data.fps === undefined || data.fps === null) {
    data.fps = meta.fps ?? 30;
  }
  if (!data.aspect_ratio) {
    data.aspect_ratio = meta.aspect_ratio ?? "16:9";
  }

  // Clean meta
  delete meta.fps;
  delete meta.aspect_ratio;
  delete meta.duration_sec;
  delete meta.approval;
  delete meta.project_id;
  data.meta = meta;

  // Audio migration
  const legacyAudio = (typeof data.audio === "object" && data.audio !== null) ? data.audio : {};
  const canonicalAudio: Record<string, any> = {};

  const voRef = data.voiceover ?? legacyAudio.voiceover_ref ?? legacyAudio.voiceover;
  if (voRef) {
    if (typeof voRef === "string") {
      canonicalAudio.voiceover = { asset_ref: voRef, volume: 1.0, startFrame: 0 };
    } else if (typeof voRef === "object" && voRef.asset_ref) {
      canonicalAudio.voiceover = voRef;
    }
  }

  const musicRef = data.bgm ?? legacyAudio.music_ref ?? legacyAudio.bgm;
  if (musicRef) {
    const musicVol = data.bgmVolume ?? legacyAudio.bgmVolume ?? legacyAudio.volume ?? 0.15;
    const duckingConf = legacyAudio.music_ducking_db
      ? { enabled: true, ducking_volume: 0.05, duck_under: ["voiceover"] }
      : legacyAudio.ducking;

    if (typeof musicRef === "string") {
      canonicalAudio.music = {
        asset_ref: musicRef,
        volume: Number(musicVol),
        startFrame: 0,
        loop: true,
        ...(duckingConf ? { ducking: duckingConf } : {}),
      };
    } else if (typeof musicRef === "object" && musicRef.asset_ref) {
      canonicalAudio.music = musicRef;
    }
  }

  if (Array.isArray(legacyAudio.global_sfx)) {
    canonicalAudio.global_sfx = legacyAudio.global_sfx;
  }

  delete data.voiceover;
  delete data.bgm;
  delete data.bgmVolume;
  if (Object.keys(canonicalAudio).length > 0) {
    data.audio = canonicalAudio;
  } else {
    delete data.audio;
  }

  // Scenes migration
  if (Array.isArray(data.scenes)) {
    data.scenes = data.scenes.map((s: any) => {
      if (!s || typeof s !== "object") return s;
      const sc = { ...s };
      if (typeof sc.transition === "string") {
        sc.transition = { type: sc.transition, durationFrames: 15 };
      }
      if (!sc.template_props && sc.props) {
        sc.template_props = sc.props;
      }
      return sc;
    });
  }

  // Manifest v2 is the sole authority for asset catalog; drop duplicate assets from Blueprint
  delete data.assets;

  data.blueprint_version = "2.0.0";
  delete data.version;

  return data;
}

