/**
 * tests/remotion/s28_r08_renderer_core.test.ts
 * Comprehensive Suite for S28-R08: Renderer Registry & Engine Abstraction.
 * Verifies:
 *   - RendererAdapter & RendererRegistry contracts
 *   - Explicit capability model & normalization
 *   - Deterministic selection & priority tie-breaking
 *   - Fail-closed behavior on missing capabilities (NO_COMPATIBLE_RENDERER, UNSUPPORTED_CAPABILITY)
 *   - R05 engine-backed template requirement derivation (map, 3d, particles, shaders)
 *   - R07 audio subsystem capability integration (vo, music, sfx, ducking, mixing, timing)
 *   - Critical End-to-End Pipeline test (Document -> Request -> Derive -> Select -> Render -> Result)
 *   - Remotion stub architecture placement & Browser preview adapter bridge
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  RendererRegistry,
  createRendererCapabilities,
  normalizeCapability,
  deriveRequiredCapabilities,
  createMockRendererAdapter,
  createRemotionAdapterStub,
  createBrowserPreviewAdapter,
  validateRenderRequest,
  NoCompatibleRendererError,
  UnsupportedCapabilityError,
  RendererNotFoundError,
  DuplicateRendererError,
  InvalidRenderRequestError,
  REMOTION_RENDERER_ID,
  BROWSER_PREVIEW_RENDERER_ID,
  type RenderRequest,
  type RendererAdapter,
} from "../../contracts/renderer";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { instantiateTemplate } from "../../contracts/template-instantiator";

describe("S28-R08 Renderer Contracts, Capability Model & Registry", () => {
  let registry: RendererRegistry;

  beforeEach(() => {
    registry = new RendererRegistry();
  });

  // ─── 1. Registry Management & Lookup ────────────────────────────────────────

  it("REG-01: can register, lookup, and list renderer adapters", () => {
    const adapter = createMockRendererAdapter({
      id: "test-adapter-1",
      capabilities: ["text", "image", "frame_rendering"],
    });

    registry.register(adapter);
    expect(registry.has("test-adapter-1")).toBe(true);
    expect(registry.get("test-adapter-1")).toBe(adapter);
    expect(registry.lookup("test-adapter-1")).toBe(adapter);
    expect(registry.list()).toEqual([adapter]);
    expect(registry.listRendererIds()).toEqual(["test-adapter-1"]);
  });

  it("REG-02: duplicate renderer IDs fail closed with DuplicateRendererError", () => {
    const adapter1 = createMockRendererAdapter({
      id: "dup-id",
      capabilities: ["text"],
    });
    const adapter2 = createMockRendererAdapter({
      id: "dup-id",
      capabilities: ["image"],
    });

    registry.register(adapter1);
    expect(() => registry.register(adapter2)).toThrow(DuplicateRendererError);
    try {
      registry.register(adapter2);
    } catch (e: any) {
      expect(e.code).toBe("DUPLICATE_RENDERER_ID");
    }
  });

  it("REG-03: requireRenderer throws RendererNotFoundError for unregistered IDs", () => {
    expect(() => registry.requireRenderer("non-existent")).toThrow(RendererNotFoundError);
    try {
      registry.requireRenderer("non-existent");
    } catch (e: any) {
      expect(e.code).toBe("RENDERER_NOT_FOUND");
    }
  });

  it("REG-04: unregister removes adapter deterministically", () => {
    const adapter = createMockRendererAdapter({
      id: "temp-adapter",
      capabilities: ["text"],
    });
    registry.register(adapter);
    expect(registry.has("temp-adapter")).toBe(true);

    const removed = registry.unregister("temp-adapter");
    expect(removed).toBe(true);
    expect(registry.has("temp-adapter")).toBe(false);
    expect(registry.get("temp-adapter")).toBeUndefined();
  });

  // ─── 2. Capabilities Model & Normalization ──────────────────────────────────

  it("CAP-01: capabilities inspection and normalization works across aliases", () => {
    const caps = createRendererCapabilities({
      supported: [
        "text",
        "custom shaders", // alias for custom_shaders
        "audio mixing",   // alias for audio_mixing
        "ducking",        // alias for audio_ducking
        "maplibre-gl",    // alias for map
        "three.js",       // alias for 3d
        "remotion-bits",  // alias for particles
      ],
    });

    expect(caps.has("text")).toBe(true);
    expect(caps.has("custom_shaders")).toBe(true);
    expect(caps.has("custom shaders")).toBe(true);
    expect(caps.has("audio_mixing")).toBe(true);
    expect(caps.has("audio_ducking")).toBe(true);
    expect(caps.has("map")).toBe(true);
    expect(caps.has("3d")).toBe(true);
    expect(caps.has("particles")).toBe(true);
    expect(caps.has("webgl")).toBe(false); // was not added

    expect(caps.hasAll(["text", "map", "3d"])).toBe(true);
    expect(caps.hasAll(["text", "webgl"])).toBe(false);

    const missing = caps.getMissing(["text", "webgl", "export_video"]);
    expect(missing).toEqual(["webgl", "export_video"]);
  });

  it("CAP-02: listCapabilities returns union of capabilities across registry", () => {
    const adapter1 = createMockRendererAdapter({
      id: "a1",
      capabilities: ["text", "image"],
    });
    const adapter2 = createMockRendererAdapter({
      id: "a2",
      capabilities: ["audio", "video"],
    });

    registry.register(adapter1);
    registry.register(adapter2);

    const allCaps = registry.listCapabilities();
    expect(allCaps).toContain("text");
    expect(allCaps).toContain("image");
    expect(allCaps).toContain("audio");
    expect(allCaps).toContain("video");

    const a1Caps = registry.listCapabilities("a1");
    expect(a1Caps).toContain("text");
    expect(a1Caps).not.toContain("audio");
  });

  // ─── 3. Deterministic Renderer Selection & Tie-Breaking ─────────────────────

  it("SEL-01: selects compatible renderer deterministically by priority and capability specificity", () => {
    const general2d = createMockRendererAdapter({
      id: "general-2d",
      priority: 10,
      capabilities: ["text", "image", "frame_rendering"],
    });

    const highPrio2d = createMockRendererAdapter({
      id: "high-prio-2d",
      priority: 50,
      capabilities: ["text", "image", "frame_rendering"],
    });

    registry.register(general2d);
    registry.register(highPrio2d);

    const request: RenderRequest = {
      id: "req_sel_01",
      type: "frame",
      frame: 0,
      document: {
        blueprint_version: "2.0.0",
        project_id: "test_proj",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [],
      },
      requiredCapabilities: ["text", "image", "frame_rendering"],
    };

    const selected = registry.selectRenderer(request);
    expect(selected.id).toBe("high-prio-2d");
  });

  it("SEL-02: preferredRendererId selects target when compatible, fails closed when incompatible", () => {
    const fastRenderer = createMockRendererAdapter({
      id: "fast-renderer",
      capabilities: ["text", "image", "frame_rendering"],
    });
    const webglRenderer = createMockRendererAdapter({
      id: "webgl-renderer",
      capabilities: ["text", "image", "frame_rendering", "webgl"],
    });

    registry.register(fastRenderer);
    registry.register(webglRenderer);

    // Case 1: Preferred renderer is compatible
    const req1: RenderRequest = {
      id: "req_pref_01",
      type: "frame",
      frame: 0,
      document: {
        blueprint_version: "2.0.0",
        project_id: "test_proj",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [],
      },
      preferredRendererId: "fast-renderer",
      requiredCapabilities: ["text", "image", "frame_rendering"],
    };
    expect(registry.selectRenderer(req1).id).toBe("fast-renderer");

    // Case 2: Preferred renderer is incompatible (needs webgl) -> fails closed, no silent fallback to webglRenderer
    const req2: RenderRequest = {
      ...req1,
      id: "req_pref_02",
      preferredRendererId: "fast-renderer",
      requiredCapabilities: ["text", "image", "frame_rendering", "webgl"],
    };
    expect(() => registry.selectRenderer(req2)).toThrow(UnsupportedCapabilityError);
    try {
      registry.selectRenderer(req2);
    } catch (e: any) {
      expect(e.code).toBe("UNSUPPORTED_CAPABILITY");
      expect(e.details.missingCapabilities).toContain("webgl");
    }
  });

  it("SEL-03: fails closed with NO_COMPATIBLE_RENDERER if no renderer satisfies required capabilities", () => {
    const renderer2d = createMockRendererAdapter({
      id: "renderer-2d",
      capabilities: ["text", "image", "shapes", "frame_rendering"],
    });
    registry.register(renderer2d);

    const req: RenderRequest = {
      id: "req_fail_01",
      type: "frame",
      frame: 0,
      document: {
        blueprint_version: "2.0.0",
        project_id: "test_proj",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [],
      },
      requiredCapabilities: ["text", "image", "map", "webgl"],
    };

    expect(() => registry.selectRenderer(req)).toThrow(NoCompatibleRendererError);
    try {
      registry.selectRenderer(req);
    } catch (e: any) {
      expect(e.code).toBe("NO_COMPATIBLE_RENDERER");
      expect(e.details.requiredCapabilities).toContain("map");
      expect(e.details.candidateRejections.length).toBe(1);
      expect(e.details.candidateRejections[0].rendererId).toBe("renderer-2d");
      expect(e.details.candidateRejections[0].missingCapabilities).toContain("map");
    }
  });

  // ─── 4. R05 Engine-Backed Template Requirement Mapping ──────────────────────

  it("R05-MAP-01: 'rui-map-flight' maps to map and webgl capabilities", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "map_flight_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_map",
          template: "rui-map-flight",
          startFrame: 0,
          durationFrames: 120,
        },
      ],
    };

    const derived = deriveRequiredCapabilities(doc, "frame");
    expect(derived).toContain("map");
    expect(derived).toContain("webgl");
    expect(derived).toContain("frame_rendering");
  });

  it("R05-MAP-02: 'scene3d-element' maps to 3d and webgl capabilities", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "scene3d_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_3d",
          template: "scene3d-element",
          startFrame: 0,
          durationFrames: 90,
        },
      ],
    };

    const derived = deriveRequiredCapabilities(doc, "frame");
    expect(derived).toContain("3d");
    expect(derived).toContain("webgl");
  });

  it("R05-MAP-03: 'particlesystem-element' maps to particles capability", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "particles_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_particles",
          template: "particlesystem-element",
          startFrame: 0,
          durationFrames: 90,
        },
      ],
    };

    const derived = deriveRequiredCapabilities(doc, "frame");
    expect(derived).toContain("particles");
  });

  it("R05-MAP-04: GL shader transitions map to custom_shaders and webgl capabilities", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "gl_trans_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_1",
          startFrame: 0,
          durationFrames: 60,
          transition: {
            type: "ripple",
            durationInFrames: 15,
          },
        },
      ],
    };

    const derived = deriveRequiredCapabilities(doc, "sequence");
    expect(derived).toContain("transitions");
    expect(derived).toContain("custom_shaders");
    expect(derived).toContain("webgl");
    expect(derived).toContain("sequence_rendering");
  });

  // ─── 5. R07 Audio Subsystem Capability Integration ──────────────────────────

  it("R07-AUD-01: Voiceover, music, ducking, and sfx map to audio capabilities", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "audio_full_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_1",
          startFrame: 0,
          durationFrames: 180,
        },
      ],
      audio: {
        voiceover: {
          asset_ref: "vo_asset_01",
          volume: 1.0,
        },
        music: {
          asset_ref: "bgm_asset_01",
          volume: 0.2,
          ducking: {
            enabled: true,
            ducking_volume: 0.05,
          },
        },
        global_sfx: [
          {
            track_id: "sfx_woosh",
            asset_ref: "sfx_asset_01",
            startFrame: 10,
          },
        ],
      },
    };

    const derived = deriveRequiredCapabilities(doc, "export");
    expect(derived).toContain("audio");
    expect(derived).toContain("audio_voiceover");
    expect(derived).toContain("audio_music");
    expect(derived).toContain("audio_sfx");
    expect(derived).toContain("audio_ducking");
    expect(derived).toContain("audio_mixing");
    expect(derived).toContain("audio_timing");
    expect(derived).toContain("export_video");
  });

  // ─── 6. Remotion & Preview Adapters ─────────────────────────────────────────

  it("REM-01: Remotion stub defines architecture placement and production capabilities", async () => {
    const stub = createRemotionAdapterStub();
    expect(stub.id).toBe(REMOTION_RENDERER_ID);

    const caps = stub.capabilities();
    expect(caps.has("text")).toBe(true);
    expect(caps.has("image")).toBe(true);
    expect(caps.has("video")).toBe(true);
    expect(caps.has("audio")).toBe(true);
    expect(caps.has("audio_mixing")).toBe(true);
    expect(caps.has("audio_ducking")).toBe(true);
    expect(caps.has("export_video")).toBe(true);
    expect(caps.has("map")).toBe(false); // Not in standard Remotion stub

    // Verify stub fails closed on execution before R09 implementation
    const dummyReq: RenderRequest = {
      id: "test_rem_stub",
      type: "export",
      document: {
        blueprint_version: "2.0.0",
        project_id: "stub_test",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [],
      },
    };

    await expect(stub.exportVideo(dummyReq)).rejects.toThrow(/S28-R09/);
  });

  it("PRV-01: Browser preview adapter supports frame preview, rejects export_video", async () => {
    const adapter = createBrowserPreviewAdapter();
    expect(adapter.id).toBe(BROWSER_PREVIEW_RENDERER_ID);

    const caps = adapter.capabilities();
    expect(caps.has("frame_rendering")).toBe(true);
    expect(caps.has("live_preview")).toBe(true);
    expect(caps.has("export_video")).toBe(false);

    const frameReq: RenderRequest = {
      id: "req_prv_frame",
      type: "frame",
      frame: 10,
      document: {
        blueprint_version: "2.0.0",
        project_id: "prv_test",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [],
      },
    };

    expect(adapter.canRender(frameReq).canRender).toBe(true);
    const res = await adapter.renderFrame(frameReq);
    expect(res.ok).toBe(true);
    expect(res.rendererId).toBe(BROWSER_PREVIEW_RENDERER_ID);

    const exportReq: RenderRequest = {
      ...frameReq,
      type: "export",
    };
    expect(adapter.canRender(exportReq).canRender).toBe(false);
    expect(adapter.canRender(exportReq).missingCapabilities).toContain("export_video");
  });

  // ─── 7. Validation Fail-Closed Checks ───────────────────────────────────────

  it("VAL-01: validateRenderRequest rejects malformed requests fail-closed", () => {
    expect(() => validateRenderRequest(null)).toThrow(InvalidRenderRequestError);
    expect(() => validateRenderRequest({})).toThrow(InvalidRenderRequestError);
    expect(() =>
      validateRenderRequest({
        id: "req1",
        type: "frame",
        frame: -5, // invalid negative frame
        document: { project_id: "p1", fps: 30, scenes: [] },
      })
    ).toThrow(InvalidRenderRequestError);
    expect(() =>
      validateRenderRequest({
        id: "req2",
        type: "sequence",
        timeRange: { startFrame: 50, endFrame: 10 }, // endFrame < startFrame
        document: { project_id: "p1", fps: 30, scenes: [] },
      })
    ).toThrow(InvalidRenderRequestError);
  });

  // ─── 8. CRITICAL END-TO-END INTEGRATION TEST ────────────────────────────────

  it("CRITICAL-E2E: Canonical VideoDocument -> RenderRequest -> derive capabilities -> Registry -> select adapter -> RenderResult", async () => {
    // 1. Create canonical document instantiated from native template
    const inst = instantiateTemplate("rui-title-card", {
      title: "الحوسبة السحابية الحديثة",
      subtitle: "محرك الفيديو المعياري الموحد",
      backgroundColor: "#0a0a0c",
      accentColor: "#3b82f6",
    }, { scene_id: "sc_title_main", startFrame: 0, durationFrames: 120 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "e2e_renderer_pipeline",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
      audio: {
        voiceover: {
          asset_ref: "vo_e2e_cloud",
          volume: 1.0,
        },
      },
    };

    // 2. Build Render Request
    const request: RenderRequest = {
      id: "req_e2e_frame_45",
      document: doc,
      type: "frame",
      frame: 45,
      output: {
        format: "png",
        width: 1920,
        height: 1080,
      },
    };

    // 3. Automatically derive required capabilities
    const requiredCaps = deriveRequiredCapabilities(doc, request.type);
    expect(requiredCaps).toContain("text");
    expect(requiredCaps).toContain("shapes");
    expect(requiredCaps).toContain("audio");
    expect(requiredCaps).toContain("audio_voiceover");
    expect(requiredCaps).toContain("frame_rendering");

    // 4. Register mock production adapter supporting these capabilities
    let frameRenderCalled = false;
    const prodAdapter = createMockRendererAdapter({
      id: "canvas-production-adapter",
      name: "Canvas Headless Production Renderer",
      version: "2.1.0",
      priority: 80,
      capabilities: [
        "text",
        "image",
        "video",
        "audio",
        "shapes",
        "groups",
        "keyframes",
        "alpha",
        "audio_voiceover",
        "audio_timing",
        "frame_rendering",
        "sequence_rendering",
      ],
      onRenderFrame: async (req) => {
        frameRenderCalled = true;
        return {
          ok: true,
          requestId: req.id,
          rendererId: "canvas-production-adapter",
          type: "frame",
          output: {
            mimeType: "image/png",
            width: req.output?.width ?? 1920,
            height: req.output?.height ?? 1080,
            frameCount: 1,
          },
          metrics: {
            renderTimeMs: 14.5,
            evaluatedFrames: 1,
          },
        };
      },
    });

    registry.register(prodAdapter);

    // 5. Select compatible renderer via Registry
    const selectedRenderer = registry.selectRenderer(request);
    expect(selectedRenderer.id).toBe("canvas-production-adapter");

    // 6. Execute render request on selected adapter
    const result = await selectedRenderer.renderFrame(request);

    // 7. Verify RenderResult
    expect(result.ok).toBe(true);
    expect(result.requestId).toBe("req_e2e_frame_45");
    expect(result.rendererId).toBe("canvas-production-adapter");
    expect(result.output?.width).toBe(1920);
    expect(result.output?.height).toBe(1080);
    expect(result.metrics?.evaluatedFrames).toBe(1);
    expect(frameRenderCalled).toBe(true);
  });

  it("CRITICAL-FAIL-CLOSED: Required capability missing -> NO_COMPATIBLE_RENDERER without silent fallback", () => {
    // Document requires map capability (from rui-map-flight)
    const mapDoc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "map_fail_closed_test",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          id: "sc_map",
          template: "rui-map-flight",
          startFrame: 0,
          durationFrames: 90,
        },
      ],
    };

    const request: RenderRequest = {
      id: "req_map_fail_test",
      document: mapDoc,
      type: "frame",
      frame: 10,
    };

    // Register only a standard 2D adapter that does NOT support map or webgl
    const standard2DAdapter = createMockRendererAdapter({
      id: "standard-2d-renderer",
      capabilities: ["text", "image", "shapes", "frame_rendering"],
    });
    registry.register(standard2DAdapter);

    // Selection MUST throw NoCompatibleRendererError and NOT fall back silently to standard-2d-renderer
    expect(() => registry.selectRenderer(request)).toThrow(NoCompatibleRendererError);

    try {
      registry.selectRenderer(request);
    } catch (e: any) {
      expect(e.code).toBe("NO_COMPATIBLE_RENDERER");
      expect(e.details.requiredCapabilities).toContain("map");
      expect(e.details.candidateRejections[0].missingCapabilities).toContain("map");
    }
  });
});
