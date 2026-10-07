import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { parseCanonicalVideo, validateCanonicalVideo } from "../../contracts/canonical-video";
import { normalizeCanonicalVideo } from "../../contracts/normalization";
import { parseRenderInput } from "../../contracts/render-input";
import { mergeProject } from "../../remotion-app/src/merge";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

const FIXTURES_DIR = path.resolve(__dirname, "../fixtures/canonical");

function loadFixture(name: string): any {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES_DIR, name), "utf-8"));
}

describe("S28-R02 Canonical Contract & Normalizer Parity Suite", () => {
  const brandFixture = {
    brandName: "Acme Brand",
    logoSrc: null,
    colors: {
      primary: "#FF5500",
      accent: "#00AAFF",
      background: "#112233",
      text: "#FFFFFF",
    },
    fonts: {
      display: "Cairo",
      body: "Cairo",
    },
  };

  const sampleMediaMap = {
    "ast_img_product_01": "projects/test/img1.png",
    "ast_video_broll_01": "projects/test/vid1.mp4",
    "ast_vo_primary": "projects/test/vo.mp3",
    "ast_music_track": "projects/test/bgm.mp3",
    "ast_sfx_hit": "projects/test/hit.wav",
  };

  const allFixtures = [
    { file: "01_simple_text_scene.json", desc: "Simple text scene (16:9, 30fps)" },
    { file: "02_image_scene.json", desc: "Image scene with AssetRefs (9:16, 30fps)" },
    { file: "03_video_scene.json", desc: "Video scene with AssetRefs (16:9, 60fps)" },
    { file: "04_audio_plan.json", desc: "Audio plan with ducking & SFX (16:9, 30fps)" },
    { file: "05_multi_scenes_effects_transitions.json", desc: "Multi-scene with effects & transitions" },
    { file: "06_overrides_and_brand.json", desc: "Brand token resolution & overrides" },
    { file: "07_aspect_1_1_non_30fps.json", desc: "Square aspect ratio (1:1, 24fps)" },
    { file: "08_aspect_9_16.json", desc: "Vertical aspect ratio (9:16, 30fps)" },
  ];

  for (const { file, desc } of allFixtures) {
    it(`parses and normalizes fixture correctly: ${desc} (${file})`, () => {
      const raw = loadFixture(file);

      // 1. Canonical Parser Path
      const canonicalBp = parseCanonicalVideo(raw);
      expect(canonicalBp.blueprint_version).toBe("2.0.0");
      expect(canonicalBp.scenes.length).toBeGreaterThan(0);

      // 2. Canonical Normalizer Path
      const overrides = file.includes("overrides")
        ? {
            scenes: {
              scene_overridden_01: {
                props: { text: "Overridden Text by Editor" },
                timing: { startFrame: 5, durationFrames: 110 },
              },
            },
          }
        : undefined;

      const normalized = normalizeCanonicalVideo({
        project: { title: raw.project_id, fps: raw.fps },
        blueprint: canonicalBp,
        brand: brandFixture,
        overrides,
        media_map: sampleMediaMap,
      });

      expect(normalized.fps).toBe(raw.fps);
      expect(normalized.totalDurationFrames).toBeGreaterThan(0);
      expect(normalized.scenes).toHaveLength(canonicalBp.scenes.length);

      // 3. Existing Remotion Compatibility Path
      const renderInputEnvelope = {
        project: { title: raw.project_id, fps: raw.fps },
        blueprint: raw,
        brand: brandFixture,
        overrides,
        media_map: sampleMediaMap,
      };

      const validatedRenderInput = parseRenderInput(renderInputEnvelope);
      const mergedRemotion = mergeProject(
        validatedRenderInput,
        (tpl) => TEMPLATE_REGISTRY[tpl]
      );

      // 4. Parity Assertions
      expect(normalized.totalDurationFrames).toBe(mergedRemotion.totalDurationFrames);
      expect(normalized.fps).toBe(mergedRemotion.fps);
      expect(normalized.scenes.length).toBe(mergedRemotion.scenes.length);

      for (let i = 0; i < normalized.scenes.length; i++) {
        const normScene = normalized.scenes[i];
        const remScene = mergedRemotion.scenes[i];
        expect(normScene.scene_id).toBe(remScene.scene_id);
        expect(normScene.startFrame).toBe(remScene.startFrame);
        expect(normScene.durationFrames).toBe(remScene.durationFrames);
        expect(normScene.template).toBe(remScene.template);
      }
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Fail-Closed Validation Parity
  // ──────────────────────────────────────────────────────────────────────────
  it("rejects unknown effect in canonical video fail-closed", () => {
    const raw = loadFixture("01_simple_text_scene.json");
    const poisoned = {
      ...raw,
      scenes: [
        {
          ...raw.scenes[0],
          effects: [{ effect: "nonexistent_effect_xyz" }],
        },
      ],
    };

    expect(() => parseCanonicalVideo(poisoned)).toThrow(/Unknown effect 'nonexistent_effect_xyz'/);
  });

  it("rejects unknown transition in canonical video fail-closed", () => {
    const raw = loadFixture("01_simple_text_scene.json");
    const poisoned = {
      ...raw,
      scenes: [
        {
          ...raw.scenes[0],
          transition: { type: "nonexistent_transition_abc", durationFrames: 15 },
        },
      ],
    };

    expect(() => parseCanonicalVideo(poisoned)).toThrow(/Invalid/);
  });

  it("rejects unknown template during canonical normalization fail-closed", () => {
    const raw = loadFixture("01_simple_text_scene.json");
    const poisoned = {
      ...raw,
      scenes: [
        {
          ...raw.scenes[0],
          template: "TotallyFakeTemplateNonexistent",
        },
      ],
    };

    const canonicalBp = parseCanonicalVideo(poisoned);
    expect(() =>
      normalizeCanonicalVideo({
        blueprint: canonicalBp,
      })
    ).toThrow(/Unknown template 'TotallyFakeTemplateNonexistent'/);
  });
});
