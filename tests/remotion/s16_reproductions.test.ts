// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { mergeProject, ProjectData } from "../../remotion-app/src/merge";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

describe("S16 Red Reproductions: LED-043, LED-044, LED-045, LED-046", () => {
  const baseBrand = {
    brandName: "TestBrand",
    logoSrc: null,
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#0A0E27", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" }
  };

  // ──────────────────────────────────────────────────────────────────────────
  // Finding 1: LED-043 — Transition dropped in mergeScene or unknown transition allowed
  // ──────────────────────────────────────────────────────────────────────────
  describe("LED-043: Transition end-to-end propagation and fail-closed validation", () => {
    it("REPRODUCTION: supported transition must NOT be dropped by mergeProject", () => {
      const projectData: ProjectData = {
        project: { title: "Transition Test" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "HeroDeviceAssembleWrapper",
              startFrame: 0,
              durationFrames: 60,
              transition: {
                type: "slide",
                durationFrames: 20
              }
            } as any
          ]
        },
        brand: baseBrand
      };

      const merged = mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t]);
      const mergedScene = merged.scenes[0] as any;

      // RED: on current HEAD, mergeScene drops transition! mergedScene.transition is undefined.
      expect(mergedScene.transition).toBeDefined();
      expect(mergedScene.transition?.type).toBe("slide");
      expect(mergedScene.transition?.durationFrames).toBe(20);
    });

    it("REPRODUCTION: unknown transition must fail closed before mount", () => {
      const projectData: ProjectData = {
        project: { title: "Bad Transition Test" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "s1",
              template: "HeroDeviceAssembleWrapper",
              startFrame: 0,
              durationFrames: 60,
              transition: {
                type: "unknown-transition-does-not-exist",
                durationFrames: 15
              }
            } as any
          ]
        },
        brand: baseBrand
      };

      // RED: on current HEAD, mergeProject doesn't validate transitions and drops it silently.
      expect(() => {
        mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t]);
      }).toThrow(/UNKNOWN_TRANSITION|Unknown transition/i);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Finding 2: LED-044 — Full Blueprint parser is not the live render entry
  // ──────────────────────────────────────────────────────────────────────────
  describe("LED-044: parseRenderInput is the single canonical runtime gate", () => {
    it("REPRODUCTION: live render input currently reaches mergeProject without full blueprint schema validation", () => {
      // Simulate live render entry props reaching mergeProject directly (as Root.tsx currently does)
      const rawLiveProps: any = {
        project: { title: "Unvalidated" },
        blueprint: {
          // Missing required blueprint fields like aspect_ratio, fps, etc.
          scenes: [
            {
              scene_id: "s1",
              template: "HeroDeviceAssembleWrapper",
              startFrame: 0,
              durationFrames: 30
            }
          ]
        },
        brand: baseBrand
      };

      // In Root.tsx: `const projectData = mergeProject(rawData, ...)`
      // RED: Currently on HEAD, mergeProject accepts this unvalidated payload without checking Blueprint schema!
      // When canonical parseRenderInput gate is in place, raw unvalidated input must be rejected fail-closed.
      expect(() => {
        // If an entry gate was enforcing blueprint validation, this malformed blueprint (missing aspect_ratio) would fail
        // Currently on HEAD, mergeProject succeeds without validating aspect_ratio or BlueprintSchema:
        const merged = mergeProject(rawLiveProps, (t) => TEMPLATE_REGISTRY[t]);
        // If it merged without failing, that proves the finding: live entry bypasses full blueprint validation!
        if (merged) {
          throw new Error("PROVED_LEAK: malformed blueprint bypassed validation and merged successfully");
        }
      }).toThrow(/INVALID_RENDER_INPUT|Invalid Blueprint|aspect_ratio/);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Finding 3: LED-045 — Template-Specific Runtime Schemas (DataStory & AnimatedText)
  // ──────────────────────────────────────────────────────────────────────────
  describe("LED-045: Template payload validation before mount", () => {
    it("REPRODUCTION: DataStory rejects invalid barData payload before mount", () => {
      const projectData: ProjectData = {
        project: { title: "DataStory Test" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "scene_datastory",
              template: "rui-data-story",
              startFrame: 0,
              durationFrames: 60,
              template_props: {
                barData: "invalid-string-should-be-array"
              }
            } as any
          ]
        },
        brand: baseBrand
      };

      // RED: on current HEAD, mergeProject accepts invalid template_props without validation!
      expect(() => {
        mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t]);
      }).toThrow(/INVALID_TEMPLATE_PAYLOAD|Template payload validation failed/i);
    });

    it("REPRODUCTION: AnimatedText rejects invalid transition payload before mount", () => {
      const projectData: ProjectData = {
        project: { title: "AnimatedText Test" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "scene_animtext",
              template: "animatedtext-element",
              startFrame: 0,
              durationFrames: 60,
              template_props: {
                transition: {
                  splitStagger: "not-a-number-must-be-number"
                }
              }
            } as any
          ]
        },
        brand: baseBrand
      };

      // RED: on current HEAD, mergeProject accepts invalid template_props without validation!
      expect(() => {
        mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t]);
      }).toThrow(/INVALID_TEMPLATE_PAYLOAD|Template payload validation failed/i);
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Finding 4: LED-046 — Unknown effects must fail closed before mount/render
  // ──────────────────────────────────────────────────────────────────────────
  describe("LED-046: Unknown effects fail-closed before render", () => {
    it("REPRODUCTION: unknown effect must throw fail-closed error before mount", () => {
      const projectData: ProjectData = {
        project: { title: "Unknown Effect Test" },
        blueprint: {
          fps: 30,
          aspect_ratio: "16:9",
          scenes: [
            {
              scene_id: "scene_effects",
              template: "HeroDeviceAssembleWrapper",
              startFrame: 0,
              durationFrames: 60,
              effects: [
                {
                  effect: "effect-does-not-exist",
                  apply: "scene"
                }
              ]
            } as any
          ]
        },
        brand: baseBrand
      };

      // RED: on current HEAD, mergeProject ignores unknown effect and BlueprintVideo drops it as no-op!
      expect(() => {
        mergeProject(projectData, (t) => TEMPLATE_REGISTRY[t]);
      }).toThrow(/UNKNOWN_EFFECT|Unknown effect/i);
    });
  });
});
