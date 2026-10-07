/**
 * planner/cache-evaluator.ts — Deterministic Cacheability & Selective Invalidation Engine.
 * S28-R12: Evaluates cache hits and propagates invalidations across the RenderGraph DAG.
 * 
 * Rules:
 *   - Fingerprints are derived strictly from canonical content, revision, time range, and profiles.
 *   - Selective Invalidation:
 *       If Scene B changes:
 *         -> Scene B is invalidated.
 *         -> Dependent MasterCompositor is invalidated.
 *         -> Independent Scene A & C remain valid cache hits!
 */

import * as crypto from "crypto";
import * as fs from "fs";
import type { BlueprintScene, BlueprintV2 } from "../contracts/blueprint";
import type { OutputProfile, IntermediateArtifact } from "../contracts/compositor";
import type { RenderPlan, RenderNode } from "../contracts/render-graph";

/**
 * Serializes an object to deterministic canonical JSON with recursively sorted keys.
 */
function canonicalJson(obj: unknown): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map(canonicalJson).join(",") + "]";
  }
  const keys = Object.keys(obj as Record<string, unknown>).sort();
  return (
    "{" +
    keys
      .map((k) => JSON.stringify(k) + ":" + canonicalJson((obj as Record<string, unknown>)[k]))
      .join(",") +
    "}"
  );
}

/**
 * Computes deterministic SHA-256 fingerprint for a scene fragment.
 */
export function computeSceneFingerprint(params: {
  scene: BlueprintScene;
  revision: string | number;
  outputProfile?: { width: number; height: number; fps: number };
  rendererId?: string;
  rendererVersion?: string;
}): string {
  const normScene = {
    id: params.scene.scene_id || params.scene.id || "",
    template: params.scene.template || "",
    startFrame: params.scene.startFrame ?? 0,
    durationFrames: params.scene.durationFrames ?? 0,
    surface: params.scene.surface ?? {},
    content: params.scene.content ?? {},
    layers: params.scene.layers ?? [],
    transition: params.scene.transition ?? null,
  };

  const payload = {
    scene: normScene,
    rev: params.revision,
    profile: params.outputProfile ?? { width: 1920, height: 1080, fps: 30 },
    renderer: params.rendererId ?? "",
    ver: params.rendererVersion ?? "1.0.0",
  };

  return crypto
    .createHash("sha256")
    .update(canonicalJson(payload))
    .digest("hex");
}

/**
 * Computes deterministic SHA-256 fingerprint for a MasterCompositor assembly node.
 */
export function computeCompositorFingerprint(params: {
  inputFingerprints: Record<string, string>;
  document: BlueprintV2;
  outputProfile: OutputProfile;
  revision: string | number;
}): string {
  // Sort input fingerprints deterministically
  const sortedInputKeys = Object.keys(params.inputFingerprints).sort();
  const sortedInputs: Record<string, string> = {};
  for (const k of sortedInputKeys) {
    sortedInputs[k] = params.inputFingerprints[k];
  }

  const payload = {
    inputs: sortedInputs,
    audio: params.document.audio ?? {},
    rev: params.revision,
    profile: {
      w: params.outputProfile.width,
      h: params.outputProfile.height,
      fps: params.outputProfile.fps,
      vc: params.outputProfile.videoCodec,
      ac: params.outputProfile.audioCodec,
    },
  };

  return crypto
    .createHash("sha256")
    .update(canonicalJson(payload))
    .digest("hex");
}

export interface NodeCacheEvaluation {
  nodeId: string;
  cacheHit: boolean;
  artifact?: IntermediateArtifact;
  invalidationReason?: "uncacheable" | "fingerprint_miss" | "dependency_invalidated" | "file_missing";
}

/**
 * Evaluates cache status for every node in a RenderPlan, propagating invalidations down the DAG.
 */
export function evaluatePlanCache(
  plan: RenderPlan,
  existingArtifacts: Map<string, IntermediateArtifact> | Record<string, IntermediateArtifact>
): Map<string, NodeCacheEvaluation> {
  const artifactMap =
    existingArtifacts instanceof Map
      ? existingArtifacts
      : new Map(Object.entries(existingArtifacts));

  const evaluations = new Map<string, NodeCacheEvaluation>();

  // Process level-by-level in topological order
  for (const group of plan.executionGroups) {
    for (const nodeId of group.nodeIds) {
      const node = plan.graph.nodes[nodeId];
      if (!node) continue;

      if (!node.cacheability.cacheable) {
        evaluations.set(nodeId, {
          nodeId,
          cacheHit: false,
          invalidationReason: "uncacheable",
        });
        continue;
      }

      // Check if any upstream dependency was invalidated
      let depInvalidated = false;
      for (const depId of node.dependencies) {
        const depEval = evaluations.get(depId);
        if (!depEval || !depEval.cacheHit) {
          depInvalidated = true;
          break;
        }
      }

      if (depInvalidated) {
        evaluations.set(nodeId, {
          nodeId,
          cacheHit: false,
          invalidationReason: "dependency_invalidated",
        });
        continue;
      }

      // Check if we have an artifact matching the fingerprint
      const fp = node.cacheability.contentFingerprint;
      const candidate = artifactMap.get(fp) || artifactMap.get(nodeId);

      if (candidate && candidate.contentFingerprint === fp) {
        // Verify disk file exists if filePath is specified
        if (candidate.filePath && !fs.existsSync(candidate.filePath)) {
          evaluations.set(nodeId, {
            nodeId,
            cacheHit: false,
            invalidationReason: "file_missing",
          });
          continue;
        }

        evaluations.set(nodeId, {
          nodeId,
          cacheHit: true,
          artifact: candidate,
        });
      } else {
        evaluations.set(nodeId, {
          nodeId,
          cacheHit: false,
          invalidationReason: "fingerprint_miss",
        });
      }
    }
  }

  return evaluations;
}
