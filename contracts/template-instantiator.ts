/**
 * contracts/template-instantiator.ts — Canonical Engine-Neutral Template Instantiation Service.
 * S28-R05: Instantiates engine-neutral TemplateSpec + inputs + context into a valid
 * Canonical VideoDocument fragment (BlueprintScene + CanonicalLayer[]) without any
 * renderer, React, Remotion, or subprocess dependencies.
 * ZERO React, Remotion, Canvas, DOM, filesystem, or subprocess dependencies.
 */
import {
  type TemplateSpec,
  type TemplateClassification,
  type TemplateParameter,
} from "./template-spec";
import {
  type BlueprintScene,
  BlueprintSceneSchema,
  type StyleSurface,
  type SceneContent,
  type TransitionRef,
} from "./blueprint";
import {
  type CanonicalLayer,
  validateLayerHierarchy,
  defaultTransform,
} from "./layers";
import {
  createTimeRange,
  type TimeRange,
} from "./timeline";
import {
  type BrandKit,
} from "./brand";
import {
  resolveAssetReference,
  ASSET_ID_REGEX,
} from "./asset-resolver";
import {
  UnknownTemplateError,
} from "./render-input";
import {
  getSemanticTemplateSpec,
} from "../registry/semantic-registry";

// ─── 1. Error Definitions ─────────────────────────────────────────────────────

export class TemplateInputValidationError extends Error {
  public readonly code = "INVALID_TEMPLATE_INPUT";
  public readonly templateId: string;
  public readonly fieldPath: string;
  public readonly reason: string;
  public readonly details: Record<string, any>;

  constructor(options: {
    templateId: string;
    fieldPath: string;
    reason: string;
    details?: Record<string, any>;
  }) {
    super(
      `INVALID_TEMPLATE_INPUT: Template '${options.templateId}' failed input validation at '${options.fieldPath}': ${options.reason}`
    );
    this.name = "TemplateInputValidationError";
    this.templateId = options.templateId;
    this.fieldPath = options.fieldPath;
    this.reason = options.reason;
    this.details = options.details || {};
  }
}

export class EngineBackedTemplateError extends Error {
  public readonly code = "ENGINE_BACKED_TEMPLATE_REQUIRED";
  public readonly templateId: string;
  public readonly requiredCapabilities: string[];
  public readonly reason: string;

  constructor(templateId: string, requiredCapabilities: string[], reason: string) {
    super(
      `ENGINE_BACKED_TEMPLATE_REQUIRED: Template '${templateId}' requires specialized engine execution (${requiredCapabilities.join(
        ", "
      ) || "specialized"}). Reason: ${reason}`
    );
    this.name = "EngineBackedTemplateError";
    this.templateId = templateId;
    this.requiredCapabilities = requiredCapabilities;
    this.reason = reason;
  }
}

export class LegacyCompatibilityTemplateError extends Error {
  public readonly code = "LEGACY_COMPATIBILITY_TEMPLATE";
  public readonly templateId: string;
  public readonly remainingGap: string;

  constructor(templateId: string, remainingGap: string) {
    super(
      `LEGACY_COMPATIBILITY_TEMPLATE: Template '${templateId}' is retained for legacy compatibility. Remaining gap: ${remainingGap}`
    );
    this.name = "LegacyCompatibilityTemplateError";
    this.templateId = templateId;
    this.remainingGap = remainingGap;
  }
}

// ─── 2. Instantiation Context & Result ────────────────────────────────────────

export interface InstantiationContext {
  scene_id?: string;
  startFrame?: number;
  durationFrames?: number;
  fps?: number;
  aspect_ratio?: string;
  brand?: BrandKit;
  media_map?: Record<string, string>;
  projectId?: string;
}

export interface TemplateInstantiationResult {
  ok: true;
  template_id: string;
  classification: TemplateClassification;
  scene: BlueprintScene;
  layers: CanonicalLayer[];
  durationFrames: number;
  metadata: {
    parameters_applied: Record<string, any>;
    slots_bound: Record<string, any>;
    deterministic_seed: string;
  };
}

// Default fallback brand kit for token resolution
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

function resolveBrandTokenValue(token: any, brand: BrandKit): any {
  if (typeof token !== "string") return token;
  if (token === "brand.primary") return brand.colors.primary;
  if (token === "brand.accent") return brand.colors.accent;
  if (token === "brand.background") return brand.colors.background;
  if (token === "brand.text") return brand.colors.text;
  if (token === "brand.surface" && brand.colors.surface) return brand.colors.surface;
  if (token === "brand.display") return brand.fonts.display;
  if (token === "brand.body") return brand.fonts.body;
  if (token === "brand.logo" && brand.logoSrc) return brand.logoSrc;
  return token;
}

// ─── 3. Core Instantiator Implementation ──────────────────────────────────────

export class TemplateInstantiator {
  /**
   * Instantiates a template into a Canonical VideoDocument fragment.
   * Deterministic, fail-closed, engine-neutral.
   */
  public static instantiate(
    templateIdOrAlias: string,
    inputs: Record<string, any> = {},
    context: InstantiationContext = {}
  ): TemplateInstantiationResult {
    // 1. Resolve canonical template spec via registry
    if (!templateIdOrAlias || typeof templateIdOrAlias !== "string" || !templateIdOrAlias.trim()) {
      throw new UnknownTemplateError(templateIdOrAlias || "", context.scene_id || "unspecified");
    }

    const spec = getSemanticTemplateSpec(templateIdOrAlias.trim());
    if (!spec) {
      throw new UnknownTemplateError(templateIdOrAlias, context.scene_id || "unspecified");
    }

    // 2. Fail-closed check for ENGINE_BACKED templates
    if (spec.classification === "ENGINE_BACKED") {
      throw new EngineBackedTemplateError(
        spec.template_id,
        spec.requirements.capabilities,
        spec.compatibility.remaining_gap || spec.metadata.description.en || "Specialized engine required"
      );
    }

    // 3. For LEGACY_COMPATIBILITY templates without native fragment, fail with diagnostic
    if (spec.classification === "LEGACY_COMPATIBILITY" && !spec.fragment) {
      throw new LegacyCompatibilityTemplateError(
        spec.template_id,
        spec.compatibility.remaining_gap || "Pending semantic layer synthesis in R08/R09"
      );
    }

    // 4. Validate inputs against parameter definitions
    const appliedParams: Record<string, any> = {};
    const brand = context.brand || DEFAULT_BRAND;

    // Check required & typed parameters
    for (const [paramName, paramDef] of Object.entries(spec.parameters)) {
      const val = inputs[paramName];
      if (val === undefined || val === null) {
        if (paramDef.required) {
          throw new TemplateInputValidationError({
            templateId: spec.template_id,
            fieldPath: `inputs.${paramName}`,
            reason: `Missing required parameter '${paramName}'`,
          });
        }
        // Apply default if provided
        if (paramDef.default !== undefined) {
          appliedParams[paramName] = resolveBrandTokenValue(paramDef.default, brand);
        }
      } else {
        // Validate type
        TemplateInstantiator.validateParamValue(spec.template_id, paramName, val, paramDef);
        appliedParams[paramName] = resolveBrandTokenValue(val, brand);
      }
    }

    // Check for unrecognized inputs (fail-closed if unknown parameter given)
    const allowedParamKeys = new Set([
      ...Object.keys(spec.parameters),
      ...Object.keys(spec.slots),
      "title",
      "subtitle",
      "text",
      "subtext",
      "backgroundColor",
      "accentColor",
      "color",
      "background",
      "media_refs",
      "transition",
      "durationFrames",
      "startFrame",
      "fps",
      "template_props",
    ]);

    for (const inputKey of Object.keys(inputs)) {
      if (!allowedParamKeys.has(inputKey) && !inputKey.startsWith("_")) {
        throw new TemplateInputValidationError({
          templateId: spec.template_id,
          fieldPath: `inputs.${inputKey}`,
          reason: `Unknown parameter '${inputKey}' not recognized by template '${spec.template_id}'`,
        });
      }
    }

    // 5. Validate duration & constraints
    const durationConstraint = spec.constraints.duration;
    const durationFrames =
      context.durationFrames ??
      inputs.durationFrames ??
      appliedParams.durationFrames ??
      durationConstraint.defaultFrames;

    if (durationConstraint.minFrames && durationFrames < durationConstraint.minFrames) {
      throw new TemplateInputValidationError({
        templateId: spec.template_id,
        fieldPath: "context.durationFrames",
        reason: `Duration ${durationFrames} frames is below minimum required ${durationConstraint.minFrames} frames`,
      });
    }

    if (durationConstraint.maxFrames && durationFrames > durationConstraint.maxFrames) {
      throw new TemplateInputValidationError({
        templateId: spec.template_id,
        fieldPath: "context.durationFrames",
        reason: `Duration ${durationFrames} frames exceeds maximum allowed ${durationConstraint.maxFrames} frames`,
      });
    }

    const aspectRatio = context.aspect_ratio || "16:9";
    if (spec.constraints.aspect_ratios && !spec.constraints.aspect_ratios.includes(aspectRatio)) {
      throw new TemplateInputValidationError({
        templateId: spec.template_id,
        fieldPath: "context.aspect_ratio",
        reason: `Aspect ratio '${aspectRatio}' is not supported by template (supported: ${spec.constraints.aspect_ratios.join(
          ", "
        )})`,
      });
    }

    // 6. Deterministic IDs
    const startFrame = context.startFrame ?? 0;
    const scene_id =
      context.scene_id ||
      `scene_${spec.template_id.replace(/[^a-zA-Z0-9_]/g, "_")}_${startFrame}`;

    const timeRange: TimeRange = createTimeRange(startFrame, durationFrames);

    // 7. Bind slots
    const appliedSlots: Record<string, any> = {};
    for (const [slotId, slotDef] of Object.entries(spec.slots)) {
      let slotVal = inputs[slotId] ?? inputs[slotDef.name] ?? appliedParams[slotId];
      if (slotVal === undefined) {
        if (slotDef.kind === "media") {
          slotVal = appliedParams.media_ref ?? inputs.media_ref ?? appliedParams.asset_ref ?? inputs.asset_ref;
        } else if (slotDef.kind === "text") {
          slotVal = appliedParams.title ?? appliedParams.text ?? inputs.title ?? inputs.text;
        }
      }
      if (slotDef.required && (slotVal === undefined || slotVal === null)) {
        throw new TemplateInputValidationError({
          templateId: spec.template_id,
          fieldPath: `slots.${slotId}`,
          reason: `Missing required slot content for '${slotId}'`,
        });
      }
      if (slotVal !== undefined) {
        appliedSlots[slotId] = slotVal;
      }
    }

    // 8. Synthesize layers deterministically
    const generatedLayers: CanonicalLayer[] = [];
    const mediaMap = context.media_map;

    if (spec.fragment && spec.fragment.default_layers && spec.fragment.default_layers.length > 0) {
      // Clone default layers and adapt time range & bindings
      for (let i = 0; i < spec.fragment.default_layers.length; i++) {
        const baseLayer = spec.fragment.default_layers[i];
        const layerClone: CanonicalLayer = JSON.parse(JSON.stringify(baseLayer));

        // Stable layer ID
        layerClone.layer_id = `${scene_id}_layer_${i}_${layerClone.kind}`;
        layerClone.time_range = timeRange;

        // Apply bindings for this layer
        if (spec.fragment.bindings) {
          for (const binding of spec.fragment.bindings) {
            if (binding.target_layer_id === baseLayer.layer_id || binding.target_layer_id === `layer_${i}`) {
              let valToBind: any = undefined;
              if (binding.source_kind === "parameter") {
                valToBind = appliedParams[binding.source_name] ?? inputs[binding.source_name] ?? binding.default_value;
              } else if (binding.source_kind === "slot") {
                valToBind = appliedSlots[binding.source_name] ?? inputs[binding.source_name] ?? binding.default_value;
              } else if (binding.source_kind === "brand") {
                valToBind = resolveBrandTokenValue(binding.source_name, brand);
              } else if (binding.source_kind === "constant") {
                valToBind = binding.default_value;
              }

              if (valToBind !== undefined) {
                TemplateInstantiator.applyPropertyPath(layerClone, binding.property, valToBind);
              }
            }
          }
        }

        // Resolve asset references if mediaMap is provided
        if ((layerClone.kind === "image" || layerClone.kind === "video") && mediaMap) {
          layerClone.asset_ref = resolveAssetReference(layerClone.asset_ref, mediaMap, {
            fieldPath: `layers[${i}].asset_ref`,
            sceneId: scene_id,
            projectId: context.projectId,
          });
        }

        generatedLayers.push(layerClone);
      }
    } else {
      // Generic synthesis for templates without explicit fragment layers
      const bg = appliedParams.backgroundColor || appliedParams.background || brand.colors.background || "#1a2238";
      const title = appliedParams.title || appliedParams.text || inputs.title || inputs.text || "العنوان";
      const subtitle = appliedParams.subtitle || appliedParams.subtext || inputs.subtitle || inputs.subtext;

      // Layer 0: Background
      generatedLayers.push({
        layer_id: `${scene_id}_bg`,
        kind: "shape",
        time_range: timeRange,
        transform: defaultTransform(),
        opacity: 1,
        visible: true,
        z_index: 0,
        shape_type: "rectangle",
        size: { width: 1920, height: 1080 },
        fillColor: bg,
        channels: [],
      });

      // Layer 1: Title
      generatedLayers.push({
        layer_id: `${scene_id}_title`,
        kind: "text",
        time_range: timeRange,
        transform: {
          position: { x: 0, y: subtitle ? -30 : 0 },
          scale: { x: 1, y: 1 },
          rotation: 0,
          anchor: { x: 0.5, y: 0.5 },
          opacity: 1,
        },
        opacity: 1,
        visible: true,
        z_index: 1,
        text: title,
        typography: {
          fontFamily: brand.fonts.display || "Cairo",
          fontSize: 64,
          textAlign: "center",
          fillColor: appliedParams.color || brand.colors.text || "#FFFFFF",
        },
        channels: [],
      });

      // Layer 2: Subtitle
      if (subtitle) {
        generatedLayers.push({
          layer_id: `${scene_id}_sub`,
          kind: "text",
          time_range: timeRange,
          transform: {
            position: { x: 0, y: 40 },
            scale: { x: 1, y: 1 },
            rotation: 0,
            anchor: { x: 0.5, y: 0.5 },
            opacity: 1,
          },
          opacity: 1,
          visible: true,
          z_index: 2,
          text: subtitle,
          typography: {
            fontFamily: brand.fonts.body || "IBMPlexSansArabic",
            fontSize: 32,
            textAlign: "center",
            fillColor: appliedParams.accentColor || brand.colors.accent || "#94a3b8",
          },
          channels: [],
        });
      }
    }

    // 9. Construct canonical BlueprintScene
    const surface: StyleSurface = {
      text: appliedParams.title || appliedParams.text || inputs.title || inputs.text,
      subtext: appliedParams.subtitle || appliedParams.subtext || inputs.subtitle || inputs.subtext,
      background: appliedParams.backgroundColor || appliedParams.background,
      color: appliedParams.accentColor || appliedParams.color,
      fontFamily: brand.fonts.display,
    };

    const content: SceneContent = {
      lines: surface.text ? [surface.text, ...(surface.subtext ? [surface.subtext] : [])] : [],
    };

    const mediaRefs: string[] = [];
    if (inputs.media_refs && Array.isArray(inputs.media_refs)) {
      mediaRefs.push(
        ...inputs.media_refs.map((ref: string) =>
          resolveAssetReference(ref, mediaMap, {
            fieldPath: `scenes[${scene_id}].media_refs`,
            sceneId: scene_id,
            projectId: context.projectId,
          })
        )
      );
    }

    let transition: TransitionRef | undefined = undefined;
    if (spec.fragment?.default_transition) {
      transition = spec.fragment.default_transition;
    } else if (inputs.transition) {
      transition = inputs.transition;
    }

    const templateProps: Record<string, any> = {};
    if (inputs.template_props && typeof inputs.template_props === "object") {
      Object.assign(templateProps, inputs.template_props);
    }

    const scene: BlueprintScene = {
      scene_id,
      template: spec.template_id,
      startFrame,
      durationFrames,
      surface,
      content,
      media_refs: mediaRefs,
      layers: generatedLayers,
      template_props: templateProps,
      transition,
    };

    // 10. Validate generated scene and layers against Canonical Contracts
    BlueprintSceneSchema.parse(scene);
    const hierarchyRes = validateLayerHierarchy(generatedLayers);
    if (!hierarchyRes.ok) {
      throw new Error(
        `Generated layers for template '${spec.template_id}' failed hierarchy validation: ${hierarchyRes.errors.join(", ")}`
      );
    }

    return {
      ok: true,
      template_id: spec.template_id,
      classification: spec.classification,
      scene,
      layers: generatedLayers,
      durationFrames,
      metadata: {
        parameters_applied: appliedParams,
        slots_bound: appliedSlots,
        deterministic_seed: scene_id,
      },
    };
  }

  private static validateParamValue(
    templateId: string,
    paramName: string,
    val: any,
    paramDef: TemplateParameter
  ): void {
    if (paramDef.type === "number" || paramDef.type === "duration") {
      if (typeof val !== "number" || isNaN(val)) {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Expected number for parameter '${paramName}', received ${typeof val}`,
        });
      }
      if (paramDef.min !== undefined && val < paramDef.min) {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Value ${val} is below minimum allowed ${paramDef.min} for '${paramName}'`,
        });
      }
      if (paramDef.max !== undefined && val > paramDef.max) {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Value ${val} exceeds maximum allowed ${paramDef.max} for '${paramName}'`,
        });
      }
    } else if (paramDef.type === "string" || paramDef.type === "color") {
      if (typeof val !== "string") {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Expected string for parameter '${paramName}', received ${typeof val}`,
        });
      }
    } else if (paramDef.type === "boolean") {
      if (typeof val !== "boolean") {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Expected boolean for parameter '${paramName}', received ${typeof val}`,
        });
      }
    } else if (paramDef.type === "enum") {
      if (paramDef.options && !paramDef.options.includes(val)) {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Invalid enum value '${val}' for '${paramName}'. Expected one of: ${paramDef.options.join(", ")}`,
        });
      }
    } else if (paramDef.type === "asset_ref") {
      if (typeof val !== "string" || !ASSET_ID_REGEX.test(val)) {
        throw new TemplateInputValidationError({
          templateId,
          fieldPath: `inputs.${paramName}`,
          reason: `Invalid asset reference '${val}' for '${paramName}'`,
        });
      }
    }
  }

  private static applyPropertyPath(target: any, path: string, value: any): void {
    const parts = path.split(".");
    let curr = target;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!curr[part] || typeof curr[part] !== "object") {
        curr[part] = {};
      }
      curr = curr[part];
    }
    const lastKey = parts[parts.length - 1];
    if (lastKey === "text" && target.kind === "text" && typeof value !== "string") {
      curr[lastKey] = String(value);
    } else {
      curr[lastKey] = value;
    }
  }
}

/** Convenience shortcut for canonical instantiation */
export function instantiateTemplate(
  templateIdOrAlias: string,
  inputs?: Record<string, any>,
  context?: InstantiationContext
): TemplateInstantiationResult {
  return TemplateInstantiator.instantiate(templateIdOrAlias, inputs, context);
}
