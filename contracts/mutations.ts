/**
 * contracts/mutations.ts — Canonical Mutation Core, Discriminated Union & Pure Engine.
 * S28-R04: Authoritative mutation engine for BlueprintV2.
 * Enforces:
 *   - Typed domain mutations (no arbitrary JSON patches)
 *   - Optimistic concurrency (expected_revision)
 *   - Idempotency tracking (mutation_id)
 *   - Fail-closed atomic batches
 *   - Structured MutationError returns (no silent overwrite or silent repair)
 *   - Invalidation ChangeSet metadata
 * ZERO React, Remotion, Canvas, DOM, filesystem, network or database dependencies.
 * ZERO wall-clock dependencies, random generators, or any-types.
 */
import { z } from "zod";
import {
  type BlueprintV2,
  BlueprintV2Schema,
  type BlueprintScene,
  BlueprintSceneSchema,
  validateBlueprintV2,
  type TransitionRef,
  TransitionRefSchema,
  type VoiceoverTrack,
  VoiceoverTrackSchema,
  type MusicTrack,
  MusicTrackSchema,
  type GlobalSfxTrack,
  GlobalSfxTrackSchema,
  StyleSurfaceSchema,
} from "./blueprint";
import { AssetRefSchema, type AssetRef } from "./asset-resolver";
import {
  StableIdSchema,
  FrameNumberSchema,
  FrameDurationSchema,
  createTimeRange,
  isStableId,
} from "./timeline";
import {
  type CanonicalLayer,
  CanonicalLayerSchema,
  type Transform,
  type CanonicalTypography,
  CanonicalTypographySchema,
  validateLayerHierarchy,
  defaultTransform,
} from "./layers";
import {
  type Keyframe,
  KeyframeSchema,
  type ChannelTarget,
  ChannelTargetSchema,
  InterpolationTypeSchema,
  EasingTypeSchema,
  SpringConfigSchema,
  validateKeyframes,
} from "./keyframes";

// ────────────────────────────────────────────────────────────────────────────
// 1. Structured Mutation Error Model
// ────────────────────────────────────────────────────────────────────────────

export const MutationErrorCodeSchema = z.enum([
  "REVISION_CONFLICT",
  "INVALID_MUTATION",
  "SCENE_NOT_FOUND",
  "LAYER_NOT_FOUND",
  "CLIP_NOT_FOUND",
  "KEYFRAME_NOT_FOUND",
  "CHANNEL_NOT_FOUND",
  "DUPLICATE_ID",
  "HIERARCHY_CYCLE",
  "DANGLING_PARENT_REFERENCE",
  "MINIMUM_SCENES_VIOLATION",
  "INVALID_SPLIT_POINT",
  "VALIDATION_FAILED",
  "UNKNOWN_MUTATION_TYPE",
  "BATCH_EXECUTION_FAILED",
]);
export type MutationErrorCode = z.infer<typeof MutationErrorCodeSchema>;

export interface MutationError {
  code: MutationErrorCode;
  message: string;
  mutation_id?: string;
  expected_revision?: number;
  actual_revision?: number;
  target_id?: string;
  details?: Record<string, unknown>;
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Invalidation & ChangeSet Metadata
// ────────────────────────────────────────────────────────────────────────────

export interface InvalidationMetadata {
  requires_layout: boolean;
  requires_render: boolean;
  requires_audio_remix: boolean;
  requires_timeline_rebuild: boolean;
}

export interface ChangeSet {
  affected_scene_ids: string[];
  affected_layer_ids: string[];
  affected_track_ids: string[];
  affected_clip_ids: string[];
  affected_keyframe_ids: string[];
  time_range?: {
    startFrame: number;
    endFrame: number;
  };
  invalidation: InvalidationMetadata;
  mutations_count: number;
}

export function emptyChangeSet(): ChangeSet {
  return {
    affected_scene_ids: [],
    affected_layer_ids: [],
    affected_track_ids: [],
    affected_clip_ids: [],
    affected_keyframe_ids: [],
    invalidation: {
      requires_layout: false,
      requires_render: false,
      requires_audio_remix: false,
      requires_timeline_rebuild: false,
    },
    mutations_count: 0,
  };
}

export function combineChangeSets(sets: ChangeSet[]): ChangeSet {
  const sceneIds = new Set<string>();
  const layerIds = new Set<string>();
  const trackIds = new Set<string>();
  const clipIds = new Set<string>();
  const keyframeIds = new Set<string>();

  let minStart = Infinity;
  let maxEnd = -Infinity;
  let hasTimeRange = false;

  const inv: InvalidationMetadata = {
    requires_layout: false,
    requires_render: false,
    requires_audio_remix: false,
    requires_timeline_rebuild: false,
  };

  let totalCount = 0;

  for (const s of sets) {
    for (const id of s.affected_scene_ids) sceneIds.add(id);
    for (const id of s.affected_layer_ids) layerIds.add(id);
    for (const id of s.affected_track_ids) trackIds.add(id);
    for (const id of s.affected_clip_ids) clipIds.add(id);
    for (const id of s.affected_keyframe_ids) keyframeIds.add(id);

    if (s.time_range) {
      hasTimeRange = true;
      if (s.time_range.startFrame < minStart) minStart = s.time_range.startFrame;
      if (s.time_range.endFrame > maxEnd) maxEnd = s.time_range.endFrame;
    }

    if (s.invalidation.requires_layout) inv.requires_layout = true;
    if (s.invalidation.requires_render) inv.requires_render = true;
    if (s.invalidation.requires_audio_remix) inv.requires_audio_remix = true;
    if (s.invalidation.requires_timeline_rebuild) inv.requires_timeline_rebuild = true;

    totalCount += s.mutations_count;
  }

  return {
    affected_scene_ids: Array.from(sceneIds),
    affected_layer_ids: Array.from(layerIds),
    affected_track_ids: Array.from(trackIds),
    affected_clip_ids: Array.from(clipIds),
    affected_keyframe_ids: Array.from(keyframeIds),
    time_range: hasTimeRange ? { startFrame: minStart, endFrame: maxEnd } : undefined,
    invalidation: inv,
    mutations_count: totalCount,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Typed Mutation Taxonomy (Discriminated Union)
// ────────────────────────────────────────────────────────────────────────────

const BaseMutationProps = {
  mutation_id: StableIdSchema,
  expected_revision: z.number().int().min(0).optional(),
  author: z.enum(["user", "ai", "system"]).default("user"),
  description: z.string().optional(),
};

// 3.1 Text & Transform
export const UpdateTextMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_TEXT"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
  }),
  payload: z.object({
    text: z.string(),
    typography: CanonicalTypographySchema.partial().optional(),
  }),
});
export type UpdateTextMutation = z.infer<typeof UpdateTextMutationSchema>;

export const UpdateTransformMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_TRANSFORM"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
  }),
  payload: z.object({
    transform: z.object({
      position: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      scale: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      rotation: z.number().optional(),
      anchor: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      opacity: z.number().min(0).max(1).optional(),
    }),
  }),
});
export type UpdateTransformMutation = z.infer<typeof UpdateTransformMutationSchema>;

export const UpdateStyleMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_STYLE"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
  }),
  payload: z.object({
    backgroundColor: z.string().optional(),
    color: z.string().optional(),
    surface: StyleSurfaceSchema.partial().optional(),
    shape: z
      .object({
        fillColor: z.string().optional(),
        strokeColor: z.string().optional(),
        strokeWidth: z.number().optional(),
      })
      .optional(),
  }),
});
export type UpdateStyleMutation = z.infer<typeof UpdateStyleMutationSchema>;

export const ReplaceMediaMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REPLACE_MEDIA"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
  }),
  payload: z.object({
    asset_ref: AssetRefSchema,
  }),
});
export type ReplaceMediaMutation = z.infer<typeof ReplaceMediaMutationSchema>;

// 3.2 Layer Operations
export const AddLayerMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("ADD_LAYER"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    layer: CanonicalLayerSchema,
    placement: z
      .object({
        relative_to: StableIdSchema.optional(),
        position: z.enum(["before", "after", "top", "bottom"]).default("top"),
      })
      .optional(),
  }),
});
export type AddLayerMutation = z.infer<typeof AddLayerMutationSchema>;

export const RemoveLayerMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REMOVE_LAYER"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
  }),
  payload: z
    .object({
      cascade: z.boolean().default(false),
    })
    .optional(),
});
export type RemoveLayerMutation = z.infer<typeof RemoveLayerMutationSchema>;

export const DuplicateLayerMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("DUPLICATE_LAYER"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
  }),
  payload: z.object({
    new_layer_id: StableIdSchema,
    offset: z
      .object({
        x: z.number().default(0),
        y: z.number().default(0),
      })
      .optional(),
  }),
});
export type DuplicateLayerMutation = z.infer<typeof DuplicateLayerMutationSchema>;

export const ReorderLayerMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REORDER_LAYER"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
  }),
  payload: z.object({
    relative_to: StableIdSchema.optional(),
    position: z.enum(["before", "after"]).optional(),
    new_z_index: z.number().int().optional(),
  }),
});
export type ReorderLayerMutation = z.infer<typeof ReorderLayerMutationSchema>;

// 3.3 Clip Operations
export const MoveClipMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("MOVE_CLIP"),
  target: z
    .object({
      clip_id: StableIdSchema.optional(),
      scene_id: StableIdSchema.optional(),
      layer_id: StableIdSchema.optional(),
      track_id: StableIdSchema.optional(),
    })
    .refine((t) => t.clip_id || t.scene_id || t.layer_id, {
      message: "Target must specify at least one of clip_id, scene_id, or layer_id",
    }),
  payload: z.object({
    new_start_frame: FrameNumberSchema,
  }),
});
export type MoveClipMutation = z.infer<typeof MoveClipMutationSchema>;

export const TrimClipMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("TRIM_CLIP"),
  target: z
    .object({
      clip_id: StableIdSchema.optional(),
      scene_id: StableIdSchema.optional(),
      layer_id: StableIdSchema.optional(),
    })
    .refine((t) => t.clip_id || t.scene_id || t.layer_id, {
      message: "Target must specify at least one of clip_id, scene_id, or layer_id",
    }),
  payload: z.object({
    start_trim_frames: z.number().int().optional(),
    end_trim_frames: z.number().int().optional(),
    new_duration_frames: FrameDurationSchema.optional(),
  }),
});
export type TrimClipMutation = z.infer<typeof TrimClipMutationSchema>;

export const SplitClipMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("SPLIT_CLIP"),
  target: z
    .object({
      clip_id: StableIdSchema.optional(),
      scene_id: StableIdSchema.optional(),
      layer_id: StableIdSchema.optional(),
    })
    .refine((t) => t.clip_id || t.scene_id || t.layer_id, {
      message: "Target must specify at least one of clip_id, scene_id, or layer_id",
    }),
  payload: z.object({
    split_frame: FrameNumberSchema,
    new_clip_id: StableIdSchema.optional(),
    new_scene_id: StableIdSchema.optional(),
    new_layer_id: StableIdSchema.optional(),
  }),
});
export type SplitClipMutation = z.infer<typeof SplitClipMutationSchema>;

// 3.4 Keyframe Operations
export const SetKeyframeMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("SET_KEYFRAME"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
    channel_id: StableIdSchema.optional(),
    channel_target: ChannelTargetSchema.optional(),
  }),
  payload: z.object({
    keyframe: KeyframeSchema,
  }),
});
export type SetKeyframeMutation = z.infer<typeof SetKeyframeMutationSchema>;

export const UpdateKeyframeMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_KEYFRAME"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
    keyframe_id: StableIdSchema,
  }),
  payload: z.object({
    patch: z.object({
      frame: FrameNumberSchema.optional(),
      value: z.number().optional(),
      interpolation: InterpolationTypeSchema.optional(),
      easing: EasingTypeSchema.optional(),
      bezier: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(),
      spring: SpringConfigSchema.optional(),
    }),
  }),
});
export type UpdateKeyframeMutation = z.infer<typeof UpdateKeyframeMutationSchema>;

export const RemoveKeyframeMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REMOVE_KEYFRAME"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema,
    keyframe_id: StableIdSchema,
  }),
  payload: z.object({}).optional(),
});
export type RemoveKeyframeMutation = z.infer<typeof RemoveKeyframeMutationSchema>;

// 3.5 Transitions
export const SetTransitionMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("SET_TRANSITION"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    transition: TransitionRefSchema,
  }),
});
export type SetTransitionMutation = z.infer<typeof SetTransitionMutationSchema>;

export const RemoveTransitionMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REMOVE_TRANSITION"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({}).optional(),
});
export type RemoveTransitionMutation = z.infer<typeof RemoveTransitionMutationSchema>;

// 3.6 Scene Operations
export const AddSceneMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("ADD_SCENE"),
  payload: z.object({
    scene: BlueprintSceneSchema,
    placement: z
      .object({
        relative_to: StableIdSchema.optional(),
        position: z.enum(["before", "after", "start", "end"]).default("end"),
      })
      .optional(),
  }),
});
export type AddSceneMutation = z.infer<typeof AddSceneMutationSchema>;

export const RemoveSceneMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REMOVE_SCENE"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({}).optional(),
});
export type RemoveSceneMutation = z.infer<typeof RemoveSceneMutationSchema>;

export const DuplicateSceneMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("DUPLICATE_SCENE"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    new_scene_id: StableIdSchema,
    new_layer_ids_map: z.record(z.string(), z.string()).optional(),
    start_frame_offset: z.number().int().optional(),
  }),
});
export type DuplicateSceneMutation = z.infer<typeof DuplicateSceneMutationSchema>;

export const ReorderSceneMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("REORDER_SCENE"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    relative_to: StableIdSchema,
    position: z.enum(["before", "after"]),
  }),
});
export type ReorderSceneMutation = z.infer<typeof ReorderSceneMutationSchema>;

// 3.7 Project & Audio
export const UpdateProjectMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_PROJECT"),
  payload: z.object({
    fps: z.number().int().min(1).max(120).optional(),
    aspect_ratio: z.enum(["9:16", "16:9", "1:1", "4:5", "21:9"]).optional(),
    meta: z.record(z.string(), z.unknown()).optional(),
  }),
});
export type UpdateProjectMutation = z.infer<typeof UpdateProjectMutationSchema>;

export const UpdateAudioMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("UPDATE_AUDIO"),
  payload: z.object({
    voiceover: VoiceoverTrackSchema.partial().optional(),
    music: MusicTrackSchema.partial().optional(),
    global_sfx: z.array(GlobalSfxTrackSchema).optional(),
  }),
});
export type UpdateAudioMutation = z.infer<typeof UpdateAudioMutationSchema>;

export const SetAudioLevelMutationSchema = z.object({
  ...BaseMutationProps,
  type: z.literal("SET_AUDIO_LEVEL"),
  payload: z.object({
    track: z.enum(["voiceover", "music", "sfx", "layer"]),
    track_id: z.string().optional(),
    volume: z.number().min(0.0).max(1.0).optional(),
    mute: z.boolean().optional(),
  }),
});
export type SetAudioLevelMutation = z.infer<typeof SetAudioLevelMutationSchema>;

// 3.8 Discriminated Union
export const CanonicalMutationSchema = z.discriminatedUnion("type", [
  UpdateTextMutationSchema,
  UpdateTransformMutationSchema,
  UpdateStyleMutationSchema,
  ReplaceMediaMutationSchema,
  AddLayerMutationSchema,
  RemoveLayerMutationSchema,
  DuplicateLayerMutationSchema,
  ReorderLayerMutationSchema,
  MoveClipMutationSchema,
  TrimClipMutationSchema,
  SplitClipMutationSchema,
  SetKeyframeMutationSchema,
  UpdateKeyframeMutationSchema,
  RemoveKeyframeMutationSchema,
  SetTransitionMutationSchema,
  RemoveTransitionMutationSchema,
  AddSceneMutationSchema,
  RemoveSceneMutationSchema,
  DuplicateSceneMutationSchema,
  ReorderSceneMutationSchema,
  UpdateProjectMutationSchema,
  UpdateAudioMutationSchema,
  SetAudioLevelMutationSchema,
]);
export type CanonicalMutation = z.infer<typeof CanonicalMutationSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 4. Mutation Batch & Result Schemas
// ────────────────────────────────────────────────────────────────────────────

export const MutationBatchSchema = z.object({
  batch_id: StableIdSchema,
  mutations: z.array(CanonicalMutationSchema).min(1, "Mutation batch must contain at least one mutation"),
  expected_revision: z.number().int().min(0).optional(),
  author: z.enum(["user", "ai", "system"]).default("user"),
  description: z.string().optional(),
});
export type MutationBatch = z.infer<typeof MutationBatchSchema>;

export interface MutationResult {
  success: boolean;
  revision: number;
  blueprint: BlueprintV2;
  applied_mutation_ids: string[];
  changeset: ChangeSet;
  idempotent?: boolean;
  error?: MutationError;
}

// ────────────────────────────────────────────────────────────────────────────
// 5. Pure Internal Helpers
// ────────────────────────────────────────────────────────────────────────────

function cloneBlueprint<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj)) as T;
}

interface StepResult {
  ok: boolean;
  changeset: ChangeSet;
  error?: MutationError;
}

function findScene(scenes: BlueprintScene[], sceneId: string): { scene: BlueprintScene; index: number } | null {
  for (let i = 0; i < scenes.length; i++) {
    if (scenes[i].scene_id === sceneId) {
      return { scene: scenes[i], index: i };
    }
  }
  return null;
}

function findLayer(scene: BlueprintScene, layerId: string): { layer: CanonicalLayer; index: number } | null {
  if (!scene.layers) return null;
  for (let i = 0; i < scene.layers.length; i++) {
    if (scene.layers[i].layer_id === layerId) {
      return { layer: scene.layers[i], index: i };
    }
  }
  return null;
}

// ────────────────────────────────────────────────────────────────────────────
// 6. Pure Domain Mutation Step Executor
// ────────────────────────────────────────────────────────────────────────────

function applyMutationStep(draft: BlueprintV2, mutation: CanonicalMutation): StepResult {
  switch (mutation.type) {
    case "UPDATE_TEXT": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;

      if (targetLayerId) {
        const layerFound = findLayer(scene, targetLayerId);
        if (!layerFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "LAYER_NOT_FOUND",
              message: `Target layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
              mutation_id: mutation.mutation_id,
              target_id: targetLayerId,
            },
          };
        }
        const layer = layerFound.layer;
        if (layer.kind !== "text") {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "INVALID_MUTATION",
              message: `Layer '${targetLayerId}' is kind '${layer.kind}', expected 'text'`,
              mutation_id: mutation.mutation_id,
              target_id: targetLayerId,
            },
          };
        }
        layer.text = mutation.payload.text;
        if (mutation.payload.typography) {
          layer.typography = {
            ...layer.typography,
            ...mutation.payload.typography,
          };
        }
        if (scene.surface) {
          scene.surface = { ...scene.surface, text: mutation.payload.text };
        }
      } else {
        // Scene level text update
        scene.surface = { ...(scene.surface || {}), text: mutation.payload.text };
        if (scene.layers) {
          for (const l of scene.layers) {
            if (l.kind === "text") {
              l.text = mutation.payload.text;
              if (mutation.payload.typography) {
                l.typography = { ...l.typography, ...mutation.payload.typography };
              }
            }
          }
        }
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: targetLayerId ? [targetLayerId] : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "UPDATE_TRANSFORM": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;

      if (targetLayerId) {
        const layerFound = findLayer(scene, targetLayerId);
        if (!layerFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "LAYER_NOT_FOUND",
              message: `Target layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
              mutation_id: mutation.mutation_id,
              target_id: targetLayerId,
            },
          };
        }
        const layer = layerFound.layer;
        const pt = mutation.payload.transform;
        layer.transform = {
          position: {
            x: pt.position?.x !== undefined ? pt.position.x : layer.transform.position.x,
            y: pt.position?.y !== undefined ? pt.position.y : layer.transform.position.y,
          },
          scale: {
            x: pt.scale?.x !== undefined ? pt.scale.x : layer.transform.scale.x,
            y: pt.scale?.y !== undefined ? pt.scale.y : layer.transform.scale.y,
          },
          rotation: pt.rotation !== undefined ? pt.rotation : layer.transform.rotation,
          anchor: {
            x: pt.anchor?.x !== undefined ? pt.anchor.x : layer.transform.anchor.x,
            y: pt.anchor?.y !== undefined ? pt.anchor.y : layer.transform.anchor.y,
          },
          opacity: pt.opacity !== undefined ? pt.opacity : layer.transform.opacity,
        };
      } else {
        const pt = mutation.payload.transform;
        const currentSurface = scene.surface || {};
        scene.surface = {
          ...currentSurface,
          position: {
            anchor: "center",
            x: pt.position?.x,
            y: pt.position?.y,
          },
          scale: pt.scale?.x,
          rotation: pt.rotation,
          opacity: pt.opacity,
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: targetLayerId ? [targetLayerId] : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "ADD_LAYER": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const newLayer = mutation.payload.layer;

      // Check ID uniqueness across all scenes
      for (const s of draft.scenes) {
        if (s.layers) {
          for (const l of s.layers) {
            if (l.layer_id === newLayer.layer_id) {
              return {
                ok: false,
                changeset: emptyChangeSet(),
                error: {
                  code: "DUPLICATE_ID",
                  message: `Layer with ID '${newLayer.layer_id}' already exists in scene '${s.scene_id}'`,
                  mutation_id: mutation.mutation_id,
                  target_id: newLayer.layer_id,
                },
              };
            }
          }
        }
      }

      if (!scene.layers) {
        scene.layers = [];
      }

      const placement = mutation.payload.placement;
      if (placement?.relative_to) {
        const refIdx = scene.layers.findIndex((l) => l.layer_id === placement.relative_to);
        if (refIdx >= 0) {
          const insertIdx = placement.position === "before" ? refIdx : refIdx + 1;
          scene.layers.splice(insertIdx, 0, newLayer);
        } else {
          scene.layers.push(newLayer);
        }
      } else if (placement?.position === "bottom") {
        scene.layers.unshift(newLayer);
      } else {
        scene.layers.push(newLayer);
      }

      const hierarchyCheck = validateLayerHierarchy(scene.layers);
      if (!hierarchyCheck.ok) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "HIERARCHY_CYCLE",
            message: `Layer hierarchy validation failed: ${hierarchyCheck.errors.join("; ")}`,
            mutation_id: mutation.mutation_id,
            target_id: newLayer.layer_id,
          },
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [newLayer.layer_id],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: newLayer.time_range.startFrame,
            endFrame: newLayer.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: newLayer.kind === "audio",
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "REMOVE_LAYER": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      if (!scene.layers) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Scene '${scene.scene_id}' has no layers`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.layer_id,
          },
        };
      }

      const targetLayerId = mutation.target.layer_id;
      const targetIdx = scene.layers.findIndex((l) => l.layer_id === targetLayerId);
      if (targetIdx < 0) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      // Check if other layers are parented to this layer
      const childLayers = scene.layers.filter((l) => l.parent_id === targetLayerId);
      const cascade = mutation.payload?.cascade ?? false;
      if (childLayers.length > 0 && !cascade) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "DANGLING_PARENT_REFERENCE",
            message: `Cannot remove layer '${targetLayerId}': layer(s) [${childLayers.map((l) => l.layer_id).join(", ")}] have it as parent. Reparent or use cascade=true.`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const layersToRemove = new Set<string>([targetLayerId]);
      if (cascade) {
        function collectChildren(parentId: string) {
          for (const l of scene.layers!) {
            if (l.parent_id === parentId && !layersToRemove.has(l.layer_id)) {
              layersToRemove.add(l.layer_id);
              collectChildren(l.layer_id);
            }
          }
        }
        collectChildren(targetLayerId);
      }

      scene.layers = scene.layers.filter((l) => !layersToRemove.has(l.layer_id));

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: Array.from(layersToRemove),
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "DUPLICATE_LAYER": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const layerFound = findLayer(scene, targetLayerId);
      if (!layerFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const newId = mutation.payload.new_layer_id;
      // Check ID uniqueness
      for (const s of draft.scenes) {
        if (s.layers?.some((l) => l.layer_id === newId)) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "DUPLICATE_ID",
              message: `Layer ID '${newId}' already exists in scene '${s.scene_id}'`,
              mutation_id: mutation.mutation_id,
              target_id: newId,
            },
          };
        }
      }

      const sourceLayer = layerFound.layer;
      const duplicated: CanonicalLayer = cloneBlueprint(sourceLayer);
      duplicated.layer_id = newId;
      if (mutation.payload.offset) {
        duplicated.transform.position.x += mutation.payload.offset.x;
        duplicated.transform.position.y += mutation.payload.offset.y;
      }
      duplicated.z_index += 1;

      // Insert immediately after source
      scene.layers!.splice(layerFound.index + 1, 0, duplicated);

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [newId],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: duplicated.time_range.startFrame,
            endFrame: duplicated.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: duplicated.kind === "audio",
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "REORDER_LAYER": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const layerFound = findLayer(scene, targetLayerId);
      if (!layerFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const layer = layerFound.layer;
      if (mutation.payload.new_z_index !== undefined) {
        layer.z_index = mutation.payload.new_z_index;
      }

      if (mutation.payload.relative_to) {
        const refId = mutation.payload.relative_to;
        scene.layers!.splice(layerFound.index, 1);
        const refIdx = scene.layers!.findIndex((l) => l.layer_id === refId);
        if (refIdx >= 0) {
          const insertIdx = mutation.payload.position === "before" ? refIdx : refIdx + 1;
          scene.layers!.splice(insertIdx, 0, layer);
        } else {
          scene.layers!.push(layer);
        }
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [targetLayerId],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: layer.time_range.startFrame,
            endFrame: layer.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "MOVE_CLIP": {
      const { clip_id, scene_id, layer_id } = mutation.target;
      const newStart = mutation.payload.new_start_frame;

      // 1. Moving audio clip
      if (clip_id === "clip_voiceover" && draft.audio?.voiceover) {
        draft.audio.voiceover.startFrame = newStart;
        return {
          ok: true,
          changeset: {
            affected_scene_ids: [],
            affected_layer_ids: [],
            affected_track_ids: ["track_voiceover"],
            affected_clip_ids: ["clip_voiceover"],
            affected_keyframe_ids: [],
            time_range: { startFrame: newStart, endFrame: newStart + (draft.audio.voiceover.durationFrames || 100) },
            invalidation: {
              requires_layout: false,
              requires_render: false,
              requires_audio_remix: true,
              requires_timeline_rebuild: true,
            },
            mutations_count: 1,
          },
        };
      }

      if (clip_id === "clip_bgm" && draft.audio?.music) {
        draft.audio.music.startFrame = newStart;
        return {
          ok: true,
          changeset: {
            affected_scene_ids: [],
            affected_layer_ids: [],
            affected_track_ids: ["track_bgm"],
            affected_clip_ids: ["clip_bgm"],
            affected_keyframe_ids: [],
            time_range: { startFrame: newStart, endFrame: newStart + (draft.audio.music.durationFrames || 100) },
            invalidation: {
              requires_layout: false,
              requires_render: false,
              requires_audio_remix: true,
              requires_timeline_rebuild: true,
            },
            mutations_count: 1,
          },
        };
      }

      // 2. Targeting scene clip
      const resolvedSceneId = scene_id || (clip_id && clip_id.startsWith("clip_sc_") ? clip_id.replace("clip_sc_", "") : null);
      if (resolvedSceneId && !layer_id) {
        const sceneFound = findScene(draft.scenes, resolvedSceneId);
        if (!sceneFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "CLIP_NOT_FOUND",
              message: `Scene clip for scene '${resolvedSceneId}' not found`,
              mutation_id: mutation.mutation_id,
              target_id: clip_id || resolvedSceneId,
            },
          };
        }
        const scene = sceneFound.scene;
        const delta = newStart - scene.startFrame;
        scene.startFrame = newStart;

        // Shift layers by same delta to preserve internal relative timing
        if (scene.layers) {
          for (const l of scene.layers) {
            l.time_range = createTimeRange(l.time_range.startFrame + delta, l.time_range.durationFrames);
          }
        }

        return {
          ok: true,
          changeset: {
            affected_scene_ids: [scene.scene_id],
            affected_layer_ids: scene.layers ? scene.layers.map((l) => l.layer_id) : [],
            affected_track_ids: ["track_main_video"],
            affected_clip_ids: [`clip_sc_${scene.scene_id}`],
            affected_keyframe_ids: [],
            time_range: { startFrame: scene.startFrame, endFrame: scene.startFrame + scene.durationFrames },
            invalidation: {
              requires_layout: true,
              requires_render: true,
              requires_audio_remix: false,
              requires_timeline_rebuild: true,
            },
            mutations_count: 1,
          },
        };
      }

      // 3. Targeting specific layer clip
      for (const s of draft.scenes) {
        if (s.layers) {
          for (const l of s.layers) {
            if ((layer_id && l.layer_id === layer_id) || (clip_id && clip_id === `clip_${l.layer_id}`)) {
              l.time_range = createTimeRange(newStart, l.time_range.durationFrames);
              return {
                ok: true,
                changeset: {
                  affected_scene_ids: [s.scene_id],
                  affected_layer_ids: [l.layer_id],
                  affected_track_ids: ["track_main_video"],
                  affected_clip_ids: [`clip_sc_${s.scene_id}`],
                  affected_keyframe_ids: [],
                  time_range: { startFrame: newStart, endFrame: l.time_range.endFrame },
                  invalidation: {
                    requires_layout: true,
                    requires_render: true,
                    requires_audio_remix: l.kind === "audio",
                    requires_timeline_rebuild: true,
                  },
                  mutations_count: 1,
                },
              };
            }
          }
        }
      }

      return {
        ok: false,
        changeset: emptyChangeSet(),
        error: {
          code: "CLIP_NOT_FOUND",
          message: `Target clip '${clip_id || scene_id || layer_id}' could not be resolved`,
          mutation_id: mutation.mutation_id,
          target_id: clip_id || scene_id || layer_id,
        },
      };
    }

    case "TRIM_CLIP": {
      const { clip_id, scene_id, layer_id } = mutation.target;
      const { start_trim_frames, end_trim_frames, new_duration_frames } = mutation.payload;

      const resolvedSceneId = scene_id || (clip_id && clip_id.startsWith("clip_sc_") ? clip_id.replace("clip_sc_", "") : null);

      if (resolvedSceneId && !layer_id) {
        const sceneFound = findScene(draft.scenes, resolvedSceneId);
        if (!sceneFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "CLIP_NOT_FOUND",
              message: `Scene '${resolvedSceneId}' not found for trim`,
              mutation_id: mutation.mutation_id,
              target_id: clip_id || resolvedSceneId,
            },
          };
        }
        const scene = sceneFound.scene;

        if (new_duration_frames !== undefined) {
          scene.durationFrames = new_duration_frames;
        } else {
          const sTrim = start_trim_frames ?? 0;
          const eTrim = end_trim_frames ?? 0;
          const newDur = scene.durationFrames - sTrim - eTrim;
          if (newDur < 1) {
            return {
              ok: false,
              changeset: emptyChangeSet(),
              error: {
                code: "INVALID_MUTATION",
                message: `Trim resulted in non-positive duration ${newDur}. Duration must be >= 1 frame.`,
                mutation_id: mutation.mutation_id,
                target_id: scene.scene_id,
              },
            };
          }
          scene.startFrame += sTrim;
          scene.durationFrames = newDur;
          if (scene.layers) {
            for (const l of scene.layers) {
              const lDur = Math.max(1, l.time_range.durationFrames - sTrim - eTrim);
              l.time_range = createTimeRange(l.time_range.startFrame + sTrim, lDur);
            }
          }
        }

        return {
          ok: true,
          changeset: {
            affected_scene_ids: [scene.scene_id],
            affected_layer_ids: scene.layers ? scene.layers.map((l) => l.layer_id) : [],
            affected_track_ids: ["track_main_video"],
            affected_clip_ids: [`clip_sc_${scene.scene_id}`],
            affected_keyframe_ids: [],
            time_range: { startFrame: scene.startFrame, endFrame: scene.startFrame + scene.durationFrames },
            invalidation: {
              requires_layout: true,
              requires_render: true,
              requires_audio_remix: false,
              requires_timeline_rebuild: true,
            },
            mutations_count: 1,
          },
        };
      }

      // Check layer trim
      for (const s of draft.scenes) {
        if (s.layers) {
          for (const l of s.layers) {
            if ((layer_id && l.layer_id === layer_id) || (clip_id && clip_id === `clip_${l.layer_id}`)) {
              if (new_duration_frames !== undefined) {
                l.time_range = createTimeRange(l.time_range.startFrame, new_duration_frames);
              } else {
                const sTrim = start_trim_frames ?? 0;
                const eTrim = end_trim_frames ?? 0;
                const newDur = l.time_range.durationFrames - sTrim - eTrim;
                if (newDur < 1) {
                  return {
                    ok: false,
                    changeset: emptyChangeSet(),
                    error: {
                      code: "INVALID_MUTATION",
                      message: `Layer trim resulted in non-positive duration ${newDur}`,
                      mutation_id: mutation.mutation_id,
                      target_id: l.layer_id,
                    },
                  };
                }
                l.time_range = createTimeRange(l.time_range.startFrame + sTrim, newDur);
              }

              return {
                ok: true,
                changeset: {
                  affected_scene_ids: [s.scene_id],
                  affected_layer_ids: [l.layer_id],
                  affected_track_ids: ["track_main_video"],
                  affected_clip_ids: [`clip_sc_${s.scene_id}`],
                  affected_keyframe_ids: [],
                  time_range: { startFrame: l.time_range.startFrame, endFrame: l.time_range.endFrame },
                  invalidation: {
                    requires_layout: true,
                    requires_render: true,
                    requires_audio_remix: l.kind === "audio",
                    requires_timeline_rebuild: true,
                  },
                  mutations_count: 1,
                },
              };
            }
          }
        }
      }

      return {
        ok: false,
        changeset: emptyChangeSet(),
        error: {
          code: "CLIP_NOT_FOUND",
          message: `Target clip '${clip_id || scene_id || layer_id}' not found for trim`,
          mutation_id: mutation.mutation_id,
          target_id: clip_id || scene_id || layer_id,
        },
      };
    }

    case "SPLIT_CLIP": {
      const { clip_id, scene_id, layer_id } = mutation.target;
      const splitFrame = mutation.payload.split_frame;
      const resolvedSceneId = scene_id || (clip_id && clip_id.startsWith("clip_sc_") ? clip_id.replace("clip_sc_", "") : null);

      if (resolvedSceneId && !layer_id) {
        const sceneFound = findScene(draft.scenes, resolvedSceneId);
        if (!sceneFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "SCENE_NOT_FOUND",
              message: `Scene '${resolvedSceneId}' not found for split`,
              mutation_id: mutation.mutation_id,
              target_id: clip_id || resolvedSceneId,
            },
          };
        }
        const scene = sceneFound.scene;
        const sStart = scene.startFrame;
        const sEnd = scene.startFrame + scene.durationFrames;

        if (splitFrame <= sStart || splitFrame >= sEnd) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "INVALID_SPLIT_POINT",
              message: `Split frame ${splitFrame} must be strictly between startFrame ${sStart} and endFrame ${sEnd}`,
              mutation_id: mutation.mutation_id,
              target_id: scene.scene_id,
            },
          };
        }

        const newSceneId = mutation.payload.new_scene_id || `${scene.scene_id}_split`;
        if (draft.scenes.some((s) => s.scene_id === newSceneId)) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "DUPLICATE_ID",
              message: `New scene ID '${newSceneId}' already exists`,
              mutation_id: mutation.mutation_id,
              target_id: newSceneId,
            },
          };
        }

        const dur1 = splitFrame - sStart;
        const dur2 = sEnd - splitFrame;
        scene.durationFrames = dur1;

        // The transition out was at the end of the original scene, so it moves to scene2
        const originalTransition = scene.transition ? cloneBlueprint(scene.transition) : undefined;
        delete scene.transition;

        const scene2: BlueprintScene = cloneBlueprint(scene);
        scene2.scene_id = newSceneId;
        scene2.startFrame = splitFrame;
        scene2.durationFrames = dur2;
        if (originalTransition) {
          scene2.transition = {
            ...originalTransition,
            durationFrames: Math.min(originalTransition.durationFrames, Math.max(1, dur2 - 1)),
          };
        }

        if (scene2.layers) {
          scene2.layers = scene2.layers.map((l, idx) => {
            const clonedLayer: CanonicalLayer = cloneBlueprint(l);
            clonedLayer.layer_id = `${newSceneId}_layer_${idx}`;
            clonedLayer.time_range = createTimeRange(splitFrame, dur2);
            return clonedLayer;
          });
        }

        draft.scenes.splice(sceneFound.index + 1, 0, scene2);

        return {
          ok: true,
          changeset: {
            affected_scene_ids: [scene.scene_id, newSceneId],
            affected_layer_ids: scene2.layers ? scene2.layers.map((l) => l.layer_id) : [],
            affected_track_ids: ["track_main_video"],
            affected_clip_ids: [`clip_sc_${scene.scene_id}`, `clip_sc_${newSceneId}`],
            affected_keyframe_ids: [],
            time_range: { startFrame: sStart, endFrame: sEnd },
            invalidation: {
              requires_layout: true,
              requires_render: true,
              requires_audio_remix: false,
              requires_timeline_rebuild: true,
            },
            mutations_count: 1,
          },
        };
      }

      // Layer split
      for (const s of draft.scenes) {
        if (s.layers) {
          for (let i = 0; i < s.layers.length; i++) {
            const l = s.layers[i];
            if ((layer_id && l.layer_id === layer_id) || (clip_id && clip_id === `clip_${l.layer_id}`)) {
              const lStart = l.time_range.startFrame;
              const lEnd = l.time_range.endFrame;

              if (splitFrame <= lStart || splitFrame >= lEnd) {
                return {
                  ok: false,
                  changeset: emptyChangeSet(),
                  error: {
                    code: "INVALID_SPLIT_POINT",
                    message: `Split frame ${splitFrame} must be strictly between layer start ${lStart} and end ${lEnd}`,
                    mutation_id: mutation.mutation_id,
                    target_id: l.layer_id,
                  },
                };
              }

              const newLayerId = mutation.payload.new_layer_id || `${l.layer_id}_split`;
              if (s.layers.some((existing) => existing.layer_id === newLayerId)) {
                return {
                  ok: false,
                  changeset: emptyChangeSet(),
                  error: {
                    code: "DUPLICATE_ID",
                    message: `New layer ID '${newLayerId}' already exists`,
                    mutation_id: mutation.mutation_id,
                    target_id: newLayerId,
                  },
                };
              }

              const dur1 = splitFrame - lStart;
              const dur2 = lEnd - splitFrame;
              l.time_range = createTimeRange(lStart, dur1);

              const l2: CanonicalLayer = cloneBlueprint(l);
              l2.layer_id = newLayerId;
              l2.time_range = createTimeRange(splitFrame, dur2);

              s.layers.splice(i + 1, 0, l2);

              return {
                ok: true,
                changeset: {
                  affected_scene_ids: [s.scene_id],
                  affected_layer_ids: [l.layer_id, newLayerId],
                  affected_track_ids: ["track_main_video"],
                  affected_clip_ids: [`clip_sc_${s.scene_id}`],
                  affected_keyframe_ids: [],
                  time_range: { startFrame: lStart, endFrame: lEnd },
                  invalidation: {
                    requires_layout: true,
                    requires_render: true,
                    requires_audio_remix: l.kind === "audio",
                    requires_timeline_rebuild: true,
                  },
                  mutations_count: 1,
                },
              };
            }
          }
        }
      }

      return {
        ok: false,
        changeset: emptyChangeSet(),
        error: {
          code: "CLIP_NOT_FOUND",
          message: `Target clip '${clip_id || scene_id || layer_id}' not found for split`,
          mutation_id: mutation.mutation_id,
          target_id: clip_id || scene_id || layer_id,
        },
      };
    }

    case "SET_KEYFRAME": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const layerFound = findLayer(scene, targetLayerId);
      if (!layerFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const layer = layerFound.layer;
      if (!layer.channels) {
        layer.channels = [];
      }

      const { channel_id, channel_target } = mutation.target;
      let channel = layer.channels.find(
        (ch) => (channel_id && ch.channel_id === channel_id) || (channel_target && ch.target === channel_target)
      );

      if (!channel) {
        const targetType = channel_target || "TRANSFORM_X";
        const newChanId = channel_id || `ch_${targetType.toLowerCase()}_${layer.layer_id}`;
        channel = {
          channel_id: newChanId,
          target: targetType,
          keyframes: [],
        };
        layer.channels.push(channel);
      }

      const newKf = mutation.payload.keyframe;
      const existingKfIdx = channel.keyframes.findIndex(
        (k) => k.keyframe_id === newKf.keyframe_id || k.frame === newKf.frame
      );

      if (existingKfIdx >= 0) {
        channel.keyframes[existingKfIdx] = newKf;
      } else {
        channel.keyframes.push(newKf);
      }

      channel.keyframes.sort((a, b) => a.frame - b.frame);
      try {
        validateKeyframes(channel.keyframes);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "INVALID_MUTATION",
            message: `Keyframe validation failed: ${msg}`,
            mutation_id: mutation.mutation_id,
            target_id: newKf.keyframe_id,
          },
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [layer.layer_id],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [newKf.keyframe_id],
          time_range: {
            startFrame: layer.time_range.startFrame,
            endFrame: layer.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "UPDATE_KEYFRAME": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const layerFound = findLayer(scene, targetLayerId);
      if (!layerFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const layer = layerFound.layer;
      const kfId = mutation.target.keyframe_id;
      let matchedKf: Keyframe | null = null;
      let matchedChannel = null;

      if (layer.channels) {
        for (const ch of layer.channels) {
          for (const kf of ch.keyframes) {
            if (kf.keyframe_id === kfId) {
              matchedKf = kf;
              matchedChannel = ch;
              break;
            }
          }
          if (matchedKf) break;
        }
      }

      if (!matchedKf || !matchedChannel) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "KEYFRAME_NOT_FOUND",
            message: `Keyframe '${kfId}' not found on layer '${layer.layer_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: kfId,
          },
        };
      }

      const patch = mutation.payload.patch;
      if (patch.frame !== undefined) matchedKf.frame = patch.frame;
      if (patch.value !== undefined) matchedKf.value = patch.value;
      if (patch.interpolation !== undefined) matchedKf.interpolation = patch.interpolation;
      if (patch.easing !== undefined) matchedKf.easing = patch.easing;
      if (patch.bezier !== undefined) matchedKf.bezier = patch.bezier;
      if (patch.spring !== undefined) matchedKf.spring = patch.spring;

      matchedChannel.keyframes.sort((a, b) => a.frame - b.frame);
      try {
        validateKeyframes(matchedChannel.keyframes);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "INVALID_MUTATION",
            message: `Keyframe update caused validation error: ${msg}`,
            mutation_id: mutation.mutation_id,
            target_id: kfId,
          },
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [layer.layer_id],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [kfId],
          time_range: {
            startFrame: layer.time_range.startFrame,
            endFrame: layer.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "REMOVE_KEYFRAME": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const layerFound = findLayer(scene, targetLayerId);
      if (!layerFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "LAYER_NOT_FOUND",
            message: `Layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: targetLayerId,
          },
        };
      }

      const layer = layerFound.layer;
      const kfId = mutation.target.keyframe_id;
      let found = false;

      if (layer.channels) {
        for (const ch of layer.channels) {
          const initLen = ch.keyframes.length;
          ch.keyframes = ch.keyframes.filter((k) => k.keyframe_id !== kfId);
          if (ch.keyframes.length < initLen) {
            found = true;
            break;
          }
        }
      }

      if (!found) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "KEYFRAME_NOT_FOUND",
            message: `Keyframe '${kfId}' not found on layer '${layer.layer_id}'`,
            mutation_id: mutation.mutation_id,
            target_id: kfId,
          },
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [layer.layer_id],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [kfId],
          time_range: {
            startFrame: layer.time_range.startFrame,
            endFrame: layer.time_range.endFrame,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "SET_TRANSITION": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      scene.transition = { ...mutation.payload.transition };

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: false,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "REMOVE_TRANSITION": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      delete scene.transition;

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: false,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "ADD_SCENE": {
      const newScene = mutation.payload.scene;
      if (draft.scenes.some((s) => s.scene_id === newScene.scene_id)) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "DUPLICATE_ID",
            message: `Scene ID '${newScene.scene_id}' already exists`,
            mutation_id: mutation.mutation_id,
            target_id: newScene.scene_id,
          },
        };
      }

      const placement = mutation.payload.placement;
      if (placement?.relative_to) {
        const refIdx = draft.scenes.findIndex((s) => s.scene_id === placement.relative_to);
        if (refIdx >= 0) {
          const insertIdx = placement.position === "before" ? refIdx : refIdx + 1;
          draft.scenes.splice(insertIdx, 0, newScene);
        } else {
          draft.scenes.push(newScene);
        }
      } else if (placement?.position === "start") {
        draft.scenes.unshift(newScene);
      } else {
        draft.scenes.push(newScene);
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [newScene.scene_id],
          affected_layer_ids: newScene.layers ? newScene.layers.map((l) => l.layer_id) : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${newScene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: newScene.startFrame,
            endFrame: newScene.startFrame + newScene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "REMOVE_SCENE": {
      const sceneId = mutation.target.scene_id;
      const sceneFound = findScene(draft.scenes, sceneId);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Scene '${sceneId}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: sceneId,
          },
        };
      }

      if (draft.scenes.length <= 1) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "MINIMUM_SCENES_VIOLATION",
            message: `Cannot remove scene '${sceneId}': video must maintain at least 1 scene`,
            mutation_id: mutation.mutation_id,
            target_id: sceneId,
          },
        };
      }

      draft.scenes.splice(sceneFound.index, 1);

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [sceneId],
          affected_layer_ids: [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${sceneId}`],
          affected_keyframe_ids: [],
          time_range: undefined,
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "DUPLICATE_SCENE": {
      const sceneId = mutation.target.scene_id;
      const sceneFound = findScene(draft.scenes, sceneId);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Scene '${sceneId}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: sceneId,
          },
        };
      }

      const newSceneId = mutation.payload.new_scene_id;
      if (draft.scenes.some((s) => s.scene_id === newSceneId)) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "DUPLICATE_ID",
            message: `New scene ID '${newSceneId}' already exists`,
            mutation_id: mutation.mutation_id,
            target_id: newSceneId,
          },
        };
      }

      const sourceScene = sceneFound.scene;
      const duplicatedScene: BlueprintScene = cloneBlueprint(sourceScene);
      duplicatedScene.scene_id = newSceneId;

      if (mutation.payload.start_frame_offset !== undefined) {
        duplicatedScene.startFrame += mutation.payload.start_frame_offset;
      }

      // Re-map layer IDs to keep global uniqueness
      if (duplicatedScene.layers) {
        const idMap = mutation.payload.new_layer_ids_map || {};
        duplicatedScene.layers = duplicatedScene.layers.map((l, idx) => {
          const mappedId = idMap[l.layer_id] || `${newSceneId}_l_${idx}`;
          const newLayer: CanonicalLayer = {
            ...l,
            layer_id: mappedId,
            time_range: createTimeRange(
              duplicatedScene.startFrame,
              duplicatedScene.durationFrames
            ),
          };
          return newLayer;
        });
      }

      draft.scenes.splice(sceneFound.index + 1, 0, duplicatedScene);

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [newSceneId],
          affected_layer_ids: duplicatedScene.layers ? duplicatedScene.layers.map((l) => l.layer_id) : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${newSceneId}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: duplicatedScene.startFrame,
            endFrame: duplicatedScene.startFrame + duplicatedScene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "REORDER_SCENE": {
      const sceneId = mutation.target.scene_id;
      const sceneFound = findScene(draft.scenes, sceneId);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Scene '${sceneId}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: sceneId,
          },
        };
      }

      const refId = mutation.payload.relative_to;
      const refFound = findScene(draft.scenes, refId);
      if (!refFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Reference scene '${refId}' not found for reorder`,
            mutation_id: mutation.mutation_id,
            target_id: refId,
          },
        };
      }

      const scene = sceneFound.scene;
      draft.scenes.splice(sceneFound.index, 1);
      const newRefIdx = draft.scenes.findIndex((s) => s.scene_id === refId);
      const insertIdx = mutation.payload.position === "before" ? newRefIdx : newRefIdx + 1;
      draft.scenes.splice(insertIdx, 0, scene);

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [sceneId, refId],
          affected_layer_ids: [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${sceneId}`, `clip_sc_${refId}`],
          affected_keyframe_ids: [],
          time_range: undefined,
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "UPDATE_PROJECT": {
      if (mutation.payload.fps !== undefined) {
        draft.fps = mutation.payload.fps;
      }
      if (mutation.payload.aspect_ratio !== undefined) {
        draft.aspect_ratio = mutation.payload.aspect_ratio;
      }
      if (mutation.payload.meta) {
        draft.meta = {
          ...(draft.meta || {}),
          ...mutation.payload.meta,
        };
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: draft.scenes.map((s) => s.scene_id),
          affected_layer_ids: [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [],
          affected_keyframe_ids: [],
          time_range: undefined,
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: true,
          },
          mutations_count: 1,
        },
      };
    }

    case "UPDATE_AUDIO": {
      if (!draft.audio) {
        draft.audio = { global_sfx: [] };
      }

      if (mutation.payload.voiceover) {
        if (!draft.audio.voiceover) {
          draft.audio.voiceover = {
            asset_ref: mutation.payload.voiceover.asset_ref || "vo_default",
            volume: mutation.payload.voiceover.volume ?? 1.0,
            startFrame: mutation.payload.voiceover.startFrame ?? 0,
            mute: mutation.payload.voiceover.mute ?? false,
          };
        } else {
          draft.audio.voiceover = {
            ...draft.audio.voiceover,
            ...mutation.payload.voiceover,
          };
        }
      }

      if (mutation.payload.music) {
        if (!draft.audio.music) {
          draft.audio.music = {
            asset_ref: mutation.payload.music.asset_ref || "bgm_default",
            volume: mutation.payload.music.volume ?? 0.15,
            startFrame: mutation.payload.music.startFrame ?? 0,
            loop: mutation.payload.music.loop ?? true,
            mute: mutation.payload.music.mute ?? false,
          };
        } else {
          draft.audio.music = {
            ...draft.audio.music,
            ...mutation.payload.music,
          };
        }
      }

      if (mutation.payload.global_sfx) {
        draft.audio.global_sfx = [...mutation.payload.global_sfx];
      }

      const isTimingChange =
        mutation.payload.voiceover?.startFrame !== undefined ||
        mutation.payload.voiceover?.durationFrames !== undefined ||
        mutation.payload.voiceover?.asset_ref !== undefined ||
        mutation.payload.music?.startFrame !== undefined ||
        mutation.payload.music?.durationFrames !== undefined ||
        mutation.payload.music?.asset_ref !== undefined ||
        Boolean(mutation.payload.global_sfx);

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [],
          affected_layer_ids: [],
          affected_track_ids: ["track_voiceover", "track_bgm", ...(mutation.payload.global_sfx ? ["track_sfx"] : [])],
          affected_clip_ids: ["clip_voiceover", "clip_bgm"],
          affected_keyframe_ids: [],
          time_range: undefined,
          invalidation: {
            requires_layout: false,
            requires_render: false,
            requires_audio_remix: true,
            requires_timeline_rebuild: isTimingChange,
          },
          mutations_count: 1,
        },
      };
    }

    case "SET_AUDIO_LEVEL": {
      if (!draft.audio) {
        draft.audio = { global_sfx: [] };
      }
      const p = mutation.payload;
      const affectedTracks: string[] = [];

      if (p.track === "voiceover") {
        if (!draft.audio.voiceover) {
          draft.audio.voiceover = {
            asset_ref: "vo_default",
            volume: p.volume ?? 1.0,
            startFrame: 0,
            mute: p.mute ?? false,
          };
        } else {
          if (p.volume !== undefined) draft.audio.voiceover.volume = p.volume;
          if (p.mute !== undefined) draft.audio.voiceover.mute = p.mute;
        }
        affectedTracks.push("track_voiceover");
      } else if (p.track === "music") {
        if (!draft.audio.music) {
          draft.audio.music = {
            asset_ref: "bgm_default",
            volume: p.volume ?? 0.15,
            startFrame: 0,
            loop: true,
            mute: p.mute ?? false,
          };
        } else {
          if (p.volume !== undefined) draft.audio.music.volume = p.volume;
          if (p.mute !== undefined) draft.audio.music.mute = p.mute;
        }
        affectedTracks.push("track_bgm");
      } else if (p.track === "sfx" && draft.audio.global_sfx) {
        if (p.track_id) {
          const found = draft.audio.global_sfx.find((s) => s.track_id === p.track_id);
          if (found) {
            if (p.volume !== undefined) found.volume = p.volume;
            if (p.mute !== undefined) found.mute = p.mute;
          }
        }
        affectedTracks.push("track_sfx");
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [],
          affected_layer_ids: [],
          affected_track_ids: affectedTracks,
          affected_clip_ids: [],
          affected_keyframe_ids: [],
          time_range: undefined,
          invalidation: {
            requires_layout: false,
            requires_render: false,
            requires_audio_remix: true,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "UPDATE_STYLE": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const p = mutation.payload;

      if (targetLayerId) {
        const layerFound = findLayer(scene, targetLayerId);
        if (!layerFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "LAYER_NOT_FOUND",
              message: `Target layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
              mutation_id: mutation.mutation_id,
              target_id: targetLayerId,
            },
          };
        }
        const layer = layerFound.layer;
        if (layer.kind === "shape") {
          if (p.shape?.fillColor !== undefined) layer.fillColor = p.shape.fillColor;
          if (p.backgroundColor !== undefined) layer.fillColor = p.backgroundColor;
          if (p.shape?.strokeColor !== undefined) layer.strokeColor = p.shape.strokeColor;
          if (p.shape?.strokeWidth !== undefined) layer.strokeWidth = p.shape.strokeWidth;
        } else if (layer.kind === "text") {
          if (p.color !== undefined) {
            layer.typography = { ...layer.typography, fillColor: p.color };
          }
          if (p.surface?.color !== undefined) {
            layer.typography = { ...layer.typography, fillColor: p.surface.color };
          }
        }
      } else {
        // Scene level surface update
        if (!scene.surface) scene.surface = {};
        if (p.backgroundColor !== undefined) scene.surface.background = p.backgroundColor;
        if (p.color !== undefined) scene.surface.color = p.color;
        if (p.surface) {
          scene.surface = { ...scene.surface, ...p.surface };
        }
        // Also update background shape layer if present (${scene_id}_bg or background)
        if (p.backgroundColor && scene.layers) {
          const bgLayer = scene.layers.find(
            (l) => l.kind === "shape" && (l.layer_id.endsWith("_bg") || l.layer_id.includes("background"))
          );
          if (bgLayer && bgLayer.kind === "shape") {
            bgLayer.fillColor = p.backgroundColor;
          }
        }
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: targetLayerId ? [targetLayerId] : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: false,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    case "REPLACE_MEDIA": {
      const sceneFound = findScene(draft.scenes, mutation.target.scene_id);
      if (!sceneFound) {
        return {
          ok: false,
          changeset: emptyChangeSet(),
          error: {
            code: "SCENE_NOT_FOUND",
            message: `Target scene '${mutation.target.scene_id}' not found`,
            mutation_id: mutation.mutation_id,
            target_id: mutation.target.scene_id,
          },
        };
      }
      const scene = sceneFound.scene;
      const targetLayerId = mutation.target.layer_id;
      const newRef = mutation.payload.asset_ref;

      if (targetLayerId) {
        const layerFound = findLayer(scene, targetLayerId);
        if (!layerFound) {
          return {
            ok: false,
            changeset: emptyChangeSet(),
            error: {
              code: "LAYER_NOT_FOUND",
              message: `Target layer '${targetLayerId}' not found in scene '${scene.scene_id}'`,
              mutation_id: mutation.mutation_id,
              target_id: targetLayerId,
            },
          };
        }
        const layer = layerFound.layer;
        if (layer.kind === "image" || layer.kind === "video" || layer.kind === "audio") {
          layer.asset_ref = newRef;
        }
      } else {
        // Scene level media update
        if (!scene.media_refs) scene.media_refs = [];
        scene.media_refs = [newRef];
        if (scene.layers) {
          const mediaLayer = scene.layers.find((l) => l.kind === "image" || l.kind === "video");
          if (mediaLayer && (mediaLayer.kind === "image" || mediaLayer.kind === "video")) {
            mediaLayer.asset_ref = newRef;
          }
        }
      }

      return {
        ok: true,
        changeset: {
          affected_scene_ids: [scene.scene_id],
          affected_layer_ids: targetLayerId ? [targetLayerId] : [],
          affected_track_ids: ["track_main_video"],
          affected_clip_ids: [`clip_sc_${scene.scene_id}`],
          affected_keyframe_ids: [],
          time_range: {
            startFrame: scene.startFrame,
            endFrame: scene.startFrame + scene.durationFrames,
          },
          invalidation: {
            requires_layout: true,
            requires_render: true,
            requires_audio_remix: false,
            requires_timeline_rebuild: false,
          },
          mutations_count: 1,
        },
      };
    }

    default: {
      const exhaustiveCheck: never = mutation;
      return {
        ok: false,
        changeset: emptyChangeSet(),
        error: {
          code: "UNKNOWN_MUTATION_TYPE",
          message: `Unhandled mutation type '${(exhaustiveCheck as CanonicalMutation).type}'`,
          mutation_id: (exhaustiveCheck as CanonicalMutation).mutation_id,
        },
      };
    }
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 7. Public Pure Mutation Engine Entrypoints
// ────────────────────────────────────────────────────────────────────────────

export interface MutationOptions {
  skipSemanticValidation?: boolean;
}

export interface BatchOptions {
  revisionPolicy?: "per_batch" | "per_mutation";
  skipSemanticValidation?: boolean;
}

/**
 * Pure, authoritative mutation applicator for BlueprintV2.
 * Enforces:
 *   - Optimistic concurrency (expected_revision check)
 *   - Idempotency (mutation_id deduplication)
 *   - Immutable transformation (input is never mutated)
 *   - Fail-closed execution (schema & semantic validation before commit)
 */
export function applyMutation(
  blueprint: BlueprintV2,
  mutationInput: unknown,
  options?: MutationOptions
): MutationResult {
  const currentRevision = blueprint.revision ?? 0;

  // 1. Structural schema parse of mutation
  const parseResult = CanonicalMutationSchema.safeParse(mutationInput);
  if (!parseResult.success) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "INVALID_MUTATION",
        message: `Mutation schema validation failed: ${parseResult.error.issues.map((i) => `[${i.path.join(".")}] ${i.message}`).join("; ")}`,
      },
    };
  }

  const mutation = parseResult.data;

  // 2. Idempotency Check (Must happen before concurrency check so retries succeed)
  const appliedMutations = blueprint.applied_mutations ?? [];
  if (appliedMutations.includes(mutation.mutation_id)) {
    return {
      success: true,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [mutation.mutation_id],
      changeset: emptyChangeSet(),
      idempotent: true,
    };
  }

  // 3. Optimistic Concurrency Check
  if (mutation.expected_revision !== undefined && mutation.expected_revision !== currentRevision) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "REVISION_CONFLICT",
        message: `Optimistic concurrency conflict: expected revision ${mutation.expected_revision}, but current revision is ${currentRevision}`,
        mutation_id: mutation.mutation_id,
        expected_revision: mutation.expected_revision,
        actual_revision: currentRevision,
      },
    };
  }

  // 4. Create pure draft clone
  const draft: BlueprintV2 = cloneBlueprint(blueprint);

  // 5. Apply mutation step
  const stepResult = applyMutationStep(draft, mutation);
  if (!stepResult.ok) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: stepResult.error,
    };
  }

  // 6. Post-mutation validation gate (fail-closed)
  const schemaValidation = BlueprintV2Schema.safeParse(draft);
  if (!schemaValidation.success) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "VALIDATION_FAILED",
        message: `Blueprint failed schema validation after mutation: ${schemaValidation.error.issues.map((i) => i.message).join("; ")}`,
        mutation_id: mutation.mutation_id,
      },
    };
  }

  if (!options?.skipSemanticValidation) {
    const semanticValidation = validateBlueprintV2(draft);
    if (!semanticValidation.ok) {
      return {
        success: false,
        revision: currentRevision,
        blueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "VALIDATION_FAILED",
          message: `Blueprint failed semantic validation after mutation: ${semanticValidation.errors.join("; ")}`,
          mutation_id: mutation.mutation_id,
        },
      };
    }
  }

  // 7. Advance revision and record applied mutation
  const nextRevision = currentRevision + 1;
  draft.revision = nextRevision;
  draft.applied_mutations = [...appliedMutations, mutation.mutation_id];

  return {
    success: true,
    revision: nextRevision,
    blueprint: draft,
    applied_mutation_ids: [mutation.mutation_id],
    changeset: stepResult.changeset,
    idempotent: false,
  };
}

/**
 * Pure, atomic batch mutation applicator.
 * Enforces:
 *   - All-or-nothing execution (if any mutation fails, entire batch is rolled back)
 *   - Optimistic concurrency on batch level
 *   - Combined ChangeSet calculation
 *   - Revision advancement
 */
export function applyBatch(
  blueprint: BlueprintV2,
  batchInput: unknown,
  options?: BatchOptions
): MutationResult {
  const currentRevision = blueprint.revision ?? 0;

  // 1. Validate batch schema
  const parseResult = MutationBatchSchema.safeParse(batchInput);
  if (!parseResult.success) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "INVALID_MUTATION",
        message: `Batch validation failed: ${parseResult.error.issues.map((i) => i.message).join("; ")}`,
      },
    };
  }

  const batch = parseResult.data;

  // 2. Optimistic Concurrency on Batch
  if (batch.expected_revision !== undefined && batch.expected_revision !== currentRevision) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "REVISION_CONFLICT",
        message: `Batch optimistic concurrency conflict: expected revision ${batch.expected_revision}, but current revision is ${currentRevision}`,
        expected_revision: batch.expected_revision,
        actual_revision: currentRevision,
      },
    };
  }

  // 3. Sequential atomic execution on draft
  const draft: BlueprintV2 = cloneBlueprint(blueprint);
  const appliedMutations = new Set<string>(blueprint.applied_mutations ?? []);
  const appliedThisBatch: string[] = [];
  const changesets: ChangeSet[] = [];
  let runningRevision = currentRevision;

  for (const mut of batch.mutations) {
    // Check mutation-level concurrency if present
    if (mut.expected_revision !== undefined && mut.expected_revision !== runningRevision) {
      return {
        success: false,
        revision: currentRevision,
        blueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "BATCH_EXECUTION_FAILED",
          message: `Batch '${batch.batch_id}' aborted at mutation '${mut.mutation_id}': mutation expected revision ${mut.expected_revision}, current is ${runningRevision}`,
          mutation_id: mut.mutation_id,
          expected_revision: mut.expected_revision,
          actual_revision: runningRevision,
        },
      };
    }

    // Skip if already applied
    if (appliedMutations.has(mut.mutation_id)) {
      appliedThisBatch.push(mut.mutation_id);
      continue;
    }

    const stepResult = applyMutationStep(draft, mut);
    if (!stepResult.ok) {
      return {
        success: false,
        revision: currentRevision,
        blueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "BATCH_EXECUTION_FAILED",
          message: `Batch '${batch.batch_id}' aborted at mutation '${mut.mutation_id}': ${stepResult.error?.message}`,
          mutation_id: mut.mutation_id,
          details: { underlying_error: stepResult.error as unknown as Record<string, unknown> },
        },
      };
    }

    appliedMutations.add(mut.mutation_id);
    appliedThisBatch.push(mut.mutation_id);
    changesets.push(stepResult.changeset);

    if (options?.revisionPolicy === "per_mutation") {
      runningRevision += 1;
    }
  }

  // 4. Post-batch validation gate
  const schemaValidation = BlueprintV2Schema.safeParse(draft);
  if (!schemaValidation.success) {
    return {
      success: false,
      revision: currentRevision,
      blueprint,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      error: {
        code: "BATCH_EXECUTION_FAILED",
        message: `Batch '${batch.batch_id}' produced invalid blueprint: ${schemaValidation.error.issues.map((i) => i.message).join("; ")}`,
      },
    };
  }

  if (!options?.skipSemanticValidation) {
    const semanticValidation = validateBlueprintV2(draft);
    if (!semanticValidation.ok) {
      return {
        success: false,
        revision: currentRevision,
        blueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "BATCH_EXECUTION_FAILED",
          message: `Batch '${batch.batch_id}' semantic validation failed: ${semanticValidation.errors.join("; ")}`,
        },
      };
    }
  }

  // 5. Finalize revision
  const finalRevision = options?.revisionPolicy === "per_mutation"
    ? runningRevision
    : currentRevision + (appliedThisBatch.length > 0 ? 1 : 0);

  draft.revision = finalRevision;
  draft.applied_mutations = Array.from(appliedMutations);

  return {
    success: true,
    revision: finalRevision,
    blueprint: draft,
    applied_mutation_ids: appliedThisBatch,
    changeset: combineChangeSets(changesets),
    idempotent: appliedThisBatch.length === 0,
  };
}
