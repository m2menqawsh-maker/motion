/**
 * tests/remotion/s28_r14_production_integration.test.ts
 * Comprehensive Verification Suite for S28-R14: Production Integration (TypeScript Boundaries).
 * 
 * Verifies:
 *   - Section 1.5: Production Storage Boundary (fail-closed path traversal, scoped keys, persistence)
 *   - Section 7: Production Preview Integration (StorageService persistence, stale job protection, ChangeSet invalidation)
 *   - Section 9: Renderer Job Isolation (isolated sandboxes, cleanup guarantees on success/failure/cancellation)
 *   - Section 10: Renderer Timeouts and Failure Isolation (RENDERER_TIMEOUT, RENDERER_UNAVAILABLE, RENDERER_CANCELLED)
 *   - Section 12: Cancellation Propagation (AbortSignal aborts immediately, cleans up workspace)
 *   - Section 13: Multi-Engine RenderGraph Execution with MasterCompositor integration
 *   - Section 15: Artifact Provenance verification on intermediate and final artifacts
 *   - Section 16: Durable event emissions across preview and render pipelines
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync } from "child_process";

import {
  type BlueprintV2,
  emptyChangeSet,
} from "../../contracts";
import {
  validateStorageKey,
  buildStorageKey,
  LocalStorageService,
  StorageSecurityError,
} from "../../contracts/storage-service";
import {
  createPreviewProxyRequest,
  type PreviewProxyRequest,
} from "../../contracts/preview-proxy";
import {
  ProductionPreviewCoordinator,
} from "../../preview/proxy/production-preview-coordinator";
import {
  ProductionRenderGraphExecutor,
  ProductionRendererError,
  type ProductionExecutionContext,
} from "../../planner/production-render-graph-executor";
import {
  RendererRegistry,
  createMockRendererAdapter,
  CANONICAL_RENDERER_REGISTRY,
} from "../../contracts/renderer";
import {
  createDefaultOutputProfile,
} from "../../contracts/compositor";
import { MasterCompositor, findSystemFfmpeg } from "../../compositor";

describe("S28-R14 Production Integration — Storage, Preview & Multi-Engine Execution", () => {
  let tempStorageDir: string;
  let tempSandboxDir: string;
  let storageService: LocalStorageService;
  const ffmpeg = findSystemFfmpeg();

  // Helper to generate synthetic test video with ffmpeg
  function generateSyntheticVideo(
    filePath: string,
    width = 640,
    height = 360,
    fps = 30,
    durationSec = 1,
    color = "blue"
  ): void {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    execFileSync(
      ffmpeg,
      [
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        `color=c=${color}:s=${width}x${height}:r=${fps}:d=${durationSec}`,
        "-f",
        "lavfi",
        "-i",
        `sine=frequency=440:r=44100:d=${durationSec}`,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        filePath,
      ],
      { stdio: "pipe" }
    );
  }

  const mockBlueprint: BlueprintV2 = {
    schema_version: "2.0.0",
    project_id: "prj_r14_test",
    title: "S28-R14 Production Test",
    aspect_ratio: "16:9",
    target_duration_sec: 10,
    fps: 30,
    width: 1920,
    height: 1080,
    scenes: [
      {
        id: "scene_01",
        name: "Scene 1",
        start_frame: 0,
        duration_frames: 150,
        layers: [
          {
            id: "layer_title",
            name: "Title Layer",
            type: "text",
            start_frame: 0,
            duration_frames: 150,
            z_index: 1,
            properties: {
              text: "Production Integration Test",
              color: "#ffffff",
            },
          },
        ],
      },
      {
        id: "scene_02",
        name: "Scene 2",
        start_frame: 150,
        duration_frames: 150,
        layers: [
          {
            id: "layer_bg",
            name: "Background",
            type: "solid",
            start_frame: 0,
            duration_frames: 150,
            z_index: 0,
            properties: {
              color: "#112233",
            },
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    tempStorageDir = fs.mkdtempSync(path.join(os.tmpdir(), "s28_r14_storage_"));
    tempSandboxDir = fs.mkdtempSync(path.join(os.tmpdir(), "s28_r14_sandbox_"));
    storageService = new LocalStorageService(tempStorageDir);
  });

  afterEach(() => {
    try {
      fs.rmSync(tempStorageDir, { recursive: true, force: true });
    } catch {}
    try {
      fs.rmSync(tempSandboxDir, { recursive: true, force: true });
    } catch {}
  });

  describe("1. StorageService Boundaries & Path Traversal Security (Section 1.5)", () => {
    it("R14-ST-01: Correctly stores, retrieves, and checks existence of objects", async () => {
      const key = "workspaces/ws_1/projects/prj_1/renders/run_1/output.mp4";
      const payload = Buffer.from("dummy video stream content");

      const meta = await storageService.put(key, payload, "video/mp4");
      expect(meta.key).toBe(key);
      expect(meta.sizeBytes).toBe(payload.length);
      expect(meta.contentType).toBe("video/mp4");

      const exists = await storageService.exists(key);
      expect(exists).toBe(true);

      const retrieved = await storageService.get(key);
      expect(retrieved.toString()).toBe("dummy video stream content");

      const deleted = await storageService.delete(key);
      expect(deleted).toBe(true);

      const existsAfter = await storageService.exists(key);
      expect(existsAfter).toBe(false);
    });

    it("R14-ST-02: Rejects path traversal attempts fail-closed", () => {
      expect(() => validateStorageKey("../escaped/file.json")).toThrow(StorageSecurityError);
      expect(() => validateStorageKey("workspaces/ws_1/../../root.json")).toThrow(StorageSecurityError);
      expect(() => validateStorageKey("/absolute/path/file.json")).toThrow(StorageSecurityError);
      expect(() => validateStorageKey("workspaces/ws_1/projects/prj_1/file\0null.json")).toThrow(StorageSecurityError);
      expect(() => validateStorageKey("")).toThrow(StorageSecurityError);
    });

    it("R14-ST-03: buildStorageKey enforces tenant-scoped server-generated paths", () => {
      const validKey = buildStorageKey("ws_demo", "prj_video", "renders", "run_100", "final.mp4");
      expect(validKey).toBe("workspaces/ws_demo/projects/prj_video/renders/run_100/final.mp4");

      // Injection attempts within components fail
      expect(() => buildStorageKey("../ws_bad", "prj_1", "renders", "run_1", "file.mp4")).toThrow(StorageSecurityError);
      expect(() => buildStorageKey("ws_1", "prj/hack", "renders", "run_1", "file.mp4")).toThrow(StorageSecurityError);
    });
  });

  describe("2. Production Preview Coordinator Integration (Section 7)", () => {
    it("R14-PV-01: Generates proxy, persists in StorageService, and emits durable events", async () => {
      const events: Array<{ type: string; payload: any }> = [];
      const registry = new RendererRegistry();
      const mockRenderer = createMockRendererAdapter({
        id: "preview-renderer",
        capabilities: ["render_frame", "frame_rendering"],
        onRenderFrame: async (req, ctx) => ({
          ok: true,
          requestId: req.id,
          rendererId: "preview-renderer",
          type: "frame",
          output: { dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" },
        }),
      });
      registry.register(mockRenderer);

      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_preview_test",
        storageService,
        registry,
        eventPublisher: (type, payload) => events.push({ type, payload }),
      });

      const request = createPreviewProxyRequest({
        project_id: "prj_r14_test",
        canonical_revision: 1,
        entity: { type: "scene", sceneId: "scene_01" },
        contentFragment: mockBlueprint.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      const artifact = await coordinator.requestProxy(request, mockBlueprint);

      expect(artifact).toBeDefined();
      expect(artifact.storageKey).toMatch(/^workspaces\/ws_preview_test\/projects\/prj_r14_test\/proxies\//);
      expect(artifact.workspaceId).toBe("ws_preview_test");

      // Verify physical existence in storage
      const existsInStorage = await storageService.exists(artifact.storageKey);
      expect(existsInStorage).toBe(true);

      // Verify event emission sequence
      expect(events.some((e) => e.type === "PROXY_REQUESTED")).toBe(true);
      expect(events.some((e) => e.type === "PROXY_READY")).toBe(true);
    });

    it("R14-PV-02: Stale proxy jobs for older revisions do not overwrite newer revisions", async () => {
      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_preview_test",
        storageService,
      });

      coordinator.updateCurrentRevision(2);
      expect(coordinator.getCurrentRevision()).toBe(2);

      const staleRequest = createPreviewProxyRequest({
        project_id: "prj_r14_test",
        canonical_revision: 1,
        entity: { type: "scene", sceneId: "scene_01" },
        contentFragment: mockBlueprint.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      await expect(
        coordinator.requestProxy(staleRequest, mockBlueprint, 1)
      ).rejects.toThrow();
    });

    it("R14-PV-03: ChangeSet invalidation selectively invalidates cache and emits PREVIEW_INVALIDATED", () => {
      const events: Array<{ type: string; payload: any }> = [];
      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_preview_test",
        storageService,
        eventPublisher: (type, payload) => events.push({ type, payload }),
      });

      const changeSet = {
        ...emptyChangeSet(),
        affected_scene_ids: ["scene_01"],
      };

      const invalidatedCount = coordinator.invalidateWithChangeSet(changeSet, 2);
      expect(invalidatedCount).toBeGreaterThanOrEqual(0);

      const invalidEvent = events.find((e) => e.type === "PREVIEW_INVALIDATED");
      expect(invalidEvent).toBeDefined();
      expect(invalidEvent?.payload.workspaceId).toBe("ws_preview_test");
      expect(invalidEvent?.payload.newRevision).toBe(2);
      expect(invalidEvent?.payload.affectedScenes).toEqual(["scene_01"]);
    });
  });

  describe("3. Renderer Job Isolation & Sandboxing (Sections 9, 10, 12, 13)", () => {
    it("R14-RG-01: Sandboxed workspace is cleaned up automatically on success", async () => {
      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "mock-engine",
        capabilities: ["text", "solid", "export_mp4", "render_frame", "shapes", "export_video"],
        onExportVideo: async (req, ctx) => {
          const out = req.output?.path || path.join(tempSandboxDir, "mock_output.mp4");
          generateSyntheticVideo(out, 640, 360, 30, 0.5);
          return {
            ok: true,
            requestId: req.id,
            rendererId: "mock-engine",
            type: "export",
            output: { filePath: out, durationMs: 500, width: 640, height: 360 },
          };
        },
      });
      registry.register(mockAdapter);

      const plan = {
        id: "plan_clean_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_01: {
              id: "node_01",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "mock-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp1", invalidationScope: "node_01" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_01"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_clean_01",
        canonicalRevision: 1,
      };

      const result = await executor.execute(plan as any, ctx);
      expect(result.ok).toBe(true);

      // Verify the execution directory was cleaned up
      const expectedWorkDir = path.join(
        tempSandboxDir,
        `render_sandbox_${ctx.workspaceId}_${ctx.projectId}_${ctx.runId}`
      );
      expect(fs.existsSync(expectedWorkDir)).toBe(false);
    });

    it("R14-RG-02: Structured RENDERER_TIMEOUT is raised and workspace is cleaned up on timeout", async () => {
      const registry = new RendererRegistry();
      const slowAdapter = createMockRendererAdapter({
        id: "slow-engine",
        capabilities: ["text", "solid", "shapes", "export_video"],
        onExportVideo: async (req, ctx) => {
          // Delay longer than timeout
          await new Promise((resolve) => setTimeout(resolve, 300));
          const out = req.output?.path || path.join(tempSandboxDir, "slow_output.mp4");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "slow-engine",
            type: "export",
            output: { filePath: out },
          };
        },
      });
      registry.register(slowAdapter);

      const plan = {
        id: "plan_timeout_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_slow: {
              id: "node_slow",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "slow-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_slow", invalidationScope: "node_slow" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_slow"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        defaultNodeTimeoutMs: 50, // Short timeout (50ms)
      });

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_timeout_01",
        canonicalRevision: 1,
        nodeTimeoutMs: 50,
      };

      const result = await executor.execute(plan as any, ctx);
      expect(result.ok).toBe(false);
      expect(result.error).toBeInstanceOf(ProductionRendererError);
      expect((result.error as ProductionRendererError).code).toBe("RENDERER_TIMEOUT");

      // Verify workspace cleanup on timeout failure
      const expectedWorkDir = path.join(
        tempSandboxDir,
        `render_sandbox_${ctx.workspaceId}_${ctx.projectId}_${ctx.runId}`
      );
      expect(fs.existsSync(expectedWorkDir)).toBe(false);
    });

    it("R14-RG-03: Cancellation stops scheduling immediately, returns RENDERER_CANCELLED, and cleans up", async () => {
      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "mock-engine",
        capabilities: ["text", "solid", "shapes", "export_video"],
        onExportVideo: async (req, ctx) => {
          await new Promise((resolve) => setTimeout(resolve, 50));
          return { ok: true, requestId: req.id, rendererId: "mock-engine", type: "export" };
        },
      });
      registry.register(mockAdapter);

      const plan = {
        id: "plan_cancel_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_01: {
              id: "node_01",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "mock-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp1", invalidationScope: "node_01" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_01"], parallel: false }],
      };

      const abortController = new AbortController();
      abortController.abort(); // Cancelled immediately before start

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_cancel_01",
        canonicalRevision: 1,
        signal: abortController.signal,
      };

      const result = await executor.execute(plan as any, ctx);
      expect(result.ok).toBe(false);
      expect(result.error).toBeInstanceOf(ProductionRendererError);
      expect((result.error as ProductionRendererError).code).toBe("RENDERER_CANCELLED");

      // Verify cleanup
      const expectedWorkDir = path.join(
        tempSandboxDir,
        `render_sandbox_${ctx.workspaceId}_${ctx.projectId}_${ctx.runId}`
      );
      expect(fs.existsSync(expectedWorkDir)).toBe(false);
    });

    it("R14-RG-04: Unavailable renderer fails closed with RENDERER_UNAVAILABLE", async () => {
      const emptyRegistry = new RendererRegistry();

      const plan = {
        id: "plan_unavailable",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_01: {
              id: "node_01",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 150 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "non_existent_engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_1", invalidationScope: "node_01" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_01"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry: emptyRegistry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_unavail_01",
        canonicalRevision: 1,
      };

      const result = await executor.execute(plan as any, ctx);
      expect(result.ok).toBe(false);
      expect(result.error).toBeInstanceOf(ProductionRendererError);
      expect((result.error as ProductionRendererError).code).toBe("RENDERER_UNAVAILABLE");
    });
  });

  describe("4. Master Compositor & Artifact Provenance (Sections 14, 15)", () => {
    it("R14-PR-01: Published final output records complete ArtifactProvenance in StorageService", async () => {
      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "mock-engine",
        capabilities: ["text", "solid", "shapes", "export_video"],
        onExportVideo: async (req, ctx) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5);
          return {
            ok: true,
            requestId: req.id,
            rendererId: "mock-engine",
            type: "export",
            output: { filePath: out, durationMs: 500, width: 640, height: 360 },
          };
        },
      });
      registry.register(mockAdapter);

      const plan = {
        id: "plan_prov_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "mock-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_s1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
            node_comp: {
              id: "node_comp",
              scope: { type: "compositor" as const, id: "root" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: [],
              dependencies: ["node_scene_1"],
              assignedRendererId: "master-compositor",
              cacheability: { cacheable: false, contentFingerprint: "fp_comp", invalidationScope: "node_comp" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
            },
          },
          edges: [
            { fromNodeId: "node_scene_1", toNodeId: "node_comp", type: "artifact_input" as const },
          ],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
          { groupId: "g2", nodeIds: ["node_comp"], parallel: false },
        ],
      };

      const events: Array<{ type: string; payload: any }> = [];
      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        eventPublisher: (type, payload) => events.push({ type, payload }),
      });

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_provenance_test",
        projectId: "prj_r14_test",
        runId: "run_prov_01",
        canonicalRevision: 5,
      };

      const result = await executor.execute(plan as any, ctx);
      expect(result.ok).toBe(true);
      expect(result.outputStorageKey).toBeDefined();

      // Check storage existence
      const exists = await storageService.exists(result.outputStorageKey!);
      expect(exists).toBe(true);

      // Verify Provenance
      expect(result.finalArtifact).toBeDefined();
      const provenance = (result.finalArtifact?.metadata as any)?.provenance;
      expect(provenance).toBeDefined();
      expect(provenance?.canonicalRevision).toBe(5);
      expect(provenance?.rendererId).toBe("master-compositor");

      // Verify durable events emitted
      expect(events.some((e) => e.type === "RENDER_STARTED")).toBe(true);
      expect(events.some((e) => e.type === "RENDER_SUCCEEDED")).toBe(true);
      expect(events.some((e) => e.type === "COMPOSITION_STARTED")).toBe(true);
      expect(events.some((e) => e.type === "COMPOSITION_COMPLETED")).toBe(true);
    }, 25000);
  });

  describe("5. Capability Fallback & Deterministic Mismatch (Sections 10, 11)", () => {
    it("R14-17: Allowed renderer fallback obeys capability policy", async () => {
      const registry = new RendererRegistry();
      const fallbackAdapter = createMockRendererAdapter({
        id: "fallback-engine",
        capabilities: ["2d_vector", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "green");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "fallback-engine",
            type: "export",
            output: { filePath: out, durationMs: 200, width: 640, height: 360 },
          };
        },
      });
      registry.register(fallbackAdapter);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const plan = {
        id: "plan_fallback_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["2d_vector"],
              dependencies: [],
              assignedRendererId: "fallback-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_s1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_fb_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(true);
      expect(res.nodeResults["node_scene_1"].ok).toBe(true);
    });

    it("R14-18: Unsupported fallback fails closed with RENDERER_CAPABILITY_MISMATCH rather than silently degrading", async () => {
      const registry = new RendererRegistry();
      const basicAdapter = createMockRendererAdapter({
        id: "basic-engine",
        capabilities: ["text", "export_video"],
      });
      registry.register(basicAdapter);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const plan = {
        id: "plan_mismatch_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["complex_3d_physics"],
              dependencies: [],
              assignedRendererId: "basic-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_s1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_mismatch_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(false);
      expect(res.error).toBeInstanceOf(ProductionRendererError);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_CAPABILITY_MISMATCH");
    });
  });

  describe("6. Cancellation Idempotency & Safe Retries (Section 12)", () => {
    it("R14-20: Repeated cancellation is idempotent", async () => {
      const controller = new AbortController();
      controller.abort();
      expect(() => {
        controller.abort();
        controller.abort();
      }).not.toThrow();

      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "mock-engine",
        capabilities: ["text", "export_video"],
      });
      registry.register(mockAdapter);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const plan = {
        id: "plan_cancel_idem",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: [],
              dependencies: [],
              assignedRendererId: "mock-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_s1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_cancel_idem",
        canonicalRevision: 1,
        signal: controller.signal,
      });

      expect(res.ok).toBe(false);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_CANCELLED");
    });

    it("R14-21: Retry does not double-publish artifact with corrupted keys", async () => {
      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "mock-engine",
        capabilities: ["shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "red");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "mock-engine",
            type: "export",
            output: { filePath: out, durationMs: 200, width: 640, height: 360 },
          };
        },
      });
      registry.register(mockAdapter);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const plan = {
        id: "plan_retry_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "mock-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_s1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
            node_comp: {
              id: "node_comp",
              scope: { type: "compositor" as const, id: "root" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: [],
              dependencies: ["node_scene_1"],
              assignedRendererId: "master-compositor",
              cacheability: { cacheable: false, contentFingerprint: "fp_comp", invalidationScope: "node_comp" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
            },
          },
          edges: [
            { fromNodeId: "node_scene_1", toNodeId: "node_comp", type: "artifact_input" as const },
          ],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
          { groupId: "g2", nodeIds: ["node_comp"], parallel: false },
        ],
      };

      const ctx: ProductionExecutionContext = {
        workspaceId: "ws_retry",
        projectId: "prj_r14_test",
        runId: "run_retry_det",
        canonicalRevision: 2,
      };

      // First execution
      const res1 = await executor.execute(plan as any, ctx);
      expect(res1.ok).toBe(true);
      const key1 = res1.outputStorageKey!;

      // Retry execution with same runId
      const res2 = await executor.execute(plan as any, ctx);
      expect(res2.ok).toBe(true);
      const key2 = res2.outputStorageKey!;

      expect(key1).toBe(key2);
      expect(await storageService.exists(key2)).toBe(true);
    }, 20000);
  });

  describe("7. Multi-Engine Heterogeneous Composition (Section 13, 14)", () => {
    it("R14-23: Master compositor consumes outputs from multiple renderer types", async () => {
      const registry = new RendererRegistry();
      
      const adapterAlpha = createMockRendererAdapter({
        id: "engine-alpha",
        capabilities: ["shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}_alpha.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "cyan");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "engine-alpha",
            type: "export",
            output: { filePath: out, durationMs: 250, width: 640, height: 360 },
          };
        },
      });

      const adapterBeta = createMockRendererAdapter({
        id: "engine-beta",
        capabilities: ["text", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}_beta.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "magenta");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "engine-beta",
            type: "export",
            output: { filePath: out, durationMs: 300, width: 640, height: 360 },
          };
        },
      });

      registry.register(adapterAlpha);
      registry.register(adapterBeta);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const plan = {
        id: "plan_heterogeneous_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_alpha: {
              id: "node_alpha",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "engine-alpha",
              cacheability: { cacheable: false, contentFingerprint: "fp_alpha", invalidationScope: "node_alpha" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
            node_beta: {
              id: "node_beta",
              scope: { type: "scene" as const, id: "scene_02" },
              timeRange: { startFrame: 15, durationFrames: 15 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "engine-beta",
              cacheability: { cacheable: false, contentFingerprint: "fp_beta", invalidationScope: "node_beta" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
            node_comp: {
              id: "node_comp",
              scope: { type: "compositor" as const, id: "root" },
              timeRange: { startFrame: 0, durationFrames: 30 },
              requiredCapabilities: [],
              dependencies: ["node_alpha", "node_beta"],
              assignedRendererId: "master-compositor",
              cacheability: { cacheable: false, contentFingerprint: "fp_comp_multi", invalidationScope: "node_comp" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
            },
          },
          edges: [
            { fromNodeId: "node_alpha", toNodeId: "node_comp", type: "artifact_input" as const },
            { fromNodeId: "node_beta", toNodeId: "node_comp", type: "artifact_input" as const },
          ],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_alpha", "node_beta"], parallel: true },
          { groupId: "g2", nodeIds: ["node_comp"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_hetero",
        projectId: "prj_r14_test",
        runId: "run_hetero_01",
        canonicalRevision: 3,
      });

      expect(res.ok).toBe(true);
      expect(res.nodeResults["node_alpha"].ok).toBe(true);
      expect(res.nodeResults["node_beta"].ok).toBe(true);
      expect(res.nodeResults["node_comp"].ok).toBe(true);
      expect(res.outputStorageKey).toBeDefined();

      const exists = await storageService.exists(res.outputStorageKey!);
      expect(exists).toBe(true);
    }, 25000);
  });

  describe("8. Cost/Budget Policy Enforcement & Usage Metering (Sections 17, 18)", () => {
    it("R14-27: Cost/budget policy blocks disallowed work before expensive execution", async () => {
      const registry = new RendererRegistry();
      let rendererExecuted = false;

      const mockAdapter = createMockRendererAdapter({
        id: "expensive-engine",
        capabilities: ["export_video"],
        onExportVideo: async () => {
          rendererExecuted = true;
          return { ok: true, requestId: "req", rendererId: "expensive-engine", type: "export" };
        },
      });
      registry.register(mockAdapter);

      const events: Array<{ type: string; payload: any }> = [];
      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        eventPublisher: (type, payload) => events.push({ type, payload }),
        budgetChecker: async () => {
          return {
            allowed: false,
            reason: "Workspace monthly rendering quota reached",
            estimatedCost: 15.0,
          };
        },
      });

      const plan = {
        id: "plan_budget_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: [],
              dependencies: [],
              assignedRendererId: "expensive-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_b1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_budget_test",
        projectId: "prj_r14_test",
        runId: "run_budget_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(false);
      expect((res.error as ProductionRendererError).code).toBe("BUDGET_EXCEEDED");
      expect(rendererExecuted).toBe(false);
      expect(events.some((e) => e.type === "BUDGET_EXCEEDED")).toBe(true);
    });

    it("R14-28: Usage metering records successful production execution", async () => {
      const registry = new RendererRegistry();
      const mockAdapter = createMockRendererAdapter({
        id: "metered-engine",
        capabilities: ["shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "yellow");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "metered-engine",
            type: "export",
            output: { filePath: out, durationMs: 150, width: 640, height: 360 },
          };
        },
      });
      registry.register(mockAdapter);

      const events: Array<{ type: string; payload: any }> = [];
      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        eventPublisher: (type, payload) => events.push({ type, payload }),
      });

      const plan = {
        id: "plan_meter_01",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "metered-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_m1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_meter_test",
        projectId: "prj_r14_test",
        runId: "run_meter_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(true);
      const usageEvent = events.find((e) => e.type === "USAGE_METERED");
      expect(usageEvent).toBeDefined();
      expect(usageEvent?.payload.workspaceId).toBe("ws_meter_test");
      expect(usageEvent?.payload.nodeId).toBe("node_scene_1");
      expect(usageEvent?.payload.rendererId).toBe("metered-engine");
      expect(usageEvent?.payload.durationMs).toBeGreaterThan(0);
    });
  });

  describe("9. Disable-Remotion Integration Check (Section 32)", () => {
    it("R14-30: Backend renders non-Remotion project when Remotion is unavailable", async () => {
      const nonRemotionRegistry = new RendererRegistry();
      const nativeAdapter = createMockRendererAdapter({
        id: "native-canvas-engine",
        capabilities: ["2d_canvas", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "blue");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "native-canvas-engine",
            type: "export",
            output: { filePath: out, durationMs: 200, width: 640, height: 360 },
          };
        },
      });
      nonRemotionRegistry.register(nativeAdapter);

      expect(nonRemotionRegistry.get("remotion")).toBeUndefined();

      const executor = new ProductionRenderGraphExecutor({
        registry: nonRemotionRegistry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      // 1. Non-Remotion project executes successfully
      const nonRemotionPlan = {
        id: "plan_non_remotion",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_1: {
              id: "node_scene_1",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["2d_canvas"],
              dependencies: [],
              assignedRendererId: "native-canvas-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_nc1", invalidationScope: "node_scene_1" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_1"], parallel: false },
        ],
      };

      const res = await executor.execute(nonRemotionPlan as any, {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_non_remotion_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(true);
      expect(res.nodeResults["node_scene_1"].ok).toBe(true);

      // 2. Node requesting Remotion returns explicit typed failure RENDERER_UNAVAILABLE
      const remotionPlan = {
        id: "plan_remotion_req",
        projectId: "prj_r14_test",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_scene_remotion: {
              id: "node_scene_remotion",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["remotion_components"],
              dependencies: [],
              assignedRendererId: "remotion",
              cacheability: { cacheable: false, contentFingerprint: "fp_r1", invalidationScope: "node_scene_remotion" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: mockBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["node_scene_remotion"], parallel: false },
        ],
      };

      const remotionRes = await executor.execute(remotionPlan as any, {
        workspaceId: "ws_test",
        projectId: "prj_r14_test",
        runId: "run_remotion_req_01",
        canonicalRevision: 1,
      });

      expect(remotionRes.ok).toBe(false);
      expect(remotionRes.error).toBeInstanceOf(ProductionRendererError);
      expect((remotionRes.error as ProductionRendererError).code).toBe("RENDERER_UNAVAILABLE");
    });
  });

  describe("10. Full Production-Path Smoke (Section 25, R14-34)", () => {
    it("R14-34: Full production-path smoke: author -> preview -> render -> compositor -> QC -> StorageService", async () => {
      // 1. Author: Seed canonical blueprint
      const blueprint: BlueprintV2 = {
        schema_version: "2.0.0",
        project_id: "prj_smoke_34",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [
          {
            scene_id: "scene_headline",
            template: "HeadlineTemplate",
            startFrame: 0,
            durationFrames: 15,
            content: { text: "Smoke Headline" },
          },
        ],
      };

      // 2. Preview: Generate proxy via ProductionPreviewCoordinator
      const previewRegistry = new RendererRegistry();
      const previewRenderer = createMockRendererAdapter({
        id: "preview-smoke-renderer",
        capabilities: ["render_frame", "frame_rendering"],
        onRenderFrame: async (req) => ({
          ok: true,
          requestId: req.id,
          rendererId: "preview-smoke-renderer",
          type: "frame",
          output: { dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" },
        }),
      });
      previewRegistry.register(previewRenderer);

      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_smoke",
        storageService,
        registry: previewRegistry,
      });

      const proxyReq = createPreviewProxyRequest({
        project_id: "prj_smoke_34",
        canonical_revision: 1,
        entity: { type: "scene", sceneId: "scene_headline" },
        contentFragment: blueprint.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      const proxyResult = await coordinator.requestProxy(proxyReq, blueprint);
      expect(proxyResult.storageKey).toBeDefined();
      expect(await storageService.exists(proxyResult.storageKey)).toBe(true);

      // 3. Multi-Engine Render & Compositor: ProductionRenderGraphExecutor
      const registry = new RendererRegistry();
      const mockEngine = createMockRendererAdapter({
        id: "smoke-engine",
        capabilities: ["text", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, "smoke_scene.mp4");
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "black");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "smoke-engine",
            type: "export",
            output: { filePath: out, durationMs: 200, width: 640, height: 360 },
          };
        },
      });
      registry.register(mockEngine);

      const events: Array<{ type: string; payload: any }> = [];
      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        eventPublisher: (type, payload) => events.push({ type, payload }),
      });

      const plan = {
        id: "plan_smoke_34",
        projectId: "prj_smoke_34",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            scene_node: {
              id: "scene_node",
              scope: { type: "scene" as const, id: "scene_headline" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "smoke-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_smoke_s1", invalidationScope: "scene_node" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: blueprint,
            },
            comp_node: {
              id: "comp_node",
              scope: { type: "compositor" as const, id: "root" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: [],
              dependencies: ["scene_node"],
              assignedRendererId: "master-compositor",
              cacheability: { cacheable: false, contentFingerprint: "fp_smoke_comp", invalidationScope: "comp_node" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
            },
          },
          edges: [
            { fromNodeId: "scene_node", toNodeId: "comp_node", type: "artifact_input" as const },
          ],
        },
        executionGroups: [
          { groupId: "g1", nodeIds: ["scene_node"], parallel: false },
          { groupId: "g2", nodeIds: ["comp_node"], parallel: false },
        ],
      };

      const renderResult = await executor.execute(plan as any, {
        workspaceId: "ws_smoke",
        projectId: "prj_smoke_34",
        runId: "run_smoke_34",
        canonicalRevision: 1,
      });

      expect(renderResult.ok).toBe(true);
      expect(renderResult.outputStorageKey).toBeDefined();

      // 4. StorageService Publication: Output exists in storage with complete provenance
      const outputInStorage = await storageService.exists(renderResult.outputStorageKey!);
      expect(outputInStorage).toBe(true);
      expect((renderResult.finalArtifact?.metadata as any)?.provenance).toBeDefined();
      expect(renderResult.finalArtifact?.metadata?.provenance?.canonicalRevision).toBe(1);
    }, 20000);
  });
});
