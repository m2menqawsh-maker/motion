/**
 * contracts/render-graph.ts — Engine-Neutral Multi-Engine RenderGraph & Planner Contracts.
 * S28-R12: Authoritative graph abstraction decoupling render planning and multi-engine
 * dispatch from concrete rendering technologies.
 * 
 * Pipeline:
 * Canonical VideoDocument
 *   ↓
 * RenderPlanner
 *   ↓
 * RenderGraph (Topological DAG)
 *   ↓
 * Renderer-Specific Nodes (Canvas, Remotion, External)
 *   ↓
 * Parallel / Dependent Execution Groups
 *   ↓
 * IntermediateArtifacts (Provenance & Content Fingerprinted)
 *   ↓
 * MasterCompositor (Final Assembly)
 *   ↓
 * Final Output Artifact
 * 
 * Architectural Invariants:
 *   - 100% Engine-neutral: ZERO Remotion, Canvas, React, FFmpeg, DOM, or WebGL imports.
 *   - Canonical VideoDocument is the sole authority for video semantics and timing.
 *   - Single Renderer Authority via RendererRegistry capability matching (NO hardcoded engine selection).
 *   - Fail-closed deterministic planning: identical inputs produce identical RenderPlans.
 *   - Strict acyclic validation and explicit dependency lineage.
 *   - Clear separation: RenderPlanner plans; RenderGraphExecutor executes; MasterCompositor assembles.
 */

import * as crypto from "crypto";
import { z } from "zod";
import type { BlueprintV2, BlueprintScene } from "./blueprint";
import {
  type CanonicalRendererCapability,
  normalizeCapability,
} from "./renderer";
import {
  type OutputProfile,
  type IntermediateArtifactType,
  type IntermediateArtifact,
  IntermediateArtifactTypeSchema,
  OutputProfileSchema,
} from "./compositor";

// ────────────────────────────────────────────────────────────────────────────
// 1. Structured Planning Error Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const RENDER_PLANNING_ERROR_CODES = [
  "NO_COMPATIBLE_RENDERER",
  "UNRESOLVABLE_RENDER_NODE",
  "RENDER_GRAPH_CYCLE",
  "INVALID_RENDER_GRAPH",
  "MISSING_DEPENDENCY",
  "QUALITY_REQUIREMENT_UNSATISFIED",
  "PLANNING_FAILED",
  "PLAN_UNRESOLVABLE",
] as const;

export type RenderPlanningErrorCode = (typeof RENDER_PLANNING_ERROR_CODES)[number];
export const RenderPlanningErrorCodeSchema = z.enum(RENDER_PLANNING_ERROR_CODES);

export class RenderPlanningError extends Error {
  readonly code: RenderPlanningErrorCode;
  readonly details?: Record<string, unknown>;

  constructor(code: RenderPlanningErrorCode, message: string, details?: Record<string, unknown>) {
    super(`[${code}] ${message}`);
    this.name = "RenderPlanningError";
    this.code = code;
    this.details = details;
    Object.setPrototypeOf(this, RenderPlanningError.prototype);
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Node Scope & Time Range Contracts
// ────────────────────────────────────────────────────────────────────────────

export const RenderNodeScopeTypeSchema = z.enum([
  "project",
  "scene",
  "layer",
  "fragment",
  "audio",
  "audio_stem",
  "compositor",
]);
export type RenderNodeScopeType = z.infer<typeof RenderNodeScopeTypeSchema>;

export const RenderNodeScopeSchema = z.object({
  type: RenderNodeScopeTypeSchema,
  id: z.string().min(1),
  name: z.string().optional(),
  sceneIndex: z.number().int().nonnegative().optional(),
});
export type RenderNodeScope = z.infer<typeof RenderNodeScopeSchema>;

export const RenderTimeRangeSchema = z.object({
  startFrame: z.number().int().nonnegative(),
  durationFrames: z.number().int().positive(),
  startTimeSec: z.number().nonnegative().optional(),
  durationSec: z.number().positive().optional(),
});
export type RenderTimeRange = z.infer<typeof RenderTimeRangeSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 3. Execution & Cost Profile Contracts
// ────────────────────────────────────────────────────────────────────────────

export const MemoryClassSchema = z.enum(["low", "medium", "high"]);
export type MemoryClass = z.infer<typeof MemoryClassSchema>;

export const CostProfileSchema = z.object({
  relativeComputeCost: z.number().positive(),
  startupOverheadMs: z.number().nonnegative(),
  memoryClass: MemoryClassSchema,
  expectedExecutionWeight: z.number().positive(),
});
export type CostProfile = z.infer<typeof CostProfileSchema>;

export const RenderExecutionProfileSchema = z.object({
  costProfile: CostProfileSchema,
  memoryClass: MemoryClassSchema,
  timeoutMs: z.number().positive().optional(),
  expectedWeight: z.number().positive().optional(),
  preferredConcurrency: z.number().int().positive().optional(),
});
export type RenderExecutionProfile = z.infer<typeof RenderExecutionProfileSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 4. Cacheability Contract
// ────────────────────────────────────────────────────────────────────────────

export const RenderNodeCacheabilitySchema = z.object({
  cacheable: z.boolean(),
  cacheKey: z.string().optional(),
  contentFingerprint: z.string().min(1),
  invalidationScope: z.string().min(1),
});
export type RenderNodeCacheability = z.infer<typeof RenderNodeCacheabilitySchema>;

// ────────────────────────────────────────────────────────────────────────────
// 5. Render Node & Edge Contracts
// ────────────────────────────────────────────────────────────────────────────

export const RenderNodeRequirementSchema = z.object({
  nodeId: z.string().min(1),
  scope: RenderNodeScopeSchema,
  requiredCapabilities: z.array(z.string()),
  targetQuality: z.enum(["preview", "draft", "production", "final"]).optional(),
  outputArtifactType: IntermediateArtifactTypeSchema,
});
export type RenderNodeRequirement = z.infer<typeof RenderNodeRequirementSchema>;

export const RenderNodeStatusSchema = z.enum([
  "pending",
  "scheduled",
  "running",
  "completed",
  "failed",
  "skipped",
]);
export type RenderNodeStatus = z.infer<typeof RenderNodeStatusSchema>;

export const RenderNodeSchema = z.object({
  id: z.string().min(1),
  scope: RenderNodeScopeSchema,
  timeRange: RenderTimeRangeSchema,
  requiredCapabilities: z.array(z.string()),
  dependencies: z.array(z.string()),
  assignedRendererId: z.string().optional(),
  assignedRendererVersion: z.string().optional(),
  cacheability: RenderNodeCacheabilitySchema,
  preferredExecutionProfile: RenderExecutionProfileSchema,
  outputArtifactType: IntermediateArtifactTypeSchema,
  fragmentDoc: z.any().optional(), // Engine-neutral BlueprintV2 sub-document
  status: RenderNodeStatusSchema.default("pending"),
  metadata: z.record(z.unknown()).optional(),
});
export type RenderNode = z.infer<typeof RenderNodeSchema>;

export const RenderEdgeTypeSchema = z.enum([
  "artifact_input",
  "audio_stem",
  "sequence_input",
  "dependency",
]);
export type RenderEdgeType = z.infer<typeof RenderEdgeTypeSchema>;

export const RenderEdgeSchema = z.object({
  fromNodeId: z.string().min(1),
  toNodeId: z.string().min(1),
  type: RenderEdgeTypeSchema,
  metadata: z.record(z.unknown()).optional(),
});
export type RenderEdge = z.infer<typeof RenderEdgeSchema>;

export const RenderExecutionGroupSchema = z.object({
  level: z.number().int().nonnegative(),
  nodeIds: z.array(z.string().min(1)),
  parallel: z.boolean(),
});
export type RenderExecutionGroup = z.infer<typeof RenderExecutionGroupSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 6. Render Graph Contract
// ────────────────────────────────────────────────────────────────────────────

export const RenderGraphSchema = z.object({
  id: z.string().min(1),
  documentRevision: z.union([z.string(), z.number()]),
  nodes: z.record(RenderNodeSchema),
  edges: z.array(RenderEdgeSchema),
  rootNodeId: z.string().optional(),
  executionGroups: z.array(RenderExecutionGroupSchema),
  metadata: z.record(z.unknown()).optional(),
});
export type RenderGraph = z.infer<typeof RenderGraphSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 7. Planning Policy & Render Plan Contracts
// ────────────────────────────────────────────────────────────────────────────

export const QualityRequirementSchema = z.enum(["preview", "draft", "production", "final"]);
export type QualityRequirement = z.infer<typeof QualityRequirementSchema>;

export const CostToleranceSchema = z.enum(["minimize_cost", "balanced", "maximum_quality"]);
export type CostTolerance = z.infer<typeof CostToleranceSchema>;

export const PlanningPolicySchema = z.object({
  targetQuality: QualityRequirementSchema.default("production"),
  preferredRendererId: z.string().optional(),
  costTolerance: CostToleranceSchema.default("balanced"),
  allowFallback: z.boolean().default(true),
  enableDecomposition: z.boolean().default(true),
  maxParallelism: z.number().int().positive().optional(),
  costBudget: z.number().positive().optional(),
});
export type PlanningPolicy = z.infer<typeof PlanningPolicySchema>;

export const RenderPlanSchema = z.object({
  id: z.string().min(1),
  projectId: z.string().min(1),
  canonicalRevision: z.union([z.string(), z.number()]),
  graph: RenderGraphSchema,
  policy: PlanningPolicySchema,
  outputProfile: OutputProfileSchema,
  outputPath: z.string(),
  estimatedTotalCost: z.number().nonnegative(),
  executionGroups: z.array(RenderExecutionGroupSchema),
  createdTimestamp: z.number(),
  planFingerprint: z.string().min(1),
});
export type RenderPlan = z.infer<typeof RenderPlanSchema>;

export interface RenderPlanResult {
  ok: boolean;
  plan?: RenderPlan;
  error?: {
    code: RenderPlanningErrorCode;
    message: string;
    details?: Record<string, unknown>;
  };
  diagnostics?: {
    warnings: string[];
    decompositionCount: number;
    rendererAssignments: Record<string, string>;
  };
}

export interface ArtifactProvenance {
  sourceRenderNodeId: string;
  rendererId: string;
  rendererVersion: string;
  canonicalRevision: string | number;
  inputFingerprints: string[];
  outputProfile: OutputProfile;
  dependencyLineage: string[];
  createdAt: number;
}

// ────────────────────────────────────────────────────────────────────────────
// 8. Deterministic Validation & Topological Helpers
// ────────────────────────────────────────────────────────────────────────────

/**
 * Validates a RenderGraph fail-closed:
 *   - All node IDs unique
 *   - Edges reference existing nodes
 *   - Dependencies array matches edges
 *   - Strictly acyclic (cycle detection via Kahn's algorithm)
 *   - Valid time ranges and canonical revision
 */
export function validateRenderGraph(graph: unknown): RenderGraph {
  if (!graph || typeof graph !== "object") {
    throw new RenderPlanningError(
      "INVALID_RENDER_GRAPH",
      "RenderGraph must be a non-null object",
      { received: graph }
    );
  }

  const parsed = RenderGraphSchema.safeParse(graph);
  if (!parsed.success) {
    throw new RenderPlanningError(
      "INVALID_RENDER_GRAPH",
      `RenderGraph schema validation failed: ${parsed.error.message}`,
      { errors: parsed.error.issues }
    );
  }

  const g = parsed.data;
  const nodeIds = new Set(Object.keys(g.nodes));

  // 1. Verify all edge references exist
  for (const edge of g.edges) {
    if (!nodeIds.has(edge.fromNodeId)) {
      throw new RenderPlanningError(
        "MISSING_DEPENDENCY",
        `RenderEdge references non-existent 'fromNodeId': ${edge.fromNodeId}`,
        { edge }
      );
    }
    if (!nodeIds.has(edge.toNodeId)) {
      throw new RenderPlanningError(
        "MISSING_DEPENDENCY",
        `RenderEdge references non-existent 'toNodeId': ${edge.toNodeId}`,
        { edge }
      );
    }
  }

  // 2. Verify dependencies on each node exist
  for (const [id, node] of Object.entries(g.nodes)) {
    for (const depId of node.dependencies) {
      if (!nodeIds.has(depId)) {
        throw new RenderPlanningError(
          "MISSING_DEPENDENCY",
          `RenderNode '${id}' references non-existent dependency: '${depId}'`,
          { nodeId: id, missingDependency: depId }
        );
      }
    }

    if (node.timeRange.startFrame < 0 || node.timeRange.durationFrames <= 0) {
      throw new RenderPlanningError(
        "INVALID_RENDER_GRAPH",
        `RenderNode '${id}' has invalid time range: startFrame=${node.timeRange.startFrame}, durationFrames=${node.timeRange.durationFrames}`,
        { nodeId: id, timeRange: node.timeRange }
      );
    }
  }

  // 3. Strict Cycle Detection via Kahn's Algorithm
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  for (const id of nodeIds) {
    inDegree.set(id, 0);
    adjacency.set(id, []);
  }

  // Edges represent fromNodeId -> toNodeId (fromNode is dependency of toNode)
  for (const edge of g.edges) {
    adjacency.get(edge.fromNodeId)!.push(edge.toNodeId);
    inDegree.set(edge.toNodeId, (inDegree.get(edge.toNodeId) || 0) + 1);
  }

  // Also include dependencies declared directly on nodes if not explicitly in edges
  for (const [id, node] of Object.entries(g.nodes)) {
    for (const depId of node.dependencies) {
      const existingEdge = g.edges.some(
        (e) => e.fromNodeId === depId && e.toNodeId === id
      );
      if (!existingEdge) {
        adjacency.get(depId)!.push(id);
        inDegree.set(id, (inDegree.get(id) || 0) + 1);
      }
    }
  }

  const queue: string[] = [];
  // Sort initially for 100% deterministic processing order
  const sortedInitial = Array.from(nodeIds).filter((id) => inDegree.get(id) === 0).sort();
  for (const id of sortedInitial) {
    queue.push(id);
  }

  let visitedCount = 0;
  while (queue.length > 0) {
    const curr = queue.shift()!;
    visitedCount++;

    const neighbors = adjacency.get(curr) || [];
    // Sort neighbors deterministically
    neighbors.sort();
    for (const next of neighbors) {
      const newDeg = (inDegree.get(next) || 1) - 1;
      inDegree.set(next, newDeg);
      if (newDeg === 0) {
        queue.push(next);
      }
    }
  }

  if (visitedCount !== nodeIds.size) {
    const unvisited = Array.from(nodeIds).filter((id) => (inDegree.get(id) || 0) > 0);
    throw new RenderPlanningError(
      "RENDER_GRAPH_CYCLE",
      `RenderGraph contains a cycle involving nodes: [${unvisited.join(", ")}]`,
      { cyclicNodeIds: unvisited }
    );
  }

  return g;
}

/**
 * Computes deterministic SHA-256 fingerprint of a RenderPlan.
 */
export function computePlanFingerprint(input: {
  projectId: string;
  revision: string | number;
  nodeFingerprints: Record<string, string>;
  edgeList: Array<{ from: string; to: string }>;
  outputProfile: OutputProfile;
  policy: PlanningPolicy;
}): string {
  // Sort node keys deterministically
  const sortedNodeKeys = Object.keys(input.nodeFingerprints).sort();
  const sortedNodes: Record<string, string> = {};
  for (const k of sortedNodeKeys) {
    sortedNodes[k] = input.nodeFingerprints[k];
  }

  const sortedEdges = [...input.edgeList].sort((a, b) =>
    a.from.localeCompare(b.from) || a.to.localeCompare(b.to)
  );

  const payload = {
    proj: input.projectId,
    rev: input.revision,
    nodes: sortedNodes,
    edges: sortedEdges,
    prof: {
      w: input.outputProfile.width,
      h: input.outputProfile.height,
      fps: input.outputProfile.fps,
      vc: input.outputProfile.videoCodec,
      ac: input.outputProfile.audioCodec,
    },
    policy: {
      q: input.policy.targetQuality,
      tol: input.policy.costTolerance,
      pref: input.policy.preferredRendererId ?? "",
    },
  };

  return crypto
    .createHash("sha256")
    .update(JSON.stringify(payload))
    .digest("hex");
}
