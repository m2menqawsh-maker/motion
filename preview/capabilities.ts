/**
 * preview/capabilities.ts — Browser Live Preview Capability Detection & Guard.
 * S28-R06: Detects and validates engine capabilities required by templates and layers.
 * Enforces explicit diagnostics and fail-closed handling for:
 *   - ENGINE_BACKED templates (MapLibre, WebGL 3D, Particle Physics)
 *   - HYBRID templates (WebGL GLSL Shaders)
 *   - LEGACY_COMPATIBILITY templates (TSX Remotion components)
 * ZERO silent fake fallbacks or disguised compatibility.
 */
import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import type { NormalizedVideo, NormalizedScene } from "../contracts/normalization";
import { getSemanticTemplateSpec } from "../registry/semantic-registry";
import type { UnsupportedCapabilityReport, UnsupportedCapabilityDetail } from "./types";
export * from "../contracts/preview-fidelity";

export class UnsupportedPreviewCapabilityError extends Error {
  public readonly code = "UNSUPPORTED_PREVIEW_CAPABILITY";
  public readonly report: UnsupportedCapabilityReport;

  constructor(report: UnsupportedCapabilityReport) {
    const summary = report.unsupportedEntities
      .map((e) => `[${e.classification}] ${e.entityType} '${e.entityId}': ${e.reason}`)
      .join("; ");
    super(`UNSUPPORTED_PREVIEW_CAPABILITY: Preview runtime cannot render document: ${summary}`);
    this.name = "UnsupportedPreviewCapabilityError";
    this.report = report;
  }
}

/**
 * Inspects a canonical video document for any features that the pure browser
 * live preview runtime cannot natively render.
 */
export function inspectDocumentCapabilities(
  doc: BlueprintV2 | NormalizedVideo | any
): UnsupportedCapabilityReport {
  const unsupportedEntities: UnsupportedCapabilityDetail[] = [];
  const missingCaps = new Set<string>();

  const scenes: Array<BlueprintScene | NormalizedScene> = doc.scenes ?? [];

  for (const scene of scenes) {
    const templateId = scene.template;
    if (!templateId) continue;

    const spec = getSemanticTemplateSpec(templateId);
    if (!spec) {
      // Unknown template
      unsupportedEntities.push({
        entityId: templateId,
        entityType: "template",
        classification: "UNKNOWN",
        reason: `Template '${templateId}' is unknown to the canonical registry`,
        requiredCapabilities: ["unknown_template_loader"],
      });
      missingCaps.add("canonical_template_definition");
      continue;
    }

    if (spec.classification === "ENGINE_BACKED") {
      const caps = spec.requirements?.capabilities ?? [];
      const libs = spec.requirements?.external_libraries ?? [];
      const reason =
        templateId === "rui-map-flight"
          ? "Requires WebGL MapLibre vector tile rendering engine"
          : templateId === "scene3d-element"
          ? "Requires 3D WebGL mesh perspective camera engine"
          : templateId === "particlesystem-element"
          ? "Requires runtime physics particle spawner simulation"
          : `Requires specialized engine capabilities: ${[...caps, ...libs].join(", ")}`;

      unsupportedEntities.push({
        entityId: templateId,
        entityType: "template",
        classification: "ENGINE_BACKED",
        reason,
        requiredCapabilities: [...caps, ...libs],
      });
      for (const c of [...caps, ...libs]) missingCaps.add(c);
    } else if (spec.classification === "HYBRID") {
      const shaders = spec.requirements?.gl_shaders ?? [];
      const reason =
        shaders.length > 0
          ? `Requires WebGL GLSL shader execution (${shaders.join(", ")})`
          : `Requires hybrid runtime execution capabilities`;

      unsupportedEntities.push({
        entityId: templateId,
        entityType: "template",
        classification: "HYBRID",
        reason,
        requiredCapabilities: shaders.length > 0 ? ["webgl_glsl_shaders"] : ["hybrid_runtime"],
      });
      missingCaps.add("webgl_glsl_shaders");
    } else if (spec.classification === "LEGACY_COMPATIBILITY") {
      unsupportedEntities.push({
        entityId: templateId,
        entityType: "template",
        classification: "LEGACY_COMPATIBILITY",
        reason: `Complex legacy template '${templateId}' requires full React TSX component execution (deferred to R08/R09)`,
        requiredCapabilities: ["remotion_tsx_runtime"],
      });
      missingCaps.add("remotion_tsx_runtime");
    }

    // Inspect transitions in scenes
    if (scene.transition) {
      const transType = scene.transition.type;
      const hybridTransitions = [
        "book-flip",
        "clock-wipe",
        "crosswarp",
        "dreamy-zoom",
        "film-burn",
        "linear-blur",
        "ripple",
        "zoom-blur",
      ];
      if (hybridTransitions.includes(transType)) {
        unsupportedEntities.push({
          entityId: transType,
          entityType: "transition",
          classification: "HYBRID",
          reason: `Transition '${transType}' requires WebGL shader pass`,
          requiredCapabilities: ["webgl_glsl_transition_shader"],
        });
        missingCaps.add("webgl_glsl_transition_shader");
      }
    }
  }

  const isSupported = unsupportedEntities.length === 0;

  return {
    isSupported,
    unsupportedEntities,
    missingCapabilities: Array.from(missingCaps),
  };
}

/**
 * Asserts that the document is natively previewable. Throws if unsupported
 * when failClosed is true.
 */
export function assertPreviewSupported(
  doc: BlueprintV2 | NormalizedVideo | any,
  options?: { failClosed?: boolean }
): UnsupportedCapabilityReport {
  const report = inspectDocumentCapabilities(doc);
  if (!report.isSupported && options?.failClosed) {
    throw new UnsupportedPreviewCapabilityError(report);
  }
  return report;
}
