/**
 * contracts/template-spec.ts — Authoritative Engine-Neutral TemplateSpec Contract.
 * S28-R05: Formal semantic video template specification, parameter contracts,
 * slots, constraints, requirements, and fragment definitions.
 * ZERO React, Remotion, TSX, JSX, Canvas, DOM, or renderer dependencies.
 */
import { z } from "zod";
import {
  CanonicalLayerSchema,
  type CanonicalLayer,
} from "./layers";
import {
  StyleSurfaceSchema,
  type StyleSurface,
  SceneContentSchema,
  type SceneContent,
  TransitionRefSchema,
  type TransitionRef,
} from "./blueprint";

// ─── 1. Template Classification Enum ──────────────────────────────────────────

export const TemplateClassificationSchema = z.enum([
  "NATIVE",
  "ENGINE_BACKED",
  "HYBRID",
  "LEGACY_COMPATIBILITY",
]);
export type TemplateClassification = z.infer<typeof TemplateClassificationSchema>;

// ─── 2. Parameter Model ───────────────────────────────────────────────────────

export const TemplateParameterTypeSchema = z.enum([
  "string",
  "number",
  "boolean",
  "enum",
  "asset_ref",
  "color",
  "duration",
  "rich_text",
  "list",
]);
export type TemplateParameterType = z.infer<typeof TemplateParameterTypeSchema>;

export const TemplateParameterSchema = z.object({
  name: z.string().min(1),
  type: TemplateParameterTypeSchema,
  required: z.boolean().default(false),
  default: z.any().optional(),
  description: z.string().optional(),
  options: z.array(z.string()).optional(), // for enum
  min: z.number().optional(), // for number / duration
  max: z.number().optional(), // for number / duration
  step: z.number().optional(),
  asset_kind: z.enum(["image", "video", "audio"]).optional(),
});
export type TemplateParameter = z.infer<typeof TemplateParameterSchema>;

// ─── 3. Slot Model ────────────────────────────────────────────────────────────

export const TemplateSlotKindSchema = z.enum([
  "text",
  "media",
  "background",
  "layer",
  "audio",
]);
export type TemplateSlotKind = z.infer<typeof TemplateSlotKindSchema>;

export const TemplateSlotSchema = z.object({
  slot_id: z.string().min(1),
  name: z.string().min(1),
  kind: TemplateSlotKindSchema,
  required: z.boolean().default(false),
  description: z.string().optional(),
  target_layer_id: z.string().optional(),
  allowed_kinds: z.array(z.string()).optional(),
});
export type TemplateSlot = z.infer<typeof TemplateSlotSchema>;

// ─── 4. Requirements & Constraints ────────────────────────────────────────────

export const TemplateRequirementsSchema = z.object({
  asset_kinds: z.array(z.enum(["image", "video", "audio"])).default([]),
  fonts: z.array(z.string()).default([]),
  capabilities: z.array(z.string()).default([]),
  audio: z
    .object({
      voiceover_supported: z.boolean().default(true),
      bgm_supported: z.boolean().default(true),
    })
    .default({ voiceover_supported: true, bgm_supported: true }),
});
export type TemplateRequirements = z.infer<typeof TemplateRequirementsSchema>;

export const TemplateConstraintsSchema = z.object({
  duration: z.object({
    minFrames: z.number().int().min(1).optional(),
    maxFrames: z.number().int().min(1).optional(),
    defaultFrames: z.number().int().min(1).default(150),
  }),
  aspect_ratios: z
    .array(z.string())
    .default(["16:9", "9:16", "1:1", "4:5", "21:9"]),
  supported_media_kinds: z.array(z.string()).default(["image", "video"]),
});
export type TemplateConstraints = z.infer<typeof TemplateConstraintsSchema>;

// ─── 5. Compatibility & Provenance ────────────────────────────────────────────

export const TemplateCompatibilitySchema = z.object({
  legacy_aliases: z.array(z.string()).default([]),
  legacy_component_name: z.string().optional(),
  legacy_implementation_path: z.string().optional(),
  engine_metadata: z.record(z.string(), z.any()).optional(),
  remaining_gap: z.string().optional(),
  migration_owner: z.string().optional(),
});
export type TemplateCompatibility = z.infer<typeof TemplateCompatibilitySchema>;

export const TemplateProvenanceSchema = z.object({
  source: z.string().default("canonical-registry"),
  migration_source: z.string().optional(),
  created_at: z.string().optional(),
  version_hash: z.string().optional(),
});
export type TemplateProvenance = z.infer<typeof TemplateProvenanceSchema>;

// ─── 6. Fragment Model & Layer Bindings ────────────────────────────────────────

export const TemplateLayerBindingSchema = z.object({
  target_layer_id: z.string().min(1),
  property: z.string().min(1),
  source_kind: z.enum(["parameter", "slot", "constant", "brand"]),
  source_name: z.string().min(1),
  default_value: z.any().optional(),
});
export type TemplateLayerBinding = z.infer<typeof TemplateLayerBindingSchema>;

export const TemplateFragmentSchema = z.object({
  template_type: z.enum([
    "SCENE_TEMPLATE",
    "ELEMENT_TEMPLATE",
    "EFFECT_TEMPLATE",
    "TRANSITION_TEMPLATE",
    "FULL_TEMPLATE",
  ]),
  default_layers: z.array(CanonicalLayerSchema).default([]),
  bindings: z.array(TemplateLayerBindingSchema).default([]),
  default_surface: StyleSurfaceSchema.optional(),
  default_content: SceneContentSchema.optional(),
  default_transition: TransitionRefSchema.optional(),
});
export type TemplateFragment = z.infer<typeof TemplateFragmentSchema>;

// ─── 7. Authoritative TemplateSpec Schema ─────────────────────────────────────

export const TemplateSpecSchema = z.object({
  template_id: z
    .string()
    .regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "Template ID must be lowercase kebab-case"),
  version: z.string().default("2.0.0"),
  status: z.enum(["experimental", "verified", "production"]).default("verified"),
  classification: TemplateClassificationSchema,
  metadata: z.object({
    display_name: z.object({
      ar: z.string(),
      en: z.string(),
    }),
    description: z.object({
      ar: z.string(),
      en: z.string(),
    }),
    category: z.string().min(1),
    family: z.string().optional(),
    tags: z.array(z.string()).default([]),
  }),
  supported_document_version: z.string().default("2.0.0"),
  parameters: z.record(z.string(), TemplateParameterSchema).default({}),
  slots: z.record(z.string(), TemplateSlotSchema).default({}),
  requirements: TemplateRequirementsSchema.default({
    asset_kinds: [],
    fonts: [],
    capabilities: [],
    audio: { voiceover_supported: true, bgm_supported: true },
  }),
  constraints: TemplateConstraintsSchema,
  fragment: TemplateFragmentSchema.optional(),
  compatibility: TemplateCompatibilitySchema.default({ legacy_aliases: [] }),
  provenance: TemplateProvenanceSchema.default({ source: "canonical-registry" }),
});
export type TemplateSpec = z.infer<typeof TemplateSpecSchema>;

// ─── 8. Rigorous Schema & Purity Validator ────────────────────────────────────

export interface TemplateValidationResult {
  ok: boolean;
  errors: string[];
}

export function validateTemplateSpec(spec: unknown): TemplateValidationResult {
  const errors: string[] = [];

  const parseRes = TemplateSpecSchema.safeParse(spec);
  if (!parseRes.success) {
    for (const issue of parseRes.error.issues) {
      errors.push(`${issue.path.join(".")}: ${issue.message}`);
    }
    return { ok: false, errors };
  }

  const valid = parseRes.data;

  // Strict architectural purity checks:
  // Reject any executable / framework functions, classes, or symbols in spec
  const forbiddenKeys = [
    "render",
    "component",
    "jsx",
    "interpolate_fn",
    "spring_fn",
    "frame_hook",
  ];
  for (const key of forbiddenKeys) {
    if (key in (valid as any)) {
      errors.push(`TemplateSpec violated purity rule: illegal property '${key}'`);
    }
  }

  // Classification specific invariants
  if (valid.classification === "NATIVE") {
    if (!valid.fragment) {
      errors.push(`NATIVE template '${valid.template_id}' must define a canonical fragment`);
    }
  } else if (valid.classification === "ENGINE_BACKED") {
    if (valid.requirements.capabilities.length === 0 && !valid.compatibility.remaining_gap) {
      errors.push(
        `ENGINE_BACKED template '${valid.template_id}' must explicitly document required capabilities or engine gap`
      );
    }
  } else if (valid.classification === "LEGACY_COMPATIBILITY") {
    if (!valid.compatibility.remaining_gap && !valid.compatibility.migration_owner) {
      errors.push(
        `LEGACY_COMPATIBILITY template '${valid.template_id}' must specify remaining_gap or migration_owner`
      );
    }
  }

  return { ok: errors.length === 0, errors };
}
