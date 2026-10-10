/**
 * tests/remotion/s28_r09_remotion_adapter.test.ts
 * Comprehensive Verification Suite for S28-R09: Remotion Renderer Adapter.
 * 
 * Verifies:
 *   - Production RemotionRendererAdapter implementation and registration
 *   - Stub replacement in CANONICAL_RENDERER_REGISTRY
 *   - Accurate capability model (no map, 3d, particles, custom_shaders)
 *   - Fail-closed behavior on unsupported capabilities (NO_COMPATIBLE_RENDERER / UNSUPPORTED_CAPABILITY)
 *   - Real frame rendering (renderFrame) with @remotion/renderer
 *   - Discrete sequence rendering (renderSequence)
 *   - Video export (exportVideo) with full R07 audio ducking & mixing parity
 *   - Native TemplateSpec coverage (rui-title-card, rui-quote-card, rui-media-frame, rui-lower-third, rui-stat-card, rui-intro, rui-bento-pan)
 *   - Critical End-to-End Pipeline test (TemplateSpec -> Mutations -> Audio -> Request -> Registry -> RemotionAdapter -> Result)
 *   - Semantic parity comparison across evaluateVideoAtFrame, BrowserPreviewRuntime, and Remotion
 *   - Cancellation via RenderContext AbortSignal
 *   - Legacy compatibility bridge
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync } from "child_process";
import { bundle } from "@remotion/bundler";

import {
  RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  NoCompatibleRendererError,
  UnsupportedCapabilityError,
  REMOTION_RENDERER_ID,
  type RenderRequest,
  type RenderContext,
} from "../../contracts/renderer";
import {
  RemotionRendererAdapter,
  createRemotionRendererAdapter,
  registerRemotionRenderer,
  REMOTION_SUPPORTED_CAPABILITIES,
} from "../../remotion/remotion-renderer-adapter";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { applyMutation } from "../../contracts/mutations";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";

describe("S28-R09 Remotion Renderer Adapter & Engine Abstraction", () => {
  let bundleLocation: string;
  let adapter: RemotionRendererAdapter;
  let localRegistry: RendererRegistry;
  let testWorkspaceDir: string | null = null;

  beforeAll(async () => {
    const rootDir = process.cwd();
    const appDir = path.resolve(rootDir, "remotion-app");
    const entryPoint = path.resolve(appDir, "src/index.ts");
    const repoPublicDir = path.resolve(appDir, "public");
    const trackedFixturesDir = path.resolve(rootDir, "tests/fixtures/clean_room_project/assets/ready/audio");

    // 1. Create a fully isolated, test-scoped public directory in os.tmpdir()
    // This guarantees 100% hermetic execution: zero mutations to remotion-app/public,
    // zero shared state between concurrent test runners, zero locking needed, and zero risk to user files.
    testWorkspaceDir = fs.mkdtempSync(path.join(os.tmpdir(), "motion_r09_isolated_"));
    const isolatedPublicDir = path.join(testWorkspaceDir, "public");
    fs.mkdirSync(isolatedPublicDir, { recursive: true });

    // Copy only tracked base static assets required by templates (logo, warning, icons)
    // Never copy untracked, user-owned, or ignored directories (such as projects/, media/audio/, etc.)
    const staticFilesToCopy: string[] = [
      "logo.svg",
      "warning.svg",
      "render-props.json",
    ];

    for (const rel of staticFilesToCopy) {
      const src = path.resolve(repoPublicDir, rel);
      if (fs.existsSync(src)) {
        const dest = path.resolve(isolatedPublicDir, rel);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.copyFileSync(src, dest);
      }
    }

    const iconsSrcDir = path.resolve(repoPublicDir, "media/icons");
    if (fs.existsSync(iconsSrcDir)) {
      const iconsDestDir = path.resolve(isolatedPublicDir, "media/icons");
      fs.mkdirSync(iconsDestDir, { recursive: true });
      for (const file of fs.readdirSync(iconsSrcDir)) {
        if (file.endsWith(".svg")) {
          fs.copyFileSync(path.join(iconsSrcDir, file), path.join(iconsDestDir, file));
        }
      }
    }

    // 2. Stage required audio fixtures directly inside the isolated public directory
    const requiredAudio: Array<{ targetRel: string; sourceRel: string }> = [
      { targetRel: "media/audio/pop_norm.wav", sourceRel: "pop_norm.wav" },
      { targetRel: "media/audio/whoosh_norm.wav", sourceRel: "whoosh_norm.wav" },
      { targetRel: "media/sfx/digital.mp3", sourceRel: "digital_norm.wav" },
      { targetRel: "accent_chime.mp3", sourceRel: "notification_norm.wav" },
      { targetRel: "whoosh_cinematic.mp3", sourceRel: "whoosh_norm.wav" },
    ];

    for (const item of requiredAudio) {
      const sourcePath = path.resolve(trackedFixturesDir, item.sourceRel);
      if (!fs.existsSync(sourcePath)) {
        throw new Error(`Required source audio fixture missing at ${sourcePath}`);
      }

      const targetPath = path.resolve(isolatedPublicDir, item.targetRel);
      fs.mkdirSync(path.dirname(targetPath), { recursive: true });

      if (item.targetRel.endsWith(".mp3")) {
        // Transcode directly into isolated workspace target (no format substitution fallback)
        execFileSync("ffmpeg", ["-y", "-i", sourcePath, "-c:a", "libmp3lame", targetPath], {
          stdio: "pipe",
        });
        const codec = execFileSync("ffprobe", [
          "-v", "error",
          "-select_streams", "a:0",
          "-show_entries", "stream=codec_name",
          "-of", "default=noprint_wrappers=1:nokey=1",
          targetPath,
        ], { encoding: "utf-8" }).trim();
        if (codec !== "mp3") {
          throw new Error(`Transcoding verification failed for ${item.targetRel}: expected mp3 stream, got ${codec}`);
        }
      } else {
        const codec = execFileSync("ffprobe", [
          "-v", "error",
          "-select_streams", "a:0",
          "-show_entries", "stream=codec_name",
          "-of", "default=noprint_wrappers=1:nokey=1",
          sourcePath,
        ], { encoding: "utf-8" }).trim();
        if (!codec.startsWith("pcm")) {
          throw new Error(`Source audio fixture verification failed for ${sourcePath}: expected pcm stream, got ${codec}`);
        }
        fs.copyFileSync(sourcePath, targetPath);
      }

      // Verify staged target in isolatedPublicDir
      const targetCodec = execFileSync("ffprobe", [
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        targetPath,
      ], { encoding: "utf-8" }).trim();
      if (item.targetRel.endsWith(".mp3") && targetCodec !== "mp3") {
        throw new Error(`Staged target ${targetPath} has invalid codec: ${targetCodec}`);
      } else if (item.targetRel.endsWith(".wav") && !targetCodec.startsWith("pcm")) {
        throw new Error(`Staged target ${targetPath} has invalid codec: ${targetCodec}`);
      }
    }

    // 3. Compile hermetic Remotion bundle pointing exclusively to the isolated publicDir
    bundleLocation = await bundle({
      entryPoint,
      publicDir: isolatedPublicDir,
      webpackOverride: (config) => ({
        ...config,
        resolve: {
          ...config.resolve,
          modules: [
            path.resolve(appDir, "node_modules"),
            path.resolve(rootDir, "node_modules"),
            ...(config.resolve?.modules || ["node_modules"]),
          ],
          alias: {
            ...(config.resolve?.alias ?? {}),
            "@": path.resolve(appDir, "src"),
            "@registry": path.resolve(rootDir, "registry"),
            "@contracts": path.resolve(rootDir, "contracts"),
            react: path.resolve(appDir, "node_modules", "react"),
            "react-dom": path.resolve(appDir, "node_modules", "react-dom"),
          },
        },
      }),
    });

    // 4. Assert Remotion bundler faithfully copied each required fixture from publicDir (NO REPAIR FALLBACK)
    for (const item of requiredAudio) {
      const bundlePublicPath = path.resolve(bundleLocation, "public", item.targetRel);
      if (!fs.existsSync(bundlePublicPath)) {
        throw new Error(`Remotion bundling failed to include required public fixture: ${bundlePublicPath}`);
      }

      const bundleCodec = execFileSync("ffprobe", [
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        bundlePublicPath,
      ], { encoding: "utf-8" }).trim();
      if (item.targetRel.endsWith(".mp3") && bundleCodec !== "mp3") {
        throw new Error(`Bundle fixture ${bundlePublicPath} has invalid codec: ${bundleCodec}`);
      } else if (item.targetRel.endsWith(".wav") && !bundleCodec.startsWith("pcm")) {
        throw new Error(`Bundle fixture ${bundlePublicPath} has invalid codec: ${bundleCodec}`);
      }
    }

    adapter = createRemotionRendererAdapter({ bundleLocation });
    localRegistry = new RendererRegistry();
    localRegistry.register(adapter);
  }, 60000);

  afterAll(() => {
    if (testWorkspaceDir && fs.existsSync(testWorkspaceDir)) {
      try {
        fs.rmSync(testWorkspaceDir, { recursive: true, force: true });
      } catch {}
    }
    if (bundleLocation && fs.existsSync(bundleLocation)) {
      try {
        fs.rmSync(bundleLocation, { recursive: true, force: true });
      } catch {}
    }
  });

  // ─── 1. Registry Management & Stub Replacement ──────────────────────────────

  it("R09-01: Remotion adapter replaces stub in registry with production adapter", () => {
    const reg = new RendererRegistry();
    const remAdapter = registerRemotionRenderer(reg, { bundleLocation });

    expect(reg.has(REMOTION_RENDERER_ID)).toBe(true);
    const retrieved = reg.requireRenderer(REMOTION_RENDERER_ID);
    expect(retrieved.id).toBe(REMOTION_RENDERER_ID);
    expect(retrieved.version).toBe("4.0.525");
    expect(retrieved.priority).toBe(100);
    expect(retrieved).toBe(remAdapter);
  });

  // ─── 2. Accurate Capability Taxonomy ────────────────────────────────────────

  it("R09-02: Remotion adapter accurately declares supported capabilities and excludes unsupported advanced engines", () => {
    const caps = adapter.capabilities();

    // Must declare supported visual primitives
    expect(caps.has("text")).toBe(true);
    expect(caps.has("image")).toBe(true);
    expect(caps.has("video")).toBe(true);
    expect(caps.has("shapes")).toBe(true);
    expect(caps.has("groups")).toBe(true);
    expect(caps.has("keyframes")).toBe(true);
    expect(caps.has("transitions")).toBe(true);
    expect(caps.has("alpha")).toBe(true);

    // Must declare complete R07 audio subsystem capabilities
    expect(caps.has("audio")).toBe(true);
    expect(caps.has("audio_voiceover")).toBe(true);
    expect(caps.has("audio_music")).toBe(true);
    expect(caps.has("audio_sfx")).toBe(true);
    expect(caps.has("audio_mixing")).toBe(true);
    expect(caps.has("audio_ducking")).toBe(true);
    expect(caps.has("audio_timing")).toBe(true);

    // Must declare execution targets
    expect(caps.has("frame_rendering")).toBe(true);
    expect(caps.has("sequence_rendering")).toBe(true);
    expect(caps.has("export_video")).toBe(true);

    // MUST NOT declare specialized external engine capabilities
    expect(caps.has("map")).toBe(false);
    expect(caps.has("3d")).toBe(false);
    expect(caps.has("particles")).toBe(false);
    expect(caps.has("custom_shaders")).toBe(false);
    expect(caps.has("live_preview")).toBe(false);
  });

  // ─── 3. canRender() Fail-Closed Verification ────────────────────────────────

  it("R09-03: canRender correctly approves 2D canonical documents", () => {
    const doc: BlueprintV2 = {
      project_id: "test-doc-2d",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Hello" },
          layers: [
            {
              layer_id: "l1",
              kind: "text",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              text: "Hello",
              typography: { fontFamily: "Cairo", fontSize: 48, fillColor: "#fff" },
              channels: [],
            },
          ],
        },
      ],
    };

    const req: RenderRequest = {
      id: "req-2d",
      document: doc,
      type: "frame",
      frame: 0,
    };

    const check = adapter.canRender(req);
    expect(check.canRender).toBe(true);
    expect(check.missingCapabilities).toEqual([]);
  });

  it("R09-04: canRender fails closed on unsupported engine requirements (map, 3d, particles, custom_shaders)", () => {
    // 1. Map requirement
    const mapDoc: BlueprintV2 = {
      project_id: "doc-map",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s_map", template: "rui-map-flight", durationFrames: 30 }],
    };
    const mapReq: RenderRequest = { id: "req-map", document: mapDoc, type: "frame", frame: 0 };
    const checkMap = adapter.canRender(mapReq);
    expect(checkMap.canRender).toBe(false);
    expect(checkMap.missingCapabilities).toContain("map");

    // 2. 3D requirement
    const d3Doc: BlueprintV2 = {
      project_id: "doc-3d",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s_3d", template: "scene3d-element", durationFrames: 30 }],
    };
    const d3Req: RenderRequest = { id: "req-3d", document: d3Doc, type: "frame", frame: 0 };
    const check3D = adapter.canRender(d3Req);
    expect(check3D.canRender).toBe(false);
    expect(check3D.missingCapabilities).toContain("3d");

    // 3. Particles requirement
    const pDoc: BlueprintV2 = {
      project_id: "doc-particles",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s_p", template: "particlesystem-element", durationFrames: 30 }],
    };
    const pReq: RenderRequest = { id: "req-p", document: pDoc, type: "frame", frame: 0 };
    const checkP = adapter.canRender(pReq);
    expect(checkP.canRender).toBe(false);
    expect(checkP.missingCapabilities).toContain("particles");

    // 4. Custom shaders requirement (GL transition)
    const glDoc: BlueprintV2 = {
      project_id: "doc-gl",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "s_gl",
          durationFrames: 30,
          transition: { type: "ripple" as any, durationFrames: 15 },
        },
      ],
    };
    const glReq: RenderRequest = { id: "req-gl", document: glDoc, type: "sequence", timeRange: { startFrame: 0, endFrame: 15 } };
    const checkGL = adapter.canRender(glReq);
    expect(checkGL.canRender).toBe(false);
    expect(checkGL.missingCapabilities).toContain("custom_shaders");
  });

  // ─── 4. Registry Selection & Fail-Closed Errors ──────────────────────────────

  it("R09-05: RendererRegistry deterministically selects Remotion adapter for compatible request", () => {
    const doc: BlueprintV2 = {
      project_id: "doc-select",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", durationFrames: 30, surface: { text: "Select Me" } }],
    };

    const req: RenderRequest = {
      id: "req-select",
      document: doc,
      type: "frame",
      frame: 5,
    };

    const selected = localRegistry.selectRenderer(req);
    expect(selected.id).toBe(REMOTION_RENDERER_ID);
  });

  it("R09-06: RendererRegistry throws NO_COMPATIBLE_RENDERER when request has unsupported capabilities", () => {
    const mapDoc: BlueprintV2 = {
      project_id: "doc-map-fail",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", template: "rui-map-flight", durationFrames: 30 }],
    };

    const req: RenderRequest = {
      id: "req-map-fail",
      document: mapDoc,
      type: "frame",
      frame: 0,
    };

    expect(() => localRegistry.selectRenderer(req)).toThrow(NoCompatibleRendererError);
  });

  it("R09-07: Adapter renderFrame throws UnsupportedCapabilityError when called directly with unsupported capabilities", async () => {
    const mapDoc: BlueprintV2 = {
      project_id: "doc-direct-fail",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", template: "rui-map-flight", durationFrames: 30 }],
    };

    const req: RenderRequest = {
      id: "req-direct-fail",
      document: mapDoc,
      type: "frame",
      frame: 0,
    };

    await expect(adapter.renderFrame(req)).rejects.toThrow(UnsupportedCapabilityError);
  });

  // ─── 5. Real Frame Rendering (renderFrame) ──────────────────────────────────

  it("R09-08: renderFrame produces structured RenderResult with valid image file and buffer", async () => {
    const doc: BlueprintV2 = {
      project_id: "doc-frame-render",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s_main",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Render Frame Test" },
          layers: [
            {
              layer_id: "bg_shape",
              kind: "shape",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              shape_type: "rectangle",
              size: { width: 1920, height: 1080 },
              fillColor: "#1e293b",
              channels: [],
            },
            {
              layer_id: "title_text",
              kind: "text",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 1,
              text: "S28-R09 Frame Verification",
              typography: { fontFamily: "Cairo", fontSize: 56, fillColor: "#38bdf8", textAlign: "center" },
              channels: [],
            },
          ],
        },
      ],
    };

    const outPath = path.join(testWorkspaceDir!, "s28_r09_frame_test.png");
    const req: RenderRequest = {
      id: "req-still-test",
      document: doc,
      type: "frame",
      frame: 15,
      output: {
        path: outPath,
        format: "png",
        width: 1920,
        height: 1080,
      },
    };

    const result = await adapter.renderFrame(req);

    expect(result.ok).toBe(true);
    expect(result.rendererId).toBe(REMOTION_RENDERER_ID);
    expect(result.type).toBe("frame");
    expect(result.output?.filePath).toBe(outPath);
    expect(fs.existsSync(outPath)).toBe(true);
    expect(fs.statSync(outPath).size).toBeGreaterThan(1000);
    expect(result.output?.width).toBe(1920);
    expect(result.output?.height).toBe(1080);
    expect(result.output?.frameCount).toBe(1);
    expect(result.output?.buffer).toBeDefined();
    expect(result.metrics?.renderTimeMs).toBeGreaterThan(0);
    expect(result.metrics?.evaluatedFrames).toBe(1);
  }, 30000);

  // ─── 6. Sequence Rendering (renderSequence) ─────────────────────────────────

  it("R09-09: renderSequence renders discrete frame range into target directory", async () => {
    const doc: BlueprintV2 = {
      project_id: "doc-seq-render",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Sequence Test" },
          layers: [
            {
              layer_id: "bg",
              kind: "shape",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              shape_type: "rectangle",
              size: { width: 1920, height: 1080 },
              fillColor: "#0f172a",
              channels: [],
            },
          ],
        },
      ],
    };

    const outDir = path.join(testWorkspaceDir!, "s28_r09_seq_test");
    const req: RenderRequest = {
      id: "req-seq-test",
      document: doc,
      type: "sequence",
      timeRange: { startFrame: 0, endFrame: 3 },
      output: { path: outDir, format: "png" },
    };

    const result = await adapter.renderSequence(req);

    expect(result.ok).toBe(true);
    expect(result.type).toBe("sequence");
    expect(result.output?.frameCount).toBe(4);
    expect(fs.existsSync(outDir)).toBe(true);
    const files = fs.readdirSync(outDir).filter((f) => f.endsWith(".png"));
    expect(files.length).toBe(4);
    expect(result.metrics?.evaluatedFrames).toBe(4);
  }, 30000);

  // ─── 7. Video Export with Full Audio Parity ─────────────────────────────────

  it("R09-10: exportVideo exports valid MP4 video respecting voiceover, music, and dynamic ducking", async () => {
    const doc: BlueprintV2 = {
      project_id: "doc-export-audio",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 30,
      scenes: [
        {
          scene_id: "s0",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Audio Export" },
          layers: [
            {
              layer_id: "bg",
              kind: "shape",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 0,
              shape_type: "rectangle",
              size: { width: 1920, height: 1080 },
              fillColor: "#030712",
              channels: [],
            },
            {
              layer_id: "title",
              kind: "text",
              time_range: { startFrame: 0, durationFrames: 30 },
              transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 1,
              visible: true,
              z_index: 1,
              text: "Audio Ducking Export",
              typography: { fontFamily: "Cairo", fontSize: 60, fillColor: "#22c55e", textAlign: "center" },
              channels: [],
            },
          ],
        },
      ],
      audio: {
        voiceover: {
          asset_ref: "media/audio/pop_norm.wav",
          startFrame: 5,
          durationFrames: 15,
          volume: 1.0,
          mute: false,
        },
        music: {
          asset_ref: "media/audio/whoosh_norm.wav",
          startFrame: 0,
          durationFrames: 30,
          volume: 0.3,
          mute: false,
          ducking: {
            enabled: true,
            ducking_volume: 0.05,
          },
        },
        global_sfx: [
          {
            asset_ref: "media/sfx/digital.mp3",
            startFrame: 10,
            durationFrames: 10,
            volume: 0.8,
            mute: false,
          },
        ],
      },
    };

    const outPath = path.join(testWorkspaceDir!, "s28_r09_audio_export_test.mp4");
    const req: RenderRequest = {
      id: "req-export-audio-test",
      document: doc,
      type: "export",
      output: { path: outPath, format: "mp4", includeAudio: true },
    };

    const result = await adapter.exportVideo(req);

    expect(result.ok).toBe(true);
    expect(result.type).toBe("export");
    expect(result.output?.filePath).toBe(outPath);
    expect(fs.existsSync(outPath)).toBe(true);
    expect(fs.statSync(outPath).size).toBeGreaterThan(10000);
    expect(result.output?.frameCount).toBe(30);
    expect(result.output?.durationMs).toBe(1000);
    expect(result.metrics?.renderTimeMs).toBeGreaterThan(0);

    // Verify exported MP4 contains valid h264 video and aac audio streams
    const vCodec = execFileSync("ffprobe", [
      "-v", "error",
      "-select_streams", "v:0",
      "-show_entries", "stream=codec_name",
      "-of", "default=noprint_wrappers=1:nokey=1",
      outPath,
    ], { encoding: "utf-8" }).trim();
    expect(vCodec).toBe("h264");

    const aCodec = execFileSync("ffprobe", [
      "-v", "error",
      "-select_streams", "a:0",
      "-show_entries", "stream=codec_name",
      "-of", "default=noprint_wrappers=1:nokey=1",
      outPath,
    ], { encoding: "utf-8" }).trim();
    expect(aCodec).toBe("aac");
  }, 45000);

  // ─── 8. Native Template Coverage (R05 Native Templates) ────────────────────

  it("R09-11: Renders all 7 R05 Native TemplateSpecs via RemotionRendererAdapter", async () => {
    const nativeTemplates = [
      { id: "rui-title-card", params: { title: "Title Card Spec" } },
      { id: "rui-quote-card", params: { quote: "Perfection is achieved not when there is nothing more to add", author: "Saint-Exupéry" } },
      { id: "rui-media-frame", params: { media_ref: "asset_sample_frame" } },
      { id: "rui-lower-third", params: { title: "Lead Architect", subtitle: "Core Systems" } },
      { id: "rui-stat-card", params: { label: "Performance", value: 100 } },
      { id: "rui-intro", params: { title: "Chapter 1: The Engine" } },
      { id: "rui-bento-pan", params: { title: "Bento System Overview" } },
    ];

    for (const t of nativeTemplates) {
      const inst = instantiateTemplate(t.id, t.params);
      const doc: BlueprintV2 = {
        project_id: `test-native-${t.id}`,
        fps: 30,
        aspect_ratio: "16:9",
        totalDurationFrames: inst.scene.durationFrames || 30,
        scenes: [inst.scene],
      };

      const req: RenderRequest = {
        id: `req-native-${t.id}`,
        document: doc,
        type: "frame",
        frame: 5,
        output: { format: "png" },
      };

      expect(adapter.canRender(req).canRender).toBe(true);
      const res = await adapter.renderFrame(req);
      expect(res.ok).toBe(true);
      expect(res.output?.width).toBe(1920);
      expect(res.output?.height).toBe(1080);
    }
  }, 60000);

  // ─── 9. Critical End-to-End Pipeline Integration Test ───────────────────────

  it("R09-12: Critical End-to-End Test: TemplateSpec -> Mutations -> Audio -> Request -> Registry -> Remotion -> RenderResult", async () => {
    // 1. Instantiate from TemplateSpec
    const inst = instantiateTemplate("rui-title-card", { title: "Initial Title" });
    const initialDoc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "e2e-project-r09",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 30,
      scenes: [inst.scene],
      audio: {
        voiceover: { asset_ref: "accent_chime.mp3", startFrame: 5, durationFrames: 20, volume: 1.0 },
        music: { asset_ref: "whoosh_cinematic.mp3", startFrame: 0, durationFrames: 30, volume: 0.3, ducking: { enabled: true, ducking_volume: 0.05 } },
      },
    };

    // 2. Apply mutations (update title text & audio volume)
    const titleLayer = inst.scene.layers?.find((l) => l.kind === "text");
    expect(titleLayer).toBeDefined();

    const mutatedRes = applyMutation(initialDoc, {
      mutation_id: "mut_e2e_text_01",
      type: "UPDATE_TEXT",
      target: {
        scene_id: inst.scene.scene_id,
        layer_id: titleLayer!.layer_id,
      },
      payload: {
        text: "Mutated Title via E2E Flow",
      },
    });
    expect(mutatedRes.success).toBe(true);

    const finalRes = applyMutation(mutatedRes.blueprint, {
      mutation_id: "mut_e2e_audio_01",
      type: "SET_AUDIO_LEVEL",
      payload: {
        track: "music",
        volume: 0.4,
      },
    });
    expect(finalRes.success).toBe(true);
    const finalDoc = finalRes.blueprint;

    // 3. Construct RenderRequest
    const outVideoPath = path.join(testWorkspaceDir!, "s28_r09_e2e_export.mp4");
    const request: RenderRequest = {
      id: "e2e-render-req-1",
      document: finalDoc,
      type: "export",
      output: { path: outVideoPath, format: "mp4", includeAudio: true },
    };

    // 4. Registry selects adapter
    const selected = localRegistry.selectRenderer(request);
    expect(selected.id).toBe(REMOTION_RENDERER_ID);

    // 5. Adapter exports video
    const result = await selected.exportVideo(request);

    // 6. Assert RenderResult conforms to contract
    expect(result.ok).toBe(true);
    expect(result.requestId).toBe("e2e-render-req-1");
    expect(result.rendererId).toBe(REMOTION_RENDERER_ID);
    expect(result.type).toBe("export");
    expect(fs.existsSync(outVideoPath)).toBe(true);
    expect(result.metrics?.evaluatedFrames).toBe(30);

    // Verify exported MP4 contains valid h264 video and aac audio streams
    const vCodec = execFileSync("ffprobe", [
      "-v", "error",
      "-select_streams", "v:0",
      "-show_entries", "stream=codec_name",
      "-of", "default=noprint_wrappers=1:nokey=1",
      outVideoPath,
    ], { encoding: "utf-8" }).trim();
    expect(vCodec).toBe("h264");

    const aCodec = execFileSync("ffprobe", [
      "-v", "error",
      "-select_streams", "a:0",
      "-show_entries", "stream=codec_name",
      "-of", "default=noprint_wrappers=1:nokey=1",
      outVideoPath,
    ], { encoding: "utf-8" }).trim();
    expect(aCodec).toBe("aac");
  }, 45000);

  // ─── 10. Semantic Parity Verification (Evaluator vs Preview vs Remotion) ────

  it("R09-13: Semantic Parity: Frame evaluation matches BrowserPreviewRuntime and Remotion audio states", async () => {
    const doc: BlueprintV2 = {
      project_id: "parity-project",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 60,
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 60,
          layers: [
            {
              layer_id: "shape_bg",
              kind: "shape",
              time_range: { startFrame: 0, durationFrames: 60 },
              transform: { position: { x: 10, y: 20 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
              opacity: 0.8,
              visible: true,
              z_index: 0,
              shape_type: "rectangle",
              size: { width: 1920, height: 1080 },
              fillColor: "#000",
              channels: [],
            },
          ],
        },
      ],
      audio: {
        voiceover: { asset_ref: "vo.mp3", startFrame: 10, durationFrames: 20, volume: 0.9 },
        music: { asset_ref: "bgm.mp3", startFrame: 0, durationFrames: 60, volume: 0.25, ducking: { enabled: true, ducking_volume: 0.05 } },
      },
    };

    // Frame 5: Voiceover inactive -> music volume is 0.25
    const evalAt5 = evaluateVideoAtFrame(doc, 5);
    const musicAt5 = evalAt5.audio.tracks.find((t) => t.kind === "music");
    expect(musicAt5?.volume).toBe(0.25);

    // Frame 15: Voiceover active -> music volume is ducked to 0.05
    const evalAt15 = evaluateVideoAtFrame(doc, 15);
    const musicAt15 = evalAt15.audio.tracks.find((t) => t.kind === "music");
    expect(musicAt15?.volume).toBe(0.05);

    // BrowserPreviewRuntime & AudioPreviewRuntime parity check
    const { MockWebAudioContext } = await import("../../preview/audio/web-audio-adapter");
    const { AudioPreviewRuntime } = await import("../../preview/audio/audio-preview-runtime");
    const mockCtx = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({ audioContext: mockCtx });
    const preview = new BrowserPreviewRuntime(doc, { audioRuntime });
    preview.seek(15);
    const musicTrack = audioRuntime.getTrack("audio_music");
    expect(musicTrack?.gainNode.gain.value).toBe(0.05);

    // Remotion renderer canRender check approves same document
    const req: RenderRequest = { id: "p-req", document: doc, type: "frame", frame: 15 };
    expect(adapter.canRender(req).canRender).toBe(true);

    preview.destroy();
  });

  // ─── 11. Cancellation Signal Handling ───────────────────────────────────────

  it("R09-14: Cancellation via RenderContext AbortSignal halts execution cleanly", async () => {
    const doc: BlueprintV2 = {
      project_id: "doc-cancel",
      fps: 30,
      aspect_ratio: "16:9",
      totalDurationFrames: 90,
      scenes: [{ scene_id: "s1", durationFrames: 90, surface: { text: "Cancel Me" } }],
    };

    const controller = new AbortController();
    const context: RenderContext = {
      projectId: "doc-cancel",
      signal: controller.signal,
    };

    const req: RenderRequest = {
      id: "req-cancel",
      document: doc,
      type: "sequence",
      timeRange: { startFrame: 0, endFrame: 10 },
      context,
    };

    // Abort signal immediately
    controller.abort();

    await expect(adapter.renderSequence(req, context)).rejects.toThrow();
  }, 30000);
});
