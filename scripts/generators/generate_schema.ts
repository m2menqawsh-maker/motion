import { z } from "zod";
import { BlueprintSchema } from "../../contracts/blueprint";
import * as fs from "fs";
import * as path from "path";

// Generate JSON Schema using native Zod 4 z.toJSONSchema
const jsonSchema = z.toJSONSchema(BlueprintSchema, { target: "draft-07", io: "input" });

// Ensure it matches the expected Draft-07 format and adds titles/descriptions
const finalSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  $id: "blueprint.schema.json",
  title: "المخطط التنفيذي — Blueprint (مصدر الحقيقة الوحيد المولد آلياً من Zod)",
  description: "عقد المخطط التنفيذي: يصف المشاهد والأنماط والحركات والأصوات — المصدر الوحيد للحقيقة لبناء الفيديو",
  ...jsonSchema,
} as any;

// Clean up non-standard properties if present
delete finalSchema["~standard"];

const outputPath = path.resolve(process.cwd(), "schemas/blueprint.schema.json");
fs.writeFileSync(outputPath, JSON.stringify(finalSchema, null, 2), "utf-8");
console.log(`Successfully generated JSON schema from Zod at ${outputPath}`);
