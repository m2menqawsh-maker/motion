/**
 * contracts/canonical-video.ts — Single Authoritative Canonical Video Contract Entrypoint.
 * S28-R02: Governs the canonical video authority, schema validation, and normalization.
 * ZERO React or Remotion dependencies.
 */

import {
  type BlueprintV2,
  BlueprintV2Schema,
  type BlueprintScene,
  validateBlueprintV2,
  type BlueprintValidationResult,
  migrateBlueprintToV2,
  isLegacyBlueprintV1,
  type SceneOverride,
  SceneOverrideSchema,
  type Overrides,
  OverridesSchema,
  type TransitionRef,
  TransitionRefSchema,
  SUPPORTED_TRANSITION_TYPES,
  type StyleSurface,
  StyleSurfaceSchema,
  LayoutSchema,
  type Layout,
} from "./blueprint";
import {
  type EffectRef,
  EffectRefSchema,
  isKnownEffect,
  isExecutableEffect,
  getExecutableEffectIds,
  SEMANTIC_EFFECTS_CATALOG,
  type EffectSemanticDefinition,
} from "./effects";
import {
  type AnimationId,
  type AnimationSpec,
  type AnimationDefinition,
  ANIMATION_DEFINITIONS,
  CANONICAL_ANIMATION_IDS,
  isKnownAnimation,
} from "./animations";
import {
  type NormalizedVideo,
  type NormalizedScene,
  type NormalizedAudio,
  type CanonicalVideoInput,
  normalizeCanonicalVideo,
  normalizeBlueprint,
  normalizeScene,
  framesToMs,
  msToFrames,
  calculateTotalDurationFrames,
} from "./normalization";
import type { ManifestV2 } from "./manifest";

export {
  // Authority Schemas & Types
  type BlueprintV2,
  BlueprintV2Schema,
  type BlueprintScene,
  validateBlueprintV2,
  type BlueprintValidationResult,
  migrateBlueprintToV2,
  isLegacyBlueprintV1,
  // Overrides
  type SceneOverride,
  SceneOverrideSchema,
  type Overrides,
  OverridesSchema,
  // Transitions
  type TransitionRef,
  TransitionRefSchema,
  SUPPORTED_TRANSITION_TYPES,
  // Effects
  type EffectRef,
  EffectRefSchema,
  isKnownEffect,
  isExecutableEffect,
  getExecutableEffectIds,
  SEMANTIC_EFFECTS_CATALOG,
  type EffectSemanticDefinition,
  // Animations
  type AnimationId,
  type AnimationSpec,
  type AnimationDefinition,
  ANIMATION_DEFINITIONS,
  CANONICAL_ANIMATION_IDS,
  isKnownAnimation,
  // Normalized Contract Representation
  type NormalizedVideo,
  type NormalizedScene,
  type NormalizedAudio,
  type CanonicalVideoInput,
  normalizeCanonicalVideo,
  normalizeBlueprint,
  normalizeScene,
  // Timing Model
  framesToMs,
  msToFrames,
  calculateTotalDurationFrames,
  // Surface & Layout
  type StyleSurface,
  StyleSurfaceSchema,
  LayoutSchema,
  type Layout,
};

export * from "./timeline";
export * from "./layers";
export * from "./keyframes";
export * from "./evaluator";
export * from "./mutations";
export * from "./editor-session";
export * from "./waveform";
export * from "./authoring";

/**
 * Parses and validates raw input into the canonical BlueprintV2 representation.
 * Fail-closed: throws if invalid schema, broken invariants, or unsupported version.
 */
export function parseCanonicalVideo(
  rawInput: unknown,
  options?: {
    expectedProjectId?: string;
    manifest?: ManifestV2;
  }
): BlueprintV2 {
  if (!rawInput || typeof rawInput !== "object") {
    throw new Error("Canonical video input must be a non-null object");
  }

  // Handle migration if legacy blueprint
  let bpData = rawInput;
  if (isLegacyBlueprintV1(bpData)) {
    bpData = migrateBlueprintToV2(bpData, options?.expectedProjectId);
  }

  const parseResult = BlueprintV2Schema.safeParse(bpData);
  if (!parseResult.success) {
    const errorMessages = parseResult.error.issues.map((i) => `[${i.path.join(".")}] ${i.message}`);
    throw new Error(`Invalid Canonical Video Blueprint: ${errorMessages.join("; ")}`);
  }

  const semanticResult = validateBlueprintV2(parseResult.data, options);
  if (!semanticResult.ok) {
    throw new Error(`Canonical Video Semantic Validation Failed: ${semanticResult.errors.join("; ")}`);
  }

  return parseResult.data;
}

/**
 * Validates canonical video without throwing.
 */
export function validateCanonicalVideo(
  rawInput: unknown,
  options?: {
    expectedProjectId?: string;
    manifest?: ManifestV2;
  }
): BlueprintValidationResult {
  try {
    const blueprint = parseCanonicalVideo(rawInput, options);
    return { ok: true, errors: [], blueprint };
  } catch (err: any) {
    return { ok: false, errors: [err.message] };
  }
}
