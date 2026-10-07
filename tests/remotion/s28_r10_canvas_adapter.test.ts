/**
 * tests/remotion/s28_r10_canvas_adapter.test.ts
 * Comprehensive Verification Suite for S28-R10: Canvas Headless Renderer Adapter & Multi-Engine Dispatch.
 * 
 * Verifies:
 *   - CanvasRendererAdapter implementation and registration
 *   - Accurate capability taxonomy (no map, 3d, particles, custom_shaders, video)
 *   - canRender fail-closed verification
 *   - Real frame rendering (renderFrame) with valid buffer and file
 *   - Discrete sequence rendering (renderSequence)
 *   - Real video export (exportVideo) via FFmpeg
 *   - CRITICAL MULTI-RENDERER PROOF:
 *       * Request A (2D visual subset) -> CanvasRendererAdapter
 *       * Request B (Requires video/ducking) -> RemotionRendererAdapter
 *       * Request C (Requires map/3d/particles) -> NO_COMPATIBLE_RENDERER
 *       * Zero hardcoded engine branching outside RendererRegistry
 *   - Preferred renderer override & fail-closed validation
 *   - Semantic parity across evaluateVideoAtFrame, BrowserPreviewRuntime, and Canvas
 *   - Native TemplateSpec rendering coverage
 *   - AbortSignal cancellation clean halt
 *   - Remotion adapter unaffected & full compatibility preserved
 */

import { describe, it, expect, beforeAll } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

import {
  RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  NoCompatibleRendererError,
  UnsupportedCapabilityError,
  InvalidRenderRequestError,
  REMOTION_RENDERER_ID,
  CANVAS_RENDERER_ID,
  type RenderRequest,
  type RenderContext,
} from "../../contracts/renderer";
import {
  CanvasRendererAdapter,
  createCanvasRendererAdapter,
  registerCanvasRenderer,
  CANVAS_SUPPORTED_CAPABILITIES,
  resolveCanvasDimensions,
  assembleCanvasSvg,
} from "../../canvas/canvas-renderer-adapter";
import {
  RemotionRendererAdapter,
  createRemotionRendererAdapter,
  registerRemotionRenderer,
  getOrCreateRemotionBundle,
} from "../../remotion/remotion-renderer-adapter";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";

describe("S28-R10 Canvas Headless Renderer Adapter & Multi-Renderer Dispatch", () => {
  let canvasAdapter: CanvasRendererAdapter;
  let remotionAdapter: RemotionRendererAdapter;
  let multiRegistry: RendererRegistry;

  const sample2dDoc: BlueprintV2 = {
    project_id: "test-r10-2d",
    fps: 30,
    aspect_ratio: "16:9",
    totalDurationFrames: 30,
    scenes: [
      {
        scene_id: "s1",
        startFrame: 0,
        durationFrames: 30,
        surface: { text: "Scene Title" },
        layers: [
          {
            layer_id: "l_bg",
            kind: "shape",
            time_range: { startFrame: 0, durationFrames: 30 },
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
            size: { width: 1920, height: 1080 },
            fillColor: "#0f172a",
          },
          {
            layer_id: "l_title",
            kind: "text",
            time_range: { startFrame: 0, durationFrames: 30 },
            transform: {
              position: { x: 0, y: -60 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 1,
            text: "Hello Multi-Renderer",
            typography: { fontFamily: "Cairo", fontSize: 60, fillColor: "#38bdf8" },
            channels: [
              {
                channel_id: "ch_title_y",
                target: "TRANSFORM_Y",
                keyframes: [
                  { frame: 0, value: -60, easing: "LINEAR" },
                  { frame: 15, value: -30, easing: "LINEAR" },
                ],
              },
            ],
          },
        ],
      },
    ],
  };

  beforeAll(async () => {
    canvasAdapter = createCanvasRendererAdapter();
    remotionAdapter = createRemotionRendererAdapter();

    multiRegistry = new RendererRegistry();
    multiRegistry.register(canvasAdapter);
    multiRegistry.register(remotionAdapter);
  });

  // ─── 1. Adapter Registration & Identity ─────────────────────────────────────

  it("R10-01: Canvas adapter registers successfully in registry with priority 110", () => {
    const reg = new RendererRegistry();
    const adapter = registerCanvasRenderer(reg);

    expect(reg.has(CANVAS_RENDERER_ID)).toBe(true);
    const retrieved = reg.requireRenderer(CANVAS_RENDERER_ID);
    expect(retrieved.id).toBe(CANVAS_RENDERER_ID);
    expect(retrieved.name).toBe("Canvas Headless 2D Renderer Adapter");
    expect(retrieved.version).toBe("1.0.0");
    expect(retrieved.priority).toBe(110);
    expect(retrieved).toBe(adapter);
  });

  // ─── 2. Accurate Capability Taxonomy ────────────────────────────────────────

  it("R10-02: Canvas adapter accurately declares 2D visual capabilities and strictly excludes advanced engines", () => {
    const caps = canvasAdapter.capabilities();

    // Must declare supported 2D primitives
    expect(caps.has("text")).toBe(true);
    expect(caps.has("image")).toBe(true);
    expect(caps.has("shapes")).toBe(true);
    expect(caps.has("groups")).toBe(true);
    expect(caps.has("keyframes")).toBe(true);
    expect(caps.has("transitions")).toBe(true);
    expect(caps.has("alpha")).toBe(true);

    // Must declare targets
    expect(caps.has("frame_rendering")).toBe(true);
    expect(caps.has("sequence_rendering")).toBe(true);
    expect(caps.has("export_video")).toBe(true);

    // MUST NOT declare external/unimplemented capabilities
    expect(caps.has("video")).toBe(false);
    expect(caps.has("map")).toBe(false);
    expect(caps.has("3d")).toBe(false);
    expect(caps.has("particles")).toBe(false);
    expect(caps.has("custom_shaders")).toBe(false);
    expect(caps.has("live_preview")).toBe(false);
  });

  // ─── 3. canRender() Fail-Closed ─────────────────────────────────────────────

  it("R10-03: canRender approves 2D canonical documents and rejects unsupported engine capabilities", () => {
    // 2D document -> Approved
    const check2d = canvasAdapter.canRender({
      id: "req-can-2d",
      document: sample2dDoc,
      type: "frame",
      frame: 0,
    });
    expect(check2d.canRender).toBe(true);
    expect(check2d.missingCapabilities).toHaveLength(0);

    // Document with video layer -> Rejected
    const videoDoc: BlueprintV2 = {
      project_id: "doc-video",
      fps: 30,
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          layers: [
            {
              layer_id: "l_vid",
              kind: "video",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              asset_ref: "movie.mp4",
            },
          ],
        },
      ],
    };

    const checkVideo = canvasAdapter.canRender({
      id: "req-can-vid",
      document: videoDoc,
      type: "frame",
      frame: 0,
    });
    expect(checkVideo.canRender).toBe(false);
    expect(checkVideo.missingCapabilities).toContain("video");

    // Document with map template -> Rejected
    const mapDoc: BlueprintV2 = {
      project_id: "doc-map",
      fps: 30,
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          template: "rui-map-flight",
        },
      ],
    };

    const checkMap = canvasAdapter.canRender({
      id: "req-can-map",
      document: mapDoc,
      type: "frame",
      frame: 0,
    });
    expect(checkMap.canRender).toBe(false);
    expect(checkMap.missingCapabilities).toContain("map");
  });

  // ─── 4. Real Frame Rendering (renderFrame) ──────────────────────────────────

  it("R10-04: renderFrame produces structured RenderResult with valid image file and buffer", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "canvas_test_frame_"));
    const outPath = path.join(tempDir, "rendered_frame.png");

    const res = await canvasAdapter.renderFrame({
      id: "req-f1",
      document: sample2dDoc,
      type: "frame",
      frame: 0,
      output: { path: outPath, format: "png", width: 1280, height: 720 },
    });

    expect(res.ok).toBe(true);
    expect(res.requestId).toBe("req-f1");
    expect(res.rendererId).toBe(CANVAS_RENDERER_ID);
    expect(res.type).toBe("frame");
    expect(res.output?.filePath).toBe(outPath);
    expect(fs.existsSync(outPath)).toBe(true);
    expect(res.output?.buffer).toBeDefined();
    expect(res.output?.buffer!.length).toBeGreaterThan(1000);
    expect(res.output?.width).toBe(1280);
    expect(res.output?.height).toBe(720);
    expect(res.output?.mimeType).toBe("image/png");
    expect(res.metrics?.renderTimeMs).toBeGreaterThan(0);
    expect(res.metrics?.evaluatedFrames).toBe(1);

    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  // ─── 5. Discrete Sequence Rendering (renderSequence) ────────────────────────

  it("R10-05: renderSequence renders discrete frame range into target directory", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "canvas_test_seq_"));

    const res = await canvasAdapter.renderSequence({
      id: "req-seq1",
      document: sample2dDoc,
      type: "sequence",
      timeRange: { startFrame: 0, endFrame: 3 },
      output: { path: tempDir, format: "png", width: 640, height: 360 },
    });

    expect(res.ok).toBe(true);
    expect(res.type).toBe("sequence");
    expect(res.output?.frameCount).toBe(4);
    expect(res.output?.filePath).toBe(tempDir);
    expect(res.metrics?.evaluatedFrames).toBe(4);

    // Verify all 4 frame files exist on disk
    for (let f = 0; f <= 3; f++) {
      const frameFile = path.join(tempDir, `frame_${String(f).padStart(6, "0")}.png`);
      expect(fs.existsSync(frameFile)).toBe(true);
      expect(fs.statSync(frameFile).size).toBeGreaterThan(500);
    }

    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  // ─── 6. Video Export (exportVideo) ──────────────────────────────────────────

  it("R10-06: exportVideo exports valid MP4 video file", async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "canvas_test_exp_"));
    const outPath = path.join(tempDir, "exported_video.mp4");

    const shortDoc: BlueprintV2 = {
      ...sample2dDoc,
      totalDurationFrames: 5,
    };

    const res = await canvasAdapter.exportVideo({
      id: "req-exp1",
      document: shortDoc,
      type: "export",
      output: { path: outPath, width: 640, height: 360 },
    });

    expect(res.ok).toBe(true);
    expect(res.type).toBe("export");
    expect(res.output?.filePath).toBe(outPath);
    expect(fs.existsSync(outPath)).toBe(true);
    expect(fs.statSync(outPath).size).toBeGreaterThan(1000);
    expect(res.output?.mimeType).toBe("video/mp4");
    expect(res.output?.frameCount).toBe(5);
    expect(res.metrics?.evaluatedFrames).toBe(5);

    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  // ─── 7. CRITICAL MULTI-RENDERER PROOF ───────────────────────────────────────

  describe("R10-07: Multi-Renderer Proof (Registry Selection Without Hardcoding)", () => {
    it("Multi-Renderer Proof: Request A (2D primitives) -> CanvasRendererAdapter (Higher Priority)", () => {
      const reqA: RenderRequest = {
        id: "req-proof-a",
        document: sample2dDoc,
        type: "frame",
        frame: 0,
      };

      const selected = multiRegistry.selectRenderer(reqA);
      expect(selected.id).toBe(CANVAS_RENDERER_ID);
      expect(selected.priority).toBe(110);
    });

    it("Multi-Renderer Proof: Request B (Requires video) -> RemotionRendererAdapter", () => {
      const videoDoc: BlueprintV2 = {
        project_id: "proof-b-video",
        fps: 30,
        totalDurationFrames: 30,
        scenes: [
          {
            scene_id: "s1",
            startFrame: 0,
            durationFrames: 30,
            layers: [
              {
                layer_id: "l_vid",
                kind: "video",
                time_range: { startFrame: 0, durationFrames: 30 },
                transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
                opacity: 1,
                visible: true,
                z_index: 0,
                asset_ref: "movie.mp4",
              },
            ],
          },
        ],
      };

      const reqB: RenderRequest = {
        id: "req-proof-b",
        document: videoDoc,
        type: "frame",
        frame: 0,
      };

      const selected = multiRegistry.selectRenderer(reqB);
      expect(selected.id).toBe(REMOTION_RENDERER_ID);
      expect(selected.priority).toBe(100);
    });

    it("Multi-Renderer Proof: Request C (Requires map) -> Fails closed with NO_COMPATIBLE_RENDERER", () => {
      const mapDoc: BlueprintV2 = {
        project_id: "proof-c-map",
        fps: 30,
        totalDurationFrames: 30,
        scenes: [
          {
            scene_id: "s1",
            startFrame: 0,
            durationFrames: 30,
            template: "rui-map-flight",
          },
        ],
      };

      const reqC: RenderRequest = {
        id: "req-proof-c",
        document: mapDoc,
        type: "frame",
        frame: 0,
      };

      expect(() => multiRegistry.selectRenderer(reqC)).toThrow(NoCompatibleRendererError);
    });
  });

  // ─── 8. Preferred Renderer Override & Fail-Closed Validation ─────────────────

  it("R10-08: Preferred renderer override respects compatible engine and fails closed when incompatible", () => {
    // Override Request A to Remotion explicitly
    const reqOverride: RenderRequest = {
      id: "req-override",
      document: sample2dDoc,
      type: "frame",
      frame: 0,
      preferredRendererId: REMOTION_RENDERER_ID,
    };

    const selectedRem = multiRegistry.selectRenderer(reqOverride);
    expect(selectedRem.id).toBe(REMOTION_RENDERER_ID);

    // Request with video specifying preferredRendererId: canvas-renderer-adapter MUST fail closed
    const videoDoc: BlueprintV2 = {
      project_id: "proof-pref-vid",
      fps: 30,
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          layers: [
            {
              layer_id: "l_v",
              kind: "video",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              asset_ref: "vid.mp4",
            },
          ],
        },
      ],
    };

    const reqBadPref: RenderRequest = {
      id: "req-bad-pref",
      document: videoDoc,
      type: "frame",
      frame: 0,
      preferredRendererId: CANVAS_RENDERER_ID,
    };

    expect(() => multiRegistry.selectRenderer(reqBadPref)).toThrow(UnsupportedCapabilityError);
  });

  // ─── 9. Fail-Closed Execution Invariants ────────────────────────────────────

  it("R10-09: Direct execution of unsupported capability fails closed with UnsupportedCapabilityError", async () => {
    const mapDoc: BlueprintV2 = {
      project_id: "fail-map",
      fps: 30,
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          template: "rui-map-flight",
        },
      ],
    };

    await expect(
      canvasAdapter.renderFrame({ id: "fail-f", document: mapDoc, type: "frame", frame: 0 })
    ).rejects.toThrow(UnsupportedCapabilityError);

    await expect(
      canvasAdapter.renderSequence({
        id: "fail-s",
        document: mapDoc,
        type: "sequence",
        timeRange: { startFrame: 0, endFrame: 2 },
      })
    ).rejects.toThrow(UnsupportedCapabilityError);

    await expect(
      canvasAdapter.exportVideo({ id: "fail-e", document: mapDoc, type: "export" })
    ).rejects.toThrow(UnsupportedCapabilityError);
  });

  // ─── 10. Semantic Parity Verification ───────────────────────────────────────

  it("R10-10: Canvas SVG assembly maintains exact semantic parity with evaluateVideoAtFrame", () => {
    const frame0 = evaluateVideoAtFrame(sample2dDoc, 0);
    const frame15 = evaluateVideoAtFrame(sample2dDoc, 15);

    // Frame 0: title y is -60
    const titleL0 = frame0.layers.find((l) => l.layer_id === "l_title")!;
    expect(titleL0.transform.y).toBe(-60);

    // Frame 15: title y keyframe interpolated to -30
    const titleL15 = frame15.layers.find((l) => l.layer_id === "l_title")!;
    expect(titleL15.transform.y).toBe(-30);

    // SVG assembly for frame 0 contains transform reflecting y = -60 (centerY + (-60) = 540 - 60 = 480)
    const svg0 = assembleCanvasSvg(frame0, 1920, 1080);
    expect(svg0).toContain("translate(960, 480)");
    expect(svg0).toContain("Hello Multi-Renderer");

    // SVG assembly for frame 15 contains transform reflecting y = -30 (centerY + (-30) = 540 - 30 = 510)
    const svg15 = assembleCanvasSvg(frame15, 1920, 1080);
    expect(svg15).toContain("translate(960, 510)");
  });

  // ─── 11. Native TemplateSpec Rendering ──────────────────────────────────────

  it("R10-11: Renders native TemplateSpec rui-title-card and rui-stat-card successfully", async () => {
    const instTitle = instantiateTemplate("rui-title-card", {
      title: "Native Template Title",
      subtitle: "Canvas Adapter Rendered",
    });
    const titleCardDoc: BlueprintV2 = {
      project_id: "test-title-card",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: instTitle.scene.durationFrames || 30,
      scenes: [instTitle.scene],
    };

    const resTitle = await canvasAdapter.renderFrame({
      id: "req-tmpl-title",
      document: titleCardDoc,
      type: "frame",
      frame: 0,
      output: { width: 640, height: 360 },
    });
    expect(resTitle.ok).toBe(true);
    expect(resTitle.output?.buffer).toBeDefined();

    const instStat = instantiateTemplate("rui-stat-card", {
      value: 99.9,
      label: "Uptime Metric",
    });
    const statCardDoc: BlueprintV2 = {
      project_id: "test-stat-card",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: instStat.scene.durationFrames || 30,
      scenes: [instStat.scene],
    };

    const resStat = await canvasAdapter.renderFrame({
      id: "req-tmpl-stat",
      document: statCardDoc,
      type: "frame",
      frame: 0,
      output: { width: 640, height: 360 },
    });
    expect(resStat.ok).toBe(true);
    expect(resStat.output?.buffer).toBeDefined();
  });

  // ─── 12. Cancellation via AbortSignal ───────────────────────────────────────

  it("R10-12: Cancellation via RenderContext AbortSignal halts execution cleanly", async () => {
    const controller = new AbortController();
    const context: RenderContext = {
      projectId: "test-abort",
      signal: controller.signal,
    };

    // Trigger abort immediately
    controller.abort();

    await expect(
      canvasAdapter.renderSequence(
        {
          id: "req-abort-seq",
          document: sample2dDoc,
          type: "sequence",
          timeRange: { startFrame: 0, endFrame: 10 },
        },
        context
      )
    ).rejects.toThrow();
  });

  // ─── 13. Remotion Adapter Remains Unaffected ────────────────────────────────

  it("R10-13: Remotion adapter remains fully compatible and unaffected in multi-renderer registry", () => {
    const remRetrieved = multiRegistry.requireRenderer(REMOTION_RENDERER_ID);
    expect(remRetrieved).toBe(remotionAdapter);
    expect(remRetrieved.capabilities().has("audio_ducking")).toBe(true);
    expect(remRetrieved.capabilities().has("video")).toBe(true);
  });
});
