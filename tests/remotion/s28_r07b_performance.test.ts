/**
 * tests/remotion/s28_r07b_performance.test.ts
 * Real Performance Baseline & Metrics Suite for S28-R07B: Preview Fidelity, Cache & Proxy System.
 * 
 * Measures:
 *   - Capability Resolution Latency (resolvePreviewFidelity)
 *   - Cache Lookup (hit & miss) Latency
 *   - Small Proxy Generation Latency
 *   - Selective Invalidation Throughput
 *   - Live Proxy Replacement Latency
 *   - Memory Footprint for 100 Cached Proxy Entries
 */

import { describe, it, expect } from "vitest";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { resolvePreviewFidelity } from "../../contracts/preview-fidelity";
import {
  createPreviewProxyRequest,
  type PreviewProxyArtifact,
} from "../../contracts/preview-proxy";
import {
  PreviewProxyCache,
  type ProxyDependencyInfo,
} from "../../preview/proxy/proxy-cache";
import { PreviewProxyCoordinator } from "../../preview/proxy/proxy-coordinator";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import {
  RendererRegistry,
  createMockRendererAdapter,
} from "../../contracts/renderer";
import { defaultTransform } from "../../contracts/layers";
import { createTimeRange } from "../../contracts/timeline";

describe("S28-R07B Real Performance Baseline & Metrics", () => {
  it("PERF-01: Measures real execution performance across all required preview proxy operations", async () => {
    // 1. Setup Document
    const testDoc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "perf-proxy-project",
      revision: 1,
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc-1",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          layers: [
            {
              layer_id: "txt-1",
              kind: "text",
              text: "Performance Title",
              transform: defaultTransform(),
              time_range: createTimeRange(0, 60),
              typography: { fontFamily: "Cairo", fontSize: 48, fillColor: "#fff" },
              visible: true,
              opacity: 1,
            },
          ],
        },
        {
          scene_id: "sc-2",
          template: "rui-map-flight",
          startFrame: 60,
          durationFrames: 60,
          layers: [],
        },
      ],
    };

    // ─── Metric 1: Capability Resolution Latency ─────────────────────────────
    const resIterations = 1000;
    const resStart = performance.now();
    for (let i = 0; i < resIterations; i++) {
      resolvePreviewFidelity(testDoc);
    }
    const resTotalMs = performance.now() - resStart;
    const resAvgMs = resTotalMs / resIterations;

    // ─── Metric 2: Cache Hit & Miss Latency ──────────────────────────────────
    const cache = new PreviewProxyCache({ maxEntries: 200, maxBytes: 100 * 1024 * 1024 });

    const dummyArtifact = (id: string, rev: number): PreviewProxyArtifact => ({
      id: `art-${id}`,
      requestId: `req-${id}`,
      cacheKey: `key-${id}`,
      project_id: "perf-proj",
      canonical_revision: rev,
      entity: { type: "scene", sceneId: `sc-${id}` },
      timeRange: { startFrame: 0, endFrame: 30 },
      width: 960,
      height: 540,
      fps: 30,
      format: "png",
      rendererId: "mock-fast",
      output: {
        dataUrl: "data:image/png;base64,PERF_FRAME",
        buffer: new Uint8Array(4096), // 4KB per proxy
      },
      createdAt: Date.now(),
      sizeBytes: 4096,
    });

    const dummyDeps = (id: string): ProxyDependencyInfo => ({
      projectId: "perf-proj",
      canonicalRevision: 1,
      contentFingerprint: `fp-${id}`,
      sceneIds: [`sc-${id}`],
      layerIds: [`ly-${id}`],
      assetIds: [],
      timeRange: { startFrame: 0, endFrame: 30 },
      requiredCapabilities: ["frame_rendering"],
    });

    // Populate 100 cached proxy entries
    const initial100BytesBefore = process.memoryUsage().heapUsed;
    for (let i = 0; i < 100; i++) {
      cache.set(`key-${i}`, dummyArtifact(`${i}`, 1), dummyDeps(`${i}`));
    }
    const initial100BytesAfter = process.memoryUsage().heapUsed;
    const memoryFootprint100Entries = Math.max(0, initial100BytesAfter - initial100BytesBefore);

    // Measure Cache Hit Latency
    const hitIterations = 10000;
    const hitStart = performance.now();
    for (let i = 0; i < hitIterations; i++) {
      cache.get("key-50");
    }
    const hitTotalMs = performance.now() - hitStart;
    const hitAvgMs = hitTotalMs / hitIterations;

    // Measure Cache Miss Latency
    const missIterations = 10000;
    const missStart = performance.now();
    for (let i = 0; i < missIterations; i++) {
      cache.get("key-non-existent");
    }
    const missTotalMs = performance.now() - missStart;
    const missAvgMs = missTotalMs / missIterations;

    // ─── Metric 3: Small Proxy Generation Latency ────────────────────────────
    const registry = new RendererRegistry();
    const mockFastAdapter = createMockRendererAdapter({
      id: "mock-fast-adapter",
      capabilities: ["map", "webgl", "frame_rendering"],
      onRenderFrame: async (req) => ({
        ok: true,
        requestId: req.id,
        rendererId: "mock-fast-adapter",
        type: "frame",
        output: {
          dataUrl: "data:image/png;base64,FAST_FRAME",
          buffer: new Uint8Array(1024),
        },
        metrics: { renderTimeMs: 1.5, evaluatedFrames: 1 },
      }),
    });
    registry.register(mockFastAdapter);

    const coordinator = new PreviewProxyCoordinator({ registry, cache });
    const genRequest = createPreviewProxyRequest({
      project_id: "perf-proxy-project",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "sc-gen" },
      requiredCapabilities: ["map", "webgl"],
      contentFragment: testDoc.scenes[1],
    });

    const genStart = performance.now();
    const genArtifact = await coordinator.requestProxy(genRequest, testDoc, 1);
    const genTotalMs = performance.now() - genStart;

    // ─── Metric 4: Selective Invalidation Latency ─────────────────────────────
    const invStart = performance.now();
    const invCount = cache.invalidateBySceneId("sc-50");
    const invTotalMs = performance.now() - invStart;

    // ─── Metric 5: Live Proxy Replacement Latency ─────────────────────────────
    const runtime = new BrowserPreviewRuntime(testDoc, { proxyCoordinator: coordinator });
    const replStart = performance.now();
    runtime.applyProxyArtifact(genArtifact);
    const replTotalMs = performance.now() - replStart;

    runtime.destroy();

    // Log Formatted Performance Baseline Table
    console.log("\n=======================================================");
    console.log("   S28-R07B REAL MEASURED PREVIEW PROXY PERFORMANCE");
    console.log("=======================================================");
    console.log(`1. Capability Resolution (resolvePreviewFidelity):`);
    console.log(`   - Average: ${resAvgMs.toFixed(4)} ms (${Math.round(1000 / resAvgMs)} ops/sec)`);
    console.log(`2. Cache Lookup (Hit):`);
    console.log(`   - Average: ${hitAvgMs.toFixed(5)} ms (${Math.round(1000 / hitAvgMs)} lookups/sec)`);
    console.log(`3. Cache Lookup (Miss):`);
    console.log(`   - Average: ${missAvgMs.toFixed(5)} ms`);
    console.log(`4. Small Proxy Generation (Dispatch -> Registry -> Adapter):`);
    console.log(`   - Total:   ${genTotalMs.toFixed(3)} ms`);
    console.log(`5. Selective Invalidation:`);
    console.log(`   - Latency: ${invTotalMs.toFixed(4)} ms (invalidated ${invCount} entry)`);
    console.log(`6. Live Proxy Replacement (applyProxyArtifact -> re-eval):`);
    console.log(`   - Latency: ${replTotalMs.toFixed(3)} ms`);
    console.log(`7. Memory Footprint for 100 Cached Proxy Entries:`);
    console.log(`   - Total:   ~${(cache.getStats().totalBytes / 1024).toFixed(1)} KB artifact payload`);
    console.log(`   - Entries: ${cache.size()} entries in LRU store`);
    console.log("=======================================================\n");

    // Invariants
    expect(resAvgMs).toBeLessThan(1.0); // Sub-millisecond capability resolution
    expect(hitAvgMs).toBeLessThan(0.05); // Microsecond cache hit
    expect(missAvgMs).toBeLessThan(0.05);
    expect(genTotalMs).toBeLessThan(50);
    expect(replTotalMs).toBeLessThan(10);
    expect(cache.size()).toBeGreaterThanOrEqual(99);
  });
});
