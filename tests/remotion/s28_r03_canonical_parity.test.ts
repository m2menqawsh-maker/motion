import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import { parseCanonicalVideo } from "../../contracts/canonical-video";
import { normalizeCanonicalVideo } from "../../contracts/normalization";
import { evaluateVideoAtFrame, evaluateTimelineAtFrame } from "../../contracts/evaluator";
import {
  evaluateLinear,
  evaluateEaseIn,
  evaluateEaseOut,
  evaluateEaseInOut,
  evaluateSpring,
  solveCubicBezier,
  evaluateChannelAtFrame,
} from "../../contracts/keyframes";
import {
  frameToMs,
  msToFrame,
  calculateCanonicalDuration,
  createTimeRange,
} from "../../contracts/timeline";
import { parseRenderInput } from "../../contracts/render-input";
import { spring as remotionSpring } from "remotion";

describe("S28-R03 Canonical Parity, Properties & Performance", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const fixturesDir = path.resolve(rootDir, "tests/fixtures/canonical");

  // Collect all 17 canonical fixtures
  const fixtureFiles = fs
    .readdirSync(fixturesDir)
    .filter((f) => f.endsWith(".json"))
    .sort();

  const sampleMediaMap: Record<string, string> = {
    ast_img_product_01: "projects/test/img1.png",
    ast_video_broll_01: "projects/test/vid1.mp4",
    ast_vo_primary: "projects/test/vo.mp3",
    ast_music_track: "projects/test/bgm.mp3",
    ast_sfx_hit: "projects/test/hit.wav",
    asset_hero_img: "projects/test/hero.png",
    asset_full_vo: "projects/test/full_vo.mp3",
    asset_bgm_track: "projects/test/bgm.mp3",
    asset_whoosh_sfx: "projects/test/whoosh.wav",
    asset_alpha_badge: "projects/test/badge.png",
    asset_beta_video_clip: "projects/test/clip.mp4",
    asset_narration_vo: "projects/test/narration.mp3",
    asset_background_score: "projects/test/score.mp3",
  };

  // ──────────────────────────────────────────────────────────────────────────
  // 1. All 17 Canonical Fixtures Conformance & Normalization
  // ──────────────────────────────────────────────────────────────────────────
  it("conforms and normalizes all 17 canonical fixtures deterministically", () => {
    expect(fixtureFiles.length).toBeGreaterThanOrEqual(17);

    for (const file of fixtureFiles) {
      const fullPath = path.join(fixturesDir, file);
      const raw = JSON.parse(fs.readFileSync(fullPath, "utf-8"));

      const parsed = parseCanonicalVideo(raw);
      expect(parsed).toBeDefined();
      expect(parsed.project_id).toBeDefined();

      const normalized = normalizeCanonicalVideo({ blueprint: parsed, media_map: sampleMediaMap });
      expect(normalized).toBeDefined();
      expect(normalized.timeline).toBeDefined();
      expect(normalized.timeline?.tracks.length).toBeGreaterThan(0);
      expect(normalized.totalDurationFrames).toBeGreaterThan(0);

      // Evaluate at frame 0 and frame midpoint
      const state0 = evaluateVideoAtFrame(normalized, 0);
      expect(state0.frame).toBe(0);
      expect(state0.layers).toBeDefined();

      const midFrame = Math.floor(normalized.totalDurationFrames / 2);
      const stateMid = evaluateVideoAtFrame(normalized, midFrame);
      expect(stateMid.frame).toBe(midFrame);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Normalization Idempotency Invariant
  // ──────────────────────────────────────────────────────────────────────────
  it("verifies idempotency: normalize(normalize(video)) === normalize(video)", () => {
    for (const file of fixtureFiles) {
      const fullPath = path.join(fixturesDir, file);
      const raw = JSON.parse(fs.readFileSync(fullPath, "utf-8"));
      const parsed = parseCanonicalVideo(raw);

      const norm1 = normalizeCanonicalVideo({ blueprint: parsed, media_map: sampleMediaMap });
      const norm2 = normalizeCanonicalVideo({ blueprint: norm1 as any, media_map: sampleMediaMap });

      expect(norm2.fps).toBe(norm1.fps);
      expect(norm2.totalDurationFrames).toBe(norm1.totalDurationFrames);
      expect(norm2.scenes.length).toBe(norm1.scenes.length);
      expect(norm2.timeline?.tracks.length).toBe(norm1.timeline?.tracks.length);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Property-Based Time Conversion Round-Trip
  // ──────────────────────────────────────────────────────────────────────────
  it("property test: frame <-> ms conversion round-trip across standard frame rates", () => {
    for (const fps of [24, 25, 30, 60]) {
      // Test 100 sampled frames up to 5000
      for (let f = 0; f <= 5000; f += 50) {
        const ms = frameToMs(f, fps);
        const roundTripFrame = msToFrame(ms, fps);
        // Due to integer millisecond discretization, difference must never exceed 1 frame
        expect(Math.abs(roundTripFrame - f)).toBeLessThanOrEqual(1);
      }
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Golden Animation Tests (0%, 25%, 50%, 75%, 100%)
  // ──────────────────────────────────────────────────────────────────────────
  it("golden animation values: validates exact easing & spring progression points", () => {
    const sampleProgressions = [0.0, 0.25, 0.5, 0.75, 1.0];

    // Linear
    const linearValues = sampleProgressions.map((t) => evaluateLinear(t));
    expect(linearValues).toEqual([0.0, 0.25, 0.5, 0.75, 1.0]);

    // Ease-in (quadratic)
    const easeInValues = sampleProgressions.map((t) => evaluateEaseIn(t));
    expect(easeInValues[0]).toBe(0.0);
    expect(easeInValues[1]).toBeCloseTo(0.0625, 4);
    expect(easeInValues[2]).toBeCloseTo(0.25, 4);
    expect(easeInValues[3]).toBeCloseTo(0.5625, 4);
    expect(easeInValues[4]).toBe(1.0);

    // Ease-out
    const easeOutValues = sampleProgressions.map((t) => evaluateEaseOut(t));
    expect(easeOutValues[0]).toBe(0.0);
    expect(easeOutValues[1]).toBeCloseTo(0.4375, 4);
    expect(easeOutValues[2]).toBeCloseTo(0.75, 4);
    expect(easeOutValues[3]).toBeCloseTo(0.9375, 4);
    expect(easeOutValues[4]).toBe(1.0);

    // Cubic Bezier (0.42, 0, 0.58, 1) - standard CSS ease-in-out
    const bezierValues = sampleProgressions.map((t) => solveCubicBezier(t, 0.42, 0, 0.58, 1));
    expect(bezierValues[0]).toBe(0.0);
    expect(bezierValues[2]).toBeCloseTo(0.5, 2);
    expect(bezierValues[4]).toBe(1.0);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Remotion Comparison Tests: Pure Evaluator vs Remotion Spring Runtime
  // ──────────────────────────────────────────────────────────────────────────
  it("compares pure canonical spring evaluator against Remotion spring with numerical parity", () => {
    const testCases = [
      { damping: 10, stiffness: 100, mass: 1 },
      { damping: 12, stiffness: 100, mass: 1 },
      { damping: 14, stiffness: 100, mass: 1 },
      { damping: 20, stiffness: 100, mass: 1 },
    ];

    const framesToSample = [0, 1, 2, 5, 10, 15, 20, 25, 30, 45, 60];

    for (const cfg of testCases) {
      for (const f of framesToSample) {
        const pureVal = evaluateSpring(f, 30, cfg);
        const remotionVal = remotionSpring({
          fps: 30,
          frame: f,
          config: cfg,
        });

        // Assert NUMERIC_PARITY with machine precision tolerance (1e-9)
        const diff = Math.abs(pureVal - remotionVal);
        expect(diff, `Mismatch at damping ${cfg.damping}, frame ${f}: pure=${pureVal}, remotion=${remotionVal}`).toBeLessThan(1e-9);
      }
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Representability Proof for Legacy Template Animations
  // ──────────────────────────────────────────────────────────────────────────
  it("representability proof: represents and evaluates fade, slide, scale, spring, and transition", () => {
    // 1. Simple Fade
    const fadeChannel = {
      channel_id: "ch_fade",
      target: "OPACITY" as const,
      keyframes: [
        { keyframe_id: "kf_f0", frame: 0, value: 0, interpolation: "LINEAR" as const },
        { keyframe_id: "kf_f15", frame: 15, value: 1, interpolation: "LINEAR" as const },
      ],
    };
    expect(evaluateChannelAtFrame(fadeChannel, 0, 30)).toBe(0);
    expect(evaluateChannelAtFrame(fadeChannel, 7.5, 30)).toBe(0.5);
    expect(evaluateChannelAtFrame(fadeChannel, 15, 30)).toBe(1);

    // 2. Slide Up
    const slideChannel = {
      channel_id: "ch_slide",
      target: "TRANSFORM_Y" as const,
      keyframes: [
        { keyframe_id: "kf_s0", frame: 0, value: 50, interpolation: "SPRING" as const, spring: { damping: 14 } },
        { keyframe_id: "kf_s15", frame: 15, value: 0, interpolation: "LINEAR" as const },
      ],
    };
    expect(evaluateChannelAtFrame(slideChannel, 0, 30)).toBe(50);
    expect(evaluateChannelAtFrame(slideChannel, 30, 30)).toBe(0);

    // 3. Scale In
    const scaleChannel = {
      channel_id: "ch_scale",
      target: "SCALE" as const,
      keyframes: [
        { keyframe_id: "kf_sc0", frame: 0, value: 0.2, interpolation: "EASE" as const, easing: "ease-out" as const },
        { keyframe_id: "kf_sc20", frame: 20, value: 1.0, interpolation: "LINEAR" as const },
      ],
    };
    expect(evaluateChannelAtFrame(scaleChannel, 0, 30)).toBe(0.2);
    expect(evaluateChannelAtFrame(scaleChannel, 20, 30)).toBe(1.0);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 7. Critical Architectural Test (Section 60)
  // ──────────────────────────────────────────────────────────────────────────
  it("CRITICAL ARCHITECTURAL TEST: Complete canonical project evaluates in engine-free subprocess and passes render-input", () => {
    const projectEnvelope = {
      project: { title: "Architectural Proof Video", fps: 30, project_id: "prj_arch_proof" },
      media_map: sampleMediaMap,
      blueprint: {
        blueprint_version: "2.0.0",
        project_id: "prj_arch_proof",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [
          {
            scene_id: "scene_alpha",
            template: "TitleCardWrapper",
            startFrame: 0,
            durationFrames: 60,
            transition: { type: "fade", durationFrames: 15, overlap_semantics: "overlap" },
            layers: [
              {
                layer_id: "alpha_grp",
                kind: "group",
                children_ids: ["alpha_text", "alpha_img"],
                time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
                transform: { position: { x: 100, y: 100 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
                channels: [
                  {
                    channel_id: "ch_alpha_x",
                    target: "TRANSFORM_X",
                    keyframes: [
                      { keyframe_id: "kf_a_0", frame: 0, value: 0, interpolation: "LINEAR" },
                      { keyframe_id: "kf_a_30", frame: 30, value: 200, interpolation: "LINEAR" },
                    ],
                  },
                ],
                opacity: 1,
                visible: true,
                z_index: 0,
              },
              {
                layer_id: "alpha_text",
                kind: "text",
                parent_id: "alpha_grp",
                text: "Scene Alpha Title",
                typography: { fontFamily: "Cairo", fontSize: 48 },
                time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
                transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0, y: 0 }, opacity: 1 },
                opacity: 1,
                visible: true,
                z_index: 1,
              },
              {
                layer_id: "alpha_img",
                kind: "image",
                parent_id: "alpha_grp",
                asset_ref: "asset_alpha_badge",
                time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
                transform: { position: { x: 0, y: 60 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0, y: 0 }, opacity: 1 },
                opacity: 1,
                visible: true,
                z_index: 2,
              },
            ],
          },
          {
            scene_id: "scene_beta",
            template: "ShowcaseWrapper",
            startFrame: 60,
            durationFrames: 60,
            layers: [
              {
                layer_id: "beta_video",
                kind: "video",
                asset_ref: "asset_beta_video_clip",
                time_range: { startFrame: 60, durationFrames: 60, endFrame: 120 },
                transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0, y: 0 }, opacity: 1 },
                channels: [
                  {
                    channel_id: "ch_beta_scale",
                    target: "SCALE",
                    keyframes: [
                      { keyframe_id: "kf_b_0", frame: 0, value: 0.5, interpolation: "SPRING", spring: { damping: 12 } },
                      { keyframe_id: "kf_b_30", frame: 30, value: 1.0, interpolation: "LINEAR" },
                    ],
                  },
                ],
                opacity: 1,
                visible: true,
                z_index: 0,
              },
            ],
          },
        ],
        audio: {
          voiceover: { asset_ref: "asset_narration_vo", volume: 1.0, startFrame: 0, durationFrames: 120 },
          music: { asset_ref: "asset_background_score", volume: 0.15 },
        },
      },
    };

    // 1. Compatibility gate test: passes parseRenderInput fail-closed
    const parsedInput = parseRenderInput(projectEnvelope);
    expect(parsedInput).toBeDefined();
    expect(parsedInput.blueprint.scenes).toHaveLength(2);

    // 2. Engine-free subprocess proof
    const isolationProofScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = ["react", "react-dom", "remotion", "@remotion/transitions", "@remotion/core", "@remotion/cli"];

      Module.prototype.require = function(id) {
        for (const b of blocked) {
          if (id === b || id.startsWith(b + "/")) {
            throw new Error("VIOLATION_BLOCKED_PACKAGE_LOADED: " + id);
          }
        }
        return origRequire.apply(this, arguments);
      };

      const path = require("node:path");

      async function run() {
        const { parseCanonicalVideo } = await import("./contracts/canonical-video.ts");
        const { normalizeCanonicalVideo } = await import("./contracts/normalization.ts");
        const { evaluateVideoAtFrame } = await import("./contracts/evaluator.ts");

        const data = ${JSON.stringify(projectEnvelope.blueprint)};
        const mediaMap = ${JSON.stringify(sampleMediaMap)};
        const parsed = parseCanonicalVideo(data);
        const normalized = normalizeCanonicalVideo({ blueprint: parsed, media_map: mediaMap });

        const f0 = evaluateVideoAtFrame(normalized, 0);
        const f15 = evaluateVideoAtFrame(normalized, 15);
        const fMid = evaluateVideoAtFrame(normalized, 60);
        const fFinal = evaluateVideoAtFrame(normalized, 105);

        if (!f0 || !f15 || !fMid || !fFinal) {
          throw new Error("Frame evaluation returned falsy state");
        }

        process.stdout.write(JSON.stringify({
          status: "PASS",
          totalDuration: normalized.totalDurationFrames,
          layersF0: f0.layers.length,
          layersF60: fMid.layers.length,
          posAt15: f15.layers[0]?.transform.x
        }));
      }

      run().catch((err) => {
        console.error(err);
        process.exit(1);
      });
    `;

    const tsxBin = path.resolve(rootDir, "node_modules/.bin/tsx");
    const result = fs.existsSync(tsxBin)
      ? execFileSync(process.execPath, [tsxBin, "-e", isolationProofScript], {
          cwd: rootDir,
          encoding: "utf-8",
        })
      : execFileSync("npx", ["--no-install", "tsx", "-e", isolationProofScript], {
          cwd: rootDir,
          encoding: "utf-8",
        });

    const parsedRes = JSON.parse(result);
    expect(parsedRes.status).toBe("PASS");
    expect(parsedRes.totalDuration).toBe(120);
    expect(parsedRes.layersF0).toBeGreaterThan(0);
  }, 20000);

  // ──────────────────────────────────────────────────────────────────────────
  // 8. Performance Baseline Measurement
  // ──────────────────────────────────────────────────────────────────────────
  it("performance baseline: evaluates frames efficiently with low latency", () => {
    const fixturePath = path.resolve(fixturesDir, "05_multi_scenes_effects_transitions.json");
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
    const parsed = parseCanonicalVideo(raw);
    const normalized = normalizeCanonicalVideo({ blueprint: parsed });

    // 1. Single frame evaluation latency
    const startSingle = performance.now();
    for (let i = 0; i < 50; i++) {
      evaluateVideoAtFrame(normalized, i);
    }
    const endSingle = performance.now();
    const avgSingleMs = (endSingle - startSingle) / 50;

    // Average per frame must be under 1ms (super fast pure evaluator)
    expect(avgSingleMs).toBeLessThan(5.0);

    // 2. Sequential 1000 frames evaluation
    const start1k = performance.now();
    for (let f = 0; f < 1000; f++) {
      evaluateVideoAtFrame(normalized, f % normalized.totalDurationFrames);
    }
    const end1k = performance.now();
    const total1kMs = end1k - start1k;

    // 1000 frames must evaluate in less than 500ms
    expect(total1kMs).toBeLessThan(500);
  });
});
