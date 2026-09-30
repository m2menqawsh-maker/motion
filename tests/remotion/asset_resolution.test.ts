import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

import {
  parseAssetRef,
  resolveAssetReference,
  collectAssetReferences,
  loadRequiredMediaMap,
  UnknownAssetReferenceError,
  MalformedAssetRefError,
  RequiredArtifactMissingError,
  ArtifactCorruptedError,
} from "../../contracts/asset-resolver";

import {
  mergeScene,
  mergeProject,
  BlueprintScene,
  ProjectData,
} from "../../remotion-app/src/merge";

import { BrandKit } from "../../contracts/brand";
import { TemplateEntry } from "../../registry/types";

const GOLDEN_FIXTURE_PATH = path.resolve(__dirname, "../../contracts/fixtures/asset_resolution_golden.json");

describe("S14 Canonical AssetRef & Fail-Closed Resolution Suite (TypeScript)", () => {
  const dummyBrand: BrandKit = {
    brandName: "Dummy",
    logoSrc: null,
    colors: { primary: "#ff0000", accent: "#00ff00", background: "#0000ff", text: "#fff" },
    fonts: { display: "Cairo", body: "Inter" }
  };

  const dummyRegistryEntry = {
    id: "test",
    label: { en: "Test", ar: "اختبار" },
    description: { en: "Test", ar: "اختبار" },
    category: "other",
    defaultDurationFrames: 30,
    defaults: { text: "default text" },
    schema: {},
    component: () => null
  } as unknown as TemplateEntry;

  // ─── 1. Cross-Language Golden Fixture Tests ─────────────────────────────────
  describe("Cross-Language Golden Fixtures", () => {
    const fixtureData = JSON.parse(fs.readFileSync(GOLDEN_FIXTURE_PATH, "utf-8"));

    fixtureData.test_cases.forEach((tc: any) => {
      it(`${tc.id}: ${tc.description}`, () => {
        if (tc.should_succeed) {
          const res = resolveAssetReference(tc.ref, tc.media_map);
          expect(res).toBe(tc.expected_resolution);
        } else {
          expect(() => {
            resolveAssetReference(tc.ref, tc.media_map);
          }).toThrowError();

          try {
            resolveAssetReference(tc.ref, tc.media_map);
          } catch (err: any) {
            expect(err.code).toBe(tc.expected_error);
          }
        }
      });
    });
  });

  // ─── 2. ASSET-005: Multiple Media Surfaces in mergeScene ────────────────────
  describe("ASSET-005: Declarative Resolution Across All Surfaces", () => {
    it("resolves media_refs, sfx_ref, captions_ref, logoSrc, and all content fields via media_map", () => {
      const scene: BlueprintScene = {
        scene_id: "s_hero",
        template: "test",
        startFrame: 0,
        durationFrames: 60,
        media_refs: ["ast_img_1"],
        sfx_ref: "ast_sfx_pop",
        captions_ref: "ast_caps_1",
        surface: {
          logoSrc: "ast_brand_logo",
        },
        content: {
          images: ["ast_img_1", "ast_img_2"],
          screen: "ast_screen_video",
          icons: ["ast_icon_star"],
          audioRef: "ast_ambient_sound",
        },
      };

      const mediaMap: Record<string, string> = {
        ast_img_1: "projects/p1/generations/g1/img1.png",
        ast_img_2: "projects/p1/generations/g1/img2.png",
        ast_sfx_pop: "projects/p1/generations/g1/pop.wav",
        ast_caps_1: "projects/p1/generations/g1/caps.json",
        ast_brand_logo: "projects/p1/generations/g1/logo.png",
        ast_screen_video: "projects/p1/generations/g1/screen.mp4",
        ast_icon_star: "projects/p1/generations/g1/star.svg",
        ast_ambient_sound: "projects/p1/generations/g1/ambient.mp3",
      };

      const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand, undefined, mediaMap, "p1");

      // Verify all surfaces resolved to S13 generation paths
      expect(merged.media_refs[0]).toBe("projects/p1/generations/g1/img1.png");
      expect(merged.sfx_ref).toBe("projects/p1/generations/g1/pop.wav");
      expect(merged.captions_ref).toBe("projects/p1/generations/g1/caps.json");
      expect(merged.surface.logoSrc).toBe("projects/p1/generations/g1/logo.png");
      expect(merged.content?.images?.[0]).toBe("projects/p1/generations/g1/img1.png");
      expect(merged.content?.images?.[1]).toBe("projects/p1/generations/g1/img2.png");
      expect(merged.content?.screen).toBe("projects/p1/generations/g1/screen.mp4");
      expect(merged.content?.icons?.[0]).toBe("projects/p1/generations/g1/star.svg");
      expect(merged.content?.audioRef).toBe("projects/p1/generations/g1/ambient.mp3");
    });
  });

  // ─── 3. ASSET-012: Fail-Closed Resolver Behavior ────────────────────────────
  describe("ASSET-012: Fail-Closed UnknownAssetReferenceError", () => {
    const mediaMap = { "ast_known": "projects/p1/generations/g1/known.mp4" };

    it("throws UnknownAssetReferenceError when media_refs contains unknown asset", () => {
      const scene: BlueprintScene = {
        scene_id: "s1",
        template: "test",
        startFrame: 0,
        durationFrames: 30,
        media_refs: ["ast_missing_video"],
      };

      expect(() => {
        mergeScene(scene, dummyRegistryEntry, dummyBrand, undefined, mediaMap, "p1");
      }).toThrowError(UnknownAssetReferenceError);

      try {
        mergeScene(scene, dummyRegistryEntry, dummyBrand, undefined, mediaMap, "p1");
      } catch (e: any) {
        expect(e.code).toBe("UNKNOWN_ASSET_REFERENCE");
        expect(e.assetId).toBe("ast_missing_video");
        expect(e.sceneId).toBe("s1");
      }
    });

    it("throws UnknownAssetReferenceError when content.images contains unknown asset", () => {
      const scene: BlueprintScene = {
        scene_id: "s1",
        template: "test",
        startFrame: 0,
        durationFrames: 30,
        content: {
          images: ["ast_missing_gallery"],
        },
      };

      expect(() => {
        mergeScene(scene, dummyRegistryEntry, dummyBrand, undefined, mediaMap, "p1");
      }).toThrowError(UnknownAssetReferenceError);
    });

    it("throws UnknownAssetReferenceError when audio.voiceover contains unknown asset", () => {
      const projectData: ProjectData = {
        project: { title: "Audio Test" },
        brand: dummyBrand,
        blueprint: {
          fps: 30,
          scenes: [
            { scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30 },
          ],
        },
        media_map: mediaMap,
      };
      (projectData as any).audio = {
        voiceover: { asset_ref: "ast_missing_vo" },
      };

      expect(() => {
        mergeProject(projectData, () => dummyRegistryEntry);
      }).toThrowError(UnknownAssetReferenceError);
    });
  });

  // ─── 4. LED-033: loadRequiredMediaMap ───────────────────────────────────────
  describe("LED-033: Mandatory media_map Loader & Error Surface", () => {
    it("throws RequiredArtifactMissingError when media_map.json is missing and isMandatory=true", () => {
      const mockDir = path.resolve(__dirname, "mock_missing_map");
      if (!fs.existsSync(mockDir)) fs.mkdirSync(mockDir, { recursive: true });

      try {
        expect(() => {
          loadRequiredMediaMap(mockDir, { isMandatory: true, state: "MATERIALIZED" });
        }).toThrowError(RequiredArtifactMissingError);
      } finally {
        fs.rmSync(mockDir, { recursive: true, force: true });
      }
    });

    it("returns empty map when media_map.json is missing and isMandatory=false", () => {
      const mockDir = path.resolve(__dirname, "mock_pre_materialized");
      if (!fs.existsSync(mockDir)) fs.mkdirSync(mockDir, { recursive: true });

      try {
        const loaded = loadRequiredMediaMap(mockDir, { isMandatory: false });
        expect(loaded).toEqual({});
      } finally {
        fs.rmSync(mockDir, { recursive: true, force: true });
      }
    });

    it("throws ArtifactCorruptedError when media_map.json is malformed JSON", () => {
      const mockDir = path.resolve(__dirname, "mock_broken_map");
      if (!fs.existsSync(mockDir)) fs.mkdirSync(mockDir, { recursive: true });
      fs.writeFileSync(path.join(mockDir, "media_map.json"), "{ invalid json");

      try {
        expect(() => {
          loadRequiredMediaMap(mockDir, { isMandatory: true });
        }).toThrowError(ArtifactCorruptedError);
      } finally {
        fs.rmSync(mockDir, { recursive: true, force: true });
      }
    });

    it("loads valid media_map.json object successfully", () => {
      const mockDir = path.resolve(__dirname, "mock_valid_map");
      if (!fs.existsSync(mockDir)) fs.mkdirSync(mockDir, { recursive: true });
      const mapContent = { "ast_img": "projects/p1/generations/g1/img.png" };
      fs.writeFileSync(path.join(mockDir, "media_map.json"), JSON.stringify(mapContent));

      try {
        const loaded = loadRequiredMediaMap(mockDir, { isMandatory: true });
        expect(loaded).toEqual(mapContent);
      } finally {
        fs.rmSync(mockDir, { recursive: true, force: true });
      }
    });
  });
});
