/**
 * tests/remotion/s28_r06_templates_and_mutations.test.ts
 * TemplateSpec Preview, Mutation Integration & Fail-Closed Capability Tests for S28-R06.
 * Verifies:
 *   - Native TemplateSpecs (title-card, quote-card, media-frame, lower-third, stat-card, intro, bento-pan)
 *   - Unsupported engine-backed, hybrid, and legacy templates fail-closed / explicit
 *   - Live update from R04 Canonical Mutations & ChangeSets
 *   - Live transient editing and undo/redo synchronization with EditorSession
 *   - Mandatory End-to-End Integration Test:
 *     TemplateSpec -> instantiate -> canonical document -> mutation -> normalize -> evaluate frame -> browser preview
 */
import { describe, it, expect } from "vitest";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { inspectDocumentCapabilities, assertPreviewSupported, UnsupportedPreviewCapabilityError } from "../../preview/capabilities";
import { DOMPreviewDriver } from "../../preview/dom-driver";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { normalizeCanonicalVideo } from "../../contracts/normalization";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import { applyMutation } from "../../contracts/mutations";
import { EditorSession } from "../../contracts/editor-session";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { JSDOM } from "jsdom";

describe("S28-R06 TemplateSpec Preview & Native Support", () => {
  // ─── 1. Native TemplateSpec Previews ────────────────────────────────────────

  it("TPL-01: 'rui-title-card' (Native) previews title, subtitle, and accent shapes", () => {
    const inst = instantiateTemplate("rui-title-card", {
      title: "العنوان الرئيسي المباشر",
      subtitle: "نظام المعاينة الحي داخل المتصفح",
      backgroundColor: "#030712",
      accentColor: "#38bdf8",
    }, { scene_id: "sc_title_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_title_card_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const caps = inspectDocumentCapabilities(doc);
    expect(caps.isSupported).toBe(true);

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    expect(vFrame.activeScenes).toContain("sc_title_01");
    expect(vFrame.nodes.length).toBe(4);

    const titleNode = vFrame.nodes.find((n) => n.kind === "text" && n.text === "العنوان الرئيسي المباشر");
    expect(titleNode).toBeDefined();

    const subNode = vFrame.nodes.find((n) => n.kind === "text" && n.text === "نظام المعاينة الحي داخل المتصفح");
    expect(subNode).toBeDefined();

    const bgNode = vFrame.nodes.find((n) => n.kind === "shape" && n.shapeFill === "#030712");
    expect(bgNode).toBeDefined();
  });

  it("TPL-02: 'rui-quote-card' (Native) previews quote typography and author citation", () => {
    const inst = instantiateTemplate("rui-quote-card", {
      quote: "«الجمال في بساطة البنية المعمارية»",
      author: "مهندس المنظومة",
      backgroundColor: "#111827",
    }, { scene_id: "sc_quote_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_quote_card_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    expect(vFrame.nodes.length).toBeGreaterThanOrEqual(3);
    const quoteNode = vFrame.nodes.find((n) => n.text === "«الجمال في بساطة البنية المعمارية»");
    expect(quoteNode).toBeDefined();
    expect(quoteNode?.computedStyles.fontStyle).toBe("italic");

    const authorNode = vFrame.nodes.find((n) => n.text === "مهندس المنظومة");
    expect(authorNode).toBeDefined();
  });

  it("TPL-03: 'rui-media-frame' (Native) previews media container with fit and assetRef", () => {
    const inst = instantiateTemplate("rui-media-frame", {
      media_ref: "asset_system_hero_preview",
      caption: "معاينة النظام الحي",
      backgroundColor: "#000000",
    }, { scene_id: "sc_media_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_media_card_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    const mediaNode = vFrame.nodes.find((n) => n.kind === "image");
    expect(mediaNode).toBeDefined();
    expect(mediaNode?.assetRef).toBe("asset_system_hero_preview");
    expect(mediaNode?.objectFit).toBe("contain");
  });

  it("TPL-04: 'rui-lower-third' (Native) previews speaker plate, name, and subtitle", () => {
    const inst = instantiateTemplate("rui-lower-third", {
      title: "د. أحمد خليل",
      subtitle: "خبير استشارات الأنظمة السحابية",
    }, { scene_id: "sc_l3_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_l3_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    const titleNode = vFrame.nodes.find((n) => n.text === "د. أحمد خليل");
    expect(titleNode).toBeDefined();
    const plateNode = vFrame.nodes.find((n) => n.kind === "shape");
    expect(plateNode).toBeDefined();
  });

  it("TPL-05: 'rui-stat-card' (Native) previews numeric statistic and label", () => {
    const inst = instantiateTemplate("rui-stat-card", {
      label: "معدل الإطارات في الثانية",
      value: 60,
      backgroundColor: "#064e3b",
      accentColor: "#10b981",
    }, { scene_id: "sc_stat_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_stat_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    const valNode = vFrame.nodes.find((n) => n.text === "60");
    expect(valNode).toBeDefined();
    expect(valNode?.computedStyles.color).toBe("#10b981");
  });

  it("TPL-06: 'rui-intro' (Native) previews main title, tagline, and presentation canvas", () => {
    const inst = instantiateTemplate("rui-intro", {
      title: "Clean Video Live Core",
      tagline: "معاينة حية ومباشرة بدون اعتمادية",
      backgroundColor: "#020617",
      accentColor: "#6366f1",
    }, { scene_id: "sc_intro_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_intro_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    const titleNode = vFrame.nodes.find((n) => n.text === "Clean Video Live Core");
    expect(titleNode).toBeDefined();
  });

  it("TPL-07: 'rui-bento-pan' (Native) previews multi-panel grid layout", () => {
    const inst = instantiateTemplate("rui-bento-pan", {
      title: "شبكة التوزيع المتعددة",
    }, { scene_id: "sc_bento_01", startFrame: 0, durationFrames: 90 });

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_bento_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
    };

    const runtime = new BrowserPreviewRuntime(doc);
    const vFrame = runtime.getCurrentVisualFrame()!;

    expect(vFrame.nodes.length).toBeGreaterThanOrEqual(4);
    const titleNode = vFrame.nodes.find((n) => n.text === "شبكة التوزيع المتعددة");
    expect(titleNode).toBeDefined();
  });
});

describe("S28-R06 Fail-Closed & Explicit Unsupported Capabilities", () => {
  it("CAP-01: ENGINE_BACKED templates (rui-map-flight, scene3d-element, particlesystem-element) are explicit", () => {
    const mapProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_map_unsupported",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_map",
          template: "rui-map-flight",
          startFrame: 0,
          durationFrames: 60,
        },
      ],
    };

    const rep = inspectDocumentCapabilities(mapProject);
    expect(rep.isSupported).toBe(false);
    expect(rep.unsupportedEntities[0].classification).toBe("ENGINE_BACKED");
    expect(rep.unsupportedEntities[0].reason).toContain("MapLibre");

    // Fail closed mode throws typed error
    expect(() => {
      new BrowserPreviewRuntime(mapProject, { failClosedOnUnsupported: true });
    }).toThrow(UnsupportedPreviewCapabilityError);

    // Permissive mode renders diagnostic overlay
    let capturedReport: any = null;
    const runtime = new BrowserPreviewRuntime(mapProject, { failClosedOnUnsupported: false });
    runtime.on("unsupportedCapability", (r) => (capturedReport = r));
    expect(capturedReport).not.toBeNull();
    expect(capturedReport.isSupported).toBe(false);

    // DOM driver displays diagnostic overlay
    const dom = new JSDOM("<div id='mount'></div>");
    const container = dom.window.document.getElementById("mount") as HTMLElement;
    runtime.mount(container);
    const overlay = container.querySelector(".cv-unsupported-capability-overlay");
    expect(overlay).not.toBeNull();
    expect(overlay?.textContent).toContain("ENGINE_BACKED");
    expect(overlay?.textContent).toContain("rui-map-flight");

    runtime.destroy();
  });

  it("CAP-02: HYBRID WebGL GLSL transitions are explicitly flagged", () => {
    const hybridProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_hybrid_trans",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_1",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 30,
          transition: {
            type: "film-burn",
            durationFrames: 15,
          },
        },
        {
          scene_id: "sc_2",
          template: "rui-quote-card",
          startFrame: 30,
          durationFrames: 30,
        },
      ],
    };

    const rep = inspectDocumentCapabilities(hybridProject);
    expect(rep.isSupported).toBe(false);
    expect(rep.unsupportedEntities.some((e) => e.entityId === "film-burn")).toBe(true);
  });

  it("CAP-03: LEGACY_COMPATIBILITY templates are explicitly reported without disguised native support", () => {
    const legacyProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "test_legacy_tpl",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_legacy",
          template: "rui-browser-flow",
          startFrame: 0,
          durationFrames: 60,
        },
      ],
    };

    const rep = inspectDocumentCapabilities(legacyProject);
    expect(rep.isSupported).toBe(false);
    expect(rep.unsupportedEntities[0].classification).toBe("LEGACY_COMPATIBILITY");
  });
});

describe("S28-R06 Mutation Integration & Live Editor Session Sync", () => {
  it("MUT-01: Canonical mutations update preview immediately via ChangeSet invalidation", () => {
    const initialProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "mut_test_proj",
      revision: 1,
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_edit_01",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60,
          surface: { text: "Original Text" },
          layers: [
            {
              layer_id: "layer_title_edit",
              kind: "text",
              text: "Original Text",
              typography: { fontFamily: "Cairo", fontSize: 48, fillColor: "#FFFFFF" },
              time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
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
              channels: [],
            },
          ],
        },
      ],
    };

    const runtime = new BrowserPreviewRuntime(initialProject);
    expect(runtime.getCurrentVisualFrame()!.nodes[0].text).toBe("Original Text");

    // Apply R04 Canonical Mutation: UPDATE_TEXT
    const mutResult = applyMutation(initialProject, {
      mutation_id: "mut_update_title",
      type: "UPDATE_TEXT",
      expected_revision: 1,
      target: { scene_id: "sc_edit_01", layer_id: "layer_title_edit" },
      payload: { text: "Mutated Title Preview" },
    });

    expect(mutResult.success).toBe(true);

    let docChangeFired = false;
    runtime.on("documentChange", (rev) => {
      docChangeFired = true;
      expect(rev).toBe(2);
    });

    // Update runtime with new document and changeset
    runtime.updateDocument(mutResult.blueprint, mutResult.changeset);

    expect(docChangeFired).toBe(true);
    expect(runtime.getCurrentVisualFrame()!.nodes[0].text).toBe("Mutated Title Preview");
  });

  it("MUT-02: EditorSession transient gestures and Undo/Redo synchronize with preview runtime", () => {
    const baseProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "session_sync_proj",
      revision: 0,
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_session",
          template: "rui-intro",
          startFrame: 0,
          durationFrames: 60,
          layers: [
            {
              layer_id: "box_drag",
              kind: "shape",
              shape_type: "rectangle",
              size: { width: 100, height: 100 },
              fillColor: "#3b82f6",
              time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
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
              channels: [],
            },
          ],
        },
      ],
    };

    const session = new EditorSession(baseProject);
    const runtime = new BrowserPreviewRuntime(session.getPreviewBlueprint());

    // 1. Simulate 60fps Pointer Drag (Transient Mutations)
    const gestureId = "mouse_drag_x_axis";
    for (let x = 10; x <= 100; x += 10) {
      const transRes = session.applyTransientMutation(
        {
          mutation_id: `drag_step_${x}`,
          type: "UPDATE_TRANSFORM",
          target: { scene_id: "sc_session", layer_id: "box_drag" },
          payload: { transform: { position: { x, y: 0 } } },
        },
        gestureId
      );
      expect(transRes.success).toBe(true);
      runtime.updateDocument(session.getPreviewBlueprint());
      expect(runtime.getCurrentVisualFrame()!.nodes[0].transform.x).toBe(x);
    }

    // 2. Commit the drag gesture (creates exactly 1 history entry)
    const commitRes = session.commitGesture(gestureId, "Dragged box to 100px");
    expect(commitRes?.success).toBe(true);
    expect(session.getRevision()).toBe(1);

    // 3. Undo
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    runtime.updateDocument(session.getPreviewBlueprint());
    // Position reverted to 0
    expect(runtime.getCurrentVisualFrame()!.nodes[0].transform.x).toBe(0);

    // 4. Redo
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    runtime.updateDocument(session.getPreviewBlueprint());
    // Position restored to 100
    expect(runtime.getCurrentVisualFrame()!.nodes[0].transform.x).toBe(100);

    runtime.destroy();
  });

  // ─── CRITICAL MANDATORY INTEGRATION TEST ────────────────────────────────────

  it("CRITICAL INTEGRATION: TemplateSpec -> instantiate -> canonical document -> mutation -> normalize -> evaluate frame -> browser preview representation", () => {
    // Step 1: TemplateSpec Instantiation
    const instResult = instantiateTemplate("rui-title-card", {
      title: "العنوان الابتدائي من القالب",
      subtitle: "الوصف الأصلي للقالب",
      backgroundColor: "#0a0f1d",
      accentColor: "#00f5ff",
    }, {
      scene_id: "scene_e2e_01",
      startFrame: 0,
      durationFrames: 90,
      fps: 30,
    });
    expect(instResult.ok).toBe(true);
    expect(instResult.classification).toBe("NATIVE");

    // Step 2: Canonical Document Construction
    const canonicalDoc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "e2e_full_lifecycle_project",
      revision: 1,
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [instResult.scene],
    };

    // Step 3: Canonical Mutation Application (Edit title and rotate accent)
    const titleLayerId = instResult.layers.find((l) => l.kind === "text" && (l as any).text === "العنوان الابتدائي من القالب")!.layer_id;
    const accentLayerId = instResult.layers.find((l) => l.kind === "shape" && (l as any).z_index === 3)!.layer_id;

    const m1 = applyMutation(canonicalDoc, {
      mutation_id: "e2e_m1_text",
      type: "UPDATE_TEXT",
      expected_revision: 1,
      target: { scene_id: "scene_e2e_01", layer_id: titleLayerId },
      payload: { text: "العنوان المعدل بعد التحرير الحي" },
    });
    expect(m1.success).toBe(true);

    const m2 = applyMutation(m1.blueprint, {
      mutation_id: "e2e_m2_transform",
      type: "UPDATE_TRANSFORM",
      expected_revision: 2,
      target: { scene_id: "scene_e2e_01", layer_id: accentLayerId },
      payload: { transform: { rotation: 45 } },
    });
    expect(m2.success).toBe(true);

    // Step 4: Normalization
    const normalized = normalizeCanonicalVideo({ blueprint: m2.blueprint });
    expect(normalized).toBeDefined();
    expect(normalized.scenes[0].layers).toHaveLength(4);

    // Step 5: Frame Evaluation at Frame 45
    const evalState = evaluateVideoAtFrame(normalized, 45);
    expect(evalState.frame).toBe(45);
    expect(evalState.layers.length).toBe(4);

    const evaluatedTitle = evalState.layers.find((l) => l.layer_id === titleLayerId)!;
    expect(evaluatedTitle.properties.text).toBe("العنوان المعدل بعد التحرير الحي");

    const evaluatedAccent = evalState.layers.find((l) => l.layer_id === accentLayerId)!;
    expect(evaluatedAccent.transform.rotation).toBe(45);

    // Step 6: Browser Preview Runtime Representation & DOM Mount
    const dom = new JSDOM("<div id='canvas-mount' style='width: 1920px; height: 1080px;'></div>");
    const container = dom.window.document.getElementById("canvas-mount") as HTMLElement;

    const runtime = new BrowserPreviewRuntime(normalized);
    runtime.mount(container);
    runtime.seek(45);

    const visualFrame = runtime.getCurrentVisualFrame()!;
    expect(visualFrame.frame).toBe(45);
    expect(visualFrame.dimensions).toEqual({ width: 1920, height: 1080 });

    // Check rendered visual node representation
    const visualTitle = visualFrame.nodes.find((n) => n.id === titleLayerId)!;
    expect(visualTitle.text).toBe("العنوان المعدل بعد التحرير الحي");

    const visualAccent = visualFrame.nodes.find((n) => n.id === accentLayerId)!;
    expect(visualAccent.transform.rotation).toBe(45);
    expect(visualAccent.computedStyles.transform).toContain("rotate(45deg)");

    // Check DOM element in stage
    const domTitleEl = container.querySelector(`[data-layer-id="${titleLayerId}"]`);
    expect(domTitleEl).not.toBeNull();
    expect(domTitleEl?.textContent).toBe("العنوان المعدل بعد التحرير الحي");

    const domAccentEl = container.querySelector(`[data-layer-id="${accentLayerId}"]`) as HTMLElement;
    expect(domAccentEl).not.toBeNull();
    expect(domAccentEl.style.transform).toContain("rotate(45deg)");

    runtime.destroy();
  });
});
