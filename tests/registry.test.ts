import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { TEMPLATE_REGISTRY } from "../registry/template-registry";
import { validateStyleSurface } from "../contracts/StyleSurface";
import type { TemplateEntry } from "../registry/types";

const SNAPCN_DIR = path.resolve(__dirname, "../.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components");
const REMOCN_DIR = path.resolve(__dirname, "../.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes");
const AUTO_GENERATED_PATH = path.resolve(__dirname, "../registry/auto-generated-entries.ts");

describe("Template Registry Conformance", () => {
  const entries = Object.values(TEMPLATE_REGISTRY) as TemplateEntry[];

  it("1. Each entry has an id matching ^[a-z0-9-]+$", () => {
    entries.forEach((entry) => {
      expect(entry.id).toMatch(/^[a-z0-9-]+$/);
    });
  });

  it("2. No duplicate IDs exist", () => {
    const ids = entries.map(e => e.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it("3. Each entry has non-empty label.ar and label.en", () => {
    entries.forEach((entry) => {
      expect(entry.label?.ar?.trim().length).toBeGreaterThan(0);
      expect(entry.label?.en?.trim().length).toBeGreaterThan(0);
    });
  });

  it("4. Each entry has a valid component (function)", () => {
    entries.forEach((entry) => {
      expect(typeof entry.component).toBe("function");
    });
  });

  it("5. Each entry has a schema object where each field has a type and label.ar", () => {
    entries.forEach((entry) => {
      expect(typeof entry.schema).toBe("object");
      Object.values(entry.schema).forEach((field) => {
        expect(field).toHaveProperty("type");
        expect(field.label?.ar?.trim().length).toBeGreaterThan(0);
      });
    });
  });

  it("6. Each entry has valid defaults matching StyleSurface", () => {
    entries.forEach((entry) => {
      const res = validateStyleSurface(entry.defaults);
      expect(res.ok).toBe(true);
    });
  });

  it("7. Each entry has defaultDurationFrames as an integer > 0", () => {
    entries.forEach((entry) => {
      expect(Number.isInteger(entry.defaultDurationFrames)).toBe(true);
      expect(entry.defaultDurationFrames).toBeGreaterThan(0);
    });
  });

  it("8. Registry contains at least 6 entries", () => {
    expect(entries.length).toBeGreaterThanOrEqual(6);
  });

  it("9. Each id in the registry has a corresponding .md file in references", () => {
    entries.forEach((entry) => {
      if (entry.origin === "docs") return; // skip for docs origin
      const inSnapcn = fs.existsSync(path.join(SNAPCN_DIR, `${entry.id}.md`));
      const inRemocn = fs.existsSync(path.join(REMOCN_DIR, `${entry.id}.md`));
      if (!inSnapcn && !inRemocn) console.error("MISSING MD FOR:", entry.id);
      expect(inSnapcn || inRemocn).toBe(true);
    });
  });

  it("10. docs-extractor.ts generates a valid file (can be parsed)", async () => {
    expect(fs.existsSync(AUTO_GENERATED_PATH)).toBe(true);
    const { AUTO_GENERATED_TEMPLATES } = await import(`file://${AUTO_GENERATED_PATH}`);
    expect(Array.isArray(AUTO_GENERATED_TEMPLATES)).toBe(true);
    expect(AUTO_GENERATED_TEMPLATES.length).toBeGreaterThan(0);
  });
});
