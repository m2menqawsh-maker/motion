/**
 * planner/render-graph-executor.ts — Lightweight Multi-Engine RenderGraph Executor.
 * S28-R12: Local execution engine executing topological DAGs across multiple rendering engines.
 * 
 * Pipeline:
 * RenderPlan
 *   ↓
 * ExecutionGroups (Topological levels)
 *   ↓
 * Parallel / Sequential Node Execution
 *   ↓
 * Engine Dispatch (Canvas / Remotion / External via RendererRegistry)
 *   ↓
 * IntermediateArtifact Caching & Provenance Tracking
 *   ↓
 * MasterCompositor Final Assembly
 *   ↓
 * ExecutionResult (Final Video Artifact)
 * 
 * Architectural Invariants:
 *   - Zero mutation of Canonical VideoDocuments.
 *   - Clean failure isolation: an isolated engine failure halts downstream dependents without corrupting independent artifacts.
 *   - Deterministic provenance attached to every intermediate and final artifact.
 *   - Respects AbortSignal cancellation immediately.
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";

import type { BlueprintV2 } from "../contracts/blueprint";
import {
  type RendererRegistry,
  type RendererAdapter,
  CANONICAL_RENDERER_REGISTRY,
  RenderFailedError,
} from "../contracts/renderer";
import {
  type IntermediateArtifact,
  type CompositorInput,
  type CompositorResult,
  createIntermediateArtifact,
} from "../contracts/compositor";
import {
  type RenderPlan,
  type RenderNode,
  type ArtifactProvenance,
  RenderPlanningError,
} from "../contracts/render-graph";
import { MasterCompositor, probeMediaFile } from "../compositor";

export interface NodeExecutionResult {
  nodeId: string;
  ok: boolean;
  artifact?: IntermediateArtifact;
  metrics?: {
    durationMs: number;
    cacheHit: boolean;
  };
  error?: Error;
}

export interface ExecutionMetrics {
  totalDurationMs: number;
  executedNodes: number;
  cachedNodes: number;
  failedNodes: number;
  parallelGroups: number;
}

export interface ExecutionResult {
  ok: boolean;
  planId: string;
  outputPath?: string;
  finalArtifact?: IntermediateArtifact;
  nodeResults: Record<string, NodeExecutionResult>;
  totalDurationMs: number;
  metrics: ExecutionMetrics;
  error?: Error;
}

export interface RenderGraphExecutorOptions {
  registry?: RendererRegistry;
  compositor?: MasterCompositor;
  artifactCache?: Map<string, IntermediateArtifact>;
  tempDir?: string;
}

export interface ExecutionContext {
  signal?: AbortSignal;
  tempDir?: string;
  logger?: {
    info: (msg: string) => void;
    warn: (msg: string) => void;
    error: (msg: string) => void;
  };
}

export class RenderGraphExecutor {
  private readonly _registry: RendererRegistry;
  private readonly _compositor: MasterCompositor;
  private readonly _cache: Map<string, IntermediateArtifact>;
  private readonly _baseTempDir: string;

  constructor(options?: RenderGraphExecutorOptions) {
    this._registry = options?.registry ?? CANONICAL_RENDERER_REGISTRY;
    this._compositor = options?.compositor ?? new MasterCompositor();
    this._cache = options?.artifactCache ?? new Map();
    this._baseTempDir = options?.tempDir ?? os.tmpdir();
  }

  /**
   * Executes a deterministic RenderPlan level by level.
   */
  async execute(plan: RenderPlan, context?: ExecutionContext): Promise<ExecutionResult> {
    const startTime = Date.now();
    const signal = context?.signal;
    const workDir = path.join(
      context?.tempDir || this._baseTempDir,
      `exec_${plan.id}_${Date.now()}`
    );
    fs.mkdirSync(workDir, { recursive: true });

    const nodeResults: Record<string, NodeExecutionResult> = {};
    const failedNodeIds = new Set<string>();
    let executedNodes = 0;
    let cachedNodes = 0;
    let failedNodes = 0;
    let parallelGroups = 0;

    try {
      for (const group of plan.executionGroups) {
        if (signal?.aborted) {
          throw new RenderPlanningError("PLANNING_FAILED", "Render graph execution aborted by signal");
        }

        if (group.parallel) {
          parallelGroups++;
        }

        // Execute all nodes in the current group
        const groupPromises = group.nodeIds.map(async (nodeId): Promise<NodeExecutionResult> => {
          if (signal?.aborted) {
            const err = new Error("Execution cancelled");
            return { nodeId, ok: false, error: err };
          }

          const node = plan.graph.nodes[nodeId];
          if (!node) {
            const err = new RenderPlanningError("MISSING_DEPENDENCY", `Node '${nodeId}' not found in graph`);
            return { nodeId, ok: false, error: err };
          }

          // 1. Dependency failure check
          for (const depId of node.dependencies) {
            if (failedNodeIds.has(depId)) {
              const err = new RenderPlanningError(
                "MISSING_DEPENDENCY",
                `Node '${nodeId}' skipped: upstream dependency '${depId}' failed.`
              );
              return { nodeId, ok: false, error: err };
            }
          }

          const nodeStart = Date.now();

          // 2. Cache hit check
          const fp = node.cacheability.contentFingerprint;
          if (node.cacheability.cacheable) {
            const cached = this._cache.get(fp) || this._cache.get(nodeId);
            if (cached && (!cached.filePath || fs.existsSync(cached.filePath))) {
              return {
                nodeId,
                ok: true,
                artifact: cached,
                metrics: {
                  durationMs: Date.now() - nodeStart,
                  cacheHit: true,
                },
              };
            }
          }

          // 3. Execution dispatch based on node scope
          try {
            if (node.scope.type === "compositor") {
              // Master Compositor assembly node
              const upstreamArtifacts: CompositorInput[] = [];
              for (const depId of node.dependencies) {
                const depRes = nodeResults[depId];
                if (!depRes || !depRes.artifact) {
                  throw new RenderPlanningError(
                    "MISSING_DEPENDENCY",
                    `Compositor node '${nodeId}' missing artifact for dependency '${depId}'`
                  );
                }
                const depNode = plan.graph.nodes[depId];
                upstreamArtifacts.push({
                  artifact: depRes.artifact,
                  canonicalSceneId: depNode?.scope.id,
                });
              }

              // Reconstruct canonical document for composition timing
              const fullDoc: BlueprintV2 = {
                blueprint_version: "2.0.0",
                project_id: plan.projectId,
                fps: plan.outputProfile.fps,
                aspect_ratio: plan.outputProfile.aspectRatio || "16:9",
                scenes: node.dependencies.map((depId) => {
                  const n = plan.graph.nodes[depId];
                  const origScene = n.fragmentDoc?.scenes?.[0] || {
                    scene_id: n.scope.id,
                    durationFrames: n.timeRange.durationFrames,
                  };
                  return {
                    ...origScene,
                    scene_id: n.scope.id,
                    startFrame: n.timeRange.startFrame,
                    durationFrames: n.timeRange.durationFrames,
                  };
                }),
              };

              const compResult: CompositorResult = await this._compositor.composite({
                id: `comp_${node.id}`,
                document: fullDoc,
                inputs: upstreamArtifacts,
                outputProfile: plan.outputProfile,
                outputPath: plan.outputPath,
                context: {
                  signal,
                  tempDir: workDir,
                },
              });

              if (!compResult.ok || !compResult.outputPath) {
                throw new RenderPlanningError(
                  "PLANNING_FAILED",
                  compResult.error?.message || "MasterCompositor execution failed"
                );
              }

              const probed = probeMediaFile(compResult.outputPath);
              const provenance: ArtifactProvenance = {
                sourceRenderNodeId: nodeId,
                rendererId: "master-compositor",
                rendererVersion: "1.0.0",
                canonicalRevision: plan.canonicalRevision,
                inputFingerprints: node.dependencies.map(
                  (d) => plan.graph.nodes[d]?.cacheability.contentFingerprint || ""
                ),
                outputProfile: plan.outputProfile,
                dependencyLineage: node.dependencies,
                createdAt: Date.now(),
              };

              const finalArtifact = createIntermediateArtifact({
                artifactId: `artifact_${nodeId}`,
                sourceRendererId: "master-compositor",
                canonicalRevision: plan.canonicalRevision,
                scope: { type: "project", id: plan.projectId },
                timeRange: node.timeRange,
                type: "video",
                filePath: compResult.outputPath,
                mediaInfo: probed,
                contentFingerprint: fp,
                metadata: { provenance },
              });

              this._cache.set(fp, finalArtifact);
              this._cache.set(nodeId, finalArtifact);

              return {
                nodeId,
                ok: true,
                artifact: finalArtifact,
                metrics: {
                  durationMs: Date.now() - nodeStart,
                  cacheHit: false,
                },
              };
            }

            // Scene render node dispatch to assigned adapter
            const rendererId = node.assignedRendererId;
            if (!rendererId) {
              throw new RenderPlanningError(
                "NO_COMPATIBLE_RENDERER",
                `Node '${nodeId}' has no assigned renderer.`
              );
            }

            const adapter: RendererAdapter = this._registry.requireRenderer(rendererId);
            const sceneOutPath = path.join(workDir, `${nodeId}_render.mp4`);

            const renderRes = await adapter.exportVideo({
              id: `req_${node.id}`,
              document: node.fragmentDoc,
              type: "export",
              output: {
                path: sceneOutPath,
                width: plan.outputProfile.width,
                height: plan.outputProfile.height,
                fps: plan.outputProfile.fps,
              },
              context: {
                projectId: plan.projectId,
                signal,
                tempDir: workDir,
              },
            });

            if (!renderRes.ok || !renderRes.output?.filePath) {
              throw new RenderPlanningError(
                "PLANNING_FAILED",
                renderRes.error?.message || `Renderer '${rendererId}' failed to export video for '${nodeId}'`
              );
            }

            const probed = probeMediaFile(renderRes.output.filePath);
            const provenance: ArtifactProvenance = {
              sourceRenderNodeId: nodeId,
              rendererId: adapter.id,
              rendererVersion: adapter.version,
              canonicalRevision: plan.canonicalRevision,
              inputFingerprints: [fp],
              outputProfile: plan.outputProfile,
              dependencyLineage: [],
              createdAt: Date.now(),
            };

            const intermediate = createIntermediateArtifact({
              artifactId: `artifact_${nodeId}`,
              sourceRendererId: adapter.id,
              canonicalRevision: plan.canonicalRevision,
              scope: { type: "scene", id: node.scope.id },
              timeRange: node.timeRange,
              type: "video",
              filePath: renderRes.output.filePath,
              mediaInfo: probed,
              contentFingerprint: fp,
              metadata: { provenance },
            });

            this._cache.set(fp, intermediate);
            this._cache.set(nodeId, intermediate);

            return {
              nodeId,
              ok: true,
              artifact: intermediate,
              metrics: {
                durationMs: Date.now() - nodeStart,
                cacheHit: false,
              },
            };
          } catch (err: unknown) {
            const errorObj = err instanceof Error ? err : new Error(String(err));
            return {
              nodeId,
              ok: false,
              error: errorObj,
            };
          }
        });

        const groupResults = await Promise.all(groupPromises);

        for (const res of groupResults) {
          nodeResults[res.nodeId] = res;
          if (res.ok) {
            if (res.metrics?.cacheHit) {
              cachedNodes++;
            } else {
              executedNodes++;
            }
          } else {
            failedNodes++;
            failedNodeIds.add(res.nodeId);
          }
        }
      }

      const totalDurationMs = Date.now() - startTime;
      const rootNodeId = plan.graph.rootNodeId || "node_master_compositor";
      const rootResult = nodeResults[rootNodeId];

      const overallOk = failedNodes === 0 && Boolean(rootResult?.ok);

      return {
        ok: overallOk,
        planId: plan.id,
        outputPath: rootResult?.artifact?.filePath || plan.outputPath,
        finalArtifact: rootResult?.artifact,
        nodeResults,
        totalDurationMs,
        metrics: {
          totalDurationMs,
          executedNodes,
          cachedNodes,
          failedNodes,
          parallelGroups,
        },
        error: overallOk ? undefined : rootResult?.error || new Error(`Execution failed for ${failedNodes} node(s)`),
      };
    } catch (err: unknown) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      return {
        ok: false,
        planId: plan.id,
        nodeResults,
        totalDurationMs: Date.now() - startTime,
        metrics: {
          totalDurationMs: Date.now() - startTime,
          executedNodes,
          cachedNodes,
          failedNodes: failedNodes + 1,
          parallelGroups,
        },
        error: errorObj,
      };
    } finally {
      // Work directory remains accessible for test inspection or can be swept
    }
  }
}
