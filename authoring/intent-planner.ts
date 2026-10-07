/**
 * authoring/intent-planner.ts — Pure Engine-Neutral Intent-to-Mutation Planner.
 * S28-R13: Translates AI & User AuthoringIntents into typed CanonicalMutations.
 * 
 * Invariants:
 *   - Pure, deterministic, zero-AI-SDK, zero-renderer, zero-side-effects.
 *   - Strict Stable-ID entity targeting (scene_id, layer_id, clip_id, keyframe_id).
 *   - Fail-closed error handling with structured diagnostics:
 *       * AUTHORING_TARGET_NOT_FOUND: entity ID does not exist in document
 *       * AUTHORING_TARGET_AMBIGUOUS: selector matches multiple candidate layers
 *       * UNSUPPORTED_AUTHORING_OPERATION: unsupported capability / 3D / direct code
 *       * AUTHORING_VALIDATION_FAILED: schema or constraint violation
 *   - Generates single mutations or atomic MutationBatches for compound commands.
 */

import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import type { CanonicalLayer } from "../contracts/layers";
import {
  type CanonicalMutation,
  type UpdateTextMutation,
  type UpdateTransformMutation,
  type UpdateStyleMutation,
  type ReplaceMediaMutation,
  type TrimClipMutation,
  type AddLayerMutation,
  type RemoveLayerMutation,
  type ReorderLayerMutation,
  type AddSceneMutation,
  type RemoveSceneMutation,
  type ReorderSceneMutation,
} from "../contracts/mutations";
import {
  type AuthoringRequest,
  type AuthoringIntent,
  type AuthoringDiagnostic,
  AuthoringRequestSchema,
} from "../contracts/authoring";

export interface IntentPlanningSuccess {
  ok: true;
  mutations: CanonicalMutation[];
  is_compound: boolean;
  description: string;
  diagnostics: AuthoringDiagnostic[];
}

export interface IntentPlanningFailure {
  ok: false;
  error: AuthoringDiagnostic;
  diagnostics: AuthoringDiagnostic[];
}

export type IntentPlanningResult = IntentPlanningSuccess | IntentPlanningFailure;

// Forbidden keywords indicating unsupported render-specific or non-canonical requests
const FORBIDDEN_CAPABILITY_PATTERNS = [
  /3d[\s_-]?hologra/i,
  /particle[\s_-]?city/i,
  /holographic/i,
  /webgl[\s_-]?shader/i,
  /direct[\s_-]?code/i,
  /eval[\s_-]?tsx/i,
  /remotion[\s_-]?code/i,
  /react[\s_-]?component/i,
  /ffmpeg[\s_-]?filter/i,
];

function checkForbiddenPatterns(text: string): string | null {
  for (const pattern of FORBIDDEN_CAPABILITY_PATTERNS) {
    if (pattern.test(text)) {
      return `Requested capability matches unsupported pattern: ${pattern.source}`;
    }
  }
  return null;
}

/**
 * Resolves a target layer in a scene either by exact layer_id or by selector query.
 * Fails closed if not found or if selector is ambiguous.
 */
function resolveTargetLayer(
  scene: BlueprintScene,
  layerId?: string,
  selector?: string
): { layer?: CanonicalLayer; error?: AuthoringDiagnostic } {
  if (layerId) {
    const found = scene.layers?.find((l) => l.layer_id === layerId);
    if (!found) {
      return {
        error: {
          code: "AUTHORING_TARGET_NOT_FOUND",
          message: `Target layer '${layerId}' not found in scene '${scene.scene_id}'`,
          target_id: layerId,
        },
      };
    }
    return { layer: found };
  }

  if (selector && scene.layers) {
    const lowerSel = selector.toLowerCase().trim();
    const matches = scene.layers.filter((l) => {
      if (lowerSel === "title") return l.layer_id.includes("title") || (l.kind === "text" && l.z_index === 1);
      if (lowerSel === "subtitle" || lowerSel === "sub") return l.layer_id.includes("sub");
      if (lowerSel === "bg" || lowerSel === "background") return l.kind === "shape" && (l.layer_id.includes("bg") || l.layer_id.includes("background"));
      if (lowerSel === "image") return l.kind === "image";
      if (lowerSel === "video") return l.kind === "video";
      if (lowerSel === "text") return l.kind === "text";
      return l.layer_id.toLowerCase().includes(lowerSel);
    });

    if (matches.length === 0) {
      return {
        error: {
          code: "AUTHORING_TARGET_NOT_FOUND",
          message: `Target selector '${selector}' did not match any layer in scene '${scene.scene_id}'`,
          target_id: selector,
        },
      };
    }

    if (matches.length > 1) {
      return {
        error: {
          code: "AUTHORING_TARGET_AMBIGUOUS",
          message: `Target selector '${selector}' is ambiguous: matched ${matches.length} layers [${matches
            .map((m) => m.layer_id)
            .join(", ")}]. Must target by exact layer_id.`,
          target_id: selector,
          details: { matched_layer_ids: matches.map((m) => m.layer_id) },
        },
      };
    }

    return { layer: matches[0] };
  }

  return {};
}

/**
 * Pure Deterministic Planner: Transforms high-level authoring requests into typed canonical mutations.
 */
export function planAuthoringIntent(
  blueprint: BlueprintV2,
  requestInput: unknown
): IntentPlanningResult {
  const parseRes = AuthoringRequestSchema.safeParse(requestInput);
  if (!parseRes.success) {
    return {
      ok: false,
      error: {
        code: "AUTHORING_VALIDATION_FAILED",
        message: `AuthoringRequest schema validation failed: ${parseRes.error.issues
          .map((i) => i.message)
          .join("; ")}`,
      },
      diagnostics: [],
    };
  }

  const req = parseRes.data;
  const intent = req.intent;
  const actor = req.actor;
  const baseRev = req.base_revision;

  // 1. Guard against unsupported requests
  if (intent.type === "UNSUPPORTED") {
    return {
      ok: false,
      error: {
        code: "UNSUPPORTED_AUTHORING_OPERATION",
        message: `Unsupported authoring operation '${intent.operation_name}': ${intent.reason}`,
        details: intent.raw_intent,
      },
      diagnostics: [],
    };
  }

  // Scan description and parameters for forbidden patterns (e.g. 3D holographic particles, direct code emission)
  const fullTextScan = JSON.stringify(intent) + (req.description ?? "");
  const forbiddenMatch = checkForbiddenPatterns(fullTextScan);
  if (forbiddenMatch) {
    return {
      ok: false,
      error: {
        code: "UNSUPPORTED_AUTHORING_OPERATION",
        message: forbiddenMatch,
        details: { requested_operation: intent.type },
      },
      diagnostics: [],
    };
  }

  // 2. Dispatch by intent type
  switch (intent.type) {
    case "UPDATE_TEXT": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const layerRes = resolveTargetLayer(scene, intent.target.layer_id, intent.target.selector);
      if (layerRes.error) {
        return { ok: false, error: layerRes.error, diagnostics: [layerRes.error] };
      }

      const resolvedLayerId = layerRes.layer?.layer_id ?? intent.target.layer_id;

      const mutation: UpdateTextMutation = {
        mutation_id: `mut_${req.request_id}_text`,
        expected_revision: baseRev,
        author: actor,
        description: req.description ?? `Update text in scene ${scene.scene_id}`,
        type: "UPDATE_TEXT",
        target: {
          scene_id: scene.scene_id,
          layer_id: resolvedLayerId,
        },
        payload: {
          text: intent.payload.text,
          typography: intent.payload.typography,
        },
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: mutation.description!,
        diagnostics: [],
      };
    }

    case "UPDATE_TRANSFORM": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const layerRes = resolveTargetLayer(scene, intent.target.layer_id, intent.target.selector);
      if (layerRes.error) {
        return { ok: false, error: layerRes.error, diagnostics: [layerRes.error] };
      }

      const resolvedLayerId = layerRes.layer?.layer_id ?? intent.target.layer_id;

      // Calculate relative delta if requested
      const payloadTransform = { ...intent.payload.transform };
      if (intent.payload.relative && layerRes.layer) {
        const cur = layerRes.layer.transform;
        if (payloadTransform.position) {
          payloadTransform.position = {
            x: (cur.position?.x ?? 0) + (payloadTransform.position.x ?? 0),
            y: (cur.position?.y ?? 0) + (payloadTransform.position.y ?? 0),
          };
        }
      }

      const mutation: UpdateTransformMutation = {
        mutation_id: `mut_${req.request_id}_xform`,
        expected_revision: baseRev,
        author: actor,
        description: req.description ?? `Update transform in scene ${scene.scene_id}`,
        type: "UPDATE_TRANSFORM",
        target: {
          scene_id: scene.scene_id,
          layer_id: resolvedLayerId,
        },
        payload: {
          transform: payloadTransform,
        },
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: mutation.description!,
        diagnostics: [],
      };
    }

    case "UPDATE_STYLE": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const layerRes = resolveTargetLayer(scene, intent.target.layer_id, intent.target.selector);
      if (layerRes.error) {
        return { ok: false, error: layerRes.error, diagnostics: [layerRes.error] };
      }

      const resolvedLayerId = layerRes.layer?.layer_id ?? intent.target.layer_id;

      const mutation: UpdateStyleMutation = {
        mutation_id: `mut_${req.request_id}_style`,
        expected_revision: baseRev,
        author: actor,
        description: req.description ?? `Update style in scene ${scene.scene_id}`,
        type: "UPDATE_STYLE",
        target: {
          scene_id: scene.scene_id,
          layer_id: resolvedLayerId,
        },
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: mutation.description!,
        diagnostics: [],
      };
    }

    case "REPLACE_MEDIA": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const layerRes = resolveTargetLayer(scene, intent.target.layer_id, intent.target.selector);
      if (layerRes.error) {
        return { ok: false, error: layerRes.error, diagnostics: [layerRes.error] };
      }

      const resolvedLayerId = layerRes.layer?.layer_id ?? intent.target.layer_id;

      const mutation: ReplaceMediaMutation = {
        mutation_id: `mut_${req.request_id}_media`,
        expected_revision: baseRev,
        author: actor,
        description: req.description ?? `Replace media in scene ${scene.scene_id}`,
        type: "REPLACE_MEDIA",
        target: {
          scene_id: scene.scene_id,
          layer_id: resolvedLayerId,
        },
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: mutation.description!,
        diagnostics: [],
      };
    }

    case "CHANGE_TIMING": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      let newDuration = intent.payload.durationFrames ?? scene.durationFrames;
      if (intent.payload.deltaFrames !== undefined) {
        newDuration = Math.max(1, scene.durationFrames + intent.payload.deltaFrames);
      }

      const newStart = intent.payload.startFrame ?? scene.startFrame;

      const mutation: TrimClipMutation = {
        mutation_id: `mut_${req.request_id}_timing`,
        expected_revision: baseRev,
        author: actor,
        description: req.description ?? `Change timing in scene ${scene.scene_id}`,
        type: "TRIM_CLIP",
        target: {
          scene_id: scene.scene_id,
          clip_id: intent.target.clip_id ?? `clip_sc_${scene.scene_id}`,
        },
        payload: {
          startFrame: newStart,
          durationFrames: newDuration,
        },
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: mutation.description!,
        diagnostics: [],
      };
    }

    case "APPLY_TEMPLATE_PARAM": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const paramName = intent.payload.parameter_name;
      const paramVal = intent.payload.value;
      const mutations: CanonicalMutation[] = [];

      // Map parameter safely to fine-grained canonical mutations
      if (paramName === "title" || paramName === "text" || paramName === "headline") {
        const titleLayer = scene.layers?.find((l) => l.layer_id.endsWith("_title") || l.kind === "text");
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_title`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: titleLayer?.layer_id },
          payload: { text: String(paramVal) },
        });
      } else if (paramName === "subtitle" || paramName === "subtext") {
        const subLayer = scene.layers?.find((l) => l.layer_id.endsWith("_sub"));
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_sub`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: subLayer?.layer_id },
          payload: { text: String(paramVal) },
        });
      } else if (paramName === "backgroundColor" || paramName === "background") {
        const bgLayer = scene.layers?.find((l) => l.layer_id.endsWith("_bg"));
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_bg`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_STYLE",
          target: { scene_id: scene.scene_id, layer_id: bgLayer?.layer_id },
          payload: { backgroundColor: String(paramVal) },
        });
      } else if (paramName === "color" || paramName === "textColor" || paramName === "accentColor") {
        const titleLayer = scene.layers?.find((l) => l.layer_id.endsWith("_title"));
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_color`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_STYLE",
          target: { scene_id: scene.scene_id, layer_id: titleLayer?.layer_id },
          payload: { color: String(paramVal) },
        });
      } else if (paramName === "media_ref" || paramName === "image" || paramName === "image_ref") {
        const imgLayer = scene.layers?.find((l) => l.kind === "image" || l.kind === "video");
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_media`,
          expected_revision: baseRev,
          author: actor,
          type: "REPLACE_MEDIA",
          target: { scene_id: scene.scene_id, layer_id: imgLayer?.layer_id },
          payload: { asset_ref: String(paramVal) },
        });
      } else if (paramName === "duration" || paramName === "durationFrames") {
        const numDur = Number(paramVal);
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_dur`,
          expected_revision: baseRev,
          author: actor,
          type: "TRIM_CLIP",
          target: { scene_id: scene.scene_id, clip_id: `clip_sc_${scene.scene_id}` },
          payload: { startFrame: scene.startFrame, durationFrames: numDur },
        });
      } else {
        // Fallback for general parameter update: update scene style/surface
        mutations.push({
          mutation_id: `mut_${req.request_id}_param_gen`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_STYLE",
          target: { scene_id: scene.scene_id },
          payload: { surface: { [paramName]: paramVal } },
        });
      }

      return {
        ok: true,
        mutations,
        is_compound: mutations.length > 1,
        description: `Apply template parameter '${paramName}' to scene ${scene.scene_id}`,
        diagnostics: [],
      };
    }

    case "COMPOUND_COMMAND": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const cmdType = intent.command_type.toLowerCase();
      const p = intent.payload;
      const mutations: CanonicalMutation[] = [];

      if (cmdType === "quote_card") {
        // Compound quote card: quote text + author + styling + background
        const quoteText = p.quote ?? p.text ?? "Quote headline";
        const authorText = p.author ?? p.subtitle ?? "Author";
        const bgColor = p.background ?? p.backgroundColor ?? "#111827";
        const accentColor = p.accentColor ?? p.color ?? "#F59E0B";

        const titleLayer = scene.layers?.find((l) => l.layer_id.endsWith("_title") || l.kind === "text");
        const subLayer = scene.layers?.find((l) => l.layer_id.endsWith("_sub"));
        const bgLayer = scene.layers?.find((l) => l.layer_id.endsWith("_bg") || l.kind === "shape");

        // 1. Title/Quote
        mutations.push({
          mutation_id: `mut_${req.request_id}_quote_text`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: titleLayer?.layer_id },
          payload: {
            text: String(quoteText),
            typography: { fontSize: 56, fontStyle: "italic", fillColor: "#FFFFFF" },
          },
        });

        // 2. Author/Subtitle
        mutations.push({
          mutation_id: `mut_${req.request_id}_quote_author`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: subLayer?.layer_id },
          payload: {
            text: `— ${authorText}`,
            typography: { fontSize: 28, fillColor: accentColor },
          },
        });

        // 3. Background styling
        mutations.push({
          mutation_id: `mut_${req.request_id}_quote_bg`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_STYLE",
          target: { scene_id: scene.scene_id, layer_id: bgLayer?.layer_id },
          payload: {
            backgroundColor: bgColor,
            shape: { fillColor: bgColor },
          },
        });
      } else if (cmdType === "cta_banner") {
        // Compound call to action banner
        const headline = p.headline ?? p.title ?? "Act Now!";
        const buttonText = p.buttonText ?? p.subtitle ?? "Get Started";
        const btnColor = p.buttonColor ?? p.accentColor ?? "#3B82F6";

        const titleLayer = scene.layers?.find((l) => l.layer_id.endsWith("_title") || l.kind === "text");
        const subLayer = scene.layers?.find((l) => l.layer_id.endsWith("_sub"));

        mutations.push({
          mutation_id: `mut_${req.request_id}_cta_h`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: titleLayer?.layer_id },
          payload: { text: String(headline) },
        });

        mutations.push({
          mutation_id: `mut_${req.request_id}_cta_b`,
          expected_revision: baseRev,
          author: actor,
          type: "UPDATE_TEXT",
          target: { scene_id: scene.scene_id, layer_id: subLayer?.layer_id },
          payload: {
            text: String(buttonText),
            typography: { fillColor: btnColor },
          },
        });
      } else {
        // Generic compound command: if user provided discrete sub-mutations
        if (Array.isArray(p.mutations)) {
          for (let i = 0; i < p.mutations.length; i++) {
            const rawM = p.mutations[i];
            mutations.push({
              ...rawM,
              mutation_id: rawM.mutation_id || `mut_${req.request_id}_sub_${i}`,
              expected_revision: baseRev,
              author: actor,
            });
          }
        }
      }

      if (mutations.length === 0) {
        return {
          ok: false,
          error: {
            code: "UNSUPPORTED_AUTHORING_OPERATION",
            message: `Unsupported or empty compound command type '${intent.command_type}'`,
          },
          diagnostics: [],
        };
      }

      return {
        ok: true,
        mutations,
        is_compound: true,
        description: req.description ?? `Compound command: ${intent.command_type}`,
        diagnostics: [],
      };
    }

    case "ADD_LAYER": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const mutation: AddLayerMutation = {
        mutation_id: `mut_${req.request_id}_add_l`,
        expected_revision: baseRev,
        author: actor,
        type: "ADD_LAYER",
        target: { scene_id: scene.scene_id },
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Add layer to scene ${scene.scene_id}`,
        diagnostics: [],
      };
    }

    case "REMOVE_LAYER": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const layer = scene.layers?.find((l) => l.layer_id === intent.target.layer_id);
      if (!layer) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Layer '${intent.target.layer_id}' not found in scene '${scene.scene_id}'`,
            target_id: intent.target.layer_id,
          },
          diagnostics: [],
        };
      }

      const mutation: RemoveLayerMutation = {
        mutation_id: `mut_${req.request_id}_rem_l`,
        expected_revision: baseRev,
        author: actor,
        type: "REMOVE_LAYER",
        target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Remove layer ${layer.layer_id}`,
        diagnostics: [],
      };
    }

    case "REORDER_LAYER": {
      const mutation: ReorderLayerMutation = {
        mutation_id: `mut_${req.request_id}_reo_l`,
        expected_revision: baseRev,
        author: actor,
        type: "REORDER_LAYER",
        target: intent.target,
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Reorder layer ${intent.target.layer_id}`,
        diagnostics: [],
      };
    }

    case "ADD_SCENE": {
      const mutation: AddSceneMutation = {
        mutation_id: `mut_${req.request_id}_add_sc`,
        expected_revision: baseRev,
        author: actor,
        type: "ADD_SCENE",
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Add scene ${intent.payload.scene.scene_id}`,
        diagnostics: [],
      };
    }

    case "REMOVE_SCENE": {
      const scene = blueprint.scenes.find((s) => s.scene_id === intent.target.scene_id);
      if (!scene) {
        return {
          ok: false,
          error: {
            code: "AUTHORING_TARGET_NOT_FOUND",
            message: `Target scene '${intent.target.scene_id}' not found`,
            target_id: intent.target.scene_id,
          },
          diagnostics: [],
        };
      }

      const mutation: RemoveSceneMutation = {
        mutation_id: `mut_${req.request_id}_rem_sc`,
        expected_revision: baseRev,
        author: actor,
        type: "REMOVE_SCENE",
        target: { scene_id: scene.scene_id },
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Remove scene ${scene.scene_id}`,
        diagnostics: [],
      };
    }

    case "REORDER_SCENE": {
      const mutation: ReorderSceneMutation = {
        mutation_id: `mut_${req.request_id}_reo_sc`,
        expected_revision: baseRev,
        author: actor,
        type: "REORDER_SCENE",
        target: intent.target,
        payload: intent.payload,
      };

      return {
        ok: true,
        mutations: [mutation],
        is_compound: false,
        description: `Reorder scene ${intent.target.scene_id}`,
        diagnostics: [],
      };
    }

    default: {
      const exhaustiveCheck: never = intent;
      return {
        ok: false,
        error: {
          code: "UNSUPPORTED_AUTHORING_OPERATION",
          message: `Unhandled authoring intent type '${(exhaustiveCheck as any)?.type}'`,
        },
        diagnostics: [],
      };
    }
  }
}
