import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { getRegistryEntry, TEMPLATE_REGISTRY } from "../registry/template-registry";
import { mergeProject, ProjectData } from "../remotion-app/src/merge";

const ROOT = path.resolve(__dirname, "..");
const CATALOG_PATH = path.join(ROOT, "ground-truth/template_catalog.json");

interface CatalogItem {
  id: string;
  name: string;
  type: string;
  path: string;
}

const rawCatalog: CatalogItem[] = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf-8"));
const activeTemplates = rawCatalog.filter(
  (item) =>
    item.path.startsWith("templates/") &&
    item.path !== "templates/brand-resolver.ts" &&
    !item.path.endsWith(".d.ts")
);

describe("CRD-019: Runtime Template Resolution Tests", () => {
  describe("1. Target Clean-Room Blueprint Templates", () => {
    const targetTemplates = [
      { gtName: "Herodeviceassemblewrapper", stem: "HeroDeviceAssembleWrapper", canonicalId: "rui-hero-device-assemble" },
      { gtName: "Splitscreenwrapper", stem: "SplitScreenWrapper", canonicalId: "rui-split-screen" },
      { gtName: "Landingcodeshowcasewrapper", stem: "LandingCodeShowcaseWrapper", canonicalId: "rui-landing-code-showcase" },
      { gtName: "Datastorywrapper", stem: "DataStoryWrapper", canonicalId: "rui-data-story" },
      { gtName: "Creatorreelwrapper", stem: "CreatorReelWrapper", canonicalId: "rui-creator-reel" }
    ];

    targetTemplates.forEach(({ gtName, stem, canonicalId }) => {
      it(`resolves ${gtName} by ground-truth name to ${canonicalId}`, () => {
        const entry = getRegistryEntry(gtName);
        expect(entry).toBeDefined();
        expect(entry?.id).toBe(canonicalId);
        expect(typeof entry?.component).toBe("function");
      });

      it(`resolves ${stem} by component stem to ${canonicalId}`, () => {
        const entry = getRegistryEntry(stem);
        expect(entry).toBeDefined();
        expect(entry?.id).toBe(canonicalId);
        expect(typeof entry?.component).toBe("function");
      });

      it(`resolves canonical ID ${canonicalId} directly`, () => {
        const entry = getRegistryEntry(canonicalId);
        expect(entry).toBeDefined();
        expect(entry?.id).toBe(canonicalId);
        expect(typeof entry?.component).toBe("function");
      });
    });
  });

  describe("2. Comprehensive Active Production Templates Invariant", () => {
    it(`verifies all ${activeTemplates.length} active templates resolve by ground-truth name and stem`, () => {
      expect(activeTemplates.length).toBe(105);

      for (const item of activeTemplates) {
        const gtName = item.name;
        const stem = path.basename(item.path, path.extname(item.path));

        // 1. Resolve by Ground Truth name
        const entryByGt = getRegistryEntry(gtName);
        expect(entryByGt, `Template ${gtName} failed to resolve via getRegistryEntry`).toBeDefined();
        expect(typeof entryByGt?.component, `Template ${gtName} has invalid component`).toBe("function");

        // 2. Resolve by Component stem
        const entryByStem = getRegistryEntry(stem);
        expect(entryByStem, `Template stem ${stem} failed to resolve via getRegistryEntry`).toBeDefined();
        expect(typeof entryByStem?.component, `Template stem ${stem} has invalid component`).toBe("function");

        // 3. Verify semantic mapping identity
        expect(entryByGt?.id).toBe(entryByStem?.id);
        expect(entryByGt?.component).toBe(entryByStem?.component);
      }
    });
  });

  describe("3. Fail-Closed Behavior for Unknown Templates", () => {
    it("returns undefined for UnknownFakeTemplate123", () => {
      expect(getRegistryEntry("UnknownFakeTemplate123")).toBeUndefined();
    });

    it("mergeProject throws when encountering an unknown template", () => {
      const dummyProject: ProjectData = {
        project: { fps: 30, title: "Test" },
        blueprint: {
          scenes: [
            {
              scene_id: "s1",
              template: "UnknownFakeTemplate123",
              startFrame: 0,
              durationFrames: 30,
              surface: {}
            } as any
          ]
        },
        brand: {}
      };

      expect(() => {
        mergeProject(dummyProject, (tmpl) => getRegistryEntry(tmpl));
      }).toThrowError(/Template not found in registry: UnknownFakeTemplate123/);
    });

    it("mergeProject succeeds for all five target templates", () => {
      const fiveTemplates = [
        "Herodeviceassemblewrapper",
        "Splitscreenwrapper",
        "Landingcodeshowcasewrapper",
        "Datastorywrapper",
        "Creatorreelwrapper"
      ];

      const validProject: ProjectData = {
        project: { fps: 30, title: "Test Five" },
        blueprint: {
          scenes: fiveTemplates.map((template, idx) => ({
            scene_id: `scene_${idx + 1}`,
            template,
            startFrame: idx * 30,
            durationFrames: 30,
            surface: { text: "Hello" }
          }))
        },
        brand: {}
      };

      const merged = mergeProject(validProject, (tmpl) => getRegistryEntry(tmpl));
      expect(merged.scenes.length).toBe(5);
      expect(merged.scenes.map((s) => s.template)).toEqual(fiveTemplates);
    });
  });
});
