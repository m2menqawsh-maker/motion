/**
 * tests/remotion/s28_r05_template_migration.test.ts
 * S28-R05 Migration & Semantic Parity Tests.
 * Verifies end-to-end instantiation, layer synthesis, determinism,
 * semantic parity, and normalization/evaluation integration across
 * representative migrated templates.
 */
import { describe, it, expect } from "vitest";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { normalizeCanonicalVideo } from "../../contracts/normalization";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import { validateLayerHierarchy } from "../../contracts/layers";

describe("S28-R05 Migration & Parity: Representative Templates", () => {
  it("MIG-01: Representative 1 (Simple) — 'rui-title-card' instantiates with semantic layers", () => {
    const res = instantiateTemplate("rui-title-card", {
      title: "عنوان رئيسي مميز",
      subtitle: "شرح تفصيلي للمشروع",
      backgroundColor: "#0f172a",
      accentColor: "#38bdf8",
    }, {
      scene_id: "scene_simple_01",
      startFrame: 0,
      durationFrames: 90,
      fps: 30,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");
    expect(res.layers).toHaveLength(4);

    // Verify layer composition
    const bgLayer = res.layers.find(l => l.kind === "shape" && l.z_index === 0);
    expect(bgLayer).toBeDefined();
    if (bgLayer && bgLayer.kind === "shape") {
      expect(bgLayer.fillColor).toBe("#0f172a");
    }

    const titleLayer = res.layers.find(l => l.kind === "text" && l.z_index === 1);
    expect(titleLayer).toBeDefined();
    if (titleLayer && titleLayer.kind === "text") {
      expect(titleLayer.text).toBe("عنوان رئيسي مميز");
      expect(titleLayer.typography.fontSize).toBe(64);
    }

    const subLayer = res.layers.find(l => l.kind === "text" && l.z_index === 2);
    expect(subLayer).toBeDefined();
    if (subLayer && subLayer.kind === "text") {
      expect(subLayer.text).toBe("شرح تفصيلي للمشروع");
      expect(subLayer.typography.fontSize).toBe(32);
    }

    const accentLayer = res.layers.find(l => l.kind === "shape" && l.z_index === 3);
    expect(accentLayer).toBeDefined();
    if (accentLayer && accentLayer.kind === "shape") {
      expect(accentLayer.fillColor).toBe("#38bdf8");
    }
  });

  it("MIG-02: Representative 2 (Text-Heavy) — 'rui-quote-card' instantiates quote typography and citation", () => {
    const res = instantiateTemplate("rui-quote-card", {
      quote: "«الإتقان ليس صدفة، بل عادة متكررة»",
      author: "أرسطو",
      backgroundColor: "#1e1b4b",
    }, {
      scene_id: "scene_quote_01",
      startFrame: 30,
      durationFrames: 120,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");
    expect(res.layers.length).toBeGreaterThanOrEqual(3);

    const quoteLayer = res.layers.find(l => l.kind === "text" && l.z_index === 1);
    expect(quoteLayer).toBeDefined();
    if (quoteLayer && quoteLayer.kind === "text") {
      expect(quoteLayer.text).toBe("«الإتقان ليس صدفة، بل عادة متكررة»");
      expect(quoteLayer.typography.fontStyle).toBe("italic");
    }

    const authorLayer = res.layers.find(l => l.kind === "text" && l.z_index === 2);
    expect(authorLayer).toBeDefined();
    if (authorLayer && authorLayer.kind === "text") {
      expect(authorLayer.text).toBe("أرسطو");
    }
  });

  it("MIG-03: Representative 3 (Image/Video) — 'rui-media-frame' binds asset_ref and framing layers", () => {
    const res = instantiateTemplate("rui-media-frame", {
      media_ref: "asset_sample_product_01",
      caption: "لقطة للمنتج الجديد بدقة عالية",
      backgroundColor: "#000000",
    }, {
      scene_id: "scene_media_01",
      startFrame: 0,
      durationFrames: 90,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");
    expect(res.layers).toHaveLength(3);

    const mediaLayer = res.layers.find(l => l.kind === "image");
    expect(mediaLayer).toBeDefined();
    if (mediaLayer && mediaLayer.kind === "image") {
      expect(mediaLayer.asset_ref).toBe("asset_sample_product_01");
      expect(mediaLayer.fit).toBe("contain");
    }

    const captionLayer = res.layers.find(l => l.kind === "text");
    expect(captionLayer).toBeDefined();
    if (captionLayer && captionLayer.kind === "text") {
      expect(captionLayer.text).toBe("لقطة للمنتج الجديد بدقة عالية");
    }
  });

  it("MIG-04: Representative 4 (Multi-Layer) — 'rui-lower-third' creates overlay plate and typography", () => {
    const res = instantiateTemplate("rui-lower-third", {
      title: "مؤمن القواسمي",
      subtitle: "مهندس برمجيات ونظم ذكاء اصطناعي",
    }, {
      scene_id: "scene_l3_01",
      startFrame: 0,
      durationFrames: 90,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");
    expect(res.layers.length).toBeGreaterThanOrEqual(3);

    const plateLayer = res.layers.find(l => l.kind === "shape" && l.z_index === 1);
    expect(plateLayer).toBeDefined();

    const titleLayer = res.layers.find(l => l.kind === "text" && l.z_index === 2);
    expect(titleLayer).toBeDefined();
    if (titleLayer && titleLayer.kind === "text") {
      expect(titleLayer.text).toBe("مؤمن القواسمي");
    }
  });

  it("MIG-05: Representative 5 (Animation/Stats) — 'rui-stat-card' synthesizes numeric value and label", () => {
    const res = instantiateTemplate("rui-stat-card", {
      label: "نسبة النجاح الإجمالية",
      value: 99.8,
      backgroundColor: "#064e3b",
      accentColor: "#34d399",
    }, {
      scene_id: "scene_stat_01",
      startFrame: 0,
      durationFrames: 90,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");

    const valLayer = res.layers.find(l => l.kind === "text" && l.z_index === 1);
    expect(valLayer).toBeDefined();
    if (valLayer && valLayer.kind === "text") {
      expect(valLayer.typography.fillColor).toBe("#34d399");
    }
  });

  it("MIG-06: Representative 6 (Scene) — 'rui-intro' instantiates intro title, tagline, and backdrop", () => {
    const res = instantiateTemplate("rui-intro", {
      title: "Clean Video Studio 2.0",
      tagline: "الجيل القادم من إنتاج الفيديو البرمجي",
      backgroundColor: "#020617",
      accentColor: "#818cf8",
    }, {
      scene_id: "scene_intro_01",
      startFrame: 0,
      durationFrames: 120,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");

    const titleLayer = res.layers.find(l => l.kind === "text" && l.z_index === 1);
    expect(titleLayer).toBeDefined();
    if (titleLayer && titleLayer.kind === "text") {
      expect(titleLayer.text).toBe("Clean Video Studio 2.0");
      expect(titleLayer.typography.fontSize).toBe(72);
    }
  });

  it("MIG-07: Representative 7 (Transition/Effect) — 'fade-transition' and 'slide-transition' instantiate valid transition fragments", () => {
    const fadeRes = instantiateTemplate("fade-transition", {
      durationFrames: 15,
    }, {
      scene_id: "scene_trans_fade",
      startFrame: 0,
      durationFrames: 30,
    });
    expect(fadeRes.ok).toBe(true);
    expect(fadeRes.classification).toBe("NATIVE");
    expect(fadeRes.scene.transition).toBeDefined();
    expect(fadeRes.scene.transition?.type).toBe("fade");

    const slideRes = instantiateTemplate("slide-transition", {
      durationFrames: 20,
    }, {
      scene_id: "scene_trans_slide",
      startFrame: 0,
      durationFrames: 30,
    });
    expect(slideRes.ok).toBe(true);
    expect(slideRes.classification).toBe("NATIVE");
    expect(slideRes.scene.transition?.type).toBe("slide");
  });

  it("MIG-08: Representative 8 (Bento / Panels) — 'rui-bento-pan' synthesizes multi-container layout", () => {
    const res = instantiateTemplate("rui-bento-pan", {
      title: "نظرة عامة على النظام",
    }, {
      scene_id: "scene_bento_01",
      startFrame: 0,
      durationFrames: 120,
    });

    expect(res.ok).toBe(true);
    expect(res.classification).toBe("NATIVE");
    expect(res.layers.length).toBeGreaterThanOrEqual(4);

    const titleLayer = res.layers.find(l => l.kind === "text");
    expect(titleLayer).toBeDefined();
    if (titleLayer && titleLayer.kind === "text") {
      expect(titleLayer.text).toBe("نظرة عامة على النظام");
    }
  });

  it("MIG-09: Representative 9 (Aliases) — BentoPanWrapper resolves to identical canonical spec and fragment", () => {
    const byCanonical = instantiateTemplate("rui-bento-pan", {
      title: "نفس المحتوى",
    }, { scene_id: "sc_alias" });

    const byWrapper = instantiateTemplate("BentoPanWrapper", {
      title: "نفس المحتوى",
    }, { scene_id: "sc_alias" });

    expect(byWrapper.template_id).toBe("rui-bento-pan");
    expect(JSON.stringify(byCanonical.scene)).toBe(JSON.stringify(byWrapper.scene));
  });

  it("MIG-10: Representative 10 (Pipeline Active) — End-to-end integration with R02 Normalizer and R03 Evaluator", () => {
    const tplRes = instantiateTemplate("rui-title-card", {
      title: "فيديو متكامل",
      subtitle: "من القالب إلى التقييم الزمني",
      backgroundColor: "#1e293b",
      accentColor: "#38bdf8",
    }, {
      scene_id: "pipeline_scene_01",
      startFrame: 0,
      durationFrames: 60,
      fps: 30,
    });

    expect(tplRes.ok).toBe(true);
    expect(validateLayerHierarchy(tplRes.layers).ok).toBe(true);

    // 1. Pass generated scene into R02 Canonical Normalizer
    const projectInput = {
      project: { title: "E2E Template Pipeline Test", fps: 30 },
      blueprint: {
        blueprint_version: "2.0.0" as const,
        project_id: "test_proj_r05",
        fps: 30,
        aspect_ratio: "16:9" as const,
        scenes: [tplRes.scene],
      },
    };

    const normalized = normalizeCanonicalVideo(projectInput);
    expect(normalized).toBeDefined();
    expect(normalized.scenes).toHaveLength(1);
    expect(normalized.scenes[0].layers).toHaveLength(4);

    // 2. Pass normalized project into R03 Deterministic Frame Evaluator
    const frame15 = evaluateVideoAtFrame(normalized, 15);
    expect(frame15).toBeDefined();
    expect(frame15.frame).toBe(15);
    expect(frame15.active_scenes).toHaveLength(1);
    expect(frame15.layers).toHaveLength(4);

    // Check evaluated layer values
    const evaluatedTitle = frame15.layers.find(l => l.kind === "text" && l.layer_id.includes("layer_1"));
    expect(evaluatedTitle).toBeDefined();
    if (evaluatedTitle) {
      expect(evaluatedTitle.properties.text).toBe("فيديو متكامل");
      expect(evaluatedTitle.opacity).toBe(1);
      expect(evaluatedTitle.transform.y).toBe(-40);
    }
  });

  it("MIG-11: Idempotency & Determinism: 50 successive instantiations produce byte-for-byte identical output", () => {
    const inputs = {
      title: "اختبار الحتمية التام",
      subtitle: "لا يوجد عشوائية",
      backgroundColor: "#000000",
    };
    const ctx = {
      scene_id: "det_scene_100",
      startFrame: 0,
      durationFrames: 90,
      fps: 30,
    };

    const baselineJson = JSON.stringify(instantiateTemplate("rui-title-card", inputs, ctx));

    for (let i = 0; i < 50; i++) {
      const currentJson = JSON.stringify(instantiateTemplate("rui-title-card", inputs, ctx));
      expect(currentJson).toBe(baselineJson);
    }
  });
});
