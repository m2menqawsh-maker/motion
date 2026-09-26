import { zodToJsonSchema } from "zod-to-json-schema";
import { BlueprintSchema } from "../contracts/blueprint";
import * as fs from "fs";
import * as path from "path";

// Generate JSON Schema
const jsonSchema = zodToJsonSchema(BlueprintSchema, "BlueprintSchema");

// Ensure it matches the expected Draft-07 format and adds titles/descriptions
const finalSchema = {
  $schema: "http://json-schema.org/draft-07/schema#",
  $id: "blueprint.schema.json",
  title: "المخطط التنفيذي — Blueprint (مصدر الحقيقة الوحيد المولد آلياً من Zod)",
  description: "عقد المخطط التنفيذي: يصف المشاهد والأنماط والحركات والأصوات — المصدر الوحيد للحقيقة لبناء الفيديو",
  ...jsonSchema.definitions?.BlueprintSchema,
  definitions: {
    // Inject inner dependencies from Zod output
    ...(jsonSchema.definitions || {})
  }
} as any;

// Cleanup definitions structure
if (finalSchema.definitions && finalSchema.definitions.BlueprintSchema) {
    delete finalSchema.definitions.BlueprintSchema;
}
if (finalSchema.definitions && Object.keys(finalSchema.definitions).length === 0) {
    delete finalSchema.definitions;
}

const outputPath = path.resolve(process.cwd(), "schemas/blueprint.schema.json");
fs.writeFileSync(outputPath, JSON.stringify(finalSchema, null, 2), "utf-8");
console.log(`Successfully generated JSON schema from Zod at ${outputPath}`);
