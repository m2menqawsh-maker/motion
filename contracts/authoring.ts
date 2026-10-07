/**
 * contracts/authoring.ts — Engine-Neutral Authoring Contract & Schema Authority.
 * S28-R13: Unified Authoring Contract governing AI, User, and Template edits.
 * 
 * Invariants:
 *   - Canonical VideoDocument (BlueprintV2) is the SINGLE authoring authority.
 *   - AI edits NEVER emit TSX, Remotion code, or renderer-specific representations.
 *   - AI intents translate strictly into typed canonical mutations.
 *   - Zero AI provider SDK dependencies (OpenAI, Anthropic, Google SDKs forbidden).
 *   - Zero renderer or bundler imports.
 */

import { z } from "zod";
import {
  type BlueprintV2,
  BlueprintV2Schema,
  type BlueprintScene,
  BlueprintSceneSchema,
  type StyleSurface,
  StyleSurfaceSchema,
} from "./blueprint";
import { StableIdSchema } from "./timeline";
import {
  type CanonicalLayer,
  CanonicalLayerSchema,
  type Transform,
  type CanonicalTypography,
  CanonicalTypographySchema,
} from "./layers";
import {
  type CanonicalMutation,
  CanonicalMutationSchema,
  type ChangeSet,
  emptyChangeSet,
} from "./mutations";
import { AssetRefSchema, type AssetRef } from "./asset-resolver";

// ────────────────────────────────────────────────────────────────────────────
// 1. Authoring Actor & Diagnostics
// ────────────────────────────────────────────────────────────────────────────

export const AuthoringActorSchema = z.enum(["user", "ai", "system"]);
export type AuthoringActor = z.infer<typeof AuthoringActorSchema>;

export const AuthoringDiagnosticCodeSchema = z.enum([
  "AUTHORING_TARGET_NOT_FOUND",
  "AUTHORING_TARGET_AMBIGUOUS",
  "UNSUPPORTED_AUTHORING_OPERATION",
  "AUTHORING_VALIDATION_FAILED",
  "REVISION_CONFLICT",
]);
export type AuthoringDiagnosticCode = z.infer<typeof AuthoringDiagnosticCodeSchema>;

export const AuthoringDiagnosticSchema = z.object({
  code: AuthoringDiagnosticCodeSchema,
  message: z.string(),
  target_id: z.string().optional(),
  details: z.record(z.string(), z.any()).optional(),
});
export type AuthoringDiagnostic = z.infer<typeof AuthoringDiagnosticSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 2. Authoring Provenance (Metadata without Rendering Impact)
// ────────────────────────────────────────────────────────────────────────────

export const AuthoringProvenanceSchema = z.object({
  actor_type: z.enum(["USER", "AI", "SYSTEM"]),
  operation_id: z.string(),
  timestamp: z.number(),
  mutation_ids: z.array(z.string()),
  base_revision: z.number().int().min(0),
  result_revision: z.number().int().min(0),
  intent_id: z.string().optional(),
});
export type AuthoringProvenance = z.infer<typeof AuthoringProvenanceSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 3. Engine-Neutral Authoring Intents
// ────────────────────────────────────────────────────────────────────────────

export const UpdateTextIntentSchema = z.object({
  type: z.literal("UPDATE_TEXT"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
    selector: z.string().optional(),
  }),
  payload: z.object({
    text: z.string(),
    typography: CanonicalTypographySchema.partial().optional(),
  }),
});
export type UpdateTextIntent = z.infer<typeof UpdateTextIntentSchema>;

export const UpdateTransformIntentSchema = z.object({
  type: z.literal("UPDATE_TRANSFORM"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
    selector: z.string().optional(),
  }),
  payload: z.object({
    transform: z.object({
      position: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      scale: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      rotation: z.number().optional(),
      anchor: z.object({ x: z.number().optional(), y: z.number().optional() }).optional(),
      opacity: z.number().min(0).max(1).optional(),
    }),
    relative: z.boolean().optional(),
  }),
});
export type UpdateTransformIntent = z.infer<typeof UpdateTransformIntentSchema>;

export const UpdateStyleIntentSchema = z.object({
  type: z.literal("UPDATE_STYLE"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
    selector: z.string().optional(),
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
export type UpdateStyleIntent = z.infer<typeof UpdateStyleIntentSchema>;

export const ReplaceMediaIntentSchema = z.object({
  type: z.literal("REPLACE_MEDIA"),
  target: z.object({
    scene_id: StableIdSchema,
    layer_id: StableIdSchema.optional(),
    selector: z.string().optional(),
  }),
  payload: z.object({
    asset_ref: AssetRefSchema,
  }),
});
export type ReplaceMediaIntent = z.infer<typeof ReplaceMediaIntentSchema>;

export const ChangeTimingIntentSchema = z.object({
  type: z.literal("CHANGE_TIMING"),
  target: z.object({
    scene_id: StableIdSchema,
    clip_id: StableIdSchema.optional(),
  }),
  payload: z.object({
    durationFrames: z.number().int().min(1).optional(),
    startFrame: z.number().int().min(0).optional(),
    deltaFrames: z.number().int().optional(),
  }),
});
export type ChangeTimingIntent = z.infer<typeof ChangeTimingIntentSchema>;

export const ApplyTemplateParamIntentSchema = z.object({
  type: z.literal("APPLY_TEMPLATE_PARAM"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    parameter_name: z.string(),
    value: z.any(),
  }),
});
export type ApplyTemplateParamIntent = z.infer<typeof ApplyTemplateParamIntentSchema>;

export const CompoundCommandIntentSchema = z.object({
  type: z.literal("COMPOUND_COMMAND"),
  command_type: z.string(),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.record(z.string(), z.any()),
});
export type CompoundCommandIntent = z.infer<typeof CompoundCommandIntentSchema>;

export const AddLayerIntentSchema = z.object({
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
export type AddLayerIntent = z.infer<typeof AddLayerIntentSchema>;

export const RemoveLayerIntentSchema = z.object({
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
export type RemoveLayerIntent = z.infer<typeof RemoveLayerIntentSchema>;

export const ReorderLayerIntentSchema = z.object({
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
export type ReorderLayerIntent = z.infer<typeof ReorderLayerIntentSchema>;

export const AddSceneIntentSchema = z.object({
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
export type AddSceneIntent = z.infer<typeof AddSceneIntentSchema>;

export const RemoveSceneIntentSchema = z.object({
  type: z.literal("REMOVE_SCENE"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
});
export type RemoveSceneIntent = z.infer<typeof RemoveSceneIntentSchema>;

export const ReorderSceneIntentSchema = z.object({
  type: z.literal("REORDER_SCENE"),
  target: z.object({
    scene_id: StableIdSchema,
  }),
  payload: z.object({
    relative_to: StableIdSchema,
    position: z.enum(["before", "after"]),
  }),
});
export type ReorderSceneIntent = z.infer<typeof ReorderSceneIntentSchema>;

export const UnsupportedIntentSchema = z.object({
  type: z.literal("UNSUPPORTED"),
  operation_name: z.string(),
  reason: z.string(),
  raw_intent: z.record(z.string(), z.any()).optional(),
});
export type UnsupportedIntent = z.infer<typeof UnsupportedIntentSchema>;

export const AuthoringIntentSchema = z.discriminatedUnion("type", [
  UpdateTextIntentSchema,
  UpdateTransformIntentSchema,
  UpdateStyleIntentSchema,
  ReplaceMediaIntentSchema,
  ChangeTimingIntentSchema,
  ApplyTemplateParamIntentSchema,
  CompoundCommandIntentSchema,
  AddLayerIntentSchema,
  RemoveLayerIntentSchema,
  ReorderLayerIntentSchema,
  AddSceneIntentSchema,
  RemoveSceneIntentSchema,
  ReorderSceneIntentSchema,
  UnsupportedIntentSchema,
]);
export type AuthoringIntent = z.infer<typeof AuthoringIntentSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 4. Authoring Request, Operation & Result
// ────────────────────────────────────────────────────────────────────────────

export const AuthoringRequestSchema = z.object({
  request_id: StableIdSchema,
  actor: AuthoringActorSchema,
  base_revision: z.number().int().min(0),
  project_id: StableIdSchema,
  idempotency_key: z.string().optional(),
  description: z.string().optional(),
  intent: AuthoringIntentSchema,
});
export type AuthoringRequest = z.infer<typeof AuthoringRequestSchema>;

export interface AuthoringOperation {
  operation_id: string;
  intent: AuthoringIntent;
  resolved_mutations: CanonicalMutation[];
  is_compound: boolean;
  expected_revision: number;
}

export const AuthoringResultSchema = z.object({
  success: z.boolean(),
  operation_id: z.string(),
  base_revision: z.number().int().min(0),
  result_revision: z.number().int().min(0),
  blueprint: BlueprintV2Schema,
  changeset: z.any(),
  applied_mutation_ids: z.array(z.string()),
  idempotent: z.boolean(),
  diagnostics: z.array(AuthoringDiagnosticSchema),
  provenance: AuthoringProvenanceSchema.optional(),
  error: AuthoringDiagnosticSchema.optional(),
});
export type AuthoringResult = z.infer<typeof AuthoringResultSchema>;
