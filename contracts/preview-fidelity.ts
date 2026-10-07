/**
 * contracts/preview-fidelity.ts — Engine-Neutral Preview Fidelity & Capability Resolution Model.
 * S28-R07B: Authoritative classification of video documents and fragments into:
 *   - LIVE_NATIVE: Can be rendered directly by BrowserPreviewRuntime with sufficient fidelity.
 *   - APPROXIMATE_PREVIEW: Feature approximated in-browser explicitly, deterministically, and with clear diagnostics.
 *   - PROXY_RENDER_REQUIRED: Feature cannot be acceptably rendered in-browser; low-res proxy artifact required via RendererRegistry.
 * 
 * Strict Architectural Invariants:
 *   - 100% Engine-neutral: ZERO Remotion, Canvas, React, DOM, or WebGL imports.
 *   - Deterministic and diagnosable classification.
 *   - ZERO silent fake fallbacks.
 */

import { z } from "zod";
import type { BlueprintV2, BlueprintScene } from "./blueprint";
import type { NormalizedVideo, NormalizedScene } from "./normalization";
import {
  type CanonicalRendererCapability,
  deriveRequiredCapabilities,
} from "./renderer";
import { getSemanticTemplateSpec } from "../registry/semantic-registry";

// ────────────────────────────────────────────────────────────────────────────
// 1. Authoritative Preview Mode & Fidelity Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const PreviewModeSchema = z.enum([
  "LIVE_NATIVE",
  "APPROXIMATE_PREVIEW",
  "PROXY_RENDER_REQUIRED",
]);
export type PreviewMode = z.infer<typeof PreviewModeSchema>;

export const PreviewQualityLevelSchema = z.enum(["native", "approximate", "proxy"]);
export type PreviewQualityLevel = z.infer<typeof PreviewQualityLevelSchema>;

export interface PreviewEntityRef {
  id: string;
  type: "scene" | "layer" | "transition" | "template" | "effect";
  classification?: string;
  reason?: string;
  requiredCapabilities?: CanonicalRendererCapability[];
}

export interface PreviewDiagnostics {
  warnings: string[];
  approximateFeatures: string[];
  unsupportedFeatures: string[];
  fallbackStrategy?: string;
  suggestedRendererId?: string;
}

export interface PreviewCapabilityAssessment {
  mode: PreviewMode;
  reason: string;
  required_capabilities: CanonicalRendererCapability[];
  affected_entities: PreviewEntityRef[];
  quality_level: PreviewQualityLevel;
  proxy_required: boolean;
  diagnostics: PreviewDiagnostics;
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Approximation Rules & Transition Taxonomy
// ────────────────────────────────────────────────────────────────────────────

/**
 * GLSL / Hybrid transition types that can be deterministically approximated
 * in live browser preview using cross-fade or basic geometric motion.
 */
export const APPROXIMATABLE_TRANSITIONS = new Set([
  "book-flip",
  "clock-wipe",
  "crosswarp",
  "dreamy-zoom",
  "film-burn",
  "linear-blur",
  "ripple",
  "zoom-blur",
]);

/**
 * Visual effects that can be approximated with deterministic CSS filters in live preview.
 */
export const APPROXIMATABLE_EFFECTS = new Set([
  "blur",
  "grayscale",
  "sepia",
  "brightness",
  "contrast",
  "vignette",
  "glow",
]);

// ────────────────────────────────────────────────────────────────────────────
// 3. Fidelity Resolution Engine
// ────────────────────────────────────────────────────────────────────────────

export interface ResolveFidelityOptions {
  sceneId?: string;
  layerId?: string;
  timeRange?: { startFrame: number; endFrame: number };
  allowApproximation?: boolean;
}

/**
 * Resolves the preview fidelity mode for a canonical document or fragment.
 * Deterministic and engine-neutral.
 */
export function resolvePreviewFidelity(
  doc: BlueprintV2 | NormalizedVideo | any,
  options?: ResolveFidelityOptions
): PreviewCapabilityAssessment {
  const allowApproximation = options?.allowApproximation ?? true;
  const scenes: Array<BlueprintScene | NormalizedScene> = doc.scenes ?? [];
  const requiredCaps = deriveRequiredCapabilities(doc, "frame");

  const affectedEntities: PreviewEntityRef[] = [];
  const warnings: string[] = [];
  const approximateFeatures: string[] = [];
  const unsupportedFeatures: string[] = [];

  let hasProxyRequired = false;
  let hasApproximation = false;
  let primaryReason = "Document features are natively supported by the BrowserPreviewRuntime.";

  const targetScenes = options?.sceneId
    ? scenes.filter((s) => s.scene_id === options.sceneId)
    : scenes;

  for (const scene of targetScenes) {
    // 1. Template Classification Check (R05 semantic taxonomy)
    if (scene.template) {
      const templateId = scene.template;
      const spec = getSemanticTemplateSpec(templateId);

      if (!spec) {
        // Unknown template cannot be rendered without external resolution
        hasProxyRequired = true;
        unsupportedFeatures.push(`unknown_template:${templateId}`);
        affectedEntities.push({
          id: templateId,
          type: "template",
          classification: "UNKNOWN",
          reason: `Template '${templateId}' is unknown to the canonical semantic registry`,
          requiredCapabilities: ["canonical_template_definition" as CanonicalRendererCapability],
        });
      } else if (spec.classification === "ENGINE_BACKED") {
        hasProxyRequired = true;
        const caps = (spec.requirements?.capabilities ?? []) as CanonicalRendererCapability[];
        unsupportedFeatures.push(`engine_backed:${templateId}`);
        affectedEntities.push({
          id: templateId,
          type: "template",
          classification: "ENGINE_BACKED",
          reason: `Template '${templateId}' requires specialized external engine (${caps.join(", ")})`,
          requiredCapabilities: caps,
        });
      } else if (spec.classification === "HYBRID") {
        const shaders = spec.requirements?.gl_shaders ?? [];
        if (shaders.length > 0 && !allowApproximation) {
          hasProxyRequired = true;
          unsupportedFeatures.push(`gl_shaders:${shaders.join(",")}`);
          affectedEntities.push({
            id: templateId,
            type: "template",
            classification: "HYBRID",
            reason: `Template '${templateId}' requires GLSL shader execution`,
            requiredCapabilities: ["custom_shaders", "webgl"],
          });
        } else if (shaders.length > 0) {
          hasApproximation = true;
          approximateFeatures.push(`hybrid_gl_shaders:${templateId}`);
          affectedEntities.push({
            id: templateId,
            type: "template",
            classification: "HYBRID",
            reason: `Template '${templateId}' GLSL shaders approximated with CSS visual blend`,
          });
        }
      } else if (spec.classification === "LEGACY_COMPATIBILITY") {
        hasProxyRequired = true;
        unsupportedFeatures.push(`legacy_compatibility:${templateId}`);
        affectedEntities.push({
          id: templateId,
          type: "template",
          classification: "LEGACY_COMPATIBILITY",
          reason: `Template '${templateId}' requires full external component execution runtime`,
          requiredCapabilities: ["frame_rendering"],
        });
      }
    }

    // 2. Transition Classification Check
    if (scene.transition) {
      const transType = scene.transition.type;
      if (APPROXIMATABLE_TRANSITIONS.has(transType)) {
        if (allowApproximation) {
          hasApproximation = true;
          approximateFeatures.push(`transition:${transType}`);
          affectedEntities.push({
            id: transType,
            type: "transition",
            classification: "HYBRID",
            reason: `Complex transition '${transType}' approximated via cross-dissolve with geometric motion`,
          });
        } else {
          hasProxyRequired = true;
          unsupportedFeatures.push(`transition:${transType}`);
          affectedEntities.push({
            id: transType,
            type: "transition",
            classification: "HYBRID",
            reason: `Transition '${transType}' requires external GLSL shader pass`,
            requiredCapabilities: ["custom_shaders", "webgl"],
          });
        }
      }
    }

    // 3. Layer Specific Checks (if specific layer requested or checking all)
    if (Array.isArray(scene.layers)) {
      for (const layer of scene.layers) {
        if (options?.layerId && layer.layer_id !== options.layerId) {
          continue;
        }

        // Check for unsupported visual effects
        const effects = (layer as any).effects;
        if (Array.isArray(effects)) {
          for (const eff of effects) {
            const effType = typeof eff === "string" ? eff : eff.type;
            if (APPROXIMATABLE_EFFECTS.has(effType)) {
              hasApproximation = true;
              approximateFeatures.push(`effect:${effType}`);
              affectedEntities.push({
                id: layer.layer_id,
                type: "effect",
                classification: "APPROXIMATED",
                reason: `Visual effect '${effType}' approximated via CSS filter`,
              });
            } else {
              hasProxyRequired = true;
              unsupportedFeatures.push(`effect:${effType}`);
              affectedEntities.push({
                id: layer.layer_id,
                type: "effect",
                classification: "CUSTOM_EFFECT",
                reason: `Visual effect '${effType}' cannot be approximated in browser`,
                requiredCapabilities: ["custom_shaders"],
              });
            }
          }
        }
      }
    }
  }

  // 4. Decision Synthesis
  let mode: PreviewMode = "LIVE_NATIVE";
  let qualityLevel: PreviewQualityLevel = "native";
  let proxyRequired = false;

  if (hasProxyRequired) {
    mode = "PROXY_RENDER_REQUIRED";
    qualityLevel = "proxy";
    proxyRequired = true;
    primaryReason = `Document contains ${unsupportedFeatures.length} feature(s) requiring proxy rendering: ${unsupportedFeatures.join(", ")}`;
  } else if (hasApproximation) {
    mode = "APPROXIMATE_PREVIEW";
    qualityLevel = "approximate";
    proxyRequired = false;
    primaryReason = `Document contains approximated feature(s) rendered with approximate fidelity: ${approximateFeatures.join(", ")}`;
  }

  return {
    mode,
    reason: primaryReason,
    required_capabilities: requiredCaps,
    affected_entities: affectedEntities,
    quality_level: qualityLevel,
    proxy_required: proxyRequired,
    diagnostics: {
      warnings,
      approximateFeatures,
      unsupportedFeatures,
      fallbackStrategy: hasProxyRequired
        ? "Render low-resolution proxy via RendererRegistry; show placeholder until proxy ready"
        : hasApproximation
        ? "Deterministic CSS / DOM approximation with metadata badge"
        : undefined,
    },
  };
}
