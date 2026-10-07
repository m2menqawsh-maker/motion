// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, waitFor } from "@testing-library/react";
import {
  parseRenderInput,
  UnknownTemplateError,
  UnknownEffectError,
  UnknownTransitionError,
} from "../../contracts/render-input";
import { InvalidTemplatePayloadError } from "../../contracts/template-schemas";
import { mergeProject } from "../../remotion-app/src/merge";
import { BlueprintVideo } from "../../remotion-app/src/BlueprintVideo";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

// Mock remotion environment
vi.mock("remotion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("remotion")>();
  return {
    ...actual,
    useCurrentFrame: () => 15,
    useVideoConfig: () => ({ fps: 30, durationInFrames: 300, width: 1080, height: 1920 }),
    delayRender: () => 1,
    continueRender: () => {},
    staticFile: (path: string) => path,
    AbsoluteFill: (props: any) => React.createElement("div", { ...props, "data-remotion-fill": "true" }, props.children),
    Sequence: (props: any) => React.createElement("div", { ...props, "data-remotion-seq": "true" }, props.children),
    Audio: (props: any) => React.createElement("audio", props),
    Img: (props: any) => React.createElement("img", props),
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

describe("S28-06A Render Smoke: COMPOSE & REUSE Pre-Mount and Mount Verification", () => {
  const validBrand = {
    brandName: "AcmeCorp",
    logoSrc: null,
    colors: { primary: "#00F5FF", accent: "#FFD700", background: "#0A0E27", text: "#FFFFFF" },
    fonts: { display: "Cairo", body: "Cairo" },
  };

  it("COMPOSE Render Smoke: mounts valid CompositionPlan blueprint without runtime crash", async () => {
    const composeBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_compose_smoke",
      fps: 30,
      aspect_ratio: "9:16",
      scenes: [
        {
          scene_id: "scene_compose_001",
          template: "rui-split-screen",
          startFrame: 0,
          durationFrames: 120,
          content: {
            text: "Compare legacy monolithic architecture with microservices.",
          },
          template_props: {
            text: "Microservices vs Monolith",
          },
          transition: {
            type: "fade",
            durationFrames: 15,
          },
          effects: [
            {
              effect: "Highlight",
              apply: "scene",
              params: {},
            },
          ],
        },
      ],
    };

    const validated = parseRenderInput({
      blueprint: composeBlueprint,
      brand: validBrand,
    });
    expect(validated).toBeDefined();

    const projectData = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
    expect(projectData.scenes.length).toBe(1);
    expect(projectData.scenes[0].template_props).toBeDefined();

    const { container } = render(
      React.createElement(BlueprintVideo, {
        projectData: projectData as any,
        brand: validBrand,
      })
    );

    expect(container).toBeDefined();
    await waitFor(() => {
      // Confirm Remotion container mounted after font/metadata loading
      const fill = container.querySelector('[data-remotion-fill="true"]');
      expect(fill).not.toBeNull();
    });
  });

  it("REUSE Render Smoke: mounts valid single-template REUSE blueprint without runtime crash", async () => {
    const reuseBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_reuse_smoke",
      fps: 30,
      aspect_ratio: "9:16",
      scenes: [
        {
          scene_id: "scene_reuse_001",
          template: "rui-stat-card",
          startFrame: 0,
          durationFrames: 90,
          content: {
            text: "Latency dropped by 80 percent.",
          },
          template_props: {
            text: "+80% Throughput",
            subtext: "Latency Reduction",
            numbers: "80%",
          },
          transition: {
            type: "fade",
            durationFrames: 15,
          },
          effects: [],
        },
      ],
    };

    const validated = parseRenderInput({
      blueprint: reuseBlueprint,
      brand: validBrand,
    });
    expect(validated).toBeDefined();

    const projectData = mergeProject(validated, (t) => TEMPLATE_REGISTRY[t]);
    expect(projectData.scenes.length).toBe(1);

    const { container } = render(
      React.createElement(BlueprintVideo, {
        projectData: projectData as any,
        brand: validBrand,
      })
    );

    expect(container).toBeDefined();
    await waitFor(() => {
      const fill = container.querySelector('[data-remotion-fill="true"]');
      expect(fill).not.toBeNull();
    });
  });

  it("Fail-Closed Boundary: rejects invalid component binding in COMPOSE before mount", () => {
    const invalidBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_bad_component",
      fps: 30,
      aspect_ratio: "9:16",
      scenes: [
        {
          scene_id: "scene_bad",
          template: "unregistered-fake-component-xyz",
          startFrame: 0,
          durationFrames: 60,
          template_props: {},
        },
      ],
    };

    expect(() =>
      parseRenderInput({
        blueprint: invalidBlueprint,
        brand: validBrand,
      })
    ).toThrow(UnknownTemplateError);
  });

  it("Fail-Closed Boundary: rejects unknown transition in COMPOSE before mount", () => {
    const badTransitionBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_bad_trans",
      fps: 30,
      aspect_ratio: "9:16",
      scenes: [
        {
          scene_id: "scene_bad_trans",
          template: "rui-stat-card",
          startFrame: 0,
          durationFrames: 60,
          template_props: {
            value: "100",
            label: "Metric",
          },
          transition: {
            type: "quantum_tunneling_super_wipe",
            durationFrames: 15,
          },
        },
      ],
    };

    expect(() =>
      parseRenderInput({
        blueprint: badTransitionBlueprint,
        brand: validBrand,
      })
    ).toThrow(UnknownTransitionError);
  });

  it("Fail-Closed Boundary: rejects unknown effect in COMPOSE before mount", () => {
    const badEffectBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_bad_effect",
      fps: 30,
      aspect_ratio: "9:16",
      scenes: [
        {
          scene_id: "scene_bad_eff",
          template: "rui-stat-card",
          startFrame: 0,
          durationFrames: 60,
          template_props: {
            value: "100",
            label: "Metric",
          },
          effects: [
            {
              effect: "NonExistentMagicalEffect",
              apply: "scene",
              params: {},
            },
          ],
        },
      ],
    };

    expect(() =>
      parseRenderInput({
        blueprint: badEffectBlueprint,
        brand: validBrand,
      })
    ).toThrow(UnknownEffectError);
  });

  it("Fail-Closed Boundary: rejects broken/poisoned props before component mount", () => {
    const poisonedBlueprint = {
      blueprint_version: "2.0.0",
      project_id: "prj_poisoned_props",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_poisoned",
          template: "rui-data-story",
          startFrame: 0,
          durationFrames: 60,
          template_props: {
            barData: "poisoned-string-should-be-array",
          },
        },
      ],
    };

    expect(() =>
      parseRenderInput({
        blueprint: poisonedBlueprint,
        brand: validBrand,
      })
    ).toThrow(InvalidTemplatePayloadError);
  });
});
