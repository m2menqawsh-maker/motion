import { z } from "zod";

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
  // Additional runtime props
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
  images: z.array(z.string()).optional(),
  screen: z.string().optional(),
  numbers: z.array(z.number()).optional(),
  range: z.object({ from: z.number(), to: z.number() }).optional(),
  path: z.string().optional(),
  icons: z.array(z.string()).optional(),
  audioRef: z.string().optional(),
  spectrum: z.array(z.array(z.number())).optional(),
});
export type SceneContent = z.infer<typeof SceneContentSchema>;

// ==========================================
// 4. V2 specific layout overrides
// ==========================================

export const LayoutSchema = z.object({
  layer: z.number().min(1).max(5).optional(),
  coverage_pct: z.number().min(0).max(100).optional(),
});

// ==========================================
// 5. Scene & Project (V1 + V2 Unified)
// ==========================================

export const BlueprintSceneSchema = z.object({
  scene_id: z.string(),
  template: z.string(),
  startFrame: z.number().min(0),
  durationFrames: z.number().min(1),
  props: z.record(z.string(), z.any()).optional(),
  // Logical Asset IDs (e.g., 'bg_music_1', 'scene_1_video') to be resolved by materialize_project.py -> media_map.json
  media_refs: z.array(z.string()).optional(),
  sfx_ref: z.string().nullable().optional(),
  captions_ref: z.string().nullable().optional(),
  content: SceneContentSchema.optional(),
  layout: LayoutSchema.optional(), // Integrated from V2 timeline
  effects: z.array(z.any()).optional(),
  template_props: z.record(z.string(), z.any()).optional(),
});
export type BlueprintScene = z.infer<typeof BlueprintSceneSchema>;

export const AssetSchema = z.object({
  asset_id: z.string(),
  type: z.enum(["image", "video", "audio", "font", "json"]),
  source: z.enum(["user_upload", "cache", "mcp_fetch", "generated"]),
  path: z.string().optional(),
  fallback: z.string().optional(),
  paid: z.boolean().optional(),
});
export type Asset = z.infer<typeof AssetSchema>;

export const MetaSchema = z.object({
  motion_personality: z.enum(["Cinematic", "Energetic", "Playful", "Technical"]).optional(),
  approval: z.object({
    blueprint_approved: z.boolean().optional()
  }).optional(),
  timings_path: z.string().optional(),
});

export const BlueprintSchema = z.object({
  project_id: z.string(),
  version: z.string(),
  fps: z.number().min(1).max(120),
  aspect_ratio: z.enum(["9:16", "16:9", "1:1"]),
  meta: MetaSchema.optional(),
  assets: z.array(AssetSchema).optional(),
  scenes: z.array(BlueprintSceneSchema),
});
export type Blueprint = z.infer<typeof BlueprintSchema>;
