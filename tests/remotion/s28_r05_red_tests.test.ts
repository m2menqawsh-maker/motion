/**
 * tests/remotion/s28_r05_red_tests.test.ts
 * S28-R05 RED Tests: Engine-Neutral TemplateSpec & Migration.
 * Verifies that the new engine-neutral template specification,
 * instantiator, registry integration, and migration contracts exist and enforce invariants.
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R05 RED Tests: Engine-Neutral TemplateSpec & Instantiator", () => {
  const rootDir = path.resolve(__dirname, "../..");

  it("RED-01: contracts/template-spec.ts exists and exports TemplateSpec schemas and types", async () => {
    const specModulePath = path.join(rootDir, "contracts/template-spec.ts");
    expect(fs.existsSync(specModulePath), "contracts/template-spec.ts must exist").toBe(true);

    const mod = await import("../../contracts/template-spec");
    expect(mod.TemplateClassificationSchema).toBeDefined();
    expect(mod.TemplateSpecSchema).toBeDefined();
    expect(mod.TemplateParameterSchema).toBeDefined();
    expect(mod.TemplateSlotSchema).toBeDefined();
    expect(mod.TemplateConstraintsSchema).toBeDefined();
    expect(mod.TemplateRequirementsSchema).toBeDefined();
  });

  it("RED-02: contracts/template-spec.ts has ZERO imports from react, remotion, or UI libraries", () => {
    const specFilePath = path.join(rootDir, "contracts/template-spec.ts");
    if (!fs.existsSync(specFilePath)) return;
    const content = fs.readFileSync(specFilePath, "utf-8");

    const forbiddenPatterns = [
      /from\s+["']react["']/,
      /from\s+["']react-dom["']/,
      /from\s+["']remotion["']/,
      /from\s+["']@remotion\//,
      /React\./,
      /JSX\./,
      /useCurrentFrame\(/,
      /interpolate\(/,
      /spring\(/,
    ];

    for (const pattern of forbiddenPatterns) {
      expect(pattern.test(content), `contracts/template-spec.ts violated purity: matched ${pattern}`).toBe(false);
    }
  });

  it("RED-03: contracts/template-instantiator.ts exists and exports instantiateTemplate and TemplateInstantiator", async () => {
    const instModulePath = path.join(rootDir, "contracts/template-instantiator.ts");
    expect(fs.existsSync(instModulePath), "contracts/template-instantiator.ts must exist").toBe(true);

    const mod = await import("../../contracts/template-instantiator");
    expect(typeof mod.instantiateTemplate).toBe("function");
    expect(mod.TemplateInstantiator).toBeDefined();
  });

  it("RED-04: TemplateInstantiator instantiates NATIVE template ('rui-title-card') into valid canonical VideoDocument scene fragment", async () => {
    const { instantiateTemplate } = await import("../../contracts/template-instantiator");
    const { BlueprintSceneSchema } = await import("../../contracts/blueprint");
    const { validateLayerHierarchy } = await import("../../contracts/layers");

    const result = instantiateTemplate("rui-title-card", {
      title: "العنوان الرئيسي الموثوق",
      subtitle: "نظام تحرير الفيديو المحايد للمحرك",
      backgroundColor: "#0d1117",
      accentColor: "#58a6ff",
    }, {
      scene_id: "scene_title_01",
      startFrame: 0,
      durationFrames: 90,
      fps: 30,
      aspect_ratio: "16:9",
    });

    expect(result.ok).toBe(true);
    expect(result.classification).toBe("NATIVE");
    expect(result.scene).toBeDefined();
    expect(result.scene.scene_id).toBe("scene_title_01");
    expect(result.scene.durationFrames).toBe(90);
    expect(result.layers.length).toBeGreaterThanOrEqual(3);

    // Validate fragment against canonical VideoDocument contract
    const parsedScene = BlueprintSceneSchema.safeParse(result.scene);
    expect(parsedScene.success, `Scene failed BlueprintSceneSchema: ${JSON.stringify(parsedScene)}`).toBe(true);

    const hierarchyValidation = validateLayerHierarchy(result.layers);
    expect(hierarchyValidation.ok, `Layer hierarchy validation failed: ${hierarchyValidation.errors.join(", ")}`).toBe(true);
  });

  it("RED-05: Missing required inputs fails closed with structured TemplateInputValidationError", async () => {
    const { instantiateTemplate, TemplateInputValidationError } = await import("../../contracts/template-instantiator");

    expect(() => {
      instantiateTemplate("rui-title-card", {}, {
        scene_id: "scene_fail_01",
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("RED-06: Unknown template fails closed with structured UnknownTemplateError", async () => {
    const { instantiateTemplate } = await import("../../contracts/template-instantiator");
    const { UnknownTemplateError } = await import("../../contracts/render-input");

    expect(() => {
      instantiateTemplate("non-existent-template-xyz", {
        title: "Test",
      });
    }).toThrow(UnknownTemplateError);
  });

  it("RED-07: Instantiation produces deterministic equivalent fragment for identical inputs", async () => {
    const { instantiateTemplate } = await import("../../contracts/template-instantiator");

    const inputs = {
      title: "عنوان متطابق",
      subtitle: "اختبار الحتمية الرياضية",
      backgroundColor: "#161b22",
    };
    const ctx = {
      scene_id: "scene_deterministic_01",
      startFrame: 10,
      durationFrames: 60,
      fps: 30,
    };

    const res1 = instantiateTemplate("rui-title-card", inputs, ctx);
    const res2 = instantiateTemplate("rui-title-card", inputs, ctx);

    expect(JSON.stringify(res1.scene)).toBe(JSON.stringify(res2.scene));
    expect(res1.layers).toEqual(res2.layers);
  });

  it("RED-08: Single canonical authority is preserved: getSemanticTemplateSpec() resolves canonical IDs and aliases", async () => {
    const { getSemanticTemplateSpec } = await import("../../registry/semantic-registry");

    const canonicalSpec = getSemanticTemplateSpec("rui-title-card");
    expect(canonicalSpec).toBeDefined();
    expect(canonicalSpec?.template_id).toBe("rui-title-card");
    expect(canonicalSpec?.classification).toBe("NATIVE");

    // Alias resolution
    const aliasSpec = getSemanticTemplateSpec("TitleCardWrapper");
    expect(aliasSpec).toBeDefined();
    expect(aliasSpec?.template_id).toBe("rui-title-card");
  });

  it("RED-09: ENGINE_BACKED template explicitly rejects native instantiation with clear engine diagnostic", async () => {
    const { instantiateTemplate, EngineBackedTemplateError } = await import("../../contracts/template-instantiator");

    expect(() => {
      instantiateTemplate("rui-map-flight", {
        center: [0, 0],
      });
    }).toThrow(EngineBackedTemplateError);
  });

  it("RED-10: Migration manifest is complete (105 templates, 0 unknown)", async () => {
    const manifestPath = path.join(rootDir, "registry/template-migration-manifest.json");
    expect(fs.existsSync(manifestPath), "Manifest file must exist").toBe(true);

    const raw = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    expect(raw.counts.total).toBe(105);
    expect(raw.counts.unknown).toBe(0);
    expect(raw.counts.native).toBeGreaterThanOrEqual(20);
    expect(raw.counts.engine_backed).toBeGreaterThanOrEqual(2);
    expect(raw.counts.hybrid).toBeGreaterThanOrEqual(10);
    expect(raw.counts.legacy_compatibility).toBeGreaterThanOrEqual(40);
    expect(Object.keys(raw.entries).length).toBe(105);
  });

  it("RED-11: Legacy getRegistryEntry() remains functional for Remotion backwards compatibility", async () => {
    const { getRegistryEntry } = await import("../../registry/template-registry");

    const entry = getRegistryEntry("rui-title-card");
    expect(entry).toBeDefined();
    expect(entry?.id).toBe("rui-title-card");
    expect(entry?.component).toBeDefined();
  }, 15000);
});
