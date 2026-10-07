/**
 * authoring/template-adapter.ts — TemplateSpec to Canonical VideoDocument Instantiation Adapter.
 * S28-R13: Instantiates TemplateSpecs into canonical editable document scenes.
 * 
 * Invariants:
 *   - TemplateSpec is instantiated once to produce canonical BlueprintScene fragments.
 *   - The template DOES NOT remain a persistent competing authority after instantiation.
 *   - AI and User parameter changes (text, subtitle, media, color, duration, layout)
 *     are applied as fine-grained canonical mutations over the stable layer IDs.
 *   - Scenes are NOT re-instantiated needlessly, ensuring user modifications survive.
 */

import type { TemplateSpec } from "../contracts/template-spec";
import {
  TemplateInstantiator,
  type TemplateInstantiationContext,
  type TemplateInstantiationResult,
} from "../contracts/template-instantiator";
import {
  type BlueprintV2,
  type BlueprintScene,
  validateBlueprintV2,
} from "../contracts/blueprint";

export interface InstantiateTemplateDocumentOptions {
  projectId?: string;
  fps?: number;
  aspectRatio?: "9:16" | "16:9" | "1:1" | "4:5" | "21:9";
  sceneId?: string;
}

/**
 * Instantiates a TemplateSpec into a complete authoritative Canonical BlueprintV2.
 */
export function instantiateTemplateToCanonicalDocument(
  spec: TemplateSpec,
  inputs: Record<string, any> = {},
  options?: InstantiateTemplateDocumentOptions
): BlueprintV2 {
  const fps = options?.fps ?? 30;
  const aspectRatio = options?.aspectRatio ?? "16:9";
  const sceneId = options?.sceneId ?? `sc_${spec.template_id}_01`;
  const projectId = options?.projectId ?? `proj_tmpl_${spec.template_id}`;

  const context: TemplateInstantiationContext = {
    scene_id: sceneId,
    startFrame: 0,
    fps,
    aspect_ratio: aspectRatio,
    projectId,
  };

  const templateId = typeof spec === "string" ? spec : spec.template_id;
  const instResult = TemplateInstantiator.instantiate(templateId, inputs, context);
  const scene: BlueprintScene = instResult.scene;

  const blueprint: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: projectId,
    fps,
    aspect_ratio: aspectRatio,
    scenes: [scene],
    revision: 0,
    applied_mutations: [],
    meta: {
      originating_template_id: templateId,
    },
  };

  const validation = validateBlueprintV2(blueprint);
  if (!validation.ok) {
    throw new Error(
      `Template instantiation produced invalid BlueprintV2: ${validation.errors.join("; ")}`
    );
  }

  return blueprint;
}

/**
 * Instantiates a TemplateSpec into a standalone BlueprintScene fragment with stable IDs.
 */
export function instantiateTemplateFragment(
  spec: TemplateSpec | string,
  inputs: Record<string, any> = {},
  context: TemplateInstantiationContext
): TemplateInstantiationResult {
  const templateId = typeof spec === "string" ? spec : spec.template_id;
  return TemplateInstantiator.instantiate(templateId, inputs, context);
}
