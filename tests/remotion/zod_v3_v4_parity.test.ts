import { describe, it, expect } from "vitest";
import { createRequire } from "module";
const require = createRequire(import.meta.url);

const z3 = require("../../node_modules/zod").z;
const z4 = require("../../remotion-app/node_modules/zod").z;

describe("PR-C2: Zod v4 (Root) vs Zod v4 (Remotion) Semantic Parity Suite", () => {
  it("verifies installed Zod versions match expected baseline", () => {
    const v3Ver = require("../../node_modules/zod/package.json").version;
    const v4Ver = require("../../remotion-app/node_modules/zod/package.json").version;
    expect(v3Ver).toBe("4.6.7");
    expect(v4Ver).toBe("4.5.4");
  });

  describe("1. Required versus Optional fields", () => {
    const makeSchema = (zInst: any) =>
      zInst.object({
        req: zInst.string(),
        opt: zInst.string().optional(),
      });

    it("accepts valid required and optional fields symmetrically", () => {
      const s3 = makeSchema(z3);
      const s4 = makeSchema(z4);
      const payload = { req: "hello", opt: "world" };

      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);
      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual(r4.data);
    });

    it("accepts omitted optional field symmetrically", () => {
      const s3 = makeSchema(z3);
      const s4 = makeSchema(z4);
      const payload = { req: "hello" };

      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);
      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual(r4.data);
    });

    it("rejects omitted required field symmetrically", () => {
      const s3 = makeSchema(z3);
      const s4 = makeSchema(z4);
      const payload = { opt: "world" };

      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);
      expect(r3.success).toBe(false);
      expect(r4.success).toBe(false);
    });
  });

  describe("2. Null versus Undefined handling", () => {
    const makeSchema = (zInst: any) =>
      zInst.object({
        nullableField: zInst.string().nullable(),
        optionalField: zInst.string().optional(),
        nullishField: zInst.string().nullish(),
      });

    it("handles null and undefined according to schema contract", () => {
      const s3 = makeSchema(z3);
      const s4 = makeSchema(z4);

      const validPayload = {
        nullableField: null,
        optionalField: undefined,
        nullishField: null,
      };

      const r3 = s3.safeParse(validPayload);
      const r4 = s4.safeParse(validPayload);
      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual(r4.data);

      // Null passed to optional field (not nullable) should fail in both
      const invalidNull = {
        nullableField: "val",
        optionalField: null,
      };
      expect(s3.safeParse(invalidNull).success).toBe(false);
      expect(s4.safeParse(invalidNull).success).toBe(false);
    });
  });

  describe("3. Discriminated Unions", () => {
    const makeUnion = (zInst: any) =>
      zInst.discriminatedUnion("type", [
        zInst.object({ type: zInst.literal("text"), content: zInst.string() }),
        zInst.object({ type: zInst.literal("image"), url: zInst.string().url() }),
      ]);

    it("parses valid union variants with equal semantics", () => {
      const u3 = makeUnion(z3);
      const u4 = makeUnion(z4);

      const textPayload = { type: "text", content: "hello" };
      const imgPayload = { type: "image", url: "https://example.com/pic.png" };

      expect(u3.safeParse(textPayload).success).toBe(true);
      expect(u4.safeParse(textPayload).success).toBe(true);
      expect(u3.safeParse(imgPayload).success).toBe(true);
      expect(u4.safeParse(imgPayload).success).toBe(true);
    });

    it("rejects unknown discriminator or invalid branch payload symmetrically", () => {
      const u3 = makeUnion(z3);
      const u4 = makeUnion(z4);

      const badDiscriminator = { type: "video", url: "https://example.com" };
      const badPayload = { type: "image", url: "not-a-url" };

      expect(u3.safeParse(badDiscriminator).success).toBe(false);
      expect(u4.safeParse(badDiscriminator).success).toBe(false);
      expect(u3.safeParse(badPayload).success).toBe(false);
      expect(u4.safeParse(badPayload).success).toBe(false);
    });
  });

  describe("4. Unknown Object Keys (strip vs strict vs passthrough)", () => {
    it("strips unknown keys by default in both versions", () => {
      const s3 = z3.object({ name: z3.string() });
      const s4 = z4.object({ name: z4.string() });

      const payload = { name: "test", extraKey: "ignored" };
      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);

      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual({ name: "test" });
      expect(r4.data).toEqual({ name: "test" });
    });

    it("rejects unknown keys in strict mode in both versions", () => {
      const s3 = z3.object({ name: z3.string() }).strict();
      const s4 = z4.object({ name: z4.string() }).strict();

      const payload = { name: "test", rogue: 123 };
      expect(s3.safeParse(payload).success).toBe(false);
      expect(s4.safeParse(payload).success).toBe(false);
    });

    it("preserves unknown keys in passthrough mode in both versions", () => {
      const s3 = z3.object({ name: z3.string() }).passthrough();
      const s4 = z4.object({ name: z4.string() }).passthrough();

      const payload = { name: "test", rogue: 123 };
      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);
      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual(payload);
      expect(r4.data).toEqual(payload);
    });
  });

  describe("5. Type Coercion and Defaults", () => {
    const makeSchema = (zInst: any) =>
      zInst.object({
        count: zInst.coerce.number(),
        active: zInst.boolean().default(true),
        label: zInst.string().default("default_label"),
      });

    it("coerces values and applies defaults symmetrically", () => {
      const s3 = makeSchema(z3);
      const s4 = makeSchema(z4);

      const payload = { count: "42" };
      const r3 = s3.safeParse(payload);
      const r4 = s4.safeParse(payload);

      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual({
        count: 42,
        active: true,
        label: "default_label",
      });
      expect(r4.data).toEqual(r3.data);
    });
  });

  describe("6. Canonical BlueprintV2 Structure Validation Parity", () => {
    // Representative canonical Blueprint schema fragment
    const makeBlueprintFragment = (zInst: any) =>
      zInst.object({
        schema_version: zInst.literal("2.0.0"),
        project_id: zInst.string().regex(/^prj_[a-zA-Z0-9_-]+$/),
        aspect_ratio: zInst.enum(["16:9", "9:16", "1:1", "4:5", "21:9"]),
        fps: zInst.number().int().min(1).max(120),
        duration_frames: zInst.number().int().positive(),
        scenes: zInst.array(
          zInst.object({
            id: zInst.string(),
            template_id: zInst.string(),
            duration_frames: zInst.number().int().positive(),
            layer: zInst.number().int().default(0),
            props: zInst.record(zInst.string(), zInst.any()).default({}),
          })
        ),
      });

    it("validates representative BlueprintV2 JSON payload across both versions with identical result", () => {
      const bp3 = makeBlueprintFragment(z3);
      const bp4 = makeBlueprintFragment(z4);

      const validBp = {
        schema_version: "2.0.0",
        project_id: "prj_test_12345",
        aspect_ratio: "9:16",
        fps: 30,
        duration_frames: 300,
        scenes: [
          {
            id: "scene_01",
            template_id: "TitleCard",
            duration_frames: 150,
            props: { title: "مرحبا بالعالم" },
          },
          {
            id: "scene_02",
            template_id: "OutroCard",
            duration_frames: 150,
            layer: 1,
            props: { callToAction: "اشترك الآن" },
          },
        ],
      };

      const r3 = bp3.safeParse(validBp);
      const r4 = bp4.safeParse(validBp);

      expect(r3.success).toBe(true);
      expect(r4.success).toBe(true);
      expect(r3.data).toEqual(r4.data);

      // Verify serialization round-trip equality
      const json3 = JSON.stringify(r3.data);
      const json4 = JSON.stringify(r4.data);
      expect(json3).toBe(json4);
    });

    it("rejects invalid aspect ratio or schema version across both versions", () => {
      const bp3 = makeBlueprintFragment(z3);
      const bp4 = makeBlueprintFragment(z4);

      const invalidAspect = {
        schema_version: "2.0.0",
        project_id: "prj_test_12345",
        aspect_ratio: "4:3", // Not in enum
        fps: 30,
        duration_frames: 300,
        scenes: [],
      };

      expect(bp3.safeParse(invalidAspect).success).toBe(false);
      expect(bp4.safeParse(invalidAspect).success).toBe(false);

      const invalidVersion = {
        schema_version: "1.0.0", // Only 2.0.0 allowed
        project_id: "prj_test_12345",
        aspect_ratio: "16:9",
        fps: 30,
        duration_frames: 300,
        scenes: [],
      };

      expect(bp3.safeParse(invalidVersion).success).toBe(false);
      expect(bp4.safeParse(invalidVersion).success).toBe(false);
    });
  });
});
