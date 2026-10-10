import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { validateStyleSurface } from "../../contracts/StyleSurface";
import type { TemplateEntry } from "../../registry/types";

const SNAPCN_DIR = path.resolve(__dirname, "../../.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components");
const REMOCN_DIR = path.resolve(__dirname, "../../.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes");
const AUTO_GENERATED_PATH = path.resolve(__dirname, "../../registry/auto-generated-entries.ts");
const RUNTIME_CONTRACT_PATH = path.resolve(__dirname, "../../contracts/template-runtime-contract.json");

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

  it("9. Each id in the registry has corresponding canonical contract documentation or reference .md", async () => {
    expect(fs.existsSync(RUNTIME_CONTRACT_PATH)).toBe(true);
    const contract = JSON.parse(fs.readFileSync(RUNTIME_CONTRACT_PATH, "utf-8"));

    // 1. Verify every registry entry is documented in authoritative contract or in skill references
    entries.forEach((entry) => {
      if (entry.origin === "snapcn") {
        const inSnapcn = fs.existsSync(path.join(SNAPCN_DIR, `${entry.id}.md`));
        const inRemocn = fs.existsSync(path.join(REMOCN_DIR, `${entry.id}.md`));
        expect(inSnapcn || inRemocn).toBe(true);
      } else {
        // Canonical system templates must be defined and documented in the authoritative runtime contract
        expect(contract.templates).toHaveProperty(entry.id);
        expect(entry.label?.ar?.length).toBeGreaterThan(0);
        expect(entry.label?.en?.length).toBeGreaterThan(0);
        expect(entry.description?.ar?.length).toBeGreaterThan(0);
        expect(entry.description?.en?.length).toBeGreaterThan(0);
      }
    });

    // 2. Verify all extracted skill templates have matching .md reference documentation
    const { AUTO_GENERATED_TEMPLATES } = await import("../../registry/auto-generated-entries");
    AUTO_GENERATED_TEMPLATES.forEach((tpl: any) => {
      const inSnapcn = fs.existsSync(path.join(SNAPCN_DIR, `${tpl.id}.md`));
      const inRemocn = fs.existsSync(path.join(REMOCN_DIR, `${tpl.id}.md`));
      expect(inSnapcn || inRemocn).toBe(true);
    });
  });

  it("10. docs-extractor.ts generates a valid file (can be parsed)", async () => {
    expect(fs.existsSync(AUTO_GENERATED_PATH)).toBe(true);
    const { AUTO_GENERATED_TEMPLATES } = await import("../../registry/auto-generated-entries");
    expect(Array.isArray(AUTO_GENERATED_TEMPLATES)).toBe(true);
    expect(AUTO_GENERATED_TEMPLATES.length).toBeGreaterThan(0);
  });
});
