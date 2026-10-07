/**
 * tests/remotion/s28_r05_template_spec.test.ts
 * S28-R05 Contract & Unit Tests: Engine-Neutral TemplateSpec and Instantiator.
 * Validates data contract schemas, parameter type system, slots, constraints,
 * deterministic defaults, and fail-closed error behaviors.
 */
import { describe, it, expect } from "vitest";
import {
  TemplateSpecSchema,
  TemplateClassificationSchema,
  TemplateParameterSchema,
  TemplateSlotSchema,
  validateTemplateSpec,
  type TemplateSpec,
} from "../../contracts/template-spec";
import {
  instantiateTemplate,
  TemplateInstantiator,
  TemplateInputValidationError,
  EngineBackedTemplateError,
  LegacyCompatibilityTemplateError,
} from "../../contracts/template-instantiator";
import {
  getSemanticTemplateSpec,
  getAllSemanticTemplateSpecs,
  isKnownTemplateSpec,
} from "../../registry/semantic-registry";
import { UnknownTemplateError } from "../../contracts/render-input";

describe("S28-R05 Contract & Unit Tests: TemplateSpec Contract", () => {
  const validNativeSpecFixture: TemplateSpec = {
    template_id: "test-native-template",
    version: "2.0.0",
    status: "verified",
    classification: "NATIVE",
    metadata: {
      display_name: { ar: "قالب أصيل تجريبي", en: "Test Native Template" },
      description: { ar: "وصف تجريبي", en: "Test description" },
      category: "composition",
      family: "test",
      tags: ["native", "test"],
    },
    supported_document_version: "2.0.0",
    parameters: {
      headline: {
        name: "headline",
        type: "string",
        required: true,
        description: "Main headline text",
      },
      counter: {
        name: "counter",
        type: "number",
        required: false,
        default: 42,
        min: 0,
        max: 100,
        description: "Numeric counter",
      },
      theme: {
        name: "theme",
        type: "enum",
        required: false,
        default: "dark",
        options: ["light", "dark"],
      },
      bg_color: {
        name: "bg_color",
        type: "color",
        required: false,
        default: "#0f172a",
      },
    },
    slots: {
      headline_slot: {
        slot_id: "headline_slot",
        name: "Headline",
        kind: "text",
        required: true,
        target_layer_id: "layer_1",
      },
    },
    requirements: {
      asset_kinds: [],
      fonts: ["Cairo"],
      capabilities: [],
      audio: { voiceover_supported: true, bgm_supported: true },
    },
    constraints: {
      duration: { minFrames: 30, maxFrames: 300, defaultFrames: 90 },
      aspect_ratios: ["16:9", "9:16"],
      supported_media_kinds: ["image"],
    },
    fragment: {
      template_type: "SCENE_TEMPLATE",
      default_layers: [
        {
          layer_id: "layer_0",
          kind: "shape",
          time_range: { startFrame: 0, durationFrames: 90, endFrame: 90 },
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
          shape_type: "rectangle",
          size: { width: 1920, height: 1080 },
          fillColor: "#0f172a",
          channels: [],
        },
        {
          layer_id: "layer_1",
          kind: "text",
          time_range: { startFrame: 0, durationFrames: 90, endFrame: 90 },
          transform: {
            position: { x: 0, y: 0 },
            scale: { x: 1, y: 1 },
            rotation: 0,
            anchor: { x: 0.5, y: 0.5 },
            opacity: 1,
          },
          opacity: 1,
          visible: true,
          z_index: 1,
          text: "Default Headline",
          typography: {
            fontFamily: "Cairo",
            fontSize: 60,
            textAlign: "center",
            fillColor: "#ffffff",
          },
          channels: [],
        },
      ],
      bindings: [
        {
          target_layer_id: "layer_1",
          property: "text",
          source_kind: "parameter",
          source_name: "headline",
        },
        {
          target_layer_id: "layer_0",
          property: "fillColor",
          source_kind: "parameter",
          source_name: "bg_color",
        },
      ],
    },
    compatibility: {
      legacy_aliases: ["TestNativeWrapper"],
      remaining_gap: undefined,
      migration_owner: "s28-core",
    },
    provenance: {
      source: "canonical-registry",
    },
  };

  it("SPEC-01: Valid NATIVE TemplateSpec parses and validates cleanly", () => {
    const parseRes = TemplateSpecSchema.safeParse(validNativeSpecFixture);
    expect(parseRes.success).toBe(true);

    const validation = validateTemplateSpec(validNativeSpecFixture);
    expect(validation.ok).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  it("SPEC-02: Invalid classification enum fails closed", () => {
    const invalid = { ...validNativeSpecFixture, classification: "INVALID_CLASS" };
    const parseRes = TemplateSpecSchema.safeParse(invalid);
    expect(parseRes.success).toBe(false);
  });

  it("SPEC-03: Malformed template_id (uppercase or spaces) fails closed", () => {
    const invalid1 = { ...validNativeSpecFixture, template_id: "InvalidTemplateId" };
    expect(TemplateSpecSchema.safeParse(invalid1).success).toBe(false);

    const invalid2 = { ...validNativeSpecFixture, template_id: "has space" };
    expect(TemplateSpecSchema.safeParse(invalid2).success).toBe(false);

    const invalid3 = { ...validNativeSpecFixture, template_id: "ends-with-dash-" };
    expect(TemplateSpecSchema.safeParse(invalid3).success).toBe(false);
  });

  it("SPEC-04: NATIVE template missing canonical fragment fails semantic validation", () => {
    const invalid = { ...validNativeSpecFixture, fragment: undefined };
    const validation = validateTemplateSpec(invalid);
    expect(validation.ok).toBe(false);
    expect(validation.errors.some(e => e.includes("must define a canonical fragment"))).toBe(true);
  });

  it("SPEC-05: Parameter schema validates parameter types, min/max and options", () => {
    const validParam = TemplateParameterSchema.parse({
      name: "speed",
      type: "number",
      min: 0.1,
      max: 5.0,
      default: 1.0,
    });
    expect(validParam.type).toBe("number");
    expect(validParam.min).toBe(0.1);

    expect(() => {
      TemplateParameterSchema.parse({
        name: "speed",
        type: "unknown_type_xyz",
      });
    }).toThrow();
  });

  it("SPEC-06: Slot schema validates slot kinds and target layers", () => {
    const validSlot = TemplateSlotSchema.parse({
      slot_id: "hero_image",
      name: "Hero Image",
      kind: "media",
      required: true,
      target_layer_id: "layer_media_0",
    });
    expect(validSlot.kind).toBe("media");
    expect(validSlot.required).toBe(true);
  });

  it("SPEC-07: All 105 registered TemplateSpecs in registry parse and validate", () => {
    const allSpecs = getAllSemanticTemplateSpecs();
    expect(allSpecs.length).toBe(105);

    for (const spec of allSpecs) {
      const parsed = TemplateSpecSchema.safeParse(spec);
      expect(parsed.success, `Template ${spec.template_id} failed schema validation: ${JSON.stringify(parsed)}`).toBe(true);

      const val = validateTemplateSpec(spec);
      expect(val.ok, `Template ${spec.template_id} failed validation: ${val.errors.join(", ")}`).toBe(true);
    }
  });
});

describe("S28-R05 Instantiator Fail-Closed & Validation Tests", () => {
  it("INST-01: Parameter type mismatch (number passed for string) throws TemplateInputValidationError", () => {
    expect(() => {
      instantiateTemplate("rui-title-card", {
        title: 12345 as any, // wrong type
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("INST-02: Unknown parameter passed to template throws TemplateInputValidationError", () => {
    expect(() => {
      instantiateTemplate("rui-title-card", {
        title: "Valid Title",
        unsupportedRandomProperty: "Injected value",
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("INST-03: Duration out of bounds throws TemplateInputValidationError", () => {
    // rui-title-card minFrames is 15
    expect(() => {
      instantiateTemplate("rui-title-card", {
        title: "Short Duration",
      }, {
        durationFrames: 5, // below minFrames (15)
      });
    }).toThrow(TemplateInputValidationError);

    // above maxFrames (600)
    expect(() => {
      instantiateTemplate("rui-title-card", {
        title: "Long Duration",
      }, {
        durationFrames: 1000,
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("INST-04: Unsupported aspect ratio throws TemplateInputValidationError", () => {
    expect(() => {
      instantiateTemplate("rui-title-card", {
        title: "Aspect Test",
      }, {
        aspect_ratio: "3:4" as any, // unsupported
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("INST-05: Missing required parameter throws TemplateInputValidationError", () => {
    expect(() => {
      instantiateTemplate("rui-title-card", {
        subtitle: "Missing title",
      });
    }).toThrow(TemplateInputValidationError);
  });

  it("INST-06: Resolving by alias produces identical canonical TemplateSpec", () => {
    const specByCanonical = getSemanticTemplateSpec("rui-bento-pan");
    const specByAlias = getSemanticTemplateSpec("BentoPanWrapper");
    const specByAlias2 = getSemanticTemplateSpec("RuiBentoPan");

    expect(specByCanonical).toBeDefined();
    expect(specByAlias).toBeDefined();
    expect(specByAlias2).toBeDefined();
    expect(specByCanonical?.template_id).toBe("rui-bento-pan");
    expect(specByAlias?.template_id).toBe("rui-bento-pan");
    expect(specByAlias2?.template_id).toBe("rui-bento-pan");
  });

  it("INST-07: Unknown template name returns undefined in registry and throws in instantiator", () => {
    expect(isKnownTemplateSpec("non-existent-template-999")).toBe(false);
    expect(getSemanticTemplateSpec("non-existent-template-999")).toBeUndefined();
    expect(getSemanticTemplateSpec("")).toBeUndefined();
    expect(getSemanticTemplateSpec("   ")).toBeUndefined();

    expect(() => {
      instantiateTemplate("non-existent-template-999", {});
    }).toThrow(UnknownTemplateError);
  });

  it("INST-08: ENGINE_BACKED templates are explicitly reported without silent fallback", () => {
    expect(() => {
      instantiateTemplate("rui-map-flight", {});
    }).toThrow(EngineBackedTemplateError);

    expect(() => {
      instantiateTemplate("scene3d-element", {});
    }).toThrow(EngineBackedTemplateError);

    expect(() => {
      instantiateTemplate("particlesystem-element", {});
    }).toThrow(EngineBackedTemplateError);
  });
});
