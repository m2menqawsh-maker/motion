import { describe, it, expect } from "vitest";
import { parseRenderInput, InvalidRenderInputError } from "../../contracts/render-input";
import { mergeProject } from "../../remotion-app/src/merge";
import { getRegistryEntry } from "../../registry/template-registry";

describe("S17: Unified Render Input Parity & parseRenderInput Integration", () => {
  const canonicalEnvelope = {
    projectData: {
      project: {
        title: "S17 Parity Test",
        fps: 30,
        project_id: "prj_s17_test"
      },
      blueprint: {
        blueprint_version: "2.0.0",
        project_id: "prj_s17_test",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [
          {
            scene_id: "scene_01",
            template: "HeroDeviceAssembleWrapper",
            startFrame: 0,
            durationFrames: 60,
            surface: {},
            media_refs: ["ast_demo_img"],
            content: {
              text: "Hello from S17"
            }
          }
        ]
      },
      brand: {
        brandName: "Acme Corp",
        logoSrc: null,
        colors: {
          primary: "#00F5FF",
          accent: "#FFD700",
          background: "#0A0E27",
          text: "#FFFFFF"
        },
        fonts: {
          display: "Cairo",
          body: "Cairo"
        }
      },
      overrides: {
        scenes: {
          scene_01: {
            props: {
              text: "Overridden Text"
            }
          }
        }
      },
      media_map: {
        ast_demo_img: "projects/prj_s17_test/demo.png"
      },
      asset_manifest: {
        manifest_version: "2.0.0",
        project_id: "prj_s17_test",
        created_at: "2026-09-28T12:00:00Z",
        assets: [
          {
            asset_id: "ast_demo_img",
            kind: "image",
            provenance: "user_upload",
            status: "ready",
            processed_path: "projects/prj_s17_test/demo.png",
            metadata: {}
          }
        ]
      }
    }
  };

  it("1. parseRenderInput parses the canonical S17 envelope successfully", () => {
    const validated = parseRenderInput(canonicalEnvelope);
    expect(validated).toBeDefined();
    expect(validated.project.project_id).toBe("prj_s17_test");
    expect(validated.project.fps).toBe(30);
    expect(validated.blueprint.scenes).toHaveLength(1);
    expect(validated.blueprint.scenes[0].scene_id).toBe("scene_01");
    expect(validated.brand.brandName).toBe("Acme Corp");
    expect(validated.media_map).toBeDefined();
    expect(validated.media_map?.["ast_demo_img"]).toBe("projects/prj_s17_test/demo.png");
    expect(validated.asset_manifest).toBeDefined();
  });

  it("2. mergeProject cleanly consumes the validated canonical render input", () => {
    const validated = parseRenderInput(canonicalEnvelope);
    const merged = mergeProject(validated, (template) => getRegistryEntry(template));
    expect(merged.scenes).toHaveLength(1);
    expect(merged.scenes[0].scene_id).toBe("scene_01");
    expect(merged.scenes[0].media_refs[0]).toBe("projects/prj_s17_test/demo.png");
  });

  it("3. parseRenderInput handles unwrapped projectData identically", () => {
    const validated = parseRenderInput(canonicalEnvelope.projectData);
    expect(validated.project.project_id).toBe("prj_s17_test");
    expect(validated.blueprint.scenes).toHaveLength(1);
  });

  it("4. rejects missing blueprint fail-closed", () => {
    const invalidEnvelope = {
      projectData: {
        project: { title: "No BP" },
        brand: canonicalEnvelope.projectData.brand
      }
    };
    expect(() => parseRenderInput(invalidEnvelope)).toThrowError(InvalidRenderInputError);
  });

  it("5. rejects null or empty render input fail-closed", () => {
    expect(() => parseRenderInput(null)).toThrowError(InvalidRenderInputError);
    expect(() => parseRenderInput({})).toThrowError(InvalidRenderInputError);
  });

  it("6. validates live generated render_props.json from Python build_render_input", () => {
    const livePropsPath = process.env.LIVE_RENDER_PROPS_PATH;
    if (livePropsPath) {
      const fs = require("fs");
      expect(fs.existsSync(livePropsPath)).toBe(true);
      const raw = JSON.parse(fs.readFileSync(livePropsPath, "utf-8"));
      const validated = parseRenderInput(raw);
      expect(validated).toBeDefined();
      expect(validated.blueprint.scenes).toHaveLength(1);
      expect(validated.blueprint.scenes[0].scene_id).toBe("scene_01");
      expect(validated.project.project_id).toBe("prj_ts_roundtrip_11");
    }
  });
});
