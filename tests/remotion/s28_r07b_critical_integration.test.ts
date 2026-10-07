/**
 * tests/remotion/s28_r07b_critical_integration.test.ts
 * Critical Integration Pipeline Test for S28-R07B:
 * 
 * Pipeline:
 * Canonical Project (Native + Proxy-Required Fragment)
 *   ↓
 * BrowserPreviewRuntime starts
 *   ↓
 * Native content renders immediately (frame 0)
 *   ↓
 * Proxy fragment classified PROXY_RENDER_REQUIRED
 *   ↓
 * PreviewProxyRequest -> RendererRegistry -> Renderer creates proxy
 *   ↓
 * Proxy artifact inserted into live preview (frame 40)
 *   ↓
 * User mutation modifies affected fragment -> ChangeSet invalidates proxy
 *   ↓
 * Old proxy becomes stale and is evicted
 *   ↓
 * Stale revision result rejection verified (rev 1 cannot overwrite rev 2)
 *   ↓
 * New proxy generated for rev 2 and applied
 *   ↓
 * Undo -> Redo maintains exact cache & preview parity
 *   ↓
 * Audio preview remains synchronized and unaffected
 */

import { describe, it, expect, beforeEach } from "vitest";
import { type BlueprintV2, BlueprintV2Schema } from "../../contracts/blueprint";
import {
  resolvePreviewFidelity,
} from "../../contracts/preview-fidelity";
import {
  createPreviewProxyRequest,
  type PreviewProxyArtifact,
} from "../../contracts/preview-proxy";
import {
  PreviewProxyCache,
} from "../../preview/proxy/proxy-cache";
import {
  PreviewProxyCoordinator,
} from "../../preview/proxy/proxy-coordinator";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { AudioPreviewRuntime } from "../../preview/audio/audio-preview-runtime";
import { MockWebAudioContext } from "../../preview/audio/web-audio-adapter";
import { EditorSession } from "../../contracts/editor-session";
import { defaultTransform } from "../../contracts/layers";
import { createTimeRange } from "../../contracts/timeline";
import {
  RendererRegistry,
  createMockRendererAdapter,
} from "../../contracts/renderer";

describe("S28-R07B Critical Integration Test: Full End-to-End Pipeline", () => {
  let registry: RendererRegistry;
  let cache: PreviewProxyCache;
  let coordinator: PreviewProxyCoordinator;

  // Mock Engine Adapter registered in RendererRegistry
  const mockEngineAdapter = createMockRendererAdapter({
    id: "mock-maplibre-engine",
    priority: 150,
    capabilities: [
      "map",
      "webgl",
      "frame_rendering",
    ],
    onRenderFrame: async (req) => ({
      ok: true,
      requestId: req.id,
      rendererId: "mock-maplibre-engine",
      type: "frame",
      output: {
        dataUrl: `data:image/png;base64,RENDERED_PROXY_FOR_REV_${req.document.revision ?? 1}`,
        mimeType: "image/png",
        width: req.output?.width ?? 960,
        height: req.output?.height ?? 540,
        buffer: new Uint8Array([1, 2, 3, 4]),
      },
      metrics: { renderTimeMs: 12, evaluatedFrames: 1 },
    }),
  });

  beforeEach(() => {
    registry = new RendererRegistry();
    registry.register(mockEngineAdapter);
    cache = new PreviewProxyCache({ maxEntries: 50 });
    coordinator = new PreviewProxyCoordinator({ registry, cache });
  });

  it("CRIT-01: End-to-End Pipeline with Mutations, Invalidation, Undo/Redo & Stale Protection", async () => {
    // 1. Canonical Project containing Native (Scene 1) and Proxy-Required (Scene 2)
    const initialProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      schema_version: "2.0.0",
      project_id: "crit-pipeline-project",
      revision: 1,
      fps: 30,
      aspect_ratio: "16:9",
      audio: {
        voiceover: {
          asset_ref: "vo-crit.mp3",
          durationMs: 3000,
        },
      },
      scenes: [
        {
          scene_id: "scene-1-native",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 30,
          layers: [
            {
              layer_id: "native-title",
              kind: "text",
              text: "Native Scene Title",
              properties: { text: "Native Scene Title" },
              transform: defaultTransform(),
              time_range: createTimeRange(0, 30),
              typography: {
                fontFamily: "Cairo",
                fontSize: 48,
                fillColor: "#ffffff",
                textAlign: "center",
              },
              visible: true,
              opacity: 1,
            },
          ],
        },
        {
          scene_id: "scene-2-proxy",
          template: "rui-map-flight", // Engine-backed template requiring proxy
          startFrame: 30,
          durationFrames: 30,
          layers: [
            {
              layer_id: "proxy-overlay-text",
              kind: "text",
              text: "Map Overlay v1",
              properties: { text: "Map Overlay v1" },
              transform: defaultTransform(),
              time_range: createTimeRange(30, 30),
              typography: {
                fontFamily: "Cairo",
                fontSize: 36,
                fillColor: "#ffffff",
                textAlign: "center",
              },
              visible: true,
              opacity: 1,
            },
          ],
        },
      ],
    };

    const session = new EditorSession(initialProject);
    const mockAudioContext = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({
      audioContext: mockAudioContext,
      initialDocument: initialProject,
    });
    const runtime = new BrowserPreviewRuntime(session.getPreviewBlueprint(), {
      proxyCoordinator: coordinator,
      audioRuntime,
    });

    // 2. BrowserPreviewRuntime starts & native content renders immediately at frame 0
    runtime.seek(0);
    const frame0 = runtime.getCurrentVisualFrame()!;
    expect(frame0.frame).toBe(0);
    expect(frame0.activeScenes).toContain("scene-1-native");
    const nativeNode = frame0.nodes.find((n) => n.id === "native-title");
    expect(nativeNode).toBeDefined();
    expect(nativeNode?.text).toBe("Native Scene Title");
    expect(nativeNode?.previewQuality).toBe("native");

    // 3. Proxy fragment classified PROXY_RENDER_REQUIRED
    const fidelity = runtime.getFidelityAssessment();
    expect(fidelity.mode).toBe("PROXY_RENDER_REQUIRED");
    expect(fidelity.proxy_required).toBe(true);
    expect(fidelity.diagnostics.unsupportedFeatures).toContain("engine_backed:rui-map-flight");

    // At frame 40 (inside scene-2-proxy), verify placeholder rendered before proxy ready
    runtime.seek(40);
    const frame40Initial = runtime.getCurrentVisualFrame()!;
    const placeholder = frame40Initial.nodes.find((n) => n.id === "placeholder-scene-scene-2-proxy");
    expect(placeholder).toBeDefined();
    expect(placeholder?.attributes?.["data-proxy-pending"]).toBe("true");

    // 4. Generate PreviewProxyRequest and execute via RendererRegistry
    const proxyReq1 = createPreviewProxyRequest({
      project_id: "crit-pipeline-project",
      canonical_revision: 1,
      entity: { type: "scene", sceneId: "scene-2-proxy", templateId: "rui-map-flight" },
      timeRange: { startFrame: 30, endFrame: 60 },
      requiredCapabilities: ["map", "webgl"],
      contentFragment: initialProject.scenes[1],
    });

    const artifact1 = await coordinator.requestProxy(proxyReq1, initialProject, 1);
    expect(artifact1.rendererId).toBe("mock-maplibre-engine");
    expect(artifact1.output.dataUrl).toContain("RENDERED_PROXY_FOR_REV_1");

    // 5. Proxy inserted into live preview
    runtime.applyProxyArtifact(artifact1);
    const frame40WithProxy = runtime.getCurrentVisualFrame()!;
    const proxyVisualNode = frame40WithProxy.nodes.find((n) => n.id === "proxy-scene-scene-2-proxy");
    expect(proxyVisualNode).toBeDefined();
    expect(proxyVisualNode?.kind).toBe("image");
    expect(proxyVisualNode?.assetRef).toBe(artifact1.output.dataUrl);
    expect(proxyVisualNode?.proxyArtifactId).toBe(artifact1.id);

    // 6. User mutation modifies affected fragment -> ChangeSet invalidates proxy
    const mutResult = session.applyMutation({
      mutation_id: "mut-edit-text",
      type: "UPDATE_TEXT",
      author: "user",
      target: { scene_id: "scene-2-proxy", layer_id: "proxy-overlay-text" },
      payload: { text: "Map Overlay v2 Modified" },
    });
    expect(mutResult.success).toBe(true);
    expect(session.getRevision()).toBe(2);

    runtime.updateDocument(session.getBlueprint(), mutResult.changeset);

    // 7. Old proxy becomes stale: active proxy cleared from preview, placeholder returns
    const frame40AfterMutation = runtime.getCurrentVisualFrame()!;
    const oldProxyNode = frame40AfterMutation.nodes.find((n) => n.id === "proxy-scene-scene-2-proxy");
    expect(oldProxyNode).toBeUndefined(); // Old proxy removed!
    const placeholderReturned = frame40AfterMutation.nodes.find((n) => n.id === "placeholder-scene-scene-2-proxy");
    expect(placeholderReturned).toBeDefined();

    // 8. Stale Revision Protection: attempting to re-apply rev 1 artifact must be REJECTED!
    const reapplyStale = runtime.applyProxyArtifact(artifact1);
    expect(reapplyStale).toBe(false); // Stale revision rejected!
    expect(runtime.getActiveProxies().find((p) => p.canonical_revision === 1)).toBeUndefined();

    // 9. Generate new proxy for revision 2
    const currentDoc = session.getBlueprint();
    const proxyReq2 = createPreviewProxyRequest({
      project_id: "crit-pipeline-project",
      canonical_revision: 2,
      entity: { type: "scene", sceneId: "scene-2-proxy", templateId: "rui-map-flight" },
      timeRange: { startFrame: 30, endFrame: 60 },
      requiredCapabilities: ["map", "webgl"],
      contentFragment: currentDoc.scenes[1],
    });

    const artifact2 = await coordinator.requestProxy(proxyReq2, currentDoc, 2);
    expect(artifact2.canonical_revision).toBe(2);
    expect(artifact2.output.dataUrl).toContain("RENDERED_PROXY_FOR_REV_2");

    runtime.applyProxyArtifact(artifact2);
    const frame40Rev2 = runtime.getCurrentVisualFrame()!;
    const proxyRev2Node = frame40Rev2.nodes.find((n) => n.id === "proxy-scene-scene-2-proxy");
    expect(proxyRev2Node).toBeDefined();
    expect(proxyRev2Node?.proxyArtifactId).toBe(artifact2.id);

    // 10. Undo Operation
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getRevision()).toBe(1);

    runtime.updateDocument(session.getBlueprint());
    const restoredArtifact = await coordinator.requestProxy(proxyReq1, session.getBlueprint(), 1);
    runtime.applyProxyArtifact(restoredArtifact);
    const frame40Undone = runtime.getCurrentVisualFrame()!;
    const proxyNodeUndone = frame40Undone.nodes.find((n) => n.id === "proxy-scene-scene-2-proxy");
    expect(proxyNodeUndone).toBeDefined();
    expect(proxyNodeUndone?.assetRef).toContain("RENDERED_PROXY_FOR_REV_1");

    // 11. Redo Operation
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getRevision()).toBe(2);

    runtime.updateDocument(session.getBlueprint());
    const redoneArtifact = await coordinator.requestProxy(proxyReq2, session.getBlueprint(), 2);
    runtime.applyProxyArtifact(redoneArtifact);
    const frame40Redone = runtime.getCurrentVisualFrame()!;
    const proxyNodeRedone = frame40Redone.nodes.find((n) => n.id === "proxy-scene-scene-2-proxy");
    expect(proxyNodeRedone).toBeDefined();
    expect(proxyNodeRedone?.assetRef).toContain("RENDERED_PROXY_FOR_REV_2");

    // 12. AudioPreviewRuntime remains unaffected & synchronized
    expect(audioRuntime).toBeDefined();
    runtime.seek(15);
    expect(runtime.getCurrentFrame()).toBe(15);
    runtime.play();
    expect(runtime.getState()).toBe("playing");
    expect(audioRuntime.getState()).toBe("playing");
    runtime.pause();
    expect(runtime.getState()).toBe("paused");
    expect(audioRuntime.getState()).toBe("paused");

    // Clean up
    runtime.destroy();
  });
});
