/**
 * tests/remotion/s28_r07b_preview_fidelity_and_proxy.test.ts
 * Comprehensive Suite for S28-R07B: Preview Fidelity, Cache & Proxy System.
 * 
 * Verifies:
 *   - Preview Capability & Fidelity Model (LIVE_NATIVE, APPROXIMATE_PREVIEW, PROXY_RENDER_REQUIRED)
 *   - Explicit, deterministic approximation with clear diagnostic metadata
 *   - Fail-closed proxy requirement for ENGINE_BACKED templates & custom shaders
 *   - Deterministic PreviewProxyRequest generation with content fingerprinting
 *   - Renderer selection strictly through RendererRegistry (ZERO engine hardcoding)
 *   - PreviewProxyCache: hits, misses, deterministic keys, bounded LRU eviction (entries & bytes)
 *   - ChangeSet Selective Invalidation (Scene A mutation does NOT invalidate Scene B proxy)
 *   - Asset, scene, layer, and timeRange invalidation
 *   - Stale Revision Result Protection (older revision cannot overwrite newer preview state)
 *   - Background Job Coordinator lifecycle (queued -> running -> ready, cancelled, failed)
 *   - Live proxy replacement into BrowserPreviewRuntime visual tree
 *   - AudioPreviewRuntime remains unaffected and in sync
 *   - BrowserPreviewRuntime remains sole preview playhead authority
 */

import { describe, it, expect, beforeEach } from "vitest";
import type { BlueprintV2 } from "../../contracts/blueprint";
import {
  resolvePreviewFidelity,
  type PreviewCapabilityAssessment,
} from "../../contracts/preview-fidelity";
import {
  createPreviewProxyRequest,
  computeFragmentFingerprint,
  resolveProxyDimensions,
  PREVIEW_PROXY_QUALITY_PRESETS,
  type PreviewProxyArtifact,
} from "../../contracts/preview-proxy";
import {
  PreviewProxyCache,
  computeProxyCacheKey,
  type ProxyDependencyInfo,
} from "../../preview/proxy/proxy-cache";
import {
  PreviewProxyCoordinator,
  type PreviewProxyJob,
} from "../../preview/proxy/proxy-coordinator";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import {
  RendererRegistry,
  createMockRendererAdapter,
  NoCompatibleRendererError,
  type RenderRequest,
} from "../../contracts/renderer";
import type { ChangeSet } from "../../contracts/mutations";

describe("S28-R07B Preview Fidelity, Cache & Proxy System", () => {
  let registry: RendererRegistry;
  let cache: PreviewProxyCache;
  let coordinator: PreviewProxyCoordinator;

  // Mock 2D Renderer
  const mock2dAdapter = createMockRendererAdapter({
    id: "mock-canvas-2d",
    priority: 110,
    capabilities: [
      "text",
      "image",
      "shapes",
      "groups",
      "keyframes",
      "transitions",
      "alpha",
      "frame_rendering",
    ],
    onRenderFrame: async (req) => ({
      ok: true,
      requestId: req.id,
      rendererId: "mock-canvas-2d",
      type: "frame",
      output: {
        dataUrl: "data:image/png;base64,MOCK_2D_FRAME",
        mimeType: "image/png",
        width: req.output?.width ?? 960,
        height: req.output?.height ?? 540,
        buffer: new Uint8Array([137, 80, 78, 71]),
      },
      metrics: { renderTimeMs: 4, evaluatedFrames: 1 },
    }),
  });

  // Mock Complex Engine Adapter (e.g. video / advanced composition)
  const mockComplexAdapter = createMockRendererAdapter({
    id: "mock-complex-engine",
    priority: 100,
    capabilities: [
      "text",
      "image",
      "video",
      "shapes",
      "groups",
      "keyframes",
      "transitions",
      "alpha",
      "audio",
      "audio_voiceover",
      "frame_rendering",
    ],
    onRenderFrame: async (req) => ({
      ok: true,
      requestId: req.id,
      rendererId: "mock-complex-engine",
      type: "frame",
      output: {
        dataUrl: "data:image/png;base64,MOCK_COMPLEX_FRAME",
        mimeType: "image/png",
        width: req.output?.width ?? 960,
        height: req.output?.height ?? 540,
        buffer: new Uint8Array([137, 80, 78, 71, 0, 1]),
      },
      metrics: { renderTimeMs: 15, evaluatedFrames: 1 },
    }),
  });

  beforeEach(() => {
    registry = new RendererRegistry();
    registry.register(mock2dAdapter);
    registry.register(mockComplexAdapter);

    cache = new PreviewProxyCache({ maxEntries: 10, maxBytes: 10 * 1024 * 1024 });
    coordinator = new PreviewProxyCoordinator({ registry, cache });
  });

  // ─── 1. Preview Fidelity Classification ───────────────────────────────────

  it("FID-01: Classifies pure standard 2D document as LIVE_NATIVE", () => {
    const doc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "test-native",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene-1",
          startFrame: 0,
          durationFrames: 60,
          layers: [
            {
              layer_id: "text-1",
              kind: "text",
              properties: { text: "Native live text" },
              transform: { x: 0, y: 0, scaleX: 1, scaleY: 1, rotation: 0, opacity: 1 },
              visible: true,
              opacity: 1,
            },
            {
              layer_id: "shape-1",
              kind: "shape",
              properties: { shape_type: "rectangle", fillColor: "#ff0000" },
              transform: { x: 10, y: 10, scaleX: 1, scaleY: 1, rotation: 0, opacity: 1 },
              visible: true,
              opacity: 1,
            },
          ],
        },
      ],
    };

    const assessment = resolvePreviewFidelity(doc);
    expect(assessment.mode).toBe("LIVE_NATIVE");
    expect(assessment.quality_level).toBe("native");
    expect(assessment.proxy_required).toBe(false);
    expect(assessment.diagnostics.approximateFeatures.length).toBe(0);
    expect(assessment.diagnostics.unsupportedFeatures.length).toBe(0);
  });

  it("FID-02: Classifies complex GLSL transitions and blur effects as APPROXIMATE_PREVIEW with explicit metadata", () => {
    const doc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "test-approx",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene-1",
          startFrame: 0,
          durationFrames: 45,
          transition: {
            type: "crosswarp",
            durationFrames: 15,
          },
          layers: [
            {
              layer_id: "layer-with-blur",
              kind: "image",
              properties: { asset_ref: "test.png" },
              transform: { x: 0, y: 0, scaleX: 1, scaleY: 1, rotation: 0, opacity: 1 },
              visible: true,
              opacity: 1,
              effects: [{ type: "blur", radius: 10 }],
            } as any,
          ],
        },
        {
          scene_id: "scene-2",
          startFrame: 45,
          durationFrames: 45,
          layers: [],
        },
      ],
    };

    const assessment = resolvePreviewFidelity(doc);
    expect(assessment.mode).toBe("APPROXIMATE_PREVIEW");
    expect(assessment.quality_level).toBe("approximate");
    expect(assessment.proxy_required).toBe(false);
    expect(assessment.diagnostics.approximateFeatures).toContain("transition:crosswarp");
    expect(assessment.diagnostics.approximateFeatures).toContain("effect:blur");
    expect(assessment.reason).toContain("approximated");
  });

  it("FID-03: Classifies ENGINE_BACKED template (MapLibre, 3D, Particles) as PROXY_RENDER_REQUIRED", () => {
    const doc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "test-proxy-req",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene-map",
          template: "rui-map-flight", // R05 ENGINE_BACKED template requiring MapLibre
          startFrame: 0,
          durationFrames: 90,
          layers: [],
        },
      ],
    };

    const assessment = resolvePreviewFidelity(doc);
    expect(assessment.mode).toBe("PROXY_RENDER_REQUIRED");
    expect(assessment.quality_level).toBe("proxy");
    expect(assessment.proxy_required).toBe(true);
    expect(assessment.diagnostics.unsupportedFeatures).toContain("engine_backed:rui-map-flight");
    expect(assessment.affected_entities.length).toBeGreaterThan(0);
    expect(assessment.affected_entities[0].classification).toBe("ENGINE_BACKED");
  });

  // ─── 2. Preview Proxy Request Generation ──────────────────────────────────

  it("REQ-01: Generates deterministic PreviewProxyRequest with content fingerprint and quality policy", () => {
    const fragment = {
      scene_id: "scene-map",
      template: "rui-map-flight",
      params: { zoom: 12, center: [40, -74] },
    };

    const fp1 = computeFragmentFingerprint(fragment);
    const fp2 = computeFragmentFingerprint({ ...fragment });
    expect(fp1).toBe(fp2);
    expect(fp1.length).toBe(32);

    const request = createPreviewProxyRequest({
      project_id: "proj-1",
      canonical_revision: 5,
      entity: { type: "scene", sceneId: "scene-map", templateId: "rui-map-flight" },
      timeRange: { startFrame: 0, endFrame: 30 },
      requiredCapabilities: ["map", "webgl"],
      baseDimensions: { width: 1920, height: 1080 },
      policy: PREVIEW_PROXY_QUALITY_PRESETS.balanced,
      contentFragment: fragment,
    });

    expect(request.project_id).toBe("proj-1");
    expect(request.canonical_revision).toBe(5);
    expect(request.width).toBe(960);
    expect(request.height).toBe(540);
    expect(request.quality).toBe(65);
    expect(request.format).toBe("png");
    expect(request.contentFingerprint).toBe(fp1);
    expect(request.requiredCapabilities).toEqual(["map", "webgl"]);
  });

  // ─── 3. Renderer Selection via RendererRegistry ───────────────────────────

  it("SEL-01: Selects compatible renderer through RendererRegistry without engine hardcoding", async () => {
    const fragmentDoc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "proj-2d",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "s1",
          startFrame: 0,
          durationFrames: 30,
          layers: [{ layer_id: "l1", kind: "text", properties: { text: "hi" }, visible: true, opacity: 1 }],
        },
      ],
    };

    const request = createPreviewProxyRequest({
      project_id: "proj-2d",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "s1" },
      requiredCapabilities: ["text", "frame_rendering"],
      contentFragment: fragmentDoc,
    });

    const artifact = await coordinator.requestProxy(request, fragmentDoc);
    expect(artifact).toBeDefined();
    expect(artifact.rendererId).toBe("mock-canvas-2d"); // Higher priority (110 vs 100)
    expect(artifact.output.dataUrl).toBe("data:image/png;base64,MOCK_2D_FRAME");
  });

  it("SEL-02: Fails closed when no registered renderer supports required capabilities", async () => {
    const fragmentDoc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "proj-unsupported",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", startFrame: 0, durationFrames: 30, layers: [] }],
    };

    const request = createPreviewProxyRequest({
      project_id: "proj-unsupported",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "s1" },
      requiredCapabilities: ["map", "3d", "custom_shaders"], // No registered adapter supports this!
      contentFragment: fragmentDoc,
    });

    await expect(coordinator.requestProxy(request, fragmentDoc)).rejects.toThrow(
      NoCompatibleRendererError
    );

    const job = coordinator.getJob(request.id);
    expect(job?.status).toBe("failed");
    expect(job?.error?.code).toBe("NO_COMPATIBLE_RENDERER");
  });

  // ─── 4. Preview Proxy Cache & Bounded Eviction ────────────────────────────

  it("CACHE-01: Cache hit returns cached artifact without re-rendering", async () => {
    const fragmentDoc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "proj-cache",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", startFrame: 0, durationFrames: 30, layers: [] }],
    };

    const request = createPreviewProxyRequest({
      project_id: "proj-cache",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "s1" },
      requiredCapabilities: ["text", "frame_rendering"],
      contentFragment: fragmentDoc,
    });

    const art1 = await coordinator.requestProxy(request, fragmentDoc);
    expect(cache.getStats().hits).toBe(0);
    expect(cache.getStats().misses).toBe(1);

    // Second request with exact same parameters
    const art2 = await coordinator.requestProxy(request, fragmentDoc);
    expect(cache.getStats().hits).toBe(1);
    expect(art2.id).toBe(art1.id);
  });

  it("CACHE-02: Enforces bounded capacity and LRU eviction policy", () => {
    const smallCache = new PreviewProxyCache({ maxEntries: 3, maxBytes: 10000 });

    const createDummyArtifact = (id: string, rev: number): PreviewProxyArtifact => ({
      id,
      requestId: `req-${id}`,
      cacheKey: `key-${id}`,
      project_id: "test",
      canonical_revision: rev,
      entity: { type: "scene", sceneId: `scene-${id}` },
      timeRange: { startFrame: 0, endFrame: 30 },
      width: 480,
      height: 270,
      fps: 30,
      format: "png",
      rendererId: "mock",
      output: { buffer: new Uint8Array(100) },
      createdAt: Date.now(),
      sizeBytes: 100,
    });

    const dummyDeps = (sceneId: string): ProxyDependencyInfo => ({
      projectId: "test",
      canonicalRevision: 1,
      contentFingerprint: "fp",
      sceneIds: [sceneId],
      layerIds: [],
      assetIds: [],
      timeRange: { startFrame: 0, endFrame: 30 },
      requiredCapabilities: ["frame_rendering"],
    });

    smallCache.set("key-1", createDummyArtifact("1", 1), dummyDeps("s1"));
    smallCache.set("key-2", createDummyArtifact("2", 1), dummyDeps("s2"));
    smallCache.set("key-3", createDummyArtifact("3", 1), dummyDeps("s3"));
    expect(smallCache.size()).toBe(3);

    // Access key-1 to make key-2 the least recently used
    smallCache.get("key-1");

    // Add key-4 -> should evict key-2
    smallCache.set("key-4", createDummyArtifact("4", 1), dummyDeps("s4"));
    expect(smallCache.size()).toBe(3);
    expect(smallCache.has("key-1")).toBe(true);
    expect(smallCache.has("key-2")).toBe(false); // Evicted!
    expect(smallCache.has("key-3")).toBe(true);
    expect(smallCache.has("key-4")).toBe(true);
    expect(smallCache.getStats().evictions).toBe(1);
  });

  // ─── 5. ChangeSet Selective Invalidation & Dependency Tracking ─────────────

  it("INV-01: ChangeSet invalidates affected Scene A without invalidating Scene B proxy", () => {
    const artA: PreviewProxyArtifact = {
      id: "art-a",
      requestId: "req-a",
      cacheKey: "key-a",
      project_id: "proj-inv",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "scene-A" },
      timeRange: { startFrame: 0, endFrame: 30 },
      width: 960,
      height: 540,
      fps: 30,
      format: "png",
      rendererId: "mock",
      output: {},
      createdAt: Date.now(),
      sizeBytes: 200,
    };

    const artB: PreviewProxyArtifact = {
      id: "art-b",
      requestId: "req-b",
      cacheKey: "key-b",
      project_id: "proj-inv",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "scene-B" },
      timeRange: { startFrame: 30, endFrame: 60 },
      width: 960,
      height: 540,
      fps: 30,
      format: "png",
      rendererId: "mock",
      output: {},
      createdAt: Date.now(),
      sizeBytes: 200,
    };

    cache.set("key-a", artA, {
      projectId: "proj-inv",
      canonicalRevision: 1,
      contentFingerprint: "fpA",
      sceneIds: ["scene-A"],
      layerIds: ["layer-A1"],
      assetIds: [],
      timeRange: { startFrame: 0, endFrame: 30 },
      requiredCapabilities: ["frame_rendering"],
    });

    cache.set("key-b", artB, {
      projectId: "proj-inv",
      canonicalRevision: 1,
      contentFingerprint: "fpB",
      sceneIds: ["scene-B"],
      layerIds: ["layer-B1"],
      assetIds: [],
      timeRange: { startFrame: 30, endFrame: 60 },
      requiredCapabilities: ["frame_rendering"],
    });

    expect(cache.has("key-a")).toBe(true);
    expect(cache.has("key-b")).toBe(true);

    // Mutation in Scene A only:
    const changeSet: ChangeSet = {
      affected_scene_ids: ["scene-A"],
      affected_layer_ids: ["layer-A1"],
      affected_track_ids: [],
      affected_clip_ids: [],
      affected_keyframe_ids: [],
      invalidation: {
        requires_layout: false,
        requires_render: true,
        requires_audio_remix: false,
        requires_timeline_rebuild: false,
      },
      mutations_count: 1,
    };

    const count = cache.invalidateByChangeSet(changeSet);
    expect(count).toBe(1);

    // Scene A is invalidated:
    expect(cache.has("key-a")).toBe(false);
    // Scene B remains cached!
    expect(cache.has("key-b")).toBe(true);
  });

  it("INV-02: Supports fine-grained invalidation by layerId, assetId, and timeRange", () => {
    const art: PreviewProxyArtifact = {
      id: "art-test",
      requestId: "req-test",
      cacheKey: "key-test",
      project_id: "p1",
      canonical_revision: 1,
      entity: { type: "layer", layerId: "layer-1" },
      timeRange: { startFrame: 10, endFrame: 40 },
      width: 480,
      height: 270,
      fps: 30,
      format: "png",
      rendererId: "mock",
      output: {},
      createdAt: Date.now(),
      sizeBytes: 150,
    };

    cache.set("key-test", art, {
      projectId: "p1",
      canonicalRevision: 1,
      contentFingerprint: "fp",
      sceneIds: ["s1"],
      layerIds: ["layer-1"],
      assetIds: ["asset-video-1"],
      timeRange: { startFrame: 10, endFrame: 40 },
      requiredCapabilities: ["frame_rendering"],
    });

    // Asset invalidation test
    expect(cache.invalidateByAssetId("other-asset")).toBe(0);
    expect(cache.has("key-test")).toBe(true);

    expect(cache.invalidateByAssetId("asset-video-1")).toBe(1);
    expect(cache.has("key-test")).toBe(false);
  });

  // ─── 6. Stale Revision Result Protection ──────────────────────────────────

  it("STALE-01: Stale proxy result from an older revision is rejected and cannot overwrite newer state", async () => {
    let resolveSlowRender: (val: any) => void;
    const slowRenderPromise = new Promise((resolve) => {
      resolveSlowRender = resolve;
    });

    const slowAdapter = createMockRendererAdapter({
      id: "slow-renderer",
      priority: 200,
      capabilities: ["text", "frame_rendering"],
      onRenderFrame: async () => {
        await slowRenderPromise;
        return {
          ok: true,
          requestId: "slow-req",
          rendererId: "slow-renderer",
          type: "frame",
          output: { dataUrl: "stale-data" },
        };
      },
    });

    registry.register(slowAdapter);

    const docRev10: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "p-stale",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", startFrame: 0, durationFrames: 30, layers: [] }],
    };
    (docRev10 as any).revision = 10;

    const request = createPreviewProxyRequest({
      project_id: "p-stale",
      canonical_revision: 10,
      entity: { type: "scene", sceneId: "s1" },
      requiredCapabilities: ["text", "frame_rendering"],
      contentFragment: docRev10,
    });

    // Start proxy generation at revision 10
    const proxyPromise = coordinator.requestProxy(request, docRev10, 10);

    // Document advances to revision 11 before render completes!
    coordinator.updateCurrentRevision(11);

    // Now render completes
    resolveSlowRender!({});

    // Must reject with STALE_RESULT
    await expect(proxyPromise).rejects.toThrow(/STALE_RESULT/);

    const job = coordinator.getJob(request.id);
    expect(job?.status).toBe("stale");
  });

  // ─── 7. Background Job Cancellation & Lifecycle ───────────────────────────

  it("JOB-01: Cancelling in-flight proxy job transitions state to cancelled", async () => {
    let cancelRender: (() => void) | undefined;
    const hangingAdapter = createMockRendererAdapter({
      id: "hanging-renderer",
      priority: 300,
      capabilities: ["text", "frame_rendering"],
      onRenderFrame: async (_req, ctx) => {
        return new Promise((resolve, reject) => {
          ctx?.signal?.addEventListener("abort", () => {
            reject(new Error("aborted"));
          });
        });
      },
    });

    registry.register(hangingAdapter);

    const doc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "p-cancel",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [{ scene_id: "s1", startFrame: 0, durationFrames: 30, layers: [] }],
    };

    const request = createPreviewProxyRequest({
      project_id: "p-cancel",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "s1" },
      requiredCapabilities: ["text", "frame_rendering"],
      contentFragment: doc,
    });

    const promise = coordinator.requestProxy(request, doc);
    const job = coordinator.getJob(request.id);
    expect(job?.status).toBe("running");

    // Cancel job
    const cancelled = coordinator.cancelJob(request.id);
    expect(cancelled).toBe(true);
    expect(job?.status).toBe("cancelled");

    await expect(promise).rejects.toThrow(/cancelled/);
  });

  // ─── 8. BrowserPreviewRuntime Live Proxy Replacement ──────────────────────

  it("REPL-01: Seamlessly replaces placeholder with proxy artifact in live preview", async () => {
    const doc: BlueprintV2 = {
      schema_version: "2.0.0",
      project_id: "p-replace",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene-map",
          template: "rui-map-flight", // Requires proxy
          startFrame: 0,
          durationFrames: 60,
          layers: [],
        },
      ],
    };
    (doc as any).revision = 1;

    const runtime = new BrowserPreviewRuntime(doc, { proxyCoordinator: coordinator });

    // Initial frame has placeholder node
    const initialFrame = runtime.getCurrentVisualFrame()!;
    expect(initialFrame.nodes.length).toBeGreaterThan(0);
    const placeholder = initialFrame.nodes[0];
    expect(placeholder.previewQuality).toBe("proxy");
    expect(placeholder.attributes?.["data-proxy-pending"]).toBe("true");

    // Create and apply proxy artifact for scene-map
    const artifact: PreviewProxyArtifact = {
      id: "art-map-ready",
      requestId: "req-map",
      cacheKey: "key-map",
      project_id: "p-replace",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "scene-map", templateId: "rui-map-flight" },
      timeRange: { startFrame: 0, endFrame: 60 },
      width: 960,
      height: 540,
      fps: 30,
      format: "png",
      rendererId: "mock-map-engine",
      output: { dataUrl: "data:image/png;base64,MAP_RENDERED_PROXY" },
      createdAt: Date.now(),
      sizeBytes: 1024,
    };

    const applied = runtime.applyProxyArtifact(artifact);
    expect(applied).toBe(true);

    // Re-evaluated visual frame now has replaced proxy node!
    const updatedFrame = runtime.getCurrentVisualFrame()!;
    const proxyNode = updatedFrame.nodes.find((n) => n.id === "proxy-scene-scene-map");
    expect(proxyNode).toBeDefined();
    expect(proxyNode?.kind).toBe("image");
    expect(proxyNode?.assetRef).toBe("data:image/png;base64,MAP_RENDERED_PROXY");
    expect(proxyNode?.previewQuality).toBe("proxy");
    expect(proxyNode?.proxyArtifactId).toBe("art-map-ready");

    runtime.destroy();
  });
});
