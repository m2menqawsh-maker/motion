/**
 * preview/proxy/proxy-coordinator.ts — Local Async Preview Proxy Job Coordinator.
 * S28-R07B: Orchestrates background preview proxy generation via RendererRegistry.
 * 
 * Strict Invariants:
 *   - Engine-neutral: NEVER checks "if remotion ... else if canvas ...".
 *   - Routes 100% of render requests through RendererRegistry.selectRenderer().
 *   - Stale Result Protection: results from older revisions NEVER overwrite newer document state.
 *   - Job lifecycle states: queued -> running -> ready | failed | cancelled | stale.
 *   - Transparent caching with PreviewProxyCache.
 */

import {
  type RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  type RenderRequest,
  type RenderResult,
  type RenderContext,
  RendererError,
} from "../../contracts/renderer";
import type { BlueprintV2 } from "../../contracts/blueprint";
import type { ChangeSet } from "../../contracts/mutations";
import {
  type PreviewProxyRequest,
  type PreviewProxyArtifact,
} from "../../contracts/preview-proxy";
import {
  PreviewProxyCache,
  computeProxyCacheKey,
  type ProxyDependencyInfo,
} from "./proxy-cache";

export type PreviewJobStatus =
  | "queued"
  | "running"
  | "ready"
  | "failed"
  | "cancelled"
  | "stale";

export interface PreviewProxyJobError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface PreviewProxyJob {
  id: string;
  request: PreviewProxyRequest;
  status: PreviewJobStatus;
  progress: number; // 0.0 to 1.0
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  error?: PreviewProxyJobError;
  artifact?: PreviewProxyArtifact;
  cancel(): void;
}

export type ProxyJobListener = (job: PreviewProxyJob) => void;

export interface PreviewProxyCoordinatorOptions {
  registry?: RendererRegistry;
  cache?: PreviewProxyCache;
  onJobStatusChange?: (job: PreviewProxyJob) => void;
}

export class PreviewProxyCoordinator {
  private readonly registry: RendererRegistry;
  private readonly cache: PreviewProxyCache;
  private readonly jobs = new Map<string, PreviewProxyJob>();
  private readonly abortControllers = new Map<string, AbortController>();
  private readonly listeners = new Set<ProxyJobListener>();

  // Current document revision tracked by this coordinator
  private currentRevision: number = 0;

  constructor(options?: PreviewProxyCoordinatorOptions) {
    this.registry = options?.registry ?? CANONICAL_RENDERER_REGISTRY;
    this.cache = options?.cache ?? new PreviewProxyCache();
    if (options?.onJobStatusChange) {
      this.listeners.add(options.onJobStatusChange);
    }
  }

  public getCache(): PreviewProxyCache {
    return this.cache;
  }

  public getRegistry(): RendererRegistry {
    return this.registry;
  }

  public updateCurrentRevision(revision: number): void {
    const previous = this.currentRevision;
    this.currentRevision = revision;
    if (revision > previous) {
      // Mark any in-flight jobs for older revisions as stale
      for (const job of this.jobs.values()) {
        if (
          (job.status === "queued" || job.status === "running") &&
          job.request.canonical_revision < revision
        ) {
          this.markJobStale(job);
        }
      }
    }
  }

  public getCurrentRevision(): number {
    return this.currentRevision;
  }

  public subscribe(listener: ProxyJobListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(job: PreviewProxyJob): void {
    for (const listener of this.listeners) {
      try {
        listener(job);
      } catch (e) {
        console.error("Error in proxy job listener:", e);
      }
    }
  }

  public getJob(jobId: string): PreviewProxyJob | undefined {
    return this.jobs.get(jobId);
  }

  public listJobs(): PreviewProxyJob[] {
    return Array.from(this.jobs.values());
  }

  public cancelJob(jobId: string): boolean {
    const job = this.jobs.get(jobId);
    if (!job) return false;

    if (job.status === "queued" || job.status === "running") {
      const controller = this.abortControllers.get(jobId);
      if (controller) {
        controller.abort();
        this.abortControllers.delete(jobId);
      }
      job.status = "cancelled";
      job.completedAt = Date.now();
      this.notify(job);
      return true;
    }
    return false;
  }

  public invalidateWithChangeSet(changeSet: ChangeSet, newRevision?: number): number {
    if (newRevision !== undefined) {
      this.updateCurrentRevision(newRevision);
    }

    // Invalidate cache
    const count = this.cache.invalidateByChangeSet(changeSet, newRevision);

    // Also mark running/queued jobs as stale if their entity/scene was affected
    const affectedScenes = new Set(changeSet.affected_scene_ids || []);
    const affectedLayers = new Set(changeSet.affected_layer_ids || []);

    for (const job of this.jobs.values()) {
      if (job.status === "queued" || job.status === "running") {
        const entity = job.request.entity;
        if (
          (entity.sceneId && affectedScenes.has(entity.sceneId)) ||
          (entity.layerId && affectedLayers.has(entity.layerId)) ||
          changeSet.invalidation?.requires_timeline_rebuild
        ) {
          this.markJobStale(job);
        }
      }
    }

    return count;
  }

  private markJobStale(job: PreviewProxyJob): void {
    job.status = "stale";
    job.completedAt = Date.now();
    const controller = this.abortControllers.get(job.id);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(job.id);
    }
    this.notify(job);
  }

  /**
   * Main entry point to request a preview proxy.
   * Checks cache first; if cache hit, resolves immediately with cached artifact.
   * Otherwise, schedules local async execution via compatible renderer in RendererRegistry.
   */
  public async requestProxy(
    request: PreviewProxyRequest,
    fragmentDocument: BlueprintV2,
    documentRevision?: number
  ): Promise<PreviewProxyArtifact> {
    const revision = documentRevision ?? request.canonical_revision;
    this.updateCurrentRevision(revision);

    const cacheKey = computeProxyCacheKey({
      projectId: request.project_id,
      canonicalRevision: request.canonical_revision,
      contentFingerprint: request.contentFingerprint,
      entity: request.entity,
      timeRange: request.timeRange,
      requiredCapabilities: request.requiredCapabilities,
      width: request.width,
      height: request.height,
      quality: request.quality,
      schemaVersion: request.schemaVersion,
    });

    // 1. Cache Check
    const cached = this.cache.get(cacheKey);
    if (cached) {
      const readyJob: PreviewProxyJob = {
        id: request.id,
        request,
        status: "ready",
        progress: 1.0,
        createdAt: Date.now(),
        startedAt: Date.now(),
        completedAt: Date.now(),
        artifact: cached,
        cancel: () => {},
      };
      this.jobs.set(readyJob.id, readyJob);
      this.notify(readyJob);
      return cached;
    }

    // 2. Stale Check before starting
    if (request.canonical_revision < this.currentRevision) {
      const staleJob: PreviewProxyJob = {
        id: request.id,
        request,
        status: "stale",
        progress: 0,
        createdAt: Date.now(),
        completedAt: Date.now(),
        cancel: () => {},
        error: {
          code: "STALE_REVISION",
          message: `Request revision ${request.canonical_revision} is older than current revision ${this.currentRevision}`,
        },
      };
      this.jobs.set(staleJob.id, staleJob);
      this.notify(staleJob);
      throw new Error(`STALE_REVISION: Request is obsolete before execution`);
    }

    // 3. Create Queued Job
    const abortController = new AbortController();
    this.abortControllers.set(request.id, abortController);

    const job: PreviewProxyJob = {
      id: request.id,
      request,
      status: "queued",
      progress: 0,
      createdAt: Date.now(),
      cancel: () => this.cancelJob(request.id),
    };
    this.jobs.set(job.id, job);
    this.notify(job);

    // 4. Construct RenderRequest for RendererRegistry
    const renderRequest: RenderRequest = {
      id: `proxy-render-${request.id}`,
      document: fragmentDocument,
      type: "frame",
      frame: request.timeRange.startFrame,
      output: {
        width: request.width,
        height: request.height,
        fps: request.fps,
        quality: request.quality,
        format: request.format,
        includeAudio: false, // Visual-only proxy
      },
      requiredCapabilities: request.requiredCapabilities,
      context: {
        projectId: request.project_id,
        signal: abortController.signal,
        ...request.context,
      },
    };

    // 5. Select compatible renderer via Registry (Fail-Closed)
    let rendererAdapter;
    try {
      rendererAdapter = this.registry.selectRenderer(renderRequest);
    } catch (err: any) {
      job.status = "failed";
      job.completedAt = Date.now();
      job.error = {
        code: err.code || "NO_COMPATIBLE_RENDERER",
        message: err.message,
        details: err.details,
      };
      this.abortControllers.delete(request.id);
      this.notify(job);
      throw err;
    }

    // 6. Transition to Running
    job.status = "running";
    job.startedAt = Date.now();
    job.progress = 0.2;
    this.notify(job);

    // 7. Execute render via adapter
    let renderResult: RenderResult;
    try {
      renderResult = await rendererAdapter.renderFrame(renderRequest, renderRequest.context);
    } catch (err: any) {
      this.abortControllers.delete(request.id);
      if (job.status === "stale" || request.canonical_revision < this.currentRevision) {
        job.status = "stale";
        job.completedAt = Date.now();
        this.notify(job);
        throw new Error(
          `STALE_RESULT: Render discarded because document revision reached ${this.currentRevision}`
        );
      }
      if (abortController.signal.aborted) {
        job.status = "cancelled";
        job.completedAt = Date.now();
        this.notify(job);
        throw new Error("Proxy job was cancelled");
      }
      job.status = "failed";
      job.completedAt = Date.now();
      job.error = {
        code: err.code || "RENDER_FAILED",
        message: err.message,
        details: err.details,
      };
      this.notify(job);
      throw err;
    } finally {
      this.abortControllers.delete(request.id);
    }

    // 8. Stale Result Protection Check
    if (job.status === "stale" || request.canonical_revision < this.currentRevision) {
      job.status = "stale";
      job.completedAt = Date.now();
      this.notify(job);
      throw new Error(
        `STALE_RESULT: Render completed for revision ${request.canonical_revision}, but current revision is ${this.currentRevision}. Overwrite rejected.`
      );
    }

    if (abortController.signal.aborted || job.status === "cancelled") {
      throw new Error("Proxy job was cancelled");
    }

    if (!renderResult.ok || !renderResult.output) {
      job.status = "failed";
      job.completedAt = Date.now();
      job.error = {
        code: renderResult.error?.code || "RENDER_FAILED",
        message: renderResult.error?.message || "RenderResult returned ok: false",
      };
      this.notify(job);
      throw new Error(job.error.message);
    }

    // 9. Build Artifact
    const outputBuffer = renderResult.output.buffer;
    const outputDataUrl = renderResult.output.dataUrl;
    const outputFilePath = renderResult.output.filePath;
    const sizeBytes = outputBuffer
      ? outputBuffer.byteLength
      : outputDataUrl
      ? outputDataUrl.length
      : 1024;

    const artifact: PreviewProxyArtifact = {
      id: `artifact-${request.id}`,
      requestId: request.id,
      cacheKey,
      project_id: request.project_id,
      canonical_revision: request.canonical_revision,
      entity: request.entity,
      timeRange: request.timeRange,
      width: request.width,
      height: request.height,
      fps: request.fps,
      format: request.format,
      rendererId: rendererAdapter.id,
      output: {
        filePath: outputFilePath,
        dataUrl: outputDataUrl,
        buffer: outputBuffer,
        mimeType: renderResult.output.mimeType || `image/${request.format}`,
      },
      createdAt: Date.now(),
      sizeBytes,
    };

    // 10. Store in Cache with fine-grained dependencies
    const dependencies: ProxyDependencyInfo = {
      projectId: request.project_id,
      canonicalRevision: request.canonical_revision,
      contentFingerprint: request.contentFingerprint,
      sceneIds: request.entity.sceneId ? [request.entity.sceneId] : [],
      layerIds: request.entity.layerId ? [request.entity.layerId] : [],
      assetIds: [],
      timeRange: request.timeRange,
      requiredCapabilities: request.requiredCapabilities,
    };

    this.cache.set(cacheKey, artifact, dependencies);

    // 11. Finalize Job
    job.status = "ready";
    job.progress = 1.0;
    job.completedAt = Date.now();
    job.artifact = artifact;
    this.notify(job);

    return artifact;
  }
}
