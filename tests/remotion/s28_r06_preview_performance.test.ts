/**
 * tests/remotion/s28_r06_preview_performance.test.ts
 * Real Measured Performance Baseline for S28-R06 Browser Live Preview Runtime.
 * Measures and records real execution timings for:
 *   - frame evaluation latency
 *   - preview update (VisualFrame) latency
 *   - seek latency
 *   - continuous playback throughput
 *   - mutation -> preview refresh latency
 *   - representative multi-layer scene latency
 */
import { describe, it, expect } from "vitest";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { buildVisualFrame } from "../../preview/visual-frame";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import { applyMutation } from "../../contracts/mutations";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import type { BlueprintV2 } from "../../contracts/blueprint";

describe("S28-R06 Real Performance Baseline & Metrics", () => {
  // Build a representative multi-layer test project
  const multiLayerScene = instantiateTemplate("rui-title-card", {
    title: "عنوان اختبار الأداء الفعلي",
    subtitle: "قياس زمن الاستجابة في بيئة التشغيل الحية",
    backgroundColor: "#0f172a",
    accentColor: "#38bdf8",
  }, { scene_id: "perf_sc_01", startFrame: 0, durationFrames: 180 });

  const mediaScene = instantiateTemplate("rui-media-frame", {
    media_ref: "asset_perf_benchmark_01",
    caption: "صورة عالية الجودة لاختبار الأداء",
    backgroundColor: "#000000",
  }, { scene_id: "perf_sc_02", startFrame: 150, durationFrames: 180 });

  const perfProject: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: "perf_benchmark_project",
    revision: 1,
    fps: 30,
    aspect_ratio: "16:9",
    scenes: [multiLayerScene.scene, mediaScene.scene],
  };

  it("PERF-01: Real performance baseline across all required preview operations", () => {
    // ─── 1. Frame Evaluation Baseline ──────────────────────────────────────────
    const evalSamples: number[] = [];
    const EVAL_ITERATIONS = 500;

    for (let i = 0; i < EVAL_ITERATIONS; i++) {
      const frame = i % 300;
      const t0 = performance.now();
      evaluateVideoAtFrame(perfProject, frame);
      const t1 = performance.now();
      evalSamples.push(t1 - t0);
    }

    evalSamples.sort((a, b) => a - b);
    const evalAvg = evalSamples.reduce((a, b) => a + b, 0) / evalSamples.length;
    const evalP50 = evalSamples[Math.floor(evalSamples.length * 0.5)];
    const evalP95 = evalSamples[Math.floor(evalSamples.length * 0.95)];

    // ─── 2. Preview Update (buildVisualFrame) Baseline ────────────────────────
    const visualSamples: number[] = [];
    const VISUAL_ITERATIONS = 500;

    for (let i = 0; i < VISUAL_ITERATIONS; i++) {
      const frame = i % 300;
      const t0 = performance.now();
      buildVisualFrame(perfProject, frame);
      const t1 = performance.now();
      visualSamples.push(t1 - t0);
    }

    visualSamples.sort((a, b) => a - b);
    const visualAvg = visualSamples.reduce((a, b) => a + b, 0) / visualSamples.length;
    const visualP50 = visualSamples[Math.floor(visualSamples.length * 0.5)];
    const visualP95 = visualSamples[Math.floor(visualSamples.length * 0.95)];

    // ─── 3. Seek Latency Baseline ─────────────────────────────────────────────
    const runtime = new BrowserPreviewRuntime(perfProject);
    const seekSamples: number[] = [];
    const SEEK_ITERATIONS = 300;

    for (let i = 0; i < SEEK_ITERATIONS; i++) {
      const targetFrame = (i * 17) % 300;
      const t0 = performance.now();
      runtime.seek(targetFrame);
      const t1 = performance.now();
      seekSamples.push(t1 - t0);
    }

    seekSamples.sort((a, b) => a - b);
    const seekAvg = seekSamples.reduce((a, b) => a + b, 0) / seekSamples.length;
    const seekP50 = seekSamples[Math.floor(seekSamples.length * 0.5)];
    const seekP95 = seekSamples[Math.floor(seekSamples.length * 0.95)];

    // ─── 4. Continuous Playback Stepping Throughput ────────────────────────────
    const PLAY_FRAMES = 300;
    const tPlayStart = performance.now();
    for (let f = 0; f < PLAY_FRAMES; f++) {
      runtime.seek(f);
    }
    const tPlayEnd = performance.now();
    const playTotalMs = tPlayEnd - tPlayStart;
    const playFpsThroughput = (PLAY_FRAMES / playTotalMs) * 1000;

    // ─── 5. Mutation -> Preview Refresh Latency ───────────────────────────────
    let currentDoc = JSON.parse(JSON.stringify(perfProject)) as BlueprintV2;
    const titleLayerId = multiLayerScene.layers.find((l) => l.kind === "text")!.layer_id;
    const mutationSamples: number[] = [];
    const MUTATION_ITERATIONS = 100;

    for (let i = 0; i < MUTATION_ITERATIONS; i++) {
      const rev = (currentDoc.revision ?? 1) + 1;
      const t0 = performance.now();
      const res = applyMutation(currentDoc, {
        mutation_id: `perf_mut_${i}`,
        type: "UPDATE_TEXT",
        expected_revision: currentDoc.revision ?? 1,
        target: { scene_id: "perf_sc_01", layer_id: titleLayerId },
        payload: { text: `Updated Title Step #${i}` },
      });
      if (res.success) {
        currentDoc = res.blueprint;
        runtime.updateDocument(res.blueprint, res.changeset);
      }
      const t1 = performance.now();
      mutationSamples.push(t1 - t0);
    }

    mutationSamples.sort((a, b) => a - b);
    const mutAvg = mutationSamples.reduce((a, b) => a + b, 0) / mutationSamples.length;
    const mutP50 = mutationSamples[Math.floor(mutationSamples.length * 0.5)];
    const mutP95 = mutationSamples[Math.floor(mutationSamples.length * 0.95)];

    // ─── 6. Representative Multi-layer Scene Latency ──────────────────────────
    // Measured as single visual frame build on multiLayerScene
    const multiLayerSamples: number[] = [];
    for (let i = 0; i < 200; i++) {
      const t0 = performance.now();
      buildVisualFrame(perfProject, 30);
      const t1 = performance.now();
      multiLayerSamples.push(t1 - t0);
    }
    multiLayerSamples.sort((a, b) => a - b);
    const multiAvg = multiLayerSamples.reduce((a, b) => a + b, 0) / multiLayerSamples.length;
    const multiP50 = multiLayerSamples[Math.floor(multiLayerSamples.length * 0.5)];
    const multiP95 = multiLayerSamples[Math.floor(multiLayerSamples.length * 0.95)];

    // Log the real measured metrics
    console.log("\n=======================================================");
    console.log("   S28-R06 REAL MEASURED PERFORMANCE BASELINE");
    console.log("=======================================================");
    console.log(`1. Frame Evaluation:`);
    console.log(`   - Average: ${evalAvg.toFixed(4)} ms`);
    console.log(`   - p50:     ${evalP50.toFixed(4)} ms`);
    console.log(`   - p95:     ${evalP95.toFixed(4)} ms`);
    console.log(`2. Preview Update (buildVisualFrame):`);
    console.log(`   - Average: ${visualAvg.toFixed(4)} ms`);
    console.log(`   - p50:     ${visualP50.toFixed(4)} ms`);
    console.log(`   - p95:     ${visualP95.toFixed(4)} ms`);
    console.log(`3. Seek Operation:`);
    console.log(`   - Average: ${seekAvg.toFixed(4)} ms`);
    console.log(`   - p50:     ${seekP50.toFixed(4)} ms`);
    console.log(`   - p95:     ${seekP95.toFixed(4)} ms`);
    console.log(`4. Continuous Playback Throughput:`);
    console.log(`   - Total 300 frames: ${playTotalMs.toFixed(2)} ms`);
    console.log(`   - Throughput:       ${playFpsThroughput.toFixed(0)} frames/sec`);
    console.log(`5. Mutation -> Preview Refresh:`);
    console.log(`   - Average: ${mutAvg.toFixed(4)} ms`);
    console.log(`   - p50:     ${mutP50.toFixed(4)} ms`);
    console.log(`   - p95:     ${mutP95.toFixed(4)} ms`);
    console.log(`6. Representative Multi-layer Scene:`);
    console.log(`   - Average: ${multiAvg.toFixed(4)} ms`);
    console.log(`   - p50:     ${multiP50.toFixed(4)} ms`);
    console.log(`   - p95:     ${multiP95.toFixed(4)} ms`);
    console.log("=======================================================\n");

    // Guard assertions against performance regressions
    expect(evalAvg).toBeLessThan(5.0); // well under 5ms threshold
    expect(visualAvg).toBeLessThan(10.0); // well under 10ms threshold
    expect(seekAvg).toBeLessThan(10.0); // well under 10ms threshold
    expect(playFpsThroughput).toBeGreaterThan(120); // must easily exceed 120 fps throughput in pure TS
    expect(mutAvg).toBeLessThan(15.0); // instant mutation response
    expect(multiAvg).toBeLessThan(10.0); // multi-layer rendering under 10ms
  });
});
