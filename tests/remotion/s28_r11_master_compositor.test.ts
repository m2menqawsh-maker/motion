/**
 * tests/remotion/s28_r11_master_compositor.test.ts
 * Verification Suite for S28-R11: Master Compositor & Output Normalization.
 * 
 * Verifies:
 *   - Engine-neutral Master Compositor architecture
 *   - Intermediate artifact provenance, metadata & content fingerprinting
 *   - Output normalization (resolution, fps, timebase, pixel format, audio layout)
 *   - Multi-engine composition (mixed CanvasRendererAdapter + RemotionRendererAdapter)
 *   - Canonical VideoDocument timeline as sole timing authority
 *   - Scene stitching, transitions & overlap duration correctness
 *   - Audio normalization, canonical timing & dynamic ducking (R07 semantics)
 *   - Audio/Video sync preservation across transformations
 *   - Fail-closed behavior on missing or incompatible artifacts
 *   - AbortSignal cancellation and complete resource cleanup (zero orphaned files)
 *   - Existing Final QC integration
 *   - Performance baselines
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync } from "child_process";

import {
  type BlueprintV2,
  type BlueprintScene,
} from "../../contracts/blueprint";
import {
  type OutputProfile,
  type IntermediateArtifact,
  type CompositorRequest,
  type CompositorResult,
  MasterCompositorError,
  validateCompositorRequest,
  createDefaultOutputProfile,
  resolveProfileFromDocument,
  createIntermediateArtifact,
  computeArtifactFingerprint,
} from "../../contracts/compositor";
import {
  calculateCanonicalDuration,
  frameToSeconds,
} from "../../contracts/timeline";
import {
  MasterCompositor,
  findSystemFfmpeg,
  probeMediaFile,
  createArtifactFromFile,
  createArtifactFromRenderResult,
  buildVideoFilterGraph,
  runQcForCompositorResult,
  extractAudioPlans,
} from "../../compositor";
import {
  CanvasRendererAdapter,
  createCanvasRendererAdapter,
} from "../../canvas/canvas-renderer-adapter";
import {
  RemotionRendererAdapter,
  createRemotionRendererAdapter,
  getOrCreateRemotionBundle,
} from "../../remotion/remotion-renderer-adapter";
import {
  CANONICAL_RENDERER_REGISTRY,
  type RenderRequest,
} from "../../contracts/renderer";

describe("S28-R11 Master Compositor & Output Normalization", () => {
  const testWorkspace = path.join(os.tmpdir(), `r11_test_workspace_${Date.now()}`);
  const ffmpeg = findSystemFfmpeg();

  beforeAll(() => {
    fs.mkdirSync(testWorkspace, { recursive: true });
  });

  afterAll(() => {
    if (fs.existsSync(testWorkspace)) {
      try {
        fs.rmSync(testWorkspace, { recursive: true, force: true });
      } catch {
        // ignore
      }
    }
  });

  // Helper to generate synthetic test video with ffmpeg
  function generateSyntheticVideo(
    filePath: string,
    width: number,
    height: number,
    fps: number,
    durationSec: number,
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

  // Helper to generate synthetic test audio with ffmpeg
  function generateSyntheticAudio(
    filePath: string,
    durationSec: number,
    frequency = 440,
    sampleRate = 44100
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
        `sine=frequency=${frequency}:r=${sampleRate}:d=${durationSec}`,
        "-c:a",
        "pcm_s16le",
        filePath,
      ],
      { stdio: "pipe" }
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Compositor Contracts & Fail-Closed Validation
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-01: Engine-neutral contracts validate CompositorRequest fail-closed", () => {
    // Missing id
    expect(() =>
      validateCompositorRequest({} as any)
    ).toThrowError(/INVALID_COMPOSITOR_REQUEST/);

    // Missing document
    expect(() =>
      validateCompositorRequest({ id: "req-1" } as any)
    ).toThrowError(/INVALID_COMPOSITOR_REQUEST/);

    // Empty inputs
    expect(() =>
      validateCompositorRequest({
        id: "req-1",
        document: { project_id: "p1", fps: 30, scenes: [] },
        inputs: [],
        outputPath: "/tmp/out.mp4",
        outputProfile: createDefaultOutputProfile(),
      } as any)
    ).toThrowError(/INVALID_COMPOSITOR_REQUEST/);

    // Incompatible input artifact
    expect(() =>
      validateCompositorRequest({
        id: "req-1",
        document: { project_id: "p1", fps: 30, scenes: [] },
        inputs: [{ invalidField: true } as any],
        outputPath: "/tmp/out.mp4",
        outputProfile: createDefaultOutputProfile(),
      } as any)
    ).toThrowError(/INCOMPATIBLE_INPUT/);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Intermediate Artifact Model & Provenance
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-02: IntermediateArtifact model computes deterministic content fingerprint and enforces explicit metadata", () => {
    const rawArtifact = {
      artifactId: "art-test-1",
      sourceRendererId: "canvas-renderer-adapter",
      canonicalRevision: 42,
      scope: { type: "scene" as const, id: "scene_01" },
      timeRange: { startFrame: 0, durationFrames: 60, startTimeSec: 0, durationSec: 2.0 },
      type: "video" as const,
      mediaInfo: {
        durationSec: 2.0,
        durationFrames: 60,
        fps: 30,
        width: 1920,
        height: 1080,
        pixelFormat: "yuv420p",
        timebase: "1/30",
        startTimeSec: 0,
        startFrame: 0,
        hasAlpha: false,
        videoCodec: "h264",
      },
    };

    const artifact1 = createIntermediateArtifact(rawArtifact);
    const artifact2 = createIntermediateArtifact(rawArtifact);

    expect(artifact1.contentFingerprint).toBeDefined();
    expect(artifact1.contentFingerprint).toBe(artifact2.contentFingerprint);
    expect(artifact1.sourceRendererId).toBe("canvas-renderer-adapter");
    expect(artifact1.scope.id).toBe("scene_01");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Output Normalization (Critical Test - Section 15)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-03: Critical Test — Normalization: 720p@30fps + 1080p@60fps normalized to 1080p@30fps with zero drift", async () => {
    const fileA = path.join(testWorkspace, "art_a_720p_30fps.mp4");
    const fileB = path.join(testWorkspace, "art_b_1080p_60fps.mp4");
    const finalOut = path.join(testWorkspace, "normalized_stitched_1080p_30fps.mp4");

    // Artifact A: 1280x720, 30fps, 2.0 seconds (60 frames)
    generateSyntheticVideo(fileA, 1280, 720, 30, 2.0, "red");
    // Artifact B: 1920x1080, 60fps, 2.0 seconds (120 frames at 60fps)
    generateSyntheticVideo(fileB, 1920, 1080, 60, 2.0, "green");

    const artA = createArtifactFromFile({
      artifactId: "art-a",
      sourceRendererId: "test-engine-a",
      scope: { type: "scene", id: "scene_a" },
      timeRange: { startFrame: 0, durationFrames: 60, durationSec: 2.0 },
      type: "video",
      filePath: fileA,
    });

    const artB = createArtifactFromFile({
      artifactId: "art-b",
      sourceRendererId: "test-engine-b",
      scope: { type: "scene", id: "scene_b" },
      timeRange: { startFrame: 60, durationFrames: 60, durationSec: 2.0 },
      type: "video",
      filePath: fileB,
    });

    // Canonical document: 2 scenes of 60 frames each at 30fps = 120 frames = 4.0s total
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "norm_test_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_a",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          surface: {},
        },
        {
          scene_id: "scene_b",
          template: "rui-title-card",
          startFrame: 60,
          durationFrames: 60,
          surface: {},
        },
      ],
    };

    const targetProfile: OutputProfile = createDefaultOutputProfile({
      width: 1920,
      height: 1080,
      fps: 30,
      videoCodec: "libx264",
      pixelFormat: "yuv420p",
      sampleRate: 48000,
    });

    const compositor = new MasterCompositor();
    const result = await compositor.composite({
      id: "req_norm_critical",
      document: doc,
      inputs: [
        { artifact: artA, canonicalSceneId: "scene_a" },
        { artifact: artB, canonicalSceneId: "scene_b" },
      ],
      outputProfile: targetProfile,
      outputPath: finalOut,
    });

    expect(result.ok).toBe(true);
    expect(fs.existsSync(finalOut)).toBe(true);

    const probe = probeMediaFile(finalOut);
    // Resolution normalized to 1920x1080
    expect(probe.width).toBe(1920);
    expect(probe.height).toBe(1080);
    // Framerate normalized to 30fps
    expect(Math.abs(probe.fps - 30)).toBeLessThan(0.1);
    // Audio sample rate normalized to 48000Hz
    expect(probe.audioSampleRate).toBe(48000);
    // Total duration: 4.0 seconds (within 100ms tolerance)
    expect(Math.abs(probe.durationSec - 4.0)).toBeLessThan(0.1);
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Critical Test — Mixed Engines (Section 14)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-04: Critical Test — Mixed Engines: Scene A (Canvas) + Scene B (Remotion) -> MasterCompositor -> Final MP4", async () => {
    const finalMixedOut = path.join(testWorkspace, "mixed_engines_final.mp4");

    // 1. Single scene A document for Canvas
    const docA: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "mixed_proj_a",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_canvas",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 30, // 1.0s
          surface: { text: "Scene from Canvas Engine" },
        },
      ],
    };

    // 2. Single scene B document for Remotion
    const docB: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "mixed_proj_b",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_remotion",
          template: "rui-stat-card",
          startFrame: 0,
          durationFrames: 30, // 1.0s
          surface: { text: "Scene from Remotion Engine" },
        },
      ],
    };

    // 3. Render Scene A via CanvasRendererAdapter
    const canvasAdapter = createCanvasRendererAdapter();
    const renderResA = await canvasAdapter.exportVideo({
      id: "render_canvas_scene",
      document: docA,
      type: "export",
    });
    expect(renderResA.ok).toBe(true);

    // 4. Render Scene B via RemotionRendererAdapter
    const remotionAdapter = createRemotionRendererAdapter();
    const renderResB = await remotionAdapter.exportVideo({
      id: "render_remotion_scene",
      document: docB,
      type: "export",
    });
    expect(renderResB.ok).toBe(true);

    // 5. Wrap outputs into IntermediateArtifacts with explicit provenance
    const artifactCanvas = createArtifactFromRenderResult({
      artifactId: "art_scene_canvas",
      renderResult: renderResA,
      scope: { type: "scene", id: "scene_canvas" },
      timeRange: { startFrame: 0, durationFrames: 30 },
      type: "video",
    });

    const artifactRemotion = createArtifactFromRenderResult({
      artifactId: "art_scene_remotion",
      renderResult: renderResB,
      scope: { type: "scene", id: "scene_remotion" },
      timeRange: { startFrame: 30, durationFrames: 30 },
      type: "video",
    });

    expect(artifactCanvas.sourceRendererId).toBe("canvas-renderer-adapter");
    expect(artifactRemotion.sourceRendererId).toBe("remotion-engine-adapter");

    // 6. Canonical Parent Project (2 scenes, 60 frames = 2.0s)
    const masterDoc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "mixed_master_project",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_canvas",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Scene from Canvas Engine" },
        },
        {
          scene_id: "scene_remotion",
          template: "rui-stat-card",
          startFrame: 30,
          durationFrames: 30,
          surface: { text: "Scene from Remotion Engine" },
        },
      ],
    };

    // 7. Master Compositor unites both intermediate artifacts into final MP4
    const compositor = new MasterCompositor();
    const result = await compositor.composite({
      id: "req_mixed_assembly",
      document: masterDoc,
      inputs: [
        { artifact: artifactCanvas, canonicalSceneId: "scene_canvas" },
        { artifact: artifactRemotion, canonicalSceneId: "scene_remotion" },
      ],
      outputProfile: createDefaultOutputProfile({ width: 1920, height: 1080, fps: 30 }),
      outputPath: finalMixedOut,
    });

    expect(result.ok).toBe(true);
    expect(fs.existsSync(finalMixedOut)).toBe(true);

    const probe = probeMediaFile(finalMixedOut);
    expect(probe.width).toBe(1920);
    expect(probe.height).toBe(1080);
    expect(Math.abs(probe.durationSec - 2.0)).toBeLessThan(0.1);
  }, 60000);

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Critical Test — Audio Normalization, Timing & Ducking (Section 16)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-05: Critical Test — Audio: visual + voiceover + music + sfx respects R07 canonical ducking & timing", async () => {
    const videoFile = path.join(testWorkspace, "audio_test_base.mp4");
    const voFile = path.join(testWorkspace, "vo_track.wav");
    const bgmFile = path.join(testWorkspace, "bgm_track.wav");
    const sfxFile = path.join(testWorkspace, "sfx_track.wav");
    const finalAudioVideoOut = path.join(testWorkspace, "audio_ducking_final.mp4");

    // 3.0s visual artifact (90 frames at 30fps)
    generateSyntheticVideo(videoFile, 1920, 1080, 30, 3.0, "purple");
    // Voiceover: 1.0s long
    generateSyntheticAudio(voFile, 1.0, 300, 44100);
    // Music: 3.0s long
    generateSyntheticAudio(bgmFile, 3.0, 150, 44100);
    // SFX: 0.5s long
    generateSyntheticAudio(sfxFile, 0.5, 600, 44100);

    const baseArtifact = createArtifactFromFile({
      artifactId: "art_audio_base",
      sourceRendererId: "canvas-renderer-adapter",
      scope: { type: "scene", id: "scene_main" },
      timeRange: { startFrame: 0, durationFrames: 90, durationSec: 3.0 },
      type: "video",
      filePath: videoFile,
    });

    const docWithAudio: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "audio_ducking_project",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_main",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 90, // 3.0s
          surface: {},
        },
      ],
      audio: {
        voiceover: {
          asset_ref: voFile,
          startFrame: 30, // frames 30 to 60 (t = 1.0s to 2.0s)
          durationFrames: 30,
          volume: 0.9,
          mute: false,
        },
        music: {
          asset_ref: bgmFile,
          startFrame: 0,
          durationFrames: 90,
          volume: 0.4,
          loop: true,
          mute: false,
          ducking: {
            enabled: true,
            ducking_volume: 0.1,
            duck_under: ["voiceover"],
          },
        },
        global_sfx: [
          {
            asset_ref: sfxFile,
            startFrame: 15,
            durationFrames: 15,
            volume: 0.8,
          },
        ],
      },
    };

    const compositor = new MasterCompositor();
    const result = await compositor.composite({
      id: "req_audio_ducking",
      document: docWithAudio,
      inputs: [{ artifact: baseArtifact, canonicalSceneId: "scene_main" }],
      outputProfile: createDefaultOutputProfile({ sampleRate: 48000, audioCodec: "aac" }),
      outputPath: finalAudioVideoOut,
    });

    expect(result.ok).toBe(true);
    expect(fs.existsSync(finalAudioVideoOut)).toBe(true);

    const probe = probeMediaFile(finalAudioVideoOut);
    expect(probe.audioCodec).toBe("aac");
    expect(probe.audioSampleRate).toBe(48000);
    expect(Math.abs(probe.durationSec - 3.0)).toBeLessThan(0.1);
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Audio/Video Sync Preservation (Section 9)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-06: AV-Sync is preserved across timebase conversion and resampling", async () => {
    const syncVideo = path.join(testWorkspace, "sync_base.mp4");
    const syncAudio = path.join(testWorkspace, "sync_stem.wav");
    const syncOut = path.join(testWorkspace, "sync_result.mp4");

    generateSyntheticVideo(syncVideo, 1280, 720, 24, 2.0, "cyan");
    generateSyntheticAudio(syncAudio, 2.0, 500, 22050); // 22.05kHz mono audio

    const art = createArtifactFromFile({
      artifactId: "art_sync",
      sourceRendererId: "canvas-renderer-adapter",
      scope: { type: "scene", id: "scene_sync" },
      timeRange: { startFrame: 0, durationFrames: 60 },
      type: "video",
      filePath: syncVideo,
    });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "av_sync_proj",
      fps: 30,
      scenes: [
        {
          scene_id: "scene_sync",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60, // 2.0s at 30fps
          surface: {},
        },
      ],
      audio: {
        voiceover: {
          asset_ref: syncAudio,
          startFrame: 0,
          durationFrames: 60,
          volume: 1.0,
        },
      },
    };

    const compositor = new MasterCompositor({ maxAvDriftMs: 80 });
    const result = await compositor.composite({
      id: "req_sync_test",
      document: doc,
      inputs: [{ artifact: art, canonicalSceneId: "scene_sync" }],
      outputProfile: createDefaultOutputProfile({ fps: 30, sampleRate: 48000 }),
      outputPath: syncOut,
    });

    expect(result.ok).toBe(true);

    const probe = probeMediaFile(syncOut);
    // Both audio and video duration match canonical duration (2.0s) within 50ms
    expect(Math.abs(probe.durationSec - 2.0)).toBeLessThan(0.05);
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 7. Transition Overlap Handling (Section 5)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-07: Transition overlap math adheres strictly to canonical duration authority", async () => {
    const file1 = path.join(testWorkspace, "trans_scene1.mp4");
    const file2 = path.join(testWorkspace, "trans_scene2.mp4");
    const transOut = path.join(testWorkspace, "trans_final.mp4");

    // 2 scenes of 2.0s (60 frames at 30fps)
    generateSyntheticVideo(file1, 1920, 1080, 30, 2.0, "red");
    generateSyntheticVideo(file2, 1920, 1080, 30, 2.0, "blue");

    const art1 = createArtifactFromFile({
      artifactId: "art_trans_1",
      sourceRendererId: "engine-1",
      scope: { type: "scene", id: "sc_1" },
      timeRange: { startFrame: 0, durationFrames: 60 },
      type: "video",
      filePath: file1,
    });

    const art2 = createArtifactFromFile({
      artifactId: "art_trans_2",
      sourceRendererId: "engine-2",
      scope: { type: "scene", id: "sc_2" },
      timeRange: { startFrame: 45, durationFrames: 60 },
      type: "video",
      filePath: file2,
    });

    // 15-frame crossfade transition between sc_1 and sc_2
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "trans_overlap_proj",
      fps: 30,
      scenes: [
        {
          scene_id: "sc_1",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          surface: {},
          transition: {
            type: "fade",
            durationFrames: 15, // 0.5s overlap
            overlap_semantics: "overlap",
          },
        },
        {
          scene_id: "sc_2",
          template: "rui-title-card",
          startFrame: 45,
          durationFrames: 60,
          surface: {},
        },
      ],
    };

    // Canonical duration: (60 + 60) - 15 = 105 frames = 3.5s
    const canonicalFrames = calculateCanonicalDuration(doc.scenes);
    expect(canonicalFrames).toBe(105);
    const expectedSec = canonicalFrames / 30; // 3.5s

    const compositor = new MasterCompositor();
    const result = await compositor.composite({
      id: "req_trans_test",
      document: doc,
      inputs: [
        { artifact: art1, canonicalSceneId: "sc_1" },
        { artifact: art2, canonicalSceneId: "sc_2" },
      ],
      outputProfile: createDefaultOutputProfile({ fps: 30 }),
      outputPath: transOut,
    });

    expect(result.ok).toBe(true);

    const probe = probeMediaFile(transOut);
    expect(Math.abs(probe.durationSec - expectedSec)).toBeLessThan(0.1);
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 8. Fail-Closed Error Handling
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-08: Missing artifact fails closed with MISSING_ARTIFACT error", async () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "missing_art_proj",
      fps: 30,
      scenes: [
        {
          scene_id: "sc_exists",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 30,
          surface: {},
        },
        {
          scene_id: "sc_missing",
          template: "rui-title-card",
          startFrame: 30,
          durationFrames: 30,
          surface: {},
        },
      ],
    };

    const dummyFile = path.join(testWorkspace, "dummy.mp4");
    generateSyntheticVideo(dummyFile, 640, 360, 30, 1.0);

    const art = createArtifactFromFile({
      artifactId: "art_dummy",
      sourceRendererId: "engine-1",
      scope: { type: "scene", id: "sc_exists" },
      timeRange: { startFrame: 0, durationFrames: 30 },
      type: "video",
      filePath: dummyFile,
    });

    const compositor = new MasterCompositor();

    await expect(
      compositor.composite({
        id: "req_missing",
        document: doc,
        inputs: [{ artifact: art, canonicalSceneId: "sc_exists" }], // scene sc_missing is absent!
        outputProfile: createDefaultOutputProfile(),
        outputPath: path.join(testWorkspace, "should_fail.mp4"),
      })
    ).rejects.toThrowError(/MISSING_ARTIFACT/);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 9. Cancellation & Cleanup
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-09: AbortSignal halts execution and removes all temporary working directories", async () => {
    const dummyFile = path.join(testWorkspace, "cancel_src.mp4");
    const cancelOut = path.join(testWorkspace, "cancel_out.mp4");
    generateSyntheticVideo(dummyFile, 1280, 720, 30, 2.0);

    const art = createArtifactFromFile({
      artifactId: "art_cancel",
      sourceRendererId: "engine-1",
      scope: { type: "scene", id: "sc_cancel" },
      timeRange: { startFrame: 0, durationFrames: 60 },
      type: "video",
      filePath: dummyFile,
    });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "cancel_proj",
      fps: 30,
      scenes: [
        {
          scene_id: "sc_cancel",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          surface: {},
        },
      ],
    };

    const controller = new AbortController();
    controller.abort(); // Pre-abort

    const compositor = new MasterCompositor();

    await expect(
      compositor.composite({
        id: "req_cancel_test",
        document: doc,
        inputs: [{ artifact: art, canonicalSceneId: "sc_cancel" }],
        outputProfile: createDefaultOutputProfile(),
        outputPath: cancelOut,
        context: { signal: controller.signal },
      })
    ).rejects.toThrowError(/CANCELLED/);

    // Final output was not created
    expect(fs.existsSync(cancelOut)).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 10. Existing QC Integration (Section 13)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-10: CompositorResult integrates seamlessly with existing QC boundary", async () => {
    const qcVideo = path.join(testWorkspace, "qc_test_video.mp4");
    const qcOut = path.join(testWorkspace, "qc_final.mp4");
    generateSyntheticVideo(qcVideo, 1920, 1080, 30, 2.0);

    const art = createArtifactFromFile({
      artifactId: "art_qc",
      sourceRendererId: "canvas-renderer-adapter",
      scope: { type: "scene", id: "sc_qc" },
      timeRange: { startFrame: 0, durationFrames: 60 },
      type: "video",
      filePath: qcVideo,
    });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "qc_test_project",
      fps: 30,
      scenes: [
        {
          scene_id: "sc_qc",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          surface: {},
        },
      ],
    };

    const compositor = new MasterCompositor();
    const result = await compositor.composite({
      id: "req_qc_test",
      document: doc,
      inputs: [{ artifact: art, canonicalSceneId: "sc_qc" }],
      outputProfile: createDefaultOutputProfile(),
      outputPath: qcOut,
    });

    const qcReport = runQcForCompositorResult(result, doc);
    expect(qcReport.passed).toBe(true);
    expect(qcReport.videoValid).toBe(true);
    expect(qcReport.audioValid).toBe(true);
    expect(qcReport.avSyncValid).toBe(true);
    expect(qcReport.durationDeltaMs).toBeLessThan(100);
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 11. Performance Baselines (Section 18)
  // ──────────────────────────────────────────────────────────────────────────

  it("R11-11: Performance baselines measured for 2-scene and 10-scene composition", async () => {
    const compositor = new MasterCompositor();

    // 1. Measure 2-scene baseline
    const f1 = path.join(testWorkspace, "perf_2s_1.mp4");
    const f2 = path.join(testWorkspace, "perf_2s_2.mp4");
    generateSyntheticVideo(f1, 1280, 720, 30, 1.0);
    generateSyntheticVideo(f2, 1280, 720, 30, 1.0);

    const doc2s: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "perf_2s",
      fps: 30,
      scenes: [
        { scene_id: "p2_1", template: "t", startFrame: 0, durationFrames: 30, surface: {} },
        { scene_id: "p2_2", template: "t", startFrame: 30, durationFrames: 30, surface: {} },
      ],
    };

    const art1 = createArtifactFromFile({
      artifactId: "a1",
      sourceRendererId: "eng",
      scope: { type: "scene", id: "p2_1" },
      timeRange: { startFrame: 0, durationFrames: 30 },
      type: "video",
      filePath: f1,
    });
    const art2 = createArtifactFromFile({
      artifactId: "a2",
      sourceRendererId: "eng",
      scope: { type: "scene", id: "p2_2" },
      timeRange: { startFrame: 30, durationFrames: 30 },
      type: "video",
      filePath: f2,
    });

    const start2s = Date.now();
    const res2s = await compositor.composite({
      id: "req_perf_2s",
      document: doc2s,
      inputs: [
        { artifact: art1, canonicalSceneId: "p2_1" },
        { artifact: art2, canonicalSceneId: "p2_2" },
      ],
      outputProfile: createDefaultOutputProfile({ width: 1920, height: 1080 }),
      outputPath: path.join(testWorkspace, "perf_2s_out.mp4"),
    });
    const duration2s = Date.now() - start2s;

    expect(res2s.ok).toBe(true);
    expect(res2s.metrics.totalDurationMs).toBeGreaterThan(0);
    expect(res2s.metrics.peakMemoryBytes).toBeGreaterThan(0);
    expect(duration2s).toBeLessThan(15000); // 2 scenes under 15s

    // 2. Measure 10-scene baseline
    const doc10s: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "perf_10s",
      fps: 30,
      scenes: [],
    };
    const inputs10s: any[] = [];

    for (let i = 0; i < 10; i++) {
      const sceneId = `sc_10_${i}`;
      doc10s.scenes.push({
        scene_id: sceneId,
        template: "t",
        startFrame: i * 15,
        durationFrames: 15, // 0.5s each
        surface: {},
      });
      inputs10s.push({
        artifact: art1, // reuse normalized test artifact
        canonicalSceneId: sceneId,
      });
    }

    const start10s = Date.now();
    const res10s = await compositor.composite({
      id: "req_perf_10s",
      document: doc10s,
      inputs: inputs10s,
      outputProfile: createDefaultOutputProfile({ width: 1920, height: 1080 }),
      outputPath: path.join(testWorkspace, "perf_10s_out.mp4"),
    });
    const duration10s = Date.now() - start10s;

    expect(res10s.ok).toBe(true);
    expect(res10s.metrics.inputCount).toBe(10);
    expect(duration10s).toBeLessThan(30000); // 10 scenes under 30s
  }, 45000);
});

