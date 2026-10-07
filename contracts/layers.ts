/**
 * contracts/layers.ts — Canonical Layer Model, Hierarchy & Spatial Coordinates.
 * S28-R03: Formal spatial specifications, layer taxonomy, group graphs, and transform math.
 * ZERO React, Remotion, Canvas or DOM dependencies.
 */
import { z } from "zod";
import { StableIdSchema, TimeRangeSchema, type TimeRange } from "./timeline";
import { AssetRefSchema, type AssetRef } from "./asset-resolver";
import { AnimationChannelSchema, type AnimationChannel } from "./keyframes";

// ────────────────────────────────────────────────────────────────────────────
// 1. Spatial Coordinates & Transform Model
// ────────────────────────────────────────────────────────────────────────────

export const CoordinateSpaceSchema = z.enum(["PIXELS", "NORMALIZED"]);
export type CoordinateSpace = z.infer<typeof CoordinateSpaceSchema>;

export const CanvasDimensionsSchema = z.object({
  width: z.number().int().positive("Canvas width must be positive integer"),
  height: z.number().int().positive("Canvas height must be positive integer"),
});
export type CanvasDimensions = z.infer<typeof CanvasDimensionsSchema>;

export const TransformSchema = z.object({
  position: z
    .object({
      x: z.number().default(0),
      y: z.number().default(0),
    })
    .default({ x: 0, y: 0 }),
  scale: z
    .object({
      x: z.number().default(1),
      y: z.number().default(1),
    })
    .default({ x: 1, y: 1 }),
  rotation: z.number().default(0), // clockwise in degrees
  anchor: z
    .object({
      x: z.number().default(0.5),
      y: z.number().default(0.5),
    })
    .default({ x: 0.5, y: 0.5 }),
  opacity: z.number().min(0).max(1).default(1),
});
export type Transform = z.infer<typeof TransformSchema>;

export function defaultTransform(): Transform {
  return {
    position: { x: 0, y: 0 },
    scale: { x: 1, y: 1 },
    rotation: 0,
    anchor: { x: 0.5, y: 0.5 },
    opacity: 1,
  };
}

/**
 * Deterministic composition of parent and child transforms.
 */
export function composeTransform(parent: Transform, child: Transform): Transform {
  const rad = (parent.rotation * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);

  const scaledChildX = child.position.x * parent.scale.x;
  const scaledChildY = child.position.y * parent.scale.y;

  const rotatedX = scaledChildX * cos - scaledChildY * sin;
  const rotatedY = scaledChildX * sin + scaledChildY * cos;

  return {
    position: {
      x: parent.position.x + rotatedX,
      y: parent.position.y + rotatedY,
    },
    scale: {
      x: parent.scale.x * child.scale.x,
      y: parent.scale.y * child.scale.y,
    },
    rotation: parent.rotation + child.rotation,
    anchor: { ...child.anchor },
    opacity: Math.max(0, Math.min(1, parent.opacity * child.opacity)),
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Canonical Typography Contract
// ────────────────────────────────────────────────────────────────────────────

export const CanonicalTypographySchema = z.object({
  fontFamily: z.string().min(1),
  fontSize: z.number().positive("fontSize must be positive"),
  fontWeight: z.union([z.number(), z.string()]).optional(),
  fontStyle: z.enum(["normal", "italic"]).optional(),
  letterSpacing: z.string().optional(),
  lineHeight: z.number().positive().optional(),
  textAlign: z.enum(["left", "center", "right", "justify"]).optional(),
  fillColor: z.string().optional(),
  strokeColor: z.string().optional(),
  strokeWidth: z.number().min(0).optional(),
});
export type CanonicalTypography = z.infer<typeof CanonicalTypographySchema>;

// ────────────────────────────────────────────────────────────────────────────
// 3. Layer Union Definitions
// ────────────────────────────────────────────────────────────────────────────

const BaseLayerProps = {
  layer_id: StableIdSchema,
  time_range: TimeRangeSchema,
  transform: TransformSchema.default(defaultTransform),
  opacity: z.number().min(0).max(1).default(1),
  parent_id: StableIdSchema.optional(),
  channels: z.array(AnimationChannelSchema).default([]),
  visible: z.boolean().default(true),
  z_index: z.number().int().default(0),
};

export const TextLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("text"),
  text: z.string(),
  typography: CanonicalTypographySchema,
});
export type TextLayer = z.infer<typeof TextLayerSchema>;

export const ImageLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("image"),
  asset_ref: AssetRefSchema,
  fit: z.enum(["contain", "cover", "fill", "none"]).default("contain"),
  crop: z
    .object({
      x: z.number().min(0),
      y: z.number().min(0),
      width: z.number().positive(),
      height: z.number().positive(),
    })
    .optional(),
});
export type ImageLayer = z.infer<typeof ImageLayerSchema>;

export const VideoLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("video"),
  asset_ref: AssetRefSchema,
  fit: z.enum(["contain", "cover", "fill", "none"]).default("contain"),
  playback_rate: z.number().positive().default(1.0),
  volume: z.number().min(0).max(1).default(1.0),
  muted: z.boolean().default(false),
  source_range: z
    .object({
      startFrame: z.number().int().min(0),
      durationFrames: z.number().int().min(1),
    })
    .optional(),
});
export type VideoLayer = z.infer<typeof VideoLayerSchema>;

export const AudioLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("audio"),
  asset_ref: AssetRefSchema,
  volume: z.number().min(0).max(1).default(1.0),
  muted: z.boolean().default(false),
  source_range: z
    .object({
      startFrame: z.number().int().min(0),
      durationFrames: z.number().int().min(1),
    })
    .optional(),
});
export type AudioLayer = z.infer<typeof AudioLayerSchema>;

export const ShapeLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("shape"),
  shape_type: z.enum(["rectangle", "ellipse", "path"]),
  size: z.object({
    width: z.number().positive(),
    height: z.number().positive(),
  }),
  fillColor: z.string().optional(),
  strokeColor: z.string().optional(),
  strokeWidth: z.number().min(0).optional(),
  borderRadius: z.number().min(0).optional(),
  pathData: z.string().optional(),
});
export type ShapeLayer = z.infer<typeof ShapeLayerSchema>;

export const GroupLayerSchema = z.object({
  ...BaseLayerProps,
  kind: z.literal("group"),
  children_ids: z.array(StableIdSchema).default([]),
});
export type GroupLayer = z.infer<typeof GroupLayerSchema>;

export const CanonicalLayerSchema = z.discriminatedUnion("kind", [
  TextLayerSchema,
  ImageLayerSchema,
  VideoLayerSchema,
  AudioLayerSchema,
  ShapeLayerSchema,
  GroupLayerSchema,
]);
export type CanonicalLayer = z.infer<typeof CanonicalLayerSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 4. Hierarchy Safety & Validation
// ────────────────────────────────────────────────────────────────────────────

export function validateLayerHierarchy(layers: CanonicalLayer[]): { ok: boolean; errors: string[] } {
  const errors: string[] = [];
  const layerMap = new Map<string, CanonicalLayer>();

  // 1. Check ID uniqueness
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    if (layerMap.has(layer.layer_id)) {
      errors.push(`layers[${i}]: duplicate layer_id '${layer.layer_id}'`);
    }
    layerMap.set(layer.layer_id, layer);
  }

  // 2. Parent checks & Cycle detection
  for (const layer of layers) {
    if (layer.parent_id) {
      if (layer.parent_id === layer.layer_id) {
        errors.push(`layer '${layer.layer_id}': cannot be its own parent (self-parenting)`);
      } else if (!layerMap.has(layer.parent_id)) {
        errors.push(`layer '${layer.layer_id}': references non-existent parent_id '${layer.parent_id}'`);
      }
    }
  }

  // Detect cycles using visited path
  for (const layer of layers) {
    const visited = new Set<string>();
    let current: CanonicalLayer | undefined = layer;

    while (current && current.parent_id) {
      if (visited.has(current.layer_id)) {
        errors.push(`layer hierarchy contains cycle involving '${current.layer_id}'`);
        break;
      }
      visited.add(current.layer_id);
      current = layerMap.get(current.parent_id);
    }
  }

  return { ok: errors.length === 0, errors };
}

export function sortLayersByZIndex(layers: CanonicalLayer[]): CanonicalLayer[] {
  return [...layers].sort((a, b) => a.z_index - b.z_index);
}
