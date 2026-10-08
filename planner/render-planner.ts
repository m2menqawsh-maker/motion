/**
 * planner/render-planner.ts — Canonical Multi-Engine Render Planner.
 * S28-R12: Authoritative planning authority transforming Canonical VideoDocuments into
 * deterministic, multi-engine RenderGraphs.
 * 
 * Pipeline:
 * Canonical VideoDocument
 *   ↓
 * RenderPlanner
 *   ↓
 * RenderGraph (Topological DAG)
 *   ↓
 * Renderer Assignment via Capability Resolution (RendererRegistry)
 *   ↓
 * Deterministic RenderPlan with Parallel Execution Groups
 * 
 * Architectural Invariants:
 *   - The Planner DOES NOT render: zero FFmpeg, zero Remotion bundler, zero Canvas rendering.
 *   - Zero hardcoded engine branching: capability-based resolution only.
 *   - 100% deterministic: identical document + registry state + policy = identical plan.
 *   - Single timing authority: relies strictly on Canonical VideoDocument & contracts/timeline.
 *   - Clean failure model: fail-closed with structured RenderPlanningError.
 */

import * as crypto from "crypto";
import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import {
  type CanonicalRendererCapability,
  type RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  normalizeCapability,
} from "../contracts/renderer";
import {
  type OutputProfile,
  resolveProfileFromDocument,
  computeArtifactFingerprint,
} from "../contracts/compositor";
import { calculateCanonicalDuration, frameToSeconds } from "../contracts/timeline";
import { getSemanticTemplateSpec } from "../registry/semantic-registry";
import {
  type RenderGraph,
  type RenderNode,
  type RenderEdge,
  type RenderExecutionGroup,
  type RenderPlan,
  type RenderPlanResult,
  type PlanningPolicy,
  type QualityRequirement,
  type RenderTimeRange,
  type RenderNodeScope,
  RenderPlanningError,
  validateRenderGraph,
  computePlanFingerprint,
} from "../contracts/render-graph";
import { resolveCompatibleRenderer } from "./planning-policy";
import { createExecutionProfile, estimateTotalPlanCost } from "./cost-estimator";
import { computeSceneFingerprint, computeCompositorFingerprint } from "./cache-evaluator";

const GL_TRANSITION_TYPES = new Set([
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
 * Derives the exact set of canonical capabilities required by a discrete scene fragment.
 */
export function deriveSceneRequiredCapabilities(
  scene: BlueprintScene,
  requestMode: "export_video" | "sequence_rendering" | "frame_rendering" = "export_video"
): CanonicalRendererCapability[] {
  const caps = new Set<CanonicalRendererCapability>();
  caps.add(requestMode);

  // 1. Template requirements (R05)
  if (scene.template) {
    const tid = scene.template;
    if (tid === "rui-map-flight") {
      caps.add("map");
      caps.add("webgl");
    } else if (tid === "scene3d-element") {
      caps.add("3d");
      caps.add("webgl");
    } else if (tid === "particlesystem-element") {
      caps.add("particles");
    }

    const spec = getSemanticTemplateSpec(tid);
    if (spec && (spec.classification === "ENGINE_BACKED" || spec.classification === "HYBRID")) {
      for (const c of spec.requirements?.capabilities ?? []) {
        const norm = normalizeCapability(c);
        caps.add(norm);
        if (norm === "map" || norm === "3d") {
          caps.add("webgl");
        }
      }
    }
  }

  // 2. Transitions
  if (scene.transition) {
    caps.add("transitions");
    if (GL_TRANSITION_TYPES.has(scene.transition.type)) {
      caps.add("custom_shaders");
      caps.add("webgl");
    }
  }

  // 3. Surface & shapes
  if (scene.surface) {
    caps.add("shapes");
  }

  // 4. Content primitives
  if (scene.content) {
    if (scene.content.title || scene.content.subtitle || scene.content.body) {
      caps.add("text");
    }
    if (scene.content.media?.kind === "image") {
      caps.add("image");
    }
    if (scene.content.media?.kind === "video") {
      caps.add("video");
    }
  }

  // 5. Explicit Layers
  if (Array.isArray(scene.layers)) {
    for (const layer of scene.layers) {
      if (layer.kind === "text") caps.add("text");
      if (layer.kind === "image") caps.add("image");
      if (layer.kind === "video") caps.add("video");
      if (layer.kind === "shape") caps.add("shapes");
      if (layer.kind === "group" || layer.parent_id) caps.add("groups");
      if (layer.kind === "audio") {
        caps.add("audio");
        caps.add("audio_timing");
      }

      if (Array.isArray(layer.channels) && layer.channels.some((c) => c.keyframes && c.keyframes.length > 0)) {
        caps.add("keyframes");
      }

      if (layer.opacity !== undefined && layer.opacity < 1.0) {
        caps.add("alpha");
      }
      if (layer.transform?.opacity !== undefined && layer.transform.opacity < 1.0) {
        caps.add("alpha");
      }
    }
  }

  return Array.from(caps).sort();
}

/**
 * Calculates topological levels and identifies parallelizable execution groups.
 */
export function buildExecutionGroups(
  nodeIds: string[],
  dependenciesMap: Map<string, string[]>
): RenderExecutionGroup[] {
  const inDegree = new Map<string, number>();
  const reverseAdjacency = new Map<string, string[]>(); // dep -> nodes that depend on dep

  for (const id of nodeIds) {
    inDegree.set(id, 0);
    reverseAdjacency.set(id, []);
  }

  for (const [nodeId, deps] of dependenciesMap.entries()) {
    inDegree.set(nodeId, deps.length);
    for (const d of deps) {
      if (!reverseAdjacency.has(d)) {
        reverseAdjacency.set(d, []);
      }
      reverseAdjacency.get(d)!.push(nodeId);
    }
  }

  const groups: RenderExecutionGroup[] = [];
  let currentLevel = 0;
  let remainingCount = nodeIds.length;

  while (remainingCount > 0) {
    const ready = Array.from(inDegree.entries())
      .filter(([_, deg]) => deg === 0)
      .map(([id]) => id)
      .sort(); // Deterministic ordering

    if (ready.length === 0) {
      const remainingNodes = Array.from(inDegree.entries())
        .filter(([_, deg]) => deg > 0)
        .map(([id]) => id);
      throw new RenderPlanningError(
        "RENDER_GRAPH_CYCLE",
        `Cycle detected during topological level calculation: [${remainingNodes.join(", ")}]`,
        { cyclicNodeIds: remainingNodes }
      );
    }

    groups.push({
      level: currentLevel,
      nodeIds: ready,
      parallel: ready.length > 1,
    });

    for (const readyId of ready) {
      inDegree.delete(readyId);
      remainingCount--;

      const dependents = reverseAdjacency.get(readyId) || [];
      for (const dep of dependents) {
        if (inDegree.has(dep)) {
          inDegree.set(dep, inDegree.get(dep)! - 1);
        }
      }
    }

    currentLevel++;
  }

  return groups;
}

export interface RenderPlannerRequest {
  document: BlueprintV2;
  outputProfile?: Partial<OutputProfile>;
  outputPath?: string;
  policy?: Partial<PlanningPolicy>;
}

export interface RenderPlannerOptions {
  registry?: RendererRegistry;
  defaultPolicy?: PlanningPolicy;
}

export class RenderPlanner {
  private readonly _registry: RendererRegistry;
  private readonly _defaultPolicy: PlanningPolicy;

  constructor(options?: RenderPlannerOptions) {
    this._registry = options?.registry ?? CANONICAL_RENDERER_REGISTRY;
    this._defaultPolicy = {
      targetQuality: "production",
      costTolerance: "balanced",
      allowFallback: true,
      enableDecomposition: true,
      ...(options?.defaultPolicy ?? {}),
    };
  }

  /**
   * Plans the execution of a Canonical VideoDocument across multiple rendering engines.
   * Returns a deterministic, fully resolved RenderPlan.
   * Fails closed if any node requirement cannot be satisfied.
   */
  plan(request: RenderPlannerRequest): RenderPlanResult {
    try {
      const doc = request.document;
      if (!doc || !doc.project_id || !Array.isArray(doc.scenes)) {
        throw new RenderPlanningError(
          "INVALID_RENDER_GRAPH",
          "Invalid BlueprintV2 document: missing project_id or scenes array"
        );
      }

      if (doc.scenes.length === 0) {
        throw new RenderPlanningError(
          "PLANNING_FAILED",
          "Cannot plan empty video: document must contain at least one scene"
        );
      }

      const policy: PlanningPolicy = {
        ...this._defaultPolicy,
        ...(request.policy ?? {}),
      };

      // 1. Output Profile Resolution (respecting quality requirements)
      let resolvedProfile = resolveProfileFromDocument(doc, request.outputProfile);
      if (policy.targetQuality === "preview") {
        resolvedProfile = {
          ...resolvedProfile,
          width: Math.max(2, Math.floor((resolvedProfile.width * 0.5) / 2) * 2),
          height: Math.max(2, Math.floor((resolvedProfile.height * 0.5) / 2) * 2),
        };
      } else if (policy.targetQuality === "draft") {
        resolvedProfile = {
          ...resolvedProfile,
          width: Math.max(2, Math.floor((resolvedProfile.width * 0.75) / 2) * 2),
          height: Math.max(2, Math.floor((resolvedProfile.height * 0.75) / 2) * 2),
        };
      }

      const outputPath = request.outputPath ?? `/tmp/${doc.project_id}_final.mp4`;
      const revision = doc.revision ?? doc.schema_version ?? "2.0.0";

      const nodes: Record<string, RenderNode> = {};
      const edges: RenderEdge[] = [];
      const dependenciesMap = new Map<string, string[]>();
      const nodeFingerprints: Record<string, string> = {};
      const rendererAssignments: Record<string, string> = {};
      const warnings: string[] = [];

      let currentStartFrame = 0;

      // 2. Decompose work by Scene (Deterministic)
      for (let i = 0; i < doc.scenes.length; i++) {
        const scene = doc.scenes[i];
        const sceneId = scene.scene_id || scene.id || `scene_${i}`;
        const nodeId = `node_scene_${sceneId}`;

        const durFrames = scene.durationFrames ?? 30;
        const timeRange: RenderTimeRange = {
          startFrame: currentStartFrame,
          durationFrames: durFrames,
          startTimeSec: frameToSeconds(currentStartFrame, doc.fps || 30),
          durationSec: frameToSeconds(durFrames, doc.fps || 30),
        };

        // Advance start frame for next scene
        currentStartFrame += durFrames;

        // Derive scene capabilities
        const requiredCaps = deriveSceneRequiredCapabilities(scene, "export_video");

        // Resolve compatible renderer
        const resResult = resolveCompatibleRenderer({
          nodeId,
          requiredCapabilities: requiredCaps,
          policy,
          registry: this._registry,
        });

        if (!resResult.ok || !resResult.adapter) {
          throw new RenderPlanningError(
            resResult.error?.code ?? "NO_COMPATIBLE_RENDERER",
            resResult.error?.message ?? `No compatible renderer found for scene node '${nodeId}'.`,
            resResult.error?.details
          );
        }

        const assignedAdapter = resResult.adapter;
        rendererAssignments[nodeId] = assignedAdapter.id;

        // Create scene sub-document (isolated scene execution)
        const sceneDoc: BlueprintV2 = {
          ...doc,
          project_id: `${doc.project_id}_fragment_${sceneId}`,
          scenes: [
            {
              ...scene,
              startFrame: 0,
            },
          ],
          audio: undefined,
        };

        // Content fingerprinting & cacheability
        const fp = computeSceneFingerprint({
          scene,
          revision,
          outputProfile: {
            width: resolvedProfile.width,
            height: resolvedProfile.height,
            fps: resolvedProfile.fps,
          },
          rendererId: assignedAdapter.id,
          rendererVersion: assignedAdapter.version,
        });
        nodeFingerprints[nodeId] = fp;

        // Execution & Cost profile
        const execProfile = createExecutionProfile(assignedAdapter.id, durFrames);

        const sceneNode: RenderNode = {
          id: nodeId,
          scope: {
            type: "scene",
            id: sceneId,
            name: scene.name ?? `Scene ${i + 1}`,
            sceneIndex: i,
          },
          timeRange,
          requiredCapabilities: requiredCaps,
          dependencies: [],
          assignedRendererId: assignedAdapter.id,
          assignedRendererVersion: assignedAdapter.version,
          cacheability: {
            cacheable: true,
            cacheKey: `cache:${sceneId}:${fp}`,
            contentFingerprint: fp,
            invalidationScope: `scene:${sceneId}`,
          },
          preferredExecutionProfile: execProfile,
          outputArtifactType: "video",
          fragmentDoc: sceneDoc,
          status: "pending",
          metadata: {
            sceneIndex: i,
          },
        };

        nodes[nodeId] = sceneNode;
        dependenciesMap.set(nodeId, []);
      }

      // 3. Final Composition Node (MasterCompositor Integration)
      const sceneNodeIds = Object.keys(nodes);
      const compositorNodeId = "node_master_compositor";
      const totalDurFrames = calculateCanonicalDuration(doc.scenes);

      const compTimeRange: RenderTimeRange = {
        startFrame: 0,
        durationFrames: totalDurFrames,
        startTimeSec: 0,
        durationSec: frameToSeconds(totalDurFrames, doc.fps || 30),
      };

      const compFingerprint = computeCompositorFingerprint({
        inputFingerprints: nodeFingerprints,
        document: doc,
        outputProfile: resolvedProfile,
        revision,
      });
      nodeFingerprints[compositorNodeId] = compFingerprint;
      rendererAssignments[compositorNodeId] = "master-compositor";

      const compNode: RenderNode = {
        id: compositorNodeId,
        scope: {
          type: "compositor",
          id: "master",
          name: "Master Compositor Assembly",
        },
        timeRange: compTimeRange,
        requiredCapabilities: ["export_video"],
        dependencies: [...sceneNodeIds],
        assignedRendererId: "master-compositor",
        assignedRendererVersion: "1.0.0",
        cacheability: {
          cacheable: true,
          cacheKey: `cache:compositor:${compFingerprint}`,
          contentFingerprint: compFingerprint,
          invalidationScope: `project:${doc.project_id}`,
        },
        preferredExecutionProfile: createExecutionProfile("master-compositor", totalDurFrames),
        outputArtifactType: "video",
        status: "pending",
      };

      nodes[compositorNodeId] = compNode;
      dependenciesMap.set(compositorNodeId, [...sceneNodeIds]);

      // Connect edges from every scene node to compositor
      for (const sceneNodeId of sceneNodeIds) {
        edges.push({
          fromNodeId: sceneNodeId,
          toNodeId: compositorNodeId,
          type: "artifact_input",
        });
      }

      // 4. Calculate Topological Levels & Parallel Execution Groups
      const allNodeIds = Object.keys(nodes);
      const executionGroups = buildExecutionGroups(allNodeIds, dependenciesMap);

      // 5. Build & Validate Complete RenderGraph
      const graphId = `graph_${doc.project_id}_${revision}`;
      const graph: RenderGraph = {
        id: graphId,
        documentRevision: revision,
        nodes,
        edges,
        rootNodeId: compositorNodeId,
        executionGroups,
      };

      validateRenderGraph(graph);

      // 6. Estimate Total Cost & Compute Plan Fingerprint
      const totalCost = estimateTotalPlanCost(Object.values(nodes));

      const planFp = computePlanFingerprint({
        projectId: doc.project_id,
        revision,
        nodeFingerprints,
        edgeList: edges.map((e) => ({ from: e.fromNodeId, to: e.toNodeId })),
        outputProfile: resolvedProfile,
        policy,
      });

      const plan: RenderPlan = {
        id: `plan_${doc.project_id}_${planFp.slice(0, 8)}`,
        projectId: doc.project_id,
        canonicalRevision: revision,
        graph,
        policy,
        outputProfile: resolvedProfile,
        outputPath,
        estimatedTotalCost: totalCost,
        executionGroups,
        createdTimestamp: Date.now(),
        planFingerprint: planFp,
      };
      (plan as any).document = doc;

      return {
        ok: true,
        plan,
        diagnostics: {
          warnings,
          decompositionCount: doc.scenes.length,
          rendererAssignments,
        },
      };
    } catch (err: unknown) {
      if (err instanceof RenderPlanningError) {
        return {
          ok: false,
          error: {
            code: err.code,
            message: err.message,
            details: err.details,
          },
        };
      }
      return {
        ok: false,
        error: {
          code: "PLANNING_FAILED",
          message: err instanceof Error ? err.message : String(err),
        },
      };
    }
  }
}
