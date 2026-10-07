/**
 * planner/production-render-graph-executor.ts — Production Multi-Engine RenderGraph Executor.
 * S28-R14: Production Integration of Multi-Engine Rendering & Master Compositor.
 * 
 * Strict Invariants:
 * - Structured failure codes: RENDERER_TIMEOUT, RENDERER_UNAVAILABLE, RENDERER_EXECUTION_FAILED,
 *   RENDERER_OUTPUT_INVALID, RENDERER_CANCELLED, RENDERER_CAPABILITY_MISMATCH.
 * - Per-node timeout policies and immediate cancellation handling.
 * - Bounded parallel execution concurrency.
 * - Strict workspace sandboxing: each renderer operates in an isolated temporary directory.
 * - Automatic guaranteed cleanup of temp workspaces on success, failure, and cancellation.
 * - Zero Remotion / Canvas branch assumptions: capability resolution through RendererRegistry.
 * - Master Compositor normalizes resolution, fps, timebase, audio across heterogeneous engines.
 * - Persistent outputs published to StorageService with full provenance metadata.
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";

import type { BlueprintV2 } from "../contracts/blueprint";
import {
  type RendererRegistry,
  type RendererAdapter,
  CANONICAL_RENDERER_REGISTRY,
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
import {
  type IStorageService,
  buildStorageKey,
  LocalStorageService,
} from "../contracts/storage-service";
import { MasterCompositor, probeMediaFile } from "../compositor";

export type ProductionRendererErrorCode =
  | "RENDERER_TIMEOUT"
  | "RENDERER_UNAVAILABLE"
  | "RENDERER_EXECUTION_FAILED"
  | "RENDERER_OUTPUT_INVALID"
  | "RENDERER_CANCELLED"
  | "RENDERER_CAPABILITY_MISMATCH"
  | "BUDGET_EXCEEDED"
  | "STORAGE_UNAVAILABLE";

export class ProductionRendererError extends Error {
  public readonly code: ProductionRendererErrorCode;
  public readonly nodeId: string;
  public readonly rendererId?: string;
  public readonly details?: Record<string, unknown>;

  constructor(
    code: ProductionRendererErrorCode,
    message: string,
    nodeId: string,
    rendererId?: string,
    details?: Record<string, unknown>
  ) {
    super(`[${code}] Node '${nodeId}'${rendererId ? ` (${rendererId})` : ""}: ${message}`);
    this.name = "ProductionRendererError";
    this.code = code;
    this.nodeId = nodeId;
    this.rendererId = rendererId;
    this.details = details;
  }
}

export interface BudgetCheckDecision {
  allowed: boolean;
  reason?: string;
  estimatedCost?: number;
}

export type BudgetChecker = (
  node: RenderNode,
  ctx: ProductionExecutionContext
) => Promise<BudgetCheckDecision> | BudgetCheckDecision;

export interface ProductionNodeResult {
  nodeId: string;
  ok: boolean;
  artifact?: IntermediateArtifact;
  storageKey?: string;
  durationMs: number;
  cacheHit: boolean;
  error?: ProductionRendererError;
}

export interface ProductionExecutionResult {
  ok: boolean;
  planId: string;
  runId?: string;
  outputPath?: string;
  outputStorageKey?: string;
  finalArtifact?: IntermediateArtifact;
  nodeResults: Record<string, ProductionNodeResult>;
  totalDurationMs: number;
  error?: ProductionRendererError | Error;
}

export interface ProductionExecutorOptions {
  registry?: RendererRegistry;
  compositor?: MasterCompositor;
  storageService?: IStorageService;
  baseTempDir?: string;
  defaultNodeTimeoutMs?: number;
  maxConcurrency?: number;
  eventPublisher?: (eventType: string, payload: Record<string, any>) => void;
  budgetChecker?: BudgetChecker;
}

export interface ProductionExecutionContext {
  workspaceId: string;
  projectId: string;
  runId?: string;
  traceId?: string;
  spanId?: string;
  canonicalRevision: number;
  signal?: AbortSignal;
  nodeTimeoutMs?: number;
  persistIntermediates?: boolean;
}

export class ProductionRenderGraphExecutor {
  private readonly registry: RendererRegistry;
  private readonly compositor: MasterCompositor;
  private readonly storage: IStorageService;
  private readonly baseTempDir: string;
  private readonly defaultNodeTimeoutMs: number;
  private readonly maxConcurrency: number;
  private readonly publishEvent: (eventType: string, payload: Record<string, any>) => void;
  private readonly budgetChecker?: BudgetChecker;
  private readonly artifactCache = new Map<string, IntermediateArtifact>();

  constructor(options?: ProductionExecutorOptions) {
    this.registry = options?.registry ?? CANONICAL_RENDERER_REGISTRY;
    this.compositor = options?.compositor ?? new MasterCompositor();
    this.storage = options?.storageService ?? new LocalStorageService();
    this.baseTempDir = options?.baseTempDir ?? os.tmpdir();
    this.defaultNodeTimeoutMs = options?.defaultNodeTimeoutMs ?? 60_000;
    this.maxConcurrency = options?.maxConcurrency ?? 4;
    this.publishEvent = options?.eventPublisher ?? (() => {});
    this.budgetChecker = options?.budgetChecker;
  }

  /**
   * Executes a multi-engine RenderPlan with failure isolation and sandboxing.
   */
  async execute(
    plan: RenderPlan,
    ctx: ProductionExecutionContext
  ): Promise<ProductionExecutionResult> {
    const startTime = Date.now();
    const runId = ctx.runId || `run_${Date.now()}`;
    const workDir = path.join(
      this.baseTempDir,
      `render_sandbox_${ctx.workspaceId}_${ctx.projectId}_${runId}`
    );
    fs.mkdirSync(workDir, { recursive: true });

    const nodeResults: Record<string, ProductionNodeResult> = {};
    const failedNodeIds = new Set<string>();

    this.publishEvent("RENDER_STARTED", {
      workspaceId: ctx.workspaceId,
      projectId: ctx.projectId,
      runId,
      planId: plan.id,
      canonicalRevision: ctx.canonicalRevision,
      nodeCount: Object.keys(plan.graph.nodes).length,
    });

    try {
      for (const group of plan.executionGroups) {
        if (ctx.signal?.aborted) {
          throw new ProductionRendererError(
            "RENDERER_CANCELLED",
            "Execution cancelled before group start",
            "group",
            undefined
          );
        }

        // Bounded concurrency pool for group execution
        const nodeIds = group.nodeIds;
        const chunks: string[][] = [];
        const concurrency = group.parallel ? Math.min(this.maxConcurrency, nodeIds.length) : 1;

        for (let i = 0; i < nodeIds.length; i += concurrency) {
          chunks.push(nodeIds.slice(i, i + concurrency));
        }

        for (const chunk of chunks) {
          if (ctx.signal?.aborted) {
            throw new ProductionRendererError(
              "RENDERER_CANCELLED",
              "Execution cancelled during group execution",
              chunk[0],
              undefined
            );
          }

          const promises = chunk.map((nodeId) =>
            this.executeNode(nodeId, plan, ctx, workDir, nodeResults, failedNodeIds)
          );

          const results = await Promise.all(promises);
          for (const res of results) {
            nodeResults[res.nodeId] = res;
            if (!res.ok) {
              failedNodeIds.add(res.nodeId);
              // Fail closed: halt subsequent execution on error
              throw res.error || new Error(`Node '${res.nodeId}' failed`);
            }
          }
        }
      }

      // Final root compositor result lookup
      const rootNode = Object.values(plan.graph.nodes).find((n) => n.scope.type === "compositor");
      const finalNodeRes = rootNode ? nodeResults[rootNode.id] : undefined;
      const finalArtifact = finalNodeRes?.artifact;

      let outputStorageKey: string | undefined;
      if (finalArtifact?.filePath && fs.existsSync(finalArtifact.filePath)) {
        // Upload final artifact to StorageService
        const finalKey = buildStorageKey(
          ctx.workspaceId,
          ctx.projectId,
          "outputs",
          runId,
          "out.mp4"
        );
        try {
          const videoBuffer = fs.readFileSync(finalArtifact.filePath);
          await this.storage.put(finalKey, videoBuffer, "video/mp4");
          outputStorageKey = finalKey;
        } catch (storageErr: any) {
          throw new ProductionRendererError(
            "STORAGE_UNAVAILABLE",
            `Failed to upload output artifact to StorageService: ${storageErr.message}`,
            rootNode?.id || "compositor",
            undefined,
            { storageKey: finalKey }
          );
        }
      }

      const totalDurationMs = Date.now() - startTime;
      this.publishEvent("RENDER_SUCCEEDED", {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        runId,
        outputStorageKey,
        totalDurationMs,
      });

      return {
        ok: true,
        planId: plan.id,
        runId,
        outputPath: finalArtifact?.filePath,
        outputStorageKey,
        finalArtifact,
        nodeResults,
        totalDurationMs,
      };
    } catch (err: any) {
      const totalDurationMs = Date.now() - startTime;
      this.publishEvent("RENDER_FAILED", {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        runId,
        error: err.message,
        code: err.code || "RENDER_FAILED",
        totalDurationMs,
      });

      return {
        ok: false,
        planId: plan.id,
        runId,
        nodeResults,
        totalDurationMs,
        error: err,
      };
    } finally {
      // Guaranteed temporary sandbox cleanup
      try {
        if (fs.existsSync(workDir)) {
          fs.rmSync(workDir, { recursive: true, force: true });
        }
      } catch (cleanupErr) {
        console.warn(`Failed to clean sandbox workdir '${workDir}':`, cleanupErr);
      }
    }
  }

  private async executeNode(
    nodeId: string,
    plan: RenderPlan,
    ctx: ProductionExecutionContext,
    parentWorkDir: string,
    completedResults: Record<string, ProductionNodeResult>,
    failedNodeIds: Set<string>
  ): Promise<ProductionNodeResult> {
    const nodeStart = Date.now();
    const node = plan.graph.nodes[nodeId];

    if (!node) {
      return {
        nodeId,
        ok: false,
        durationMs: 0,
        cacheHit: false,
        error: new ProductionRendererError(
          "RENDERER_EXECUTION_FAILED",
          `Node '${nodeId}' not found in RenderGraph`,
          nodeId
        ),
      };
    }

    // 1. Upstream dependency check
    for (const depId of node.dependencies) {
      if (failedNodeIds.has(depId)) {
        return {
          nodeId,
          ok: false,
          durationMs: 0,
          cacheHit: false,
          error: new ProductionRendererError(
            "RENDERER_EXECUTION_FAILED",
            `Skipped because upstream dependency '${depId}' failed`,
            nodeId
          ),
        };
      }
    }

    // 2. Cancellation check
    if (ctx.signal?.aborted) {
      return {
        nodeId,
        ok: false,
        durationMs: 0,
        cacheHit: false,
        error: new ProductionRendererError(
          "RENDERER_CANCELLED",
          "Node execution cancelled by AbortSignal",
          nodeId,
          node.assignedRendererId
        ),
      };
    }

    // 3. Cache check
    const fp = node.cacheability.contentFingerprint;
    if (node.cacheability.cacheable) {
      const cached = this.artifactCache.get(fp) || this.artifactCache.get(nodeId);
      if (cached && (!cached.filePath || fs.existsSync(cached.filePath))) {
        return {
          nodeId,
          ok: true,
          artifact: cached,
          durationMs: Date.now() - nodeStart,
          cacheHit: true,
        };
      }
    }

    // 3.5. Pre-execution budget and cost policy evaluation (Section 18)
    if (this.budgetChecker) {
      const budgetDecision = await this.budgetChecker(node, ctx);
      if (!budgetDecision.allowed) {
        this.publishEvent("BUDGET_EXCEEDED", {
          workspaceId: ctx.workspaceId,
          projectId: ctx.projectId,
          runId: ctx.runId,
          nodeId,
          reason: budgetDecision.reason,
        });
        return {
          nodeId,
          ok: false,
          durationMs: 0,
          cacheHit: false,
          error: new ProductionRendererError(
            "BUDGET_EXCEEDED",
            budgetDecision.reason || `Cost/budget policy rejected node '${nodeId}'`,
            nodeId,
            node.assignedRendererId,
            { estimatedCost: budgetDecision.estimatedCost }
          ),
        };
      }
    }

    // 4. Create isolated sandboxed workspace for node
    const nodeWorkDir = path.join(parentWorkDir, `node_${nodeId}`);
    fs.mkdirSync(nodeWorkDir, { recursive: true });

    const timeoutMs = ctx.nodeTimeoutMs || this.defaultNodeTimeoutMs;

    this.publishEvent("RENDER_NODE_STARTED", {
      workspaceId: ctx.workspaceId,
      projectId: ctx.projectId,
      nodeId,
      rendererId: node.assignedRendererId,
      timeRange: node.timeRange,
    });

    try {
      let artifact: IntermediateArtifact;

      if (node.scope.type === "compositor") {
        // Master Compositor Node
        this.publishEvent("COMPOSITION_STARTED", {
          workspaceId: ctx.workspaceId,
          projectId: ctx.projectId,
          nodeId,
        });

        const upstreamArtifacts: CompositorInput[] = [];
        for (const depId of node.dependencies) {
          const depRes = completedResults[depId];
          if (!depRes || !depRes.artifact) {
            throw new ProductionRendererError(
              "RENDERER_EXECUTION_FAILED",
              `Missing required upstream intermediate artifact '${depId}'`,
              nodeId
            );
          }
          const depNode = plan.graph.nodes[depId];
          upstreamArtifacts.push({
            artifact: depRes.artifact,
            canonicalSceneId: depNode?.scope.id,
          });
        }

        const compDoc: BlueprintV2 = {
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

        const compPromise = this.compositor.composite({
          id: `comp_${node.id}`,
          document: compDoc,
          inputs: upstreamArtifacts,
          outputProfile: plan.outputProfile,
          outputPath: path.join(nodeWorkDir, "master_composite.mp4"),
          context: {
            signal: ctx.signal,
            tempDir: nodeWorkDir,
          },
        });

        const compResult = (await this.withTimeout(
          compPromise,
          timeoutMs,
          nodeId,
          "master-compositor"
        )) as CompositorResult;

        if (!compResult.ok || !compResult.outputPath || !fs.existsSync(compResult.outputPath)) {
          throw new ProductionRendererError(
            "RENDERER_OUTPUT_INVALID",
            compResult.error?.message || "MasterCompositor produced invalid or missing output",
            nodeId,
            "master-compositor"
          );
        }

        const probed = probeMediaFile(compResult.outputPath);
        const provenance: ArtifactProvenance = {
          sourceRenderNodeId: nodeId,
          rendererId: "master-compositor",
          rendererVersion: "1.0.0",
          canonicalRevision: ctx.canonicalRevision,
          inputFingerprints: node.dependencies.map(
            (d) => plan.graph.nodes[d]?.cacheability.contentFingerprint || ""
          ),
          outputProfile: plan.outputProfile,
          dependencyLineage: node.dependencies,
          createdAt: Date.now(),
        };

        artifact = createIntermediateArtifact({
          artifactId: `artifact_${nodeId}`,
          sourceRendererId: "master-compositor",
          canonicalRevision: ctx.canonicalRevision,
          scope: { type: "project", id: plan.projectId },
          timeRange: node.timeRange,
          type: "video",
          filePath: compResult.outputPath,
          mediaInfo: probed,
          contentFingerprint: fp,
          metadata: { provenance },
        });

        this.publishEvent("COMPOSITION_COMPLETED", {
          workspaceId: ctx.workspaceId,
          projectId: ctx.projectId,
          nodeId,
        });
      } else {
        // Leaf / Scene Render Node
        const rendererId = node.assignedRendererId;
        if (!rendererId) {
          throw new ProductionRendererError(
            "RENDERER_UNAVAILABLE",
            "Node has no assigned renderer",
            nodeId
          );
        }

        let adapter: RendererAdapter;
        try {
          adapter = this.registry.requireRenderer(rendererId);
        } catch (e: any) {
          throw new ProductionRendererError(
            "RENDERER_UNAVAILABLE",
            `Assigned renderer '${rendererId}' is not registered: ${e.message}`,
            nodeId,
            rendererId
          );
        }

        // Capability validation check
        const missingCaps = adapter.capabilities().getMissing(node.requiredCapabilities);
        if (missingCaps.length > 0) {
          throw new ProductionRendererError(
            "RENDERER_CAPABILITY_MISMATCH",
            `Renderer '${rendererId}' lacks required capabilities: ${missingCaps.join(", ")}`,
            nodeId,
            rendererId,
            { missingCapabilities: missingCaps }
          );
        }

        const sceneOutPath = path.join(nodeWorkDir, `${nodeId}_render.mp4`);
        const renderPromise = adapter.exportVideo({
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
            signal: ctx.signal,
            tempDir: nodeWorkDir,
          },
        });

        const renderRes = (await this.withTimeout(
          renderPromise,
          timeoutMs,
          nodeId,
          rendererId
        )) as any;

        if (!renderRes.ok || !renderRes.output?.filePath || !fs.existsSync(renderRes.output.filePath)) {
          throw new ProductionRendererError(
            "RENDERER_EXECUTION_FAILED",
            renderRes.error?.message || `Renderer '${rendererId}' failed to export video`,
            nodeId,
            rendererId
          );
        }

        const probed = probeMediaFile(renderRes.output.filePath);
        if (!probed || (probed.durationSec || 0) <= 0) {
          throw new ProductionRendererError(
            "RENDERER_OUTPUT_INVALID",
            `Renderer '${rendererId}' produced unreadable or zero-duration media`,
            nodeId,
            rendererId
          );
        }

        const provenance: ArtifactProvenance = {
          sourceRenderNodeId: nodeId,
          rendererId: adapter.id,
          rendererVersion: adapter.version,
          canonicalRevision: ctx.canonicalRevision,
          inputFingerprints: [fp],
          outputProfile: plan.outputProfile,
          dependencyLineage: [],
          createdAt: Date.now(),
        };

        artifact = createIntermediateArtifact({
          artifactId: `artifact_${nodeId}`,
          sourceRendererId: adapter.id,
          canonicalRevision: ctx.canonicalRevision,
          scope: { type: "scene", id: node.scope.id },
          timeRange: node.timeRange,
          type: "video",
          filePath: renderRes.output.filePath,
          mediaInfo: probed,
          contentFingerprint: fp,
          metadata: { provenance },
        });
      }

      this.artifactCache.set(fp, artifact);
      this.artifactCache.set(nodeId, artifact);

      let intermediateStorageKey: string | undefined;
      if (ctx.persistIntermediates && artifact.filePath && fs.existsSync(artifact.filePath)) {
        const iKey = buildStorageKey(
          ctx.workspaceId,
          ctx.projectId,
          "intermediates",
          `rev_${ctx.canonicalRevision}_${nodeId}`,
          "intermediate.mp4"
        );
        try {
          await this.storage.put(iKey, fs.readFileSync(artifact.filePath), "video/mp4");
          intermediateStorageKey = iKey;
        } catch (storageErr: any) {
          throw new ProductionRendererError(
            "STORAGE_UNAVAILABLE",
            `Failed to upload intermediate artifact to StorageService: ${storageErr.message}`,
            nodeId,
            node.assignedRendererId,
            { storageKey: iKey }
          );
        }
      }

      const durationMs = Date.now() - nodeStart;
      this.publishEvent("RENDER_NODE_COMPLETED", {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        nodeId,
        durationMs,
      });

      this.publishEvent("USAGE_METERED", {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        runId: ctx.runId,
        nodeId,
        rendererId: node.assignedRendererId || "master-compositor",
        durationMs,
        outputBytes: (artifact.filePath && fs.existsSync(artifact.filePath)) ? fs.statSync(artifact.filePath).size : 0,
      });

      return {
        nodeId,
        ok: true,
        artifact,
        storageKey: intermediateStorageKey,
        durationMs,
        cacheHit: false,
      };
    } catch (err: any) {
      const prodErr: ProductionRendererError =
        err instanceof ProductionRendererError
          ? err
          : new ProductionRendererError(
              ctx.signal?.aborted ? "RENDERER_CANCELLED" : "RENDERER_EXECUTION_FAILED",
              err.message || String(err),
              nodeId,
              node.assignedRendererId
            );

      this.publishEvent("RENDER_NODE_FAILED", {
        workspaceId: ctx.workspaceId,
        projectId: ctx.projectId,
        nodeId,
        code: prodErr.code,
        message: prodErr.message,
      });

      return {
        nodeId,
        ok: false,
        durationMs: Date.now() - nodeStart,
        cacheHit: false,
        error: prodErr,
      };
    }
  }

  private async withTimeout<T>(
    promise: Promise<T>,
    timeoutMs: number,
    nodeId: string,
    rendererId?: string
  ): Promise<T> {
    let timer: any;
    const timeoutPromise = new Promise<never>((_, reject) => {
      timer = setTimeout(() => {
        reject(
          new ProductionRendererError(
            "RENDERER_TIMEOUT",
            `Execution exceeded timeout of ${timeoutMs}ms`,
            nodeId,
            rendererId
          )
        );
      }, timeoutMs);
    });

    try {
      return await Promise.race([promise, timeoutPromise]);
    } finally {
      clearTimeout(timer);
    }
  }
}
