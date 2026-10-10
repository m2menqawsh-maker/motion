import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";

describe("S28-R03 RED Tests: Canonical Timeline, Layers, Keyframes & Animation Mathematics", () => {
  const rootDir = path.resolve(__dirname, "../..");

  // ──────────────────────────────────────────────────────────────────────────
  // RED-01: Canonical time ranges have deterministic semantics
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-01: Canonical time ranges have deterministic semantics", async () => {
    const {
      createTimeRange,
      TimeRangeSchema,
      frameToMs,
      msToFrame,
      frameToSeconds,
      secondsToFrame,
      localFrameToGlobal,
      globalFrameToLocal,
    } = await import("../../contracts/timeline");

    const range = createTimeRange(30, 60);
    expect(range.startFrame).toBe(30);
    expect(range.durationFrames).toBe(60);
    expect(range.endFrame).toBe(90);

    // Schema validation invariant: endFrame must equal startFrame + durationFrames
    const valid = TimeRangeSchema.safeParse(range);
    expect(valid.success).toBe(true);

    const invalid = TimeRangeSchema.safeParse({ startFrame: 10, durationFrames: 20, endFrame: 50 });
    expect(invalid.success).toBe(false);

    const negativeDuration = TimeRangeSchema.safeParse({ startFrame: 0, durationFrames: -10, endFrame: -10 });
    expect(negativeDuration.success).toBe(false);

    // Frame/ms conversions with explicit rounding policies across fps (24, 25, 30, 60)
    for (const fps of [24, 25, 30, 60]) {
      expect(frameToMs(0, fps)).toBe(0);
      expect(msToFrame(0, fps)).toBe(0);

      const msFor1Sec = frameToMs(fps, fps);
      expect(msFor1Sec).toBe(1000);
      expect(msToFrame(1000, fps)).toBe(fps);

      expect(frameToSeconds(fps * 2, fps)).toBe(2);
      expect(secondsToFrame(2, fps)).toBe(fps * 2);

      // Rounding policy check
      expect(msToFrame(35, 30, "ROUND")).toBe(1); // 35 * 30 / 1000 = 1.05 -> 1
      expect(msToFrame(35, 30, "FLOOR")).toBe(1);
      expect(msToFrame(35, 30, "CEIL")).toBe(2);
    }

    // Local/Global conversions
    expect(localFrameToGlobal(15, 100)).toBe(115);
    expect(globalFrameToLocal(115, 100)).toBe(15);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-02: Layer model imports zero renderer/UI frameworks
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-02: Layer model imports zero renderer/UI frameworks", () => {
    const modulesToCheck = [
      "contracts/timeline.ts",
      "contracts/layers.ts",
      "contracts/keyframes.ts",
      "contracts/evaluator.ts",
    ];

    for (const modRel of modulesToCheck) {
      const fullPath = path.resolve(rootDir, modRel);
      expect(fs.existsSync(fullPath), `Module '${modRel}' must exist`).toBe(true);

      const content = fs.readFileSync(fullPath, "utf-8");
      expect(content).not.toMatch(/from\s+["']react["']/);
      expect(content).not.toMatch(/from\s+["']react-dom["']/);
      expect(content).not.toMatch(/from\s+["']remotion["']/);
      expect(content).not.toMatch(/from\s+["']@remotion\//);
      expect(content).not.toMatch(/\.tsx["']/);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-03: Keyframes can evaluate LINEAR interpolation
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-03: Keyframes can evaluate LINEAR interpolation", async () => {
    const { evaluateChannelAtFrame } = await import("../../contracts/keyframes");

    const channel = {
      channel_id: "ch_opacity",
      target: "OPACITY" as const,
      keyframes: [
        { keyframe_id: "kf_1", frame: 0, value: 0, interpolation: "LINEAR" as const },
        { keyframe_id: "kf_2", frame: 30, value: 1, interpolation: "LINEAR" as const },
      ],
    };

    expect(evaluateChannelAtFrame(channel, 0, 30)).toBe(0);
    expect(evaluateChannelAtFrame(channel, 15, 30)).toBe(0.5);
    expect(evaluateChannelAtFrame(channel, 30, 30)).toBe(1);
    // Clamping behavior before first and after last keyframe
    expect(evaluateChannelAtFrame(channel, -10, 30)).toBe(0);
    expect(evaluateChannelAtFrame(channel, 50, 30)).toBe(1);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-04: Keyframes can evaluate easing deterministically
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-04: Keyframes can evaluate easing deterministically", async () => {
    const { evaluateEasing, solveCubicBezier } = await import("../../contracts/keyframes");

    // Easing functions monotonic tests at 0, 0.5, 1.0
    expect(evaluateEasing("linear", 0)).toBe(0);
    expect(evaluateEasing("linear", 0.5)).toBe(0.5);
    expect(evaluateEasing("linear", 1)).toBe(1);

    expect(evaluateEasing("ease-in", 0)).toBe(0);
    expect(evaluateEasing("ease-in", 0.5)).toBeLessThan(0.5);
    expect(evaluateEasing("ease-in", 1)).toBe(1);

    expect(evaluateEasing("ease-out", 0)).toBe(0);
    expect(evaluateEasing("ease-out", 0.5)).toBeGreaterThan(0.5);
    expect(evaluateEasing("ease-out", 1)).toBe(1);

    expect(evaluateEasing("ease-in-out", 0)).toBe(0);
    expect(evaluateEasing("ease-in-out", 0.5)).toBe(0.5);
    expect(evaluateEasing("ease-in-out", 1)).toBe(1);

    // Cubic bezier evaluation
    const bezierVal = solveCubicBezier(0.5, 0.42, 0, 0.58, 1);
    expect(bezierVal).toBeCloseTo(0.5, 3);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-05: Spring animation can be evaluated without Remotion loaded
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-05: Spring animation can be evaluated without Remotion loaded", async () => {
    const { evaluateSpring } = await import("../../contracts/keyframes");

    // Pure reference spring test
    const v0 = evaluateSpring(0, 30, { damping: 12, stiffness: 100, mass: 1 });
    expect(v0).toBe(0);

    const v10 = evaluateSpring(10, 30, { damping: 12, stiffness: 100, mass: 1 });
    expect(v10).toBeGreaterThan(1.0); // Overshoot for underdamped spring

    const v30 = evaluateSpring(30, 30, { damping: 12, stiffness: 100, mass: 1 });
    expect(v30).toBeCloseTo(1.0, 2);

    // Critically damped spring
    const vCrit20 = evaluateSpring(20, 30, { damping: 20, stiffness: 100, mass: 1 });
    expect(vCrit20).toBeCloseTo(1.0, 1);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-06: Frame evaluator returns active layers deterministically
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-06: Frame evaluator returns active layers deterministically", async () => {
    const { evaluateVideoAtFrame } = await import("../../contracts/evaluator");

    const sampleProject = {
      blueprint_version: "2.0.0" as const,
      project_id: "test_eval_01",
      fps: 30,
      aspect_ratio: "16:9" as const,
      scenes: [
        {
          scene_id: "sc_1",
          template: "HeaderSubtext",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Scene 1 Text" },
        },
        {
          scene_id: "sc_2",
          template: "HeaderSubtext",
          startFrame: 30,
          durationFrames: 30,
          surface: { text: "Scene 2 Text" },
        },
      ],
    };

    const stateAt10 = evaluateVideoAtFrame(sampleProject, 10);
    expect(stateAt10.frame).toBe(10);
    expect(stateAt10.active_scenes).toEqual(["sc_1"]);
    expect(stateAt10.layers.length).toBeGreaterThan(0);
    const activeLayerIds10 = stateAt10.layers.filter((l) => l.visible).map((l) => l.layer_id);
    expect(activeLayerIds10.some((id) => id.includes("sc_1"))).toBe(true);
    expect(activeLayerIds10.some((id) => id.includes("sc_2"))).toBe(false);

    const stateAt45 = evaluateVideoAtFrame(sampleProject, 45);
    expect(stateAt45.frame).toBe(45);
    expect(stateAt45.active_scenes).toEqual(["sc_2"]);
    const activeLayerIds45 = stateAt45.layers.filter((l) => l.visible).map((l) => l.layer_id);
    expect(activeLayerIds45.some((id) => id.includes("sc_2"))).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-07: Duplicate stable IDs fail closed
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-07: Duplicate stable IDs fail closed", async () => {
    const { validateLayerHierarchy } = await import("../../contracts/layers");

    const duplicateLayers: any[] = [
      {
        layer_id: "layer_dup",
        kind: "text",
        time_range: { startFrame: 0, durationFrames: 30, endFrame: 30 },
        transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
        opacity: 1,
        visible: true,
        z_index: 0,
        text: "Layer 1",
        typography: { fontFamily: "Cairo", fontSize: 40 },
      },
      {
        layer_id: "layer_dup",
        kind: "text",
        time_range: { startFrame: 0, durationFrames: 30, endFrame: 30 },
        transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
        opacity: 1,
        visible: true,
        z_index: 1,
        text: "Layer 2",
        typography: { fontFamily: "Cairo", fontSize: 40 },
      },
    ];

    const result = validateLayerHierarchy(duplicateLayers);
    expect(result.ok).toBe(false);
    expect(result.errors.some((e: string) => e.includes("duplicate layer_id"))).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-08: Invalid group cycles fail closed
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-08: Invalid group cycles fail closed", async () => {
    const { validateLayerHierarchy } = await import("../../contracts/layers");

    const cyclicLayers: any[] = [
      {
        layer_id: "grp_A",
        kind: "group",
        parent_id: "grp_B",
        time_range: { startFrame: 0, durationFrames: 30, endFrame: 30 },
        transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
        opacity: 1,
        visible: true,
        z_index: 0,
        children_ids: ["grp_B"],
      },
      {
        layer_id: "grp_B",
        kind: "group",
        parent_id: "grp_A",
        time_range: { startFrame: 0, durationFrames: 30, endFrame: 30 },
        transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
        opacity: 1,
        visible: true,
        z_index: 1,
        children_ids: ["grp_A"],
      },
    ];

    const result = validateLayerHierarchy(cyclicLayers);
    expect(result.ok).toBe(false);
    expect(result.errors.some((e: string) => e.includes("cycle"))).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-09: Non-30fps fixture evaluates correctly
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-09: Non-30fps fixture evaluates correctly", async () => {
    const { parseCanonicalVideo } = await import("../../contracts/canonical-video");
    const { evaluateVideoAtFrame } = await import("../../contracts/evaluator");

    const fixturePath = path.resolve(rootDir, "tests/fixtures/canonical/07_aspect_1_1_non_30fps.json");
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));

    const parsed = parseCanonicalVideo(raw);
    expect(parsed.fps).toBe(24);

    const state = evaluateVideoAtFrame(parsed, 24);
    expect(state.frame).toBe(24);
    expect(state.fps).toBe(24);
    expect(state.timeMs).toBe(1000); // 24 frames at 24 fps = 1000ms
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-10: Legacy canonical fixture remains compatible
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-10: Legacy canonical fixture remains compatible", async () => {
    const { parseCanonicalVideo } = await import("../../contracts/canonical-video");
    const { normalizeCanonicalVideo } = await import("../../contracts/normalization");
    const { evaluateVideoAtFrame } = await import("../../contracts/evaluator");

    const fixturePath = path.resolve(rootDir, "tests/fixtures/canonical/01_simple_text_scene.json");
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));

    const parsed = parseCanonicalVideo(raw);
    const normalized = normalizeCanonicalVideo({ blueprint: parsed });

    expect(normalized.timeline).toBeDefined();
    expect(normalized.timeline.tracks.length).toBeGreaterThan(0);

    const evaluated = evaluateVideoAtFrame(normalized, 15);
    expect(evaluated.frame).toBe(15);
    expect(evaluated.layers.length).toBeGreaterThan(0);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-11: Evaluation succeeds with React and Remotion forcibly unavailable
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-11: Evaluation succeeds with React and Remotion forcibly unavailable", () => {
    const isolationScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = ["react", "react-dom", "remotion", "@remotion/transitions", "@remotion/core", "@remotion/cli"];

      Module.prototype.require = function(id) {
        for (const b of blocked) {
          if (id === b || id.startsWith(b + "/")) {
            throw new Error("ISOLATION_VIOLATION_MODULE_LOADED: " + id);
          }
        }
        return origRequire.apply(this, arguments);
      };

      const fs = require("node:fs");
      const path = require("node:path");

      async function run() {
        const { parseCanonicalVideo } = await import("./contracts/canonical-video.ts");
        const { normalizeCanonicalVideo } = await import("./contracts/normalization.ts");
        const { evaluateVideoAtFrame } = await import("./contracts/evaluator.ts");
        const { evaluateSpring } = await import("./contracts/keyframes.ts");
        const { calculateCanonicalDuration } = await import("./contracts/timeline.ts");

        const fixturePath = path.resolve("./tests/fixtures/canonical/05_multi_scenes_effects_transitions.json");
        const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));

        const parsed = parseCanonicalVideo(raw);
        const normalized = normalizeCanonicalVideo({ blueprint: parsed });
        const evaluated = evaluateVideoAtFrame(normalized, 15);
        const springVal = evaluateSpring(10, 30, { damping: 12, stiffness: 100, mass: 1 });
        const duration = calculateCanonicalDuration(normalized.scenes, normalized.scenes.map(s => s.transition).filter(Boolean));

        if (!evaluated || !springVal || duration <= 0) {
          throw new Error("Evaluation failed");
        }

        process.stdout.write(JSON.stringify({ status: "PASS", evaluatedLayers: evaluated.layers.length, springVal, duration }));
      }

      run().catch((err) => {
        console.error(err);
        process.exit(1);
      });
    `;

    const tsxBin = path.resolve(rootDir, "node_modules/.bin/tsx");
    const result = fs.existsSync(tsxBin)
      ? execFileSync(process.execPath, [tsxBin, "-e", isolationScript], {
          cwd: rootDir,
          encoding: "utf-8",
        })
      : execFileSync("npx", ["--no-install", "tsx", "-e", isolationScript], {
          cwd: rootDir,
          encoding: "utf-8",
        });

    const parsedOutput = JSON.parse(result);
    expect(parsedOutput.status).toBe("PASS");
    expect(parsedOutput.evaluatedLayers).toBeGreaterThan(0);
  }, 20000);

  // ──────────────────────────────────────────────────────────────────────────
  // RED-12: Canonical duration calculation is deterministic
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-12: Canonical duration calculation is deterministic", async () => {
    const { calculateCanonicalDuration } = await import("../../contracts/timeline");

    const scenesNoTransition = [
      { startFrame: 0, durationFrames: 30 },
      { startFrame: 30, durationFrames: 45 },
    ];
    expect(calculateCanonicalDuration(scenesNoTransition)).toBe(75);

    // With 15 frame overlap transition
    const scenesWithOverlap = [
      { startFrame: 0, durationFrames: 30, transition: { durationFrames: 10, overlap_semantics: "overlap" as const } },
      { startFrame: 30, durationFrames: 45 },
    ];
    // Overlap: 30 + 45 - 10 = 65
    expect(calculateCanonicalDuration(scenesWithOverlap, { transitionMode: "overlap" })).toBe(65);

    // Insert transition: 30 + 10 + 45 = 85
    const scenesWithInsert = [
      { startFrame: 0, durationFrames: 30, transition: { durationFrames: 10, overlap_semantics: "insert" as const } },
      { startFrame: 30, durationFrames: 45 },
    ];
    expect(calculateCanonicalDuration(scenesWithInsert, { transitionMode: "insert" })).toBe(85);
  });
});
