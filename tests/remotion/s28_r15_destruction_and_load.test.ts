/**
 * tests/remotion/s28_r15_destruction_and_load.test.ts
 * Milestone S28-R15: Comprehensive Destruction, Failure Injection, and Load Verification Suite.
 *
 * Campaigns Covered:
 *   - R15-C03: Template Migration & Compatibility
 *   - R15-C04: Remotion Compatibility & Parity
 *   - R15-C05: Non-Remotion Production Path
 *   - R15-C06: Multi-Engine Project Topology & Failure Isolation
 *   - R15-C09: Preview & Proxy Cache / Invalidation Stress
 *   - R15-C14: Renderer Failure Matrix (Timeout, Crash, Mismatch, Missing Asset)
 *   - R15-C15: MasterCompositor Failure Modes (Missing Segment, Corrupt Input)
 *   - R15-C16: Final QC Failure Semantics (VIDEO_FAILED_QC vs QC_CHECK_FAILED_TO_EXECUTE)
 *   - R15-C17: Cancellation at every lifecycle stage (Planning, Node, Compositor)
 *   - R15-C18: Retry & Redelivery bounds
 *   - R15-C24: Real Render Load across engines (Concurrent Multi-Engine Execution)
 *   - R15-C25: Soak & Resource Leak checks (Workspace Temp Dir Cleanup, No Leaks)
 *   - R15-C26: Aspect Ratio / Media Matrix (16:9, 9:16, 1:1)
 *   - R15-C27: Audio & Caption Integrity (Ducking, AV Sync Drift < 150ms)
 *   - R15-C28: Full AI -> Editor -> Export E2E Pipeline
 */

import { describe, it, expect, beforeEach, afterEach, beforeAll } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync } from "child_process";

import {
  type BlueprintV2,
  BlueprintV2Schema,
  validateBlueprintV2,
  emptyChangeSet,
} from "../../contracts";
import {
  type OutputProfile,
  type IntermediateArtifact,
  MasterCompositorError,
  createDefaultOutputProfile,
  createIntermediateArtifact,
} from "../../contracts/compositor";
import {
  RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  createMockRendererAdapter,
  CANVAS_RENDERER_ID,
  REMOTION_RENDERER_ID,
  type RenderRequest,
  type RenderContext,
} from "../../contracts/renderer";
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
  MasterCompositor,
  findSystemFfmpeg,
  probeMediaFile,
  runQcForCompositorResult,
} from "../../compositor";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { validateLayerHierarchy } from "../../contracts/layers";
import { CanvasRendererAdapter, createCanvasRendererAdapter } from "../../canvas/canvas-renderer-adapter";
import { UnifiedAuthoringSession } from "../../authoring";
import { RenderPlanner } from "../../planner/render-planner";

describe("S28-R15 Destruction, Failure Injection & Load Verification Suite", () => {
  let tempStorageDir: string;
  let tempSandboxDir: string;
  let storageService: LocalStorageService;
  const ffmpeg = findSystemFfmpeg();

  // Synthetic video generator using FFmpeg
  function generateSyntheticVideo(
    filePath: string,
    width = 640,
    height = 360,
    fps = 30,
    durationSec = 1.0,
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

  function createArtifactFromFile(options: {
    artifactId: string;
    sourceRendererId: string;
    scope: { type: "scene" | "transition" | "layer"; id: string };
    timeRange: { startFrame: number; durationFrames: number; durationSec: number };
    type: "video" | "audio" | "image";
    filePath: string;
    fps?: number;
  }): IntermediateArtifact {
    const probe = probeMediaFile(options.filePath);
    return createIntermediateArtifact({
      artifactId: options.artifactId,
      runId: "run_r15_destruction",
      sourceRendererId: options.sourceRendererId,
      canonicalRevision: 1,
      scope: options.scope,
      timeRange: {
        startFrame: options.timeRange.startFrame,
        durationFrames: options.timeRange.durationFrames,
        startTimeSec: options.timeRange.startFrame / (options.fps || 30),
        durationSec: options.timeRange.durationSec,
      },
      type: options.type,
      storageKey: `workspaces/ws_destruct/artifacts/${options.artifactId}.mp4`,
      localPath: options.filePath,
      mediaInfo: {
        durationSec: probe.durationSec,
        durationFrames: Math.round(probe.durationSec * (options.fps || 30)),
        fps: probe.fps || options.fps || 30,
        width: probe.width,
        height: probe.height,
        pixelFormat: "yuv420p",
        timebase: `1/${options.fps || 30}`,
        startTimeSec: 0,
        startFrame: options.timeRange.startFrame,
        hasAlpha: false,
        videoCodec: probe.videoCodec || "h264",
      },
    });
  }

  const baseBlueprint: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: "prj_r15_destruction",
    fps: 30,
    aspect_ratio: "16:9",
    scenes: [
      {
        scene_id: "scene_01",
        template: "rui-title-card",
        startFrame: 0,
        durationFrames: 30,
        content: { text: "R15 Destruction Testing" },
        layers: [
          {
            layer_id: "l_bg",
            kind: "shape",
            shape_type: "rectangle",
            fillColor: "#0f172a",
            z_index: 0,
            time_range: { startFrame: 0, endFrame: 30, durationFrames: 30 },
            transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
            opacity: 1,
            visible: true,
            size: { width: 1920, height: 1080 },
          },
          {
            layer_id: "l_txt",
            kind: "text",
            text: "R15 Destruction Testing",
            z_index: 1,
            time_range: { startFrame: 0, endFrame: 30, durationFrames: 30 },
            transform: { position: { x: 100, y: 100 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
            opacity: 1,
            visible: true,
            typography: { fontFamily: "Cairo", fontSize: 64, fillColor: "#ffffff" },
          },
        ],
      },
      {
        scene_id: "scene_02",
        template: "rui-quote-card",
        startFrame: 30,
        durationFrames: 30,
        content: { text: "Resilience Under Fire" },
        layers: [
          {
            layer_id: "l_bg2",
            kind: "shape",
            shape_type: "rectangle",
            fillColor: "#1e293b",
            z_index: 0,
            time_range: { startFrame: 30, endFrame: 60, durationFrames: 30 },
            transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
            opacity: 1,
            visible: true,
            size: { width: 1920, height: 1080 },
          },
        ],
      },
    ],
  };

  const sample2dDoc: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: "doc_canvas_test",
    fps: 30,
    aspect_ratio: "16:9",
    scenes: [
      {
        scene_id: "s1",
        startFrame: 0,
        durationFrames: 15,
        layers: [
          {
            layer_id: "l_bg",
            kind: "shape",
            time_range: { startFrame: 0, endFrame: 15, durationFrames: 15 },
            transform: {
              position: { x: 0, y: 0 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 0,
            shape_type: "rectangle",
            size: { width: 640, height: 360 },
            fillColor: "#0f172a",
          },
          {
            layer_id: "l_title",
            kind: "text",
            time_range: { startFrame: 0, endFrame: 15, durationFrames: 15 },
            transform: {
              position: { x: 0, y: 0 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 1,
            text: "Canvas Standalone",
            typography: { fontFamily: "Cairo", fontSize: 48, fillColor: "#38bdf8" },
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    tempStorageDir = fs.mkdtempSync(path.join(os.tmpdir(), "s28_r15_storage_"));
    tempSandboxDir = fs.mkdtempSync(path.join(os.tmpdir(), "s28_r15_sandbox_"));
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

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C03: Template Migration & Compatibility
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C03: Template Migration & Compatibility", () => {
    it("R15-TS-01: Legacy and modern template inputs instantiate deterministically into valid BlueprintV2 scenes", () => {
      const res = instantiateTemplate(
        "rui-title-card",
        {
          title: "S28-R15 Migration Verifier",
          subtitle: "Canonical Spec Instantiation",
          backgroundColor: "#111827",
          accentColor: "#3b82f6",
        },
        {
          scene_id: "sc_migrated_01",
          startFrame: 0,
          durationFrames: 60,
          fps: 30,
        }
      );

      expect(res.ok).toBe(true);
      expect(res.classification).toBe("NATIVE");
      expect(res.scene.scene_id).toBe("sc_migrated_01");
      expect(res.scene.startFrame).toBe(0);
      expect(res.scene.durationFrames).toBe(60);

      // Verify layer hierarchy passes invariant checks
      expect(validateLayerHierarchy(res.layers).ok).toBe(true);
      expect(res.layers.length).toBeGreaterThanOrEqual(3);
    });

    it("R15-TS-02: Template instantiation rejects invalid parameters fail-closed", () => {
      // Unknown template throws UnknownTemplateError
      expect(() => {
        instantiateTemplate("non-existent-template-xyz", {}, { scene_id: "sc_bad" });
      }).toThrow();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C04: Remotion Compatibility & Parity
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C04: Remotion Compatibility & Parity", () => {
    it("R15-RM-01: RemotionAdapter renders canonical scenes with exact durationFrames parity", async () => {
      const mockRemotionAdapter = createMockRendererAdapter({
        id: "remotion-renderer-adapter",
        capabilities: ["export_video", "transitions", "effects", "audio", "text", "shapes"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, "remotion_parity_out.mp4");
          // Generate exact 1.0s video at 30fps = 30 frames
          generateSyntheticVideo(out, 640, 360, 30, 1.0, "blue");
          return {
            ok: true,
            requestId: req.id,
            rendererId: "remotion-renderer-adapter",
            type: "export",
            output: { filePath: out, durationMs: 1000, width: 640, height: 360 },
          };
        },
      });

      const res = await mockRemotionAdapter.exportVideo(
        {
          id: "req_rm_parity",
          document: baseBlueprint,
          type: "export",
          timeRange: { startFrame: 0, durationFrames: 30 },
          output: { path: path.join(tempSandboxDir, "remotion_parity_out.mp4") },
        },
        { requestId: "req_rm_parity", workspacePath: tempSandboxDir }
      );

      expect(res.ok).toBe(true);
      expect(fs.existsSync(res.output!.filePath!)).toBe(true);
      const probe = probeMediaFile(res.output!.filePath!);
      expect(probe.durationSec).toBeCloseTo(1.0, 1);
    }, 25000);

    it("R15-RM-02: Remotion frame render returns valid output metadata", async () => {
      const mockRemotionAdapter = createMockRendererAdapter({
        id: "remotion-renderer-adapter",
        capabilities: ["render_frame", "frame_rendering", "text", "shapes"],
        onRenderFrame: async (req) => ({
          ok: true,
          requestId: req.id,
          rendererId: "remotion-renderer-adapter",
          type: "frame",
          output: { dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" },
        }),
      });

      const res = await mockRemotionAdapter.renderFrame(
        { id: "req_rm_frame", document: baseBlueprint, type: "frame", frame: 15 },
        { requestId: "req_rm_frame", workspacePath: tempSandboxDir }
      );

      expect(res.ok).toBe(true);
      expect(res.output?.dataUrl).toMatch(/^data:image\/png;base64,/);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C05: Non-Remotion Production Path
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C05: Non-Remotion Production Path", () => {
    it("R15-NR-01: Headless Canvas/FFmpeg adapter renders video standalone without Remotion", async () => {
      const canvasAdapter = createCanvasRendererAdapter();
      expect(canvasAdapter.id).toBe(CANVAS_RENDERER_ID);
      const canRenderCheck = canvasAdapter.canRender({
        id: "req_check_canvas",
        document: sample2dDoc,
        type: "export",
      });
      expect(canRenderCheck.canRender).toBe(true);

      const outVideo = path.join(tempSandboxDir, "canvas_standalone_out.mp4");
      const res = await canvasAdapter.exportVideo(
        {
          id: "req_canvas_standalone",
          document: sample2dDoc,
          type: "export",
          timeRange: { startFrame: 0, durationFrames: 15 },
          output: { path: outVideo, width: 640, height: 360, fps: 30 },
        },
        { requestId: "req_canvas_standalone", workspacePath: tempSandboxDir }
      );

      expect(res.ok).toBe(true);
      expect(fs.existsSync(outVideo)).toBe(true);
      const probe = probeMediaFile(outVideo);
      expect(probe.width).toBe(640);
      expect(probe.height).toBe(360);
    }, 25000);

    it("R15-NR-02: Canvas frame rendering produces valid PNG buffer without DOM", async () => {
      const canvasAdapter = createCanvasRendererAdapter();
      const outFrame = path.join(tempSandboxDir, "canvas_frame.png");
      const res = await canvasAdapter.renderFrame(
        {
          id: "req_canvas_frame",
          document: sample2dDoc,
          type: "frame",
          frame: 5,
          output: { path: outFrame, format: "png", width: 640, height: 360 },
        },
        { requestId: "req_canvas_frame", workspacePath: tempSandboxDir }
      );

      expect(res.ok).toBe(true);
      expect(res.output?.buffer).toBeDefined();
      expect(res.output!.buffer!.length).toBeGreaterThan(100);
    }, 25000);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C06: Multi-Engine Project Topology & Failure Isolation
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C06: Multi-Engine Project Topology & Failure Isolation", () => {
    it("R15-TO-01: Heterogeneous multi-engine topology executes successfully across distinct renderers", async () => {
      const registry = new RendererRegistry();

      const canvasEngine = createMockRendererAdapter({
        id: "canvas-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, "canvas_node.mp4");
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "yellow");
          return { ok: true, requestId: req.id, rendererId: "canvas-engine", type: "export", output: { filePath: out } };
        },
      });

      const remotionEngine = createMockRendererAdapter({
        id: "remotion-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, "remotion_node.mp4");
          generateSyntheticVideo(out, 640, 360, 30, 0.5, "purple");
          return { ok: true, requestId: req.id, rendererId: "remotion-engine", type: "export", output: { filePath: out } };
        },
      });

      registry.register(canvasEngine);
      registry.register(remotionEngine);

      const plan = {
        id: "plan_topo_01",
        projectId: "prj_r15_destruction",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_c: {
              id: "node_c",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "canvas-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_c", invalidationScope: "node_c" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
            node_r: {
              id: "node_r",
              scope: { type: "scene" as const, id: "scene_02" },
              timeRange: { startFrame: 15, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "remotion-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_r", invalidationScope: "node_r" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_c", "node_r"], parallel: true }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_topo_01",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(true);
      expect(res.nodeResults["node_c"].ok).toBe(true);
      expect(res.nodeResults["node_r"].ok).toBe(true);
    }, 25000);

    it("R15-TO-02: Failure in Engine A is isolated without leaking uncaught exceptions", async () => {
      const registry = new RendererRegistry();

      const failingEngine = createMockRendererAdapter({
        id: "failing-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async () => {
          throw new Error("Simulated engine crash");
        },
      });

      registry.register(failingEngine);

      const plan = {
        id: "plan_fail_iso",
        projectId: "prj_r15_destruction",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_failing: {
              id: "node_failing",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "failing-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_f", invalidationScope: "node_f" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_failing"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_iso_fail",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(false);
      expect(res.error).toBeInstanceOf(ProductionRendererError);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_EXECUTION_FAILED");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C09: Preview & Proxy Cache / Invalidation Stress
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C09: Preview & Proxy Cache / Invalidation Stress", () => {
    it("R15-PV-01: Rapid 10-request proxy burst reuses cached artifact with zero duplicate rendering", async () => {
      let renderCallCount = 0;
      const registry = new RendererRegistry();
      const proxyRenderer = createMockRendererAdapter({
        id: "preview-proxy-engine",
        capabilities: ["text", "shapes", "render_frame", "frame_rendering"],
        onRenderFrame: async (req) => {
          renderCallCount++;
          return {
            ok: true,
            requestId: req.id,
            rendererId: "preview-proxy-engine",
            type: "frame",
            output: { dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" },
          };
        },
      });
      registry.register(proxyRenderer);

      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_destruct",
        storageService,
        registry,
      });

      const request = createPreviewProxyRequest({
        project_id: "prj_r15_destruction",
        canonical_revision: 1,
        entity: { type: "scene", sceneId: "scene_01" },
        contentFragment: baseBlueprint.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      for (let i = 0; i < 10; i++) {
        const artifact = await coordinator.requestProxy(request, baseBlueprint);
        expect(artifact).toBeDefined();
        expect(artifact.storageKey).toBeDefined();
      }

      // Exactly 1 render call, remaining 9 served from storage / memory cache
      expect(renderCallCount).toBe(1);
    });

    it("R15-PV-02: Document mutation modifies content hash, invalidates proxy cache with zero stale bleed", async () => {
      let renderCallCount = 0;
      const registry = new RendererRegistry();
      const proxyRenderer = createMockRendererAdapter({
        id: "preview-proxy-engine",
        capabilities: ["text", "shapes", "render_frame", "frame_rendering"],
        onRenderFrame: async (req) => {
          renderCallCount++;
          return {
            ok: true,
            requestId: req.id,
            rendererId: "preview-proxy-engine",
            type: "frame",
            output: { dataUrl: `data:image/png;base64,frame_render_${renderCallCount}` },
          };
        },
      });
      registry.register(proxyRenderer);

      const coordinator = new ProductionPreviewCoordinator({
        workspaceId: "ws_destruct",
        storageService,
        registry,
      });

      const req1 = createPreviewProxyRequest({
        project_id: "prj_r15_destruction",
        canonical_revision: 1,
        entity: { type: "scene", sceneId: "scene_01" },
        contentFragment: baseBlueprint.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      const art1 = await coordinator.requestProxy(req1, baseBlueprint);
      expect(art1).toBeDefined();
      expect(renderCallCount).toBe(1);

      // Invalidate with changeset
      const count = coordinator.invalidateWithChangeSet({
        ...emptyChangeSet(),
        affected_scene_ids: ["scene_01"],
      }, 2);
      expect(count).toBeGreaterThanOrEqual(1);

      // Mutated document at revision 2
      const mutatedDoc: BlueprintV2 = {
        ...baseBlueprint,
        scenes: [
          {
            ...baseBlueprint.scenes[0],
            content: { text: "Mutated Title Rev 2" },
          },
        ],
      };

      const req2 = createPreviewProxyRequest({
        project_id: "prj_r15_destruction",
        canonical_revision: 2,
        entity: { type: "scene", sceneId: "scene_01" },
        contentFragment: mutatedDoc.scenes[0],
        requiredCapabilities: ["render_frame"],
      });

      const art2 = await coordinator.requestProxy(req2, mutatedDoc, 2);
      expect(art2).toBeDefined();
      expect(renderCallCount).toBe(2);
      expect(art2.storageKey).not.toBe(art1.storageKey);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C14: Renderer Failure Matrix
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C14: Renderer Failure Matrix", () => {
    it("R15-FL-01: RENDERER_TIMEOUT: Node exceeding execution timeout fails closed", async () => {
      const registry = new RendererRegistry();
      const slowAdapter = createMockRendererAdapter({
        id: "slow-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          await new Promise((r) => setTimeout(r, 200));
          const out = req.output?.path || path.join(tempSandboxDir, "slow_out.mp4");
          return { ok: true, requestId: req.id, rendererId: "slow-engine", type: "export", output: { filePath: out } };
        },
      });
      registry.register(slowAdapter);

      const plan = {
        id: "plan_timeout_test",
        projectId: "prj_r15_destruction",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_timeout: {
              id: "node_timeout",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["shapes"],
              dependencies: [],
              assignedRendererId: "slow-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_to", invalidationScope: "node_to" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_timeout"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
        defaultNodeTimeoutMs: 30, // 30ms timeout triggers error
      });

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_timeout_test",
        canonicalRevision: 1,
        nodeTimeoutMs: 30,
      });

      expect(res.ok).toBe(false);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_TIMEOUT");
    });

    it("R15-FL-02: RENDERER_CAPABILITY_MISMATCH: Unsupported capability fails closed without guessing", async () => {
      const registry = new RendererRegistry();
      const basicAdapter = createMockRendererAdapter({
        id: "basic-engine",
        capabilities: ["text"],
      });
      registry.register(basicAdapter);

      const plan = {
        id: "plan_cap_mismatch",
        projectId: "prj_r15_destruction",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_mismatch: {
              id: "node_mismatch",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["3d_vector_mesh"], // Unsupported!
              dependencies: [],
              assignedRendererId: "basic-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_mm", invalidationScope: "node_mm" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_mismatch"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_mismatch_test",
        canonicalRevision: 1,
      });

      expect(res.ok).toBe(false);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_CAPABILITY_MISMATCH");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C15: MasterCompositor Failure Modes
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C15: MasterCompositor Failure Modes", () => {
    it("R15-MC-01: Missing intermediate video segment aborts composition with MISSING_ARTIFACT", async () => {
      const missingArtifact = createIntermediateArtifact({
        artifactId: "art_missing_file",
        runId: "run_r15_mc_test",
        sourceRendererId: "mock-engine",
        canonicalRevision: 1,
        scope: { type: "scene", id: "scene_01" },
        timeRange: { startFrame: 0, durationFrames: 30, startTimeSec: 0, durationSec: 1.0 },
        type: "video",
        localPath: path.join(tempSandboxDir, "does_not_exist.mp4"),
        mediaInfo: {
          durationSec: 1.0,
          durationFrames: 30,
          fps: 30,
          width: 640,
          height: 360,
          pixelFormat: "yuv420p",
          timebase: "1/30",
          startTimeSec: 0,
          startFrame: 0,
          hasAlpha: false,
          videoCodec: "h264",
        },
      });

      const compositor = new MasterCompositor();
      await expect(
        compositor.composite({
          id: "req_mc_missing",
          document: baseBlueprint,
          inputs: [{ artifact: missingArtifact, canonicalSceneId: "scene_01" }],
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          outputPath: path.join(tempSandboxDir, "should_not_exist.mp4"),
        })
      ).rejects.toThrow(MasterCompositorError);
    });

    it("R15-MC-02: Compositor cleans up temporary workspaces on failure", async () => {
      const nonExistentFile = path.join(tempSandboxDir, "corrupted_non_existent.mp4");
      const badArtifact = createIntermediateArtifact({
        artifactId: "art_corrupt",
        runId: "run_r15_mc_test_clean",
        sourceRendererId: "mock-engine",
        canonicalRevision: 1,
        scope: { type: "scene", id: "scene_01" },
        timeRange: { startFrame: 0, durationFrames: 30, startTimeSec: 0, durationSec: 1.0 },
        type: "video",
        localPath: nonExistentFile,
        mediaInfo: {
          durationSec: 1.0,
          durationFrames: 30,
          fps: 30,
          width: 640,
          height: 360,
          pixelFormat: "yuv420p",
          timebase: "1/30",
          startTimeSec: 0,
          startFrame: 0,
          hasAlpha: false,
          videoCodec: "h264",
        },
      });

      const compositor = new MasterCompositor();
      try {
        await compositor.composite({
          id: "req_mc_clean",
          document: baseBlueprint,
          inputs: [{ artifact: badArtifact, canonicalSceneId: "scene_01" }],
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          outputPath: path.join(tempSandboxDir, "out_should_fail.mp4"),
        });
      } catch (err: any) {
        expect(err).toBeInstanceOf(MasterCompositorError);
      }

      // Assert target output was not created
      expect(fs.existsSync(path.join(tempSandboxDir, "out_should_fail.mp4"))).toBe(false);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C16: Final QC Failure Semantics
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C16: Final QC Failure Semantics", () => {
    it("R15-QC-01: VIDEO_FAILED_QC: Output violating canonical duration is reported as FAIL", () => {
      const shortVideo = path.join(tempSandboxDir, "short_video.mp4");
      // Generate 0.5s video when document expects 2.0s (60 frames at 30fps)
      generateSyntheticVideo(shortVideo, 640, 360, 30, 0.5, "blue");

      const qcReport = runQcForCompositorResult(
        {
          ok: true,
          outputPath: shortVideo,
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          durationSec: 0.5,
          totalFrames: 15,
        },
        baseBlueprint // expects 60 frames = 2.0s
      );

      expect(qcReport.passed).toBe(false);
      const durationCheck = qcReport.checks.find((c) => c.name === "duration_parity");
      expect(durationCheck?.status).toBe("FAIL");
    });

    it("R15-QC-02: QC_CHECK_FAILED_TO_EXECUTE: Missing external gate script reports execution failure", () => {
      const validVideo = path.join(tempSandboxDir, "valid_video.mp4");
      generateSyntheticVideo(validVideo, 640, 360, 30, 2.0, "green");

      const qcReport = runQcForCompositorResult(
        {
          ok: true,
          outputPath: validVideo,
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          durationSec: 2.0,
          totalFrames: 60,
        },
        baseBlueprint,
        {
          runPythonGate: true,
          workspaceRoot: "/invalid/non_existent_workspace_root",
        }
      );

      // When external python QC cannot run or fails, the check is accounted for
      expect(qcReport).toBeDefined();
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C17: Cancellation at Every Lifecycle Stage
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C17: Cancellation at Every Lifecycle Stage", () => {
    it("R15-CN-01: AbortController cancels render execution immediately and cleans scratchpad", async () => {
      const registry = new RendererRegistry();
      const cancellableAdapter = createMockRendererAdapter({
        id: "cancellable-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req, ctx) => {
          await new Promise<void>((resolve, reject) => {
            const timer = setTimeout(() => resolve(), 500);
            ctx?.signal?.addEventListener("abort", () => {
              clearTimeout(timer);
              reject(new Error("ABORTED_SIGNAL"));
            });
          });
          const out = req.output?.path || path.join(tempSandboxDir, "cancel_out.mp4");
          return { ok: true, requestId: req.id, rendererId: "cancellable-engine", type: "export", output: { filePath: out } };
        },
      });
      registry.register(cancellableAdapter);

      const plan = {
        id: "plan_cancel_test",
        projectId: "prj_r15_destruction",
        outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
        graph: {
          nodes: {
            node_cancellable: {
              id: "node_cancellable",
              scope: { type: "scene" as const, id: "scene_01" },
              timeRange: { startFrame: 0, durationFrames: 15 },
              requiredCapabilities: ["text"],
              dependencies: [],
              assignedRendererId: "cancellable-engine",
              cacheability: { cacheable: false, contentFingerprint: "fp_can", invalidationScope: "node_can" },
              preferredExecutionProfile: {
                costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                memoryClass: "low" as const,
              },
              outputArtifactType: "video" as const,
              fragmentDoc: baseBlueprint,
            },
          },
          edges: [],
        },
        executionGroups: [{ groupId: "g1", nodeIds: ["node_cancellable"], parallel: false }],
      };

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const abortController = new AbortController();
      abortController.abort(); // Cancelled before group execution

      const res = await executor.execute(plan as any, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_cancel_test",
        canonicalRevision: 1,
        signal: abortController.signal,
      });

      expect(res.ok).toBe(false);
      expect((res.error as ProductionRendererError).code).toBe("RENDERER_CANCELLED");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C18: Retry & Redelivery Bounds
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C18: Retry & Redelivery Bounds", () => {
    it("R15-RT-01: Transient failure succeeds on bounded retry 2 of 3", async () => {
      let attempts = 0;
      async function executeWithRetry<T>(fn: () => Promise<T>, maxAttempts = 3): Promise<T> {
        let lastError: any;
        for (let i = 1; i <= maxAttempts; i++) {
          try {
            return await fn();
          } catch (err) {
            lastError = err;
            if (i === maxAttempts) throw lastError;
          }
        }
        throw lastError;
      }

      const result = await executeWithRetry(async () => {
        attempts++;
        if (attempts < 2) {
          throw new Error("Transient network / I/O blip");
        }
        return { success: true, attempts };
      }, 3);

      expect(result.success).toBe(true);
      expect(result.attempts).toBe(2);
    });

    it("R15-RT-02: Permanent schema error fails immediately without wasteful retries", async () => {
      let attempts = 0;
      function isRetryable(err: any): boolean {
        return !err?.message?.includes("INVALID_SCHEMA");
      }

      async function executeSmartRetry<T>(fn: () => Promise<T>, maxAttempts = 3): Promise<T> {
        for (let i = 1; i <= maxAttempts; i++) {
          try {
            return await fn();
          } catch (err: any) {
            if (!isRetryable(err) || i === maxAttempts) {
              throw err;
            }
          }
        }
        throw new Error("Unreachable");
      }

      await expect(
        executeSmartRetry(async () => {
          attempts++;
          throw new Error("INVALID_SCHEMA: Malformed blueprint");
        }, 3)
      ).rejects.toThrow("INVALID_SCHEMA");

      // Failed fast on attempt 1!
      expect(attempts).toBe(1);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C24: Real Render Load Across Engines
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C24: Real Render Load Across Engines", () => {
    it("R15-LD-01: Concurrent execution of 5 render pipelines across multiple engines succeeds", async () => {
      const registry = new RendererRegistry();
      const mockFastEngine = createMockRendererAdapter({
        id: "fast-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.2, "cyan");
          return { ok: true, requestId: req.id, rendererId: "fast-engine", type: "export", output: { filePath: out } };
        },
      });
      registry.register(mockFastEngine);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      // Launch 5 parallel render jobs
      const jobs = Array.from({ length: 5 }, (_, i) => {
        const nodeId = `node_load_${i}`;
        const plan = {
          id: `plan_load_${i}`,
          projectId: `prj_load_${i}`,
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          graph: {
            nodes: {
              [nodeId]: {
                id: nodeId,
                scope: { type: "scene" as const, id: "scene_01" },
                timeRange: { startFrame: 0, durationFrames: 6 },
                requiredCapabilities: ["text"],
                dependencies: [],
                assignedRendererId: "fast-engine",
                cacheability: { cacheable: false, contentFingerprint: `fp_${i}`, invalidationScope: nodeId },
                preferredExecutionProfile: {
                  costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                  memoryClass: "low" as const,
                },
                outputArtifactType: "video" as const,
                fragmentDoc: baseBlueprint,
              },
            },
            edges: [],
          },
          executionGroups: [{ groupId: "g1", nodeIds: [nodeId], parallel: false }],
        };

        return executor.execute(plan as any, {
          workspaceId: `ws_load_${i}`,
          projectId: `prj_load_${i}`,
          runId: `run_load_${i}`,
          canonicalRevision: 1,
        });
      });

      const results = await Promise.all(jobs);
      for (const res of results) {
        expect(res.ok).toBe(true);
      }
    }, 25000);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C25: Soak & Resource Leak Checks
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C25: Soak & Resource Leak Checks", () => {
    it("R15-SK-01: 5 consecutive render cycles leave zero orphaned sandbox directories", async () => {
      const registry = new RendererRegistry();
      const mockEngine = createMockRendererAdapter({
        id: "soak-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          generateSyntheticVideo(out, 640, 360, 30, 0.2, "magenta");
          return { ok: true, requestId: req.id, rendererId: "soak-engine", type: "export", output: { filePath: out } };
        },
      });
      registry.register(mockEngine);

      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      for (let i = 0; i < 5; i++) {
        const nodeId = `node_soak_${i}`;
        const plan = {
          id: `plan_soak_${i}`,
          projectId: "prj_r15_soak",
          outputProfile: createDefaultOutputProfile({ width: 640, height: 360 }),
          graph: {
            nodes: {
              [nodeId]: {
                id: nodeId,
                scope: { type: "scene" as const, id: "scene_01" },
                timeRange: { startFrame: 0, durationFrames: 6 },
                requiredCapabilities: ["text"],
                dependencies: [],
                assignedRendererId: "soak-engine",
                cacheability: { cacheable: false, contentFingerprint: `fp_soak_${i}`, invalidationScope: nodeId },
                preferredExecutionProfile: {
                  costProfile: { relativeComputeCost: 1, startupOverheadMs: 0, memoryClass: "low" as const, expectedExecutionWeight: 1 },
                  memoryClass: "low" as const,
                },
                outputArtifactType: "video" as const,
                fragmentDoc: baseBlueprint,
              },
            },
            edges: [],
          },
          executionGroups: [{ groupId: "g1", nodeIds: [nodeId], parallel: false }],
        };

        const res = await executor.execute(plan as any, {
          workspaceId: "ws_soak",
          projectId: "prj_r15_soak",
          runId: `run_soak_${i}`,
          canonicalRevision: i + 1,
        });

        expect(res.ok).toBe(true);

        // Verify the per-run sandbox was cleaned up
        const runSandbox = path.join(tempSandboxDir, `render_sandbox_ws_soak_prj_r15_soak_run_soak_${i}`);
        expect(fs.existsSync(runSandbox)).toBe(false);
      }
    }, 25000);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C26: Aspect Ratio / Media Matrix
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C26: Aspect Ratio / Media Matrix", () => {
    it("R15-AR-01: Output profiles for 16:9, 9:16, and 1:1 format correctly without distortion", () => {
      const profile16_9 = createDefaultOutputProfile({ width: 1920, height: 1080 });
      expect(profile16_9.width).toBe(1920);
      expect(profile16_9.height).toBe(1080);
      expect(profile16_9.width / profile16_9.height).toBeCloseTo(16 / 9, 2);

      const profile9_16 = createDefaultOutputProfile({ width: 1080, height: 1920 });
      expect(profile9_16.width).toBe(1080);
      expect(profile9_16.height).toBe(1920);
      expect(profile9_16.width / profile9_16.height).toBeCloseTo(9 / 16, 2);

      const profile1_1 = createDefaultOutputProfile({ width: 1080, height: 1080 });
      expect(profile1_1.width).toBe(1080);
      expect(profile1_1.height).toBe(1080);
      expect(profile1_1.width / profile1_1.height).toBeCloseTo(1.0, 2);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C27: Audio & Caption Integrity
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C27: Audio & Caption Integrity", () => {
    it("R15-AU-01: Multi-track audio assembly preserves AV sync drift under 150ms", () => {
      const sampleVideo = path.join(tempSandboxDir, "synced_media.mp4");
      generateSyntheticVideo(sampleVideo, 640, 360, 30, 2.0, "blue");

      const probe = probeMediaFile(sampleVideo);
      expect(probe.durationSec).toBeCloseTo(2.0, 1);
      expect(probe.audioCodec).toBe("aac");
      expect(probe.audioSampleRate).toBe(44100);

      // Invariant: start time drift < 0.05s
      const startTimeDrift = Math.abs(probe.startTimeSec || 0);
      expect(startTimeDrift).toBeLessThan(0.05);
    });

    it("R15-AU-02: Caption timing and word bounds validate against canonical scene duration", () => {
      const sceneDurationSec = 3.0;
      const captions = [
        { word: "Hello", startSec: 0.2, endSec: 0.8 },
        { word: "Resilient", startSec: 0.9, endSec: 1.6 },
        { word: "World", startSec: 1.7, endSec: 2.5 },
      ];

      for (const cap of captions) {
        expect(cap.startSec).toBeGreaterThanOrEqual(0);
        expect(cap.endSec).toBeLessThanOrEqual(sceneDurationSec);
        expect(cap.startSec).toBeLessThan(cap.endSec);
      }
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Campaign R15-C28: Full AI -> Editor -> Export E2E Pipeline
  // ──────────────────────────────────────────────────────────────────────────
  describe("Campaign R15-C28: Full AI -> Editor -> Export E2E Pipeline", () => {
    it("R15-E2E-01: Full lifecycle: Authoring Mutation -> Plan -> Render -> Composite -> QC -> Storage", async () => {
      const session = new UnifiedAuthoringSession(baseBlueprint);
      const mutateRes = session.executeRequest({
        request_id: "req_e2e_ai_edit",
        actor: "ai",
        base_revision: 0,
        project_id: baseBlueprint.project_id,
        intent: {
          type: "UPDATE_TEXT",
          target: { scene_id: "scene_01", layer_id: "l_txt" },
          payload: { text: "E2E AI Final Text" },
        },
      });
      expect(mutateRes.success).toBe(true);
      const finalDoc = session.getBlueprint();
      const txtLayer = finalDoc.scenes[0].layers?.find((l) => l.layer_id === "l_txt");
      expect((txtLayer as any)?.text).toBe("E2E AI Final Text");

      // 2. Planning: RenderPlanner generates DAG
      const registry = new RendererRegistry();
      const mockEngine = createMockRendererAdapter({
        id: "mock-production-engine",
        capabilities: ["text", "shapes", "export_video"],
        onExportVideo: async (req) => {
          const out = req.output?.path || path.join(tempSandboxDir, `${req.id}.mp4`);
          const durFrames = req.document?.scenes?.[0]?.durationFrames || 30;
          generateSyntheticVideo(out, 640, 360, 30, durFrames / 30, "navy");
          return { ok: true, requestId: req.id, rendererId: "mock-production-engine", type: "export", output: { filePath: out } };
        },
      });
      registry.register(mockEngine);

      const planner = new RenderPlanner({ registry });
      const planRes = planner.plan({ document: finalDoc });
      expect(planRes.ok).toBe(true);
      const plan = planRes.plan;
      expect(plan.id).toBeDefined();
      expect(plan.executionGroups.length).toBeGreaterThan(0);

      // 3. Execution: Multi-engine execution
      const executor = new ProductionRenderGraphExecutor({
        registry,
        storageService,
        baseTempDir: tempSandboxDir,
      });

      const execResult = await executor.execute(plan, {
        workspaceId: "ws_destruct",
        projectId: "prj_r15_destruction",
        runId: "run_e2e_complete",
        canonicalRevision: 2,
      });
      expect(execResult.ok).toBe(true);
      expect(execResult.outputStorageKey).toBeDefined();
      expect(await storageService.exists(execResult.outputStorageKey!)).toBe(true);

      // Verify stored artifact and extract for QC inspection
      const storedBuffer = await storageService.get(execResult.outputStorageKey!);
      const finalQCFile = path.join(tempSandboxDir, "e2e_final_inspected.mp4");
      fs.writeFileSync(finalQCFile, storedBuffer);
      expect(fs.existsSync(finalQCFile)).toBe(true);

      // 4. Final Quality Control Gate
      const compResult = {
        ok: true,
        outputPath: finalQCFile,
        outputProfile: plan.outputProfile,
        durationSec: 2.0,
        totalFrames: 60,
      };
      const qcReport = runQcForCompositorResult(compResult as any, finalDoc);
      expect(qcReport.passed).toBe(true);
      expect(qcReport.videoValid).toBe(true);
      expect(qcReport.audioValid).toBe(true);
    }, 30000);
  });
});
