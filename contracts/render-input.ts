/**
 * contracts/render-input.ts — Canonical Runtime Render Input Gate & Pre-Mount Validation Authority (S16 - LED-044).
 * Single authority responsible for validating and normalizing raw render input before merge and mount.
 */
import { z } from "zod";
import {
  BlueprintV2Schema,
  validateBlueprintV2,
  isLegacyBlueprintV1,
  migrateBlueprintToV2,
  BlueprintV2,
  BlueprintScene,
  TransitionRefSchema,
  SUPPORTED_TRANSITION_TYPES,
  TransitionRef,
} from "./blueprint";
import { BrandKit } from "./brand";
import { getRegistryEntry } from "../registry/template-registry";
import { EFFECTS_RUNTIME, isKnownEffect, isExecutableEffect } from "../registry/effects-runtime";
import {
  validateTemplatePayload,
  InvalidTemplatePayloadError,
} from "./template-schemas";
import { SceneOverride } from "../remotion-app/src/merge";

// ─── 1. Error Taxonomy ────────────────────────────────────────────────────────

export class RenderInputValidationError extends Error {
  public readonly code: string;
  public readonly details: Record<string, any>;

  constructor(message: string, code = "INVALID_RENDER_INPUT", details: Record<string, any> = {}) {
    super(`${code}: ${message}`);
    this.name = "RenderInputValidationError";
    this.code = code;
    this.details = details;
  }
}

export class InvalidRenderInputError extends RenderInputValidationError {
  constructor(message: string, details: Record<string, any> = {}) {
    super(message, "INVALID_RENDER_INPUT", details);
    this.name = "InvalidRenderInputError";
  }
}

export class UnknownTemplateError extends RenderInputValidationError {
  public readonly templateId: string;
  public readonly sceneId?: string;
  public readonly fieldPath?: string;

  constructor(templateId: string, sceneId?: string, fieldPath?: string) {
    const loc = sceneId ? ` in scene '${sceneId}'` : "";
    const pathMsg = fieldPath ? ` at '${fieldPath}'` : "";
    super(`Unknown template '${templateId}' (Template not found in registry: ${templateId})${loc}${pathMsg}`, "UNKNOWN_TEMPLATE", {
      templateId,
      sceneId,
      fieldPath,
    });
    this.name = "UnknownTemplateError";
    this.templateId = templateId;
    this.sceneId = sceneId;
    this.fieldPath = fieldPath;
  }
}

export class UnknownEffectError extends RenderInputValidationError {
  public readonly effectId: string;
  public readonly sceneId?: string;
  public readonly fieldPath?: string;

  constructor(effectId: string, sceneId?: string, fieldPath?: string) {
    const loc = sceneId ? ` in scene '${sceneId}'` : "";
    const pathMsg = fieldPath ? ` at '${fieldPath}'` : "";
    super(`Unknown effect '${effectId}'${loc}${pathMsg}. Must be registered in EFFECTS_RUNTIME.`, "UNKNOWN_EFFECT", {
      effectId,
      sceneId,
      fieldPath,
    });
    this.name = "UnknownEffectError";
    this.effectId = effectId;
    this.sceneId = sceneId;
    this.fieldPath = fieldPath;
  }
}

export class UnknownTransitionError extends RenderInputValidationError {
  public readonly transitionType: string;
  public readonly sceneId?: string;
  public readonly fieldPath?: string;

  constructor(transitionType: string, sceneId?: string, fieldPath?: string) {
    const loc = sceneId ? ` in scene '${sceneId}'` : "";
    const pathMsg = fieldPath ? ` at '${fieldPath}'` : "";
    const supportedList = SUPPORTED_TRANSITION_TYPES.join(", ");
    super(
      `Unknown transition '${transitionType}'${loc}${pathMsg}. Supported transitions: ${supportedList}`,
      "UNKNOWN_TRANSITION",
      { transitionType, sceneId, fieldPath, supportedTransitions: SUPPORTED_TRANSITION_TYPES }
    );
    this.name = "UnknownTransitionError";
    this.transitionType = transitionType;
    this.sceneId = sceneId;
    this.fieldPath = fieldPath;
  }
}

export { InvalidTemplatePayloadError } from "./template-schemas";

// ─── 2. Input Schemas ────────────────────────────────────────────────────────

export const ProjectMetaSchema = z.object({
  title: z.string().default("Untitled"),
  fps: z.number().int().min(1).max(120).optional(),
  project_id: z.string().optional(),
}).passthrough();

export const BrandColorsSchema = z.object({
  primary: z.string().min(1, "colors.primary is required"),
  accent: z.string().min(1, "colors.accent is required"),
  background: z.string().min(1, "colors.background is required"),
  text: z.string().min(1, "colors.text is required"),
  surface: z.string().optional(),
});

export const BrandFontsSchema = z.object({
  display: z.string().min(1, "fonts.display is required"),
  body: z.string().min(1, "fonts.body is required"),
});

export const BrandKitSchema = z.object({
  brandName: z.string().min(1, "brandName is required").default("Default"),
  logoSrc: z.string().nullable().optional().default(null),
  colors: BrandColorsSchema,
  fonts: BrandFontsSchema,
  tone: z.string().optional(),
});

export const DEFAULT_BRAND_KIT: BrandKit = {
  brandName: "Default",
  logoSrc: null,
  colors: {
    primary: "#00F5FF",
    accent: "#FFD700",
    background: "#0A0E27",
    text: "#FFFFFF"
  },
  fonts: {
    display: "Cairo",
    body: "IBMPlexSansArabic"
  }
};

export const SceneOverrideSchema = z.object({
  props: z.record(z.string(), z.any()).optional(),
  timing: z.object({
    startFrame: z.number().int().optional(),
    durationFrames: z.number().int().optional(),
  }).optional(),
});

export const OverridesSchema = z.object({
  scenes: z.record(z.string(), SceneOverrideSchema).default({}),
}).default({ scenes: {} });

// ─── 3. Canonical Validated Render Input Interface ────────────────────────────

export interface ValidatedRenderInput {
  project: { title: string; fps?: number; project_id?: string; [key: string]: any };
  blueprint: BlueprintV2;
  brand: BrandKit;
  overrides?: { scenes: Record<string, SceneOverride> };
  media_map?: Record<string, string>;
  asset_manifest?: any;
}

// ─── 4. parseRenderInput — The Single Runtime Gate (S16 LED-044) ─────────────

/**
 * Parses and validates raw render input fail-closed.
 * Guarantees that:
 * 1. Raw envelope is valid and unwrapped.
 * 2. Blueprint is validated against BlueprintV2Schema and passes semantic checks.
 * 3. Every scene's template resolves to a registered canonical template.
 * 4. Every effect is registered in EFFECTS_RUNTIME (no silent drop as no-op).
 * 5. Every transition is in SUPPORTED_TRANSITION_TYPES and not dropped.
 * 6. Every scene passes template-specific schema validation before merge/mount.
 */
export function parseRenderInput(rawInput: unknown): ValidatedRenderInput {
  if (!rawInput || typeof rawInput !== "object") {
    throw new InvalidRenderInputError("Raw render input must be a non-null object");
  }

  // Handle { projectData: ... } envelope (Remotion CLI --props convention) or flat structure
  const input = ((rawInput as any).projectData && typeof (rawInput as any).projectData === "object")
    ? (rawInput as any).projectData
    : rawInput;

  if (!input || typeof input !== "object") {
    throw new InvalidRenderInputError("Render input payload must contain an object");
  }

  // 1. Mandatory Blueprint Presence Check
  if (!input.blueprint) {
    throw new InvalidRenderInputError("Missing mandatory 'blueprint' in render input payload");
  }

  const rawProject = input.project && typeof input.project === "object" ? input.project : {};
  const projectId = rawProject.project_id || (input.blueprint as any).project_id;

  // 2. Blueprint Legacy Migration & Canonical Parsing
  let blueprintData = input.blueprint;
  if (isLegacyBlueprintV1(blueprintData)) {
    try {
      blueprintData = migrateBlueprintToV2(blueprintData, projectId);
    } catch (e: any) {
      throw new InvalidRenderInputError(`Failed to migrate legacy blueprint: ${e.message}`, { originalError: e });
    }
  }

  const bpParseResult = BlueprintV2Schema.safeParse(blueprintData);
  if (!bpParseResult.success) {
    for (const issue of bpParseResult.error.issues) {
      const pathStr = issue.path.join(".");
      const sceneIndex = typeof issue.path[1] === "number" ? issue.path[1] : undefined;
      const sceneId = sceneIndex !== undefined ? (blueprintData as any)?.scenes?.[sceneIndex]?.scene_id : undefined;

      if (issue.path.includes("transition") && issue.path.includes("type")) {
        const received = (issue as any).received || String((issue as any).input || "");
        throw new UnknownTransitionError(received, sceneId, pathStr);
      }
      if ((issue.path.includes("effects") && issue.path.includes("effect")) || issue.message.includes("Unknown effect")) {
        const match = issue.message.match(/Unknown effect '([^']+)'/);
        const effectName = match ? match[1] : String((issue as any).received || (issue as any).input || "");
        throw new UnknownEffectError(effectName, sceneId, pathStr);
      }
    }
    const errorMessages = bpParseResult.error.issues.map((i) => `[${i.path.join(".")}] ${i.message}`);
    throw new InvalidRenderInputError(
      `Invalid Blueprint schema: ${errorMessages.join("; ")}`,
      { issues: bpParseResult.error.issues }
    );
  }

  const validatedBlueprint = bpParseResult.data;

  // 3. Blueprint Semantic Validation (Timing, Uniqueness, Asset Kind Checks)
  const semanticResult = validateBlueprintV2(validatedBlueprint, {
    expectedProjectId: projectId,
    manifest: input.asset_manifest,
  });

  if (!semanticResult.ok) {
    throw new InvalidRenderInputError(
      `Blueprint semantic validation failed: ${semanticResult.errors.join("; ")}`,
      { errors: semanticResult.errors }
    );
  }

  // 4. Scene-Level Fail-Closed Verification (Template, Effects, Transitions, Template Props)
  for (let idx = 0; idx < validatedBlueprint.scenes.length; idx++) {
    const scene = validatedBlueprint.scenes[idx];
    const scenePath = `scenes[${idx}] ('${scene.scene_id}')`;

    // 4a. Template Identity Check (S15 Authority)
    const entry = getRegistryEntry(scene.template);
    if (!entry) {
      throw new UnknownTemplateError(scene.template, scene.scene_id, `scenes[${idx}].template`);
    }

    // 4b. Effects Fail-Closed Verification (LED-046)
    if (scene.effects && scene.effects.length > 0) {
      for (let eIdx = 0; eIdx < scene.effects.length; eIdx++) {
        const eff = scene.effects[eIdx];
        if (!isKnownEffect(eff.effect)) {
          throw new UnknownEffectError(eff.effect, scene.scene_id, `scenes[${idx}].effects[${eIdx}].effect`);
        }
        if (!isExecutableEffect(eff.effect)) {
          const reason = EFFECTS_RUNTIME[eff.effect]?.reason || "unbridged";
          throw new UnknownEffectError(
            `${eff.effect} (unsupported: ${reason})`,
            scene.scene_id,
            `scenes[${idx}].effects[${eIdx}].effect`
          );
        }
      }
    }

    // 4c. Transition Fail-Closed Verification (LED-043)
    if (scene.transition) {
      if (!SUPPORTED_TRANSITION_TYPES.includes(scene.transition.type as any)) {
        throw new UnknownTransitionError(scene.transition.type, scene.scene_id, `scenes[${idx}].transition.type`);
      }
    }

    // 4d. Template-Specific Payload Validation (LED-045)
    validateTemplatePayload(entry, scene, `scenes[${idx}]`);
  }

  // 5. Project Metadata Validation (fail closed on malformed project input)
  let validatedProject: { title: string; fps?: number; project_id?: string; [key: string]: any };
  if (input.project !== undefined && input.project !== null) {
    if (typeof input.project !== "object") {
      throw new InvalidRenderInputError("Project metadata must be an object");
    }
    const projectParse = ProjectMetaSchema.safeParse(input.project);
    if (!projectParse.success) {
      const errs = projectParse.error.issues.map((i) => `[project.${i.path.join(".")}] ${i.message}`).join("; ");
      throw new InvalidRenderInputError(`Invalid project metadata: ${errs}`, { issues: projectParse.error.issues });
    }
    validatedProject = { ...projectParse.data, fps: projectParse.data.fps ?? validatedBlueprint.fps };
  } else {
    validatedProject = { title: "Untitled", fps: validatedBlueprint.fps };
  }

  // 6. Brand Kit Validation with Defaults (fail closed on malformed brand input)
  let validatedBrand: BrandKit;
  if (input.brand !== undefined && input.brand !== null) {
    if (typeof input.brand !== "object") {
      throw new InvalidRenderInputError("Brand kit must be an object");
    }
    const brandParse = BrandKitSchema.safeParse(input.brand);
    if (!brandParse.success) {
      const errs = brandParse.error.issues.map((i) => `[brand.${i.path.join(".")}] ${i.message}`).join("; ");
      throw new InvalidRenderInputError(`Invalid brand kit: ${errs}`, { issues: brandParse.error.issues });
    }
    validatedBrand = brandParse.data;
  } else {
    validatedBrand = { ...DEFAULT_BRAND_KIT };
  }

  // 7. Overrides Validation (fail closed on malformed overrides)
  let validatedOverrides: { scenes: Record<string, SceneOverride> } = { scenes: {} };
  if (input.overrides !== undefined && input.overrides !== null) {
    if (typeof input.overrides !== "object") {
      throw new InvalidRenderInputError("Overrides must be an object");
    }
    const overridesParse = OverridesSchema.safeParse(input.overrides);
    if (!overridesParse.success) {
      const errs = overridesParse.error.issues.map((i) => `[overrides.${i.path.join(".")}] ${i.message}`).join("; ");
      throw new InvalidRenderInputError(`Invalid overrides: ${errs}`, { issues: overridesParse.error.issues });
    }
    validatedOverrides = overridesParse.data;
  }

  // 8. Media Map
  const media_map = (input.media_map && typeof input.media_map === "object")
    ? input.media_map
    : undefined;

  return {
    project: validatedProject,
    blueprint: validatedBlueprint,
    brand: validatedBrand,
    overrides: validatedOverrides,
    media_map,
    asset_manifest: input.asset_manifest,
  };
}
