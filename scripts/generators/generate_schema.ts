import { z } from "zod";
import { BlueprintSchema, StyleSurfaceSchema } from "../../contracts/blueprint";
import * as fs from "fs";
import * as path from "path";

// Enforce additionalProperties: false for all closed z.object instances (not passthrough and not catchall)
const enforceClosedObjects = ({ zodSchema, jsonSchema }: any) => {
  if (zodSchema?.def?.type === "object" && !zodSchema?.def?.catchall) {
    jsonSchema.additionalProperties = false;
  }
};

// Generate JSON Schema using native Zod 4 z.toJSONSchema with io: "input" and closed object enforcement
const jsonSchema = z.toJSONSchema(BlueprintSchema, {
  target: "draft-07",
  io: "input",
  override: enforceClosedObjects,
}) as any;

// Canonical definitions required for external schema references (e.g. overrides.schema.json#/definitions/styleSurface)
const hexColorDef = {
  type: "string",
  pattern: "^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$",
  description: "لون HEX — 6 أو 8 خانات",
};

const anchorDef = {
  type: "string",
  enum: [
    "top-left", "top-center", "top-right",
    "center-left", "center", "center-right",
    "bottom-left", "bottom-center", "bottom-right",
  ],
  description: "نقطة الارتكاز المكانية (9 قيم)",
};

const fontKeyDef = {
  type: "string",
  enum: [
    "Cairo", "Tajawal", "Almarai", "IBMPlexSansArabic", "NotoKufiArabic",
    "Inter", "Manrope", "Fraunces", "JetBrainsMono",
  ],
  description: "مفتاح الخط من القائمة المعتمدة",
};

const styleSurfaceSchemaRaw = z.toJSONSchema(StyleSurfaceSchema, {
  target: "draft-07",
  io: "input",
  override: enforceClosedObjects,
}) as any;
delete styleSurfaceSchemaRaw["$schema"];

const styleSurfaceDef = {
  ...styleSurfaceSchemaRaw,
  additionalProperties: true,
  description: "سطح الأنماط البصرية — يجمع كل خصائص العرض في كائن واحد",
  properties: {
    ...styleSurfaceSchemaRaw.properties,
    fontFamily: { $ref: "#/definitions/fontKey", description: "عائلة الخط" },
    color: { $ref: "#/definitions/hexColor", description: "لون النص" },
    background: { $ref: "#/definitions/hexColor", description: "لون الخلفية" },
    gradient: {
      type: "object",
      required: ["from", "to"],
      additionalProperties: false,
      properties: {
        from: { $ref: "#/definitions/hexColor" },
        to: { $ref: "#/definitions/hexColor" },
        angle: { type: "number", description: "زاوية التدرج بالدرجات" },
      },
      description: "تدرج لوني",
    },
    position: {
      type: "object",
      required: ["anchor"],
      additionalProperties: false,
      properties: {
        anchor: { $ref: "#/definitions/anchor" },
        x: { type: "number", description: "إزاحة أفقية" },
        y: { type: "number", description: "إزاحة عمودية" },
      },
      description: "الموقع المكاني",
    },
  },
};

// Ensure it matches the expected Draft-07 format and adds titles/descriptions
const finalSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  $id: "blueprint.schema.json",
  title: "المخطط التنفيذي — Blueprint (مصدر الحقيقة الوحيد المولد آلياً من Zod)",
  description: "عقد المخطط التنفيذي: يصف المشاهد والأنماط والحركات والأصوات — المصدر الوحيد للحقيقة لبناء الفيديو",
  type: "object",
  definitions: {
    hexColor: hexColorDef,
    anchor: anchorDef,
    fontKey: fontKeyDef,
    styleSurface: styleSurfaceDef,
    ...(jsonSchema.definitions || {}),
  },
  ...jsonSchema,
  additionalProperties: false,
} as any;

// Clean up non-standard properties if present
delete finalSchema["~standard"];

const outputPath = path.resolve(process.cwd(), "schemas/blueprint.schema.json");
fs.writeFileSync(outputPath, JSON.stringify(finalSchema, null, 2), "utf-8");
console.log(`Successfully generated JSON schema from Zod at ${outputPath}`);
