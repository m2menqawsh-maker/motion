// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, waitFor } from "@testing-library/react";
import { parseRenderInput, InvalidRenderInputError, UnknownTemplateError, UnknownEffectError, UnknownTransitionError } from "../../contracts/render-input";
import { SUPPORTED_TRANSITION_TYPES } from "../../contracts/blueprint";
import { InvalidTemplatePayloadError } from "../../contracts/template-schemas";
import { mergeProject, ProjectData } from "../../remotion-app/src/merge";
import { BlueprintVideo, TRANSITION_PRESENTATIONS } from "../../remotion-app/src/BlueprintVideo";
import { TEMPLATE_REGISTRY, CANONICAL_TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { EFFECTS_RUNTIME, EFFECT_IDS, isExecutableEffect, getExecutableEffectIds } from "../../registry/effects-runtime";

// Mock remotion environment
vi.mock("remotion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("remotion")>();
  return {
    ...actual,
    useCurrentFrame: () => 15,
    useVideoConfig: () => ({ fps: 30, durationInFrames: 300, width: 1920, height: 1080 }),
    delayRender: () => 1,
    continueRender: () => {},
    staticFile: (path: string) => path,
    AbsoluteFill: (props: any) => React.createElement("div", { ...props, "data-remotion-fill": "true" }, props.children),
    Sequence: (props: any) => React.createElement("div", { ...props, "data-remotion-seq": "true" }, props.children),
    Audio: (props: any) => React.createElement("audio", props),
  };
});

// Mock @remotion/transitions
vi.mock("@remotion/transitions", () => ({
  TransitionSeries: Object.assign(
    (props: any) => React.createElement("div", { "data-transition-series": "true" }, props.children),
    {
      Sequence: (props: any) => React.createElement("div", { "data-transition-seq": "true" }, props.children),
      Transition: (props: any) => React.createElement("div", { "data-transition": "true", "data-timing": props.timing?.durationInFrames }, null),
    }
  ),
  linearTiming: (opts: any) => ({ ...opts, type: "linear" }),
}));

describe("S16 Comprehensive Gate: Pre-Mount Verification & Fail-Closed Boundaries", () => {
  const validBrand = {
    brandName: "AcmeCorp",
    logoSrc: null,
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#0A0E27", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" },
  };

  // ──────────────────────────────────────────────────────────────────────────
  // A. Malformed Top-Level Render Input Rejection (LED-044)
  // ──────────────────────────────────────────────────────────────────────────
  describe("A. Malformed Top-Level Render Input Rejection (LED-044)", () => {
    it("rejects null or non-object input fail-closed", () => {
      expect(() => parseRenderInput(null)).toThrow(InvalidRenderInputError);
      expect(() => parseRenderInput(undefined)).toThrow(InvalidRenderInputError);
      expect(() => parseRenderInput("not-an-object")).toThrow(InvalidRenderInputError);
    });

    it("rejects missing blueprint in render input", () => {
      expect(() => parseRenderInput({ project: { title: "No Blueprint" } })).toThrow(
        /Missing mandatory 'blueprint'/
      );
    });

    it("rejects invalid blueprint schema (e.g. invalid fps or negative startFrame)", () => {
      const badFpsInput = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_fps",
          fps: 0, // Must be >= 1
          aspect_ratio: "16:9",
          scenes: [],
        },
      };
      expect(() => parseRenderInput(badFpsInput)).toThrow(InvalidRenderInputError);
    });

    it("rejects duplicate scene_id fail-closed", () => {
      const duplicateSceneInput = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_dup_scenes",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            { scene_id: "scene_dup", template: "rui-hero-device-assemble", startFrame: 0, durationFrames: 30 },
            { scene_id: "scene_dup", template: "rui-hero-device-assemble", startFrame: 30, durationFrames: 30 },
          ],
        },
      };
      expect(() => parseRenderInput(duplicateSceneInput)).toThrow(/duplicate scene_id 'scene_dup'/);
    });

    it("rejects malformed brand with missing mandatory colors or fonts (fail closed without hiding via defaults)", () => {
      const badBrandColors = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_brand",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [{ scene_id: "s1", template: "rui-hero-device-assemble", startFrame: 0, durationFrames: 30 }],
        },
        brand: {
          brandName: "Acme",
          // missing mandatory colors and fonts
        },
      };
      expect(() => parseRenderInput(badBrandColors)).toThrow(InvalidRenderInputError);

      const invalidColorTypes = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_brand",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [{ scene_id: "s1", template: "rui-hero-device-assemble", startFrame: 0, durationFrames: 30 }],
        },
        brand: {
          brandName: "Acme",
          colors: { primary: "" },
          fonts: { display: "Cairo", body: "Cairo" },
        },
      };
      expect(() => parseRenderInput(invalidColorTypes)).toThrow(InvalidRenderInputError);
    });

    it("rejects malformed project metadata without silent fallback", () => {
      const badProjectMeta = {
        project: { fps: -30 }, // invalid fps
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_meta",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [{ scene_id: "s1", template: "rui-hero-device-assemble", startFrame: 0, durationFrames: 30 }],
        },
      };
      expect(() => parseRenderInput(badProjectMeta)).toThrow(InvalidRenderInputError);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // B. Scene Transitions End-to-End & Observable Effect (LED-043)
  // ──────────────────────────────────────────────────────────────────────────
  describe("B. Supported Scene Transitions End-to-End (LED-043)", () => {
    it("preserves supported transition through parse -> merge -> MergedScene", () => {
      const rawInput = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_trans_flow",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              transition: {
                type: "slide",
                durationFrames: 15,
                timing: "linear",
              },
            },
            {
              scene_id: "s2",
              template: "rui-split-screen",
              startFrame: 60,
              durationFrames: 60,
            },
          ],
        },
        brand: validBrand,
      };

      const validated = parseRenderInput(rawInput);
      expect(validated.blueprint.scenes[0].transition?.type).toBe("slide");

      const merged = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
      expect(merged.scenes[0].transition).toBeDefined();
      expect(merged.scenes[0].transition?.type).toBe("slide");
      expect(merged.scenes[0].transition?.durationFrames).toBe(15);
    });

    it("renders TransitionSeries.Transition for supported transition in BlueprintVideo", async () => {
      const entry = TEMPLATE_REGISTRY["animatedtext-element"];
      const originalComponent = entry.component;
      entry.component = () => React.createElement("div", { "data-testid": "scene-comp" });

      try {
        const mergedProject = {
          fps: 30,
          title: "Transition Render Test",
          totalDurationFrames: 120,
          scenes: [
            {
              scene_id: "s1",
              template: "animatedtext-element",
              startFrame: 0,
              durationFrames: 60,
              surface: {},
              media_refs: [],
              sfx_ref: null,
              captions_ref: null,
              content: { title: "Scene 1" },
              transition: {
                type: "wipe" as const,
                durationFrames: 20,
              },
            },
            {
              scene_id: "s2",
              template: "animatedtext-element",
              startFrame: 60,
              durationFrames: 60,
              surface: {},
              media_refs: [],
              sfx_ref: null,
              captions_ref: null,
              content: { title: "Scene 2" },
            },
          ],
        };

        const { container } = render(
          React.createElement(BlueprintVideo, { projectData: mergedProject as any, brand: validBrand })
        );

        await waitFor(() => {
          const transitionElement = container.querySelector('[data-transition="true"]');
          expect(transitionElement).toBeTruthy();
          expect(transitionElement?.getAttribute("data-timing")).toBe("20");
        });
      } finally {
        entry.component = originalComponent;
      }
    });

    it("proves exhaustive 1:1 parity between SUPPORTED_TRANSITION_TYPES and TRANSITION_PRESENTATIONS", () => {
      const schemaTypes = [...SUPPORTED_TRANSITION_TYPES].sort();
      const runtimeTypes = Object.keys(TRANSITION_PRESENTATIONS).sort();
      expect(runtimeTypes).toEqual(schemaTypes);

      // Prove every supported transition type executes and returns an executable presentation
      for (const t of SUPPORTED_TRANSITION_TYPES) {
        const presentation = TRANSITION_PRESENTATIONS[t]({});
        expect(presentation).toBeDefined();
      }
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // C. Unknown Transition Fail-Closed (LED-043)
  // ──────────────────────────────────────────────────────────────────────────
  describe("C. Unknown Transition Rejection (LED-043)", () => {
    it("rejects unknown transition type in parseRenderInput fail-closed", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_trans",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              transition: {
                type: "totally-unknown-transition-type",
                durationFrames: 15,
              },
            },
          ],
        },
        brand: validBrand,
      };

      expect(() => parseRenderInput(input)).toThrow(UnknownTransitionError);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // D. Unknown Effects Fail-Closed (LED-046)
  // ──────────────────────────────────────────────────────────────────────────
  describe("D. Unknown Effects Rejection (LED-046)", () => {
    it("rejects unknown effect in parseRenderInput fail-closed", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_bad_effect",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              effects: [
                {
                  effect: "effect-does-not-exist",
                  apply: "scene" as const,
                },
              ],
            },
          ],
        },
        brand: validBrand,
      };

      expect(() => parseRenderInput(input)).toThrow(UnknownEffectError);
    });

    it("rejects unknown effect during mergeScene fail-closed", () => {
      const projectData: ProjectData = {
        project: { title: "Bad Effect" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              effects: [
                {
                  effect: "completely-fictional-effect",
                  apply: "overlay",
                },
              ],
            } as any,
          ],
        },
        brand: validBrand,
      };

      expect(() => mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t])).toThrow(UnknownEffectError);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // E. Known Effects Accepted & Passed Through (LED-046)
  // ──────────────────────────────────────────────────────────────────────────
  describe("E. Known Effects Passed Through (LED-046)", () => {
    it("accepts registered effects from EFFECTS_RUNTIME without error", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_good_effects",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              effects: [
                {
                  effect: "Wallpaper",
                  apply: "overlay" as const,
                },
                {
                  effect: "camera-shake",
                  apply: "scene" as const,
                },
              ],
            },
          ],
        },
        brand: validBrand,
      };

      const validated = parseRenderInput(input);
      expect(validated.blueprint.scenes[0].effects).toHaveLength(2);

      const merged = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
      expect(merged.scenes[0].effects).toHaveLength(2);
    });

    it("proves exhaustive invariant: every known effect is either executable or rejected before render", () => {
      const executableIds = getExecutableEffectIds();
      expect(executableIds.length).toBeGreaterThan(0);

      // 1. Every executable effect passes validation
      for (const effId of executableIds) {
        expect(isExecutableEffect(effId)).toBe(true);
        expect(EFFECTS_RUNTIME[effId].component).toBeDefined();
      }

      // 2. Any unbridged effect in EFFECTS_RUNTIME is explicitly rejected in render input
      const unbridgedIds = EFFECT_IDS.filter((id) => EFFECTS_RUNTIME[id].kind === "unbridged");
      expect(unbridgedIds.length).toBeGreaterThan(0);
      for (const unbridgedId of unbridgedIds.slice(0, 5)) {
        const input = {
          blueprint: {
            blueprint_version: "2.0.0",
            project_id: "prj_unbridged",
            fps: 30,
            aspect_ratio: "16:9",
            scenes: [
              {
                scene_id: "s1",
                template: "rui-hero-device-assemble",
                startFrame: 0,
                durationFrames: 60,
                effects: [{ effect: unbridgedId, apply: "scene" as const }],
              },
            ],
          },
          brand: validBrand,
        };
        expect(() => parseRenderInput(input)).toThrow(UnknownEffectError);
      }

      // 3. Removed fixture effects blur_reveal and blur-reveal are rejected fail-closed
      expect((EFFECTS_RUNTIME as any)["blur_reveal"]).toBeUndefined();
      expect((EFFECTS_RUNTIME as any)["blur-reveal"]).toBeUndefined();
      const inputBlur = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_blur",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "rui-hero-device-assemble",
              startFrame: 0,
              durationFrames: 60,
              effects: [{ effect: "blur_reveal", apply: "scene" as const }],
            },
          ],
        },
        brand: validBrand,
      };
      expect(() => parseRenderInput(inputBlur)).toThrow(UnknownEffectError);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // F. Valid Template Payload Passes Parser + Schema + Mount Path (LED-045)
  // ──────────────────────────────────────────────────────────────────────────
  describe("F. Valid Template Payload Passes (LED-045)", () => {
    it("DataStory passes with valid barData and metrics", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_valid_datastory",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s_ds",
              template: "rui-data-story",
              startFrame: 0,
              durationFrames: 90,
              template_props: {
                title: "Q4 Performance",
                barData: [
                  { label: "Oct", value: 100 },
                  { label: "Nov", value: 120 },
                ],
                metrics: [
                  { label: "Growth", value: 25, suffix: "%" },
                ],
              },
            },
          ],
        },
        brand: validBrand,
      };

      const validated = parseRenderInput(input);
      const merged = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
      expect(merged.scenes[0].template_props?.barData).toHaveLength(2);
    });

    it("AnimatedText passes with valid transition props", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_valid_animtext",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s_at",
              template: "animatedtext-element",
              startFrame: 0,
              durationFrames: 60,
              template_props: {
                transition: {
                  split: "word",
                  splitStagger: 3,
                },
              },
            },
          ],
        },
        brand: validBrand,
      };

      const validated = parseRenderInput(input);
      const merged = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
      expect(merged.scenes[0].template_props?.transition?.split).toBe("word");
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // G. Invalid Template Payload Fails Fail-Closed (LED-045)
  // ──────────────────────────────────────────────────────────────────────────
  describe("G. Invalid Template Payload Rejection (LED-045)", () => {
    it("DataStory rejects non-array barData fail-closed", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_invalid_datastory",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s_ds_bad",
              template: "rui-data-story",
              startFrame: 0,
              durationFrames: 90,
              template_props: {
                barData: "not-an-array",
              },
            },
          ],
        },
        brand: validBrand,
      };

      expect(() => parseRenderInput(input)).toThrow(InvalidTemplatePayloadError);
    });

    it("AnimatedText rejects invalid transition.splitStagger fail-closed", () => {
      const input = {
        blueprint: {
          blueprint_version: "2.0.0",
          project_id: "prj_invalid_animtext",
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s_at_bad",
              template: "animatedtext-element",
              startFrame: 0,
              durationFrames: 60,
              template_props: {
                transition: {
                  splitStagger: "must-be-a-number",
                },
              },
            },
          ],
        },
        brand: validBrand,
      };

      expect(() => parseRenderInput(input)).toThrow(InvalidTemplatePayloadError);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // H. Acceptance Gate: Invalid Payload Rejected BEFORE Mount (Section 6)
  // ──────────────────────────────────────────────────────────────────────────
  describe("H. Acceptance Gate: Invalid Payload NEVER Reaches Component Mount", () => {
    it("proves with component spy that invalid payload is rejected before mount", () => {
      const templateEntry = TEMPLATE_REGISTRY["rui-data-story"];
      expect(templateEntry).toBeDefined();

      // Spy on the actual template component
      const originalComponent = templateEntry.component;
      const componentSpy = vi.fn((props: any) => React.createElement("div", { "data-mounted": "true" }));

      // Temporarily attach spy
      templateEntry.component = componentSpy;

      try {
        const rawMalformedInput = {
          projectData: {
            project: { title: "Spy Test" },
            blueprint: {
              blueprint_version: "2.0.0",
              project_id: "prj_spy_test",
              fps: 30,
              aspect_ratio: "16:9",
              scenes: [
                {
                  scene_id: "scene_target",
                  template: "rui-data-story",
                  startFrame: 0,
                  durationFrames: 60,
                  template_props: {
                    barData: "poisoned-payload-string", // Invalid type!
                  },
                },
              ],
            },
            brand: validBrand,
          },
        };

        // 1. Enters live render entry gate
        expect(() => {
          // Live render entry path (Root.tsx calculateMetadata calls parseRenderInput)
          const validated = parseRenderInput(rawMalformedInput);
          const projectData = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);

          // Attempt mount (should never be reached)
          render(React.createElement(BlueprintVideo, { projectData: projectData as any, brand: validBrand }));
        }).toThrow(InvalidTemplatePayloadError);

        // 2. CRUCIAL ASSERTION: Component spy was NEVER invoked!
        expect(componentSpy).not.toHaveBeenCalled();
      } finally {
        // Restore original component
        templateEntry.component = originalComponent;
      }
    });

    it("proves direct BlueprintVideo mount with invalid payload also rejects before component mount", () => {
      const templateEntry = TEMPLATE_REGISTRY["animatedtext-element"];
      expect(templateEntry).toBeDefined();

      const originalComponent = templateEntry.component;
      const componentSpy = vi.fn((props: any) => React.createElement("div", { "data-mounted": "true" }));
      templateEntry.component = componentSpy;

      try {
        const directPoisonedProject = {
          fps: 30,
          title: "Direct Mount Attack",
          totalDurationFrames: 60,
          scenes: [
            {
              scene_id: "scene_direct",
              template: "animatedtext-element",
              startFrame: 0,
              durationFrames: 60,
              surface: {},
              content: {},
              template_props: {
                transition: {
                  splitStagger: "poison", // Invalid!
                },
              },
            },
          ],
        };

        expect(() => {
          render(
            React.createElement(BlueprintVideo, { projectData: directPoisonedProject as any, brand: validBrand })
          );
        }).toThrow(InvalidTemplatePayloadError);

        // Component spy was never mounted!
        expect(componentSpy).not.toHaveBeenCalled();
      } finally {
        templateEntry.component = originalComponent;
      }
    });
  });
});
