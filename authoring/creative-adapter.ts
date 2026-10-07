/**
 * authoring/creative-adapter.ts — CreativePlan to Canonical VideoDocument Compiler Adapter.
 * S28-R13: Adapts upstream S28 CreativePlan proposals into authoritative BlueprintV2 documents.
 * 
 * Invariants:
 *   - CreativePlan is an input proposal/planning representation ONLY.
 *   - Once compiled into BlueprintV2, the Canonical VideoDocument becomes the SINGLE AUTHORITY.
 *   - Subsequent AI and User edits are executed exclusively as typed mutations on BlueprintV2.
 *   - Recompiling the entire CreativePlan after initial creation is STRICTLY FORBIDDEN,
 *     guaranteeing that user customizations survive downstream AI modifications.
 */

import {
  type BlueprintV2,
  type BlueprintScene,
  BlueprintV2Schema,
  validateBlueprintV2,
} from "../contracts/blueprint";
import { type CanonicalLayer, defaultTransform } from "../contracts/layers";
import { createTimeRange } from "../contracts/timeline";

export interface CreativePlanCompilationOptions {
  projectId?: string;
  fps?: number;
  aspectRatio?: "9:16" | "16:9" | "1:1" | "4:5" | "21:9";
  templateMapping?: Record<string, string>;
}

export interface CreativeSceneIntent {
  scene_id: string;
  scene_index?: number;
  beat_id?: string;
  intent_label?: string;
  estimated_duration_sec?: number;
  spoken_text?: string;
  mood?: string;
  motion_personality?: string;
}

export interface CreativePlanLike {
  plan_id: string;
  brief_id?: string;
  title: string;
  scenes: CreativeSceneIntent[];
  narrative_plan?: any;
  total_estimated_duration_sec?: number;
  tier_decisions?: any[];
}

/**
 * Compiles a high-level CreativePlan into an authoritative, editable Canonical BlueprintV2.
 * Pure deterministic compilation with fail-closed schema validation.
 */
export function compileCreativePlanToCanonical(
  plan: CreativePlanLike,
  options?: CreativePlanCompilationOptions
): BlueprintV2 {
  if (!plan || !plan.scenes || plan.scenes.length === 0) {
    throw new Error("Cannot compile CreativePlan: Plan must contain at least one scene.");
  }

  const fps = options?.fps ?? 30;
  const aspectRatio = options?.aspectRatio ?? "9:16";
  const projectId = (options?.projectId || plan.brief_id || plan.plan_id || "proj_cplan")
    .replace(/[^a-zA-Z0-9_\-]/g, "_");

  const scenes: BlueprintScene[] = [];
  let currentStartFrame = 0;

  for (let i = 0; i < plan.scenes.length; i++) {
    const sc = plan.scenes[i];
    const durationSec = sc.estimated_duration_sec ?? 5.0;
    const durationFrames = Math.max(1, Math.round(durationSec * fps));
    const startFrame = currentStartFrame;
    const timeRange = createTimeRange(startFrame, durationFrames);

    // Template decision mapping
    let templateId = "StatCard";
    if (options?.templateMapping && options.templateMapping[sc.scene_id]) {
      templateId = options.templateMapping[sc.scene_id];
    } else if (sc.intent_label === "hook") {
      templateId = "kinetic_typography";
    } else if (sc.intent_label === "cta") {
      templateId = "cta_minimal";
    }

    const titleText = sc.spoken_text || `${plan.title} - Beat ${i + 1}`;
    const subtitleText = sc.intent_label ? `Scene Phase: ${sc.intent_label}` : undefined;

    // Synthesize canonical layer stack with deterministic stable IDs
    const layers: CanonicalLayer[] = [
      // Layer 0: Background shape
      {
        layer_id: `${sc.scene_id}_bg`,
        kind: "shape",
        time_range: timeRange,
        transform: defaultTransform(),
        opacity: 1,
        visible: true,
        z_index: 0,
        shape_type: "rectangle",
        size: { width: 1080, height: 1920 },
        fillColor: i % 2 === 0 ? "#0d1117" : "#161b22",
        channels: [],
      },
      // Layer 1: Title text
      {
        layer_id: `${sc.scene_id}_title`,
        kind: "text",
        time_range: timeRange,
        transform: {
          position: { x: 0, y: subtitleText ? -30 : 0 },
          scale: { x: 1, y: 1 },
          rotation: 0,
          anchor: { x: 0.5, y: 0.5 },
          opacity: 1,
        },
        opacity: 1,
        visible: true,
        z_index: 1,
        text: titleText,
        typography: {
          fontFamily: "Cairo",
          fontSize: 60,
          textAlign: "center",
          fillColor: "#FFFFFF",
        },
        channels: [],
      },
    ];

    // Layer 2: Subtitle if applicable
    if (subtitleText) {
      layers.push({
        layer_id: `${sc.scene_id}_sub`,
        kind: "text",
        time_range: timeRange,
        transform: {
          position: { x: 0, y: 50 },
          scale: { x: 1, y: 1 },
          rotation: 0,
          anchor: { x: 0.5, y: 0.5 },
          opacity: 1,
        },
        opacity: 1,
        visible: true,
        z_index: 2,
        text: subtitleText,
        typography: {
          fontFamily: "IBMPlexSansArabic",
          fontSize: 28,
          textAlign: "center",
          fillColor: "#58a6ff",
        },
        channels: [],
      });
    }

    const scene: BlueprintScene = {
      scene_id: sc.scene_id,
      template: templateId,
      startFrame,
      durationFrames,
      surface: {
        text: titleText,
        subtext: subtitleText,
        background: i % 2 === 0 ? "#0d1117" : "#161b22",
        color: "#FFFFFF",
        fontFamily: "Cairo",
      },
      layers,
    };

    scenes.push(scene);
    currentStartFrame += durationFrames;
  }

  const blueprint: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: projectId,
    fps,
    aspect_ratio: aspectRatio,
    scenes,
    revision: 0,
    applied_mutations: [],
    meta: {
      originating_plan_id: plan.plan_id,
      title: plan.title,
    },
  };

  const validation = validateBlueprintV2(blueprint);
  if (!validation.ok) {
    throw new Error(
      `CreativePlan compilation resulted in invalid BlueprintV2: ${validation.errors.join("; ")}`
    );
  }

  return blueprint;
}
