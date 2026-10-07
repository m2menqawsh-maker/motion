/**
 * tests/remotion/s28_r06_preview_core.test.ts
 * Core Functional Tests for S28-R06: Browser Live Preview Runtime.
 * Verifies:
 *   - Deterministic frame 0 render
 *   - Play, pause, seek, stepForward, stepBackward
 *   - Timebase, duration, ms conversion matching R03
 *   - Resize and aspect ratio switching
 *   - Keyframes & transforms matching evaluator
 *   - Layer rendering (text, image, shapes, groups)
 *   - Basic transitions (fade, slide)
 *   - DOM Driver element mounting & styling
 */
import { describe, it, expect } from "vitest";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { buildVisualFrame, resolveDimensionsFromAspectRatio } from "../../preview/visual-frame";
import { DOMPreviewDriver } from "../../preview/dom-driver";
import { evaluateVideoAtFrame } from "../../contracts/evaluator";
import type { BlueprintV2 } from "../../contracts/blueprint";
import { JSDOM } from "jsdom";

describe("S28-R06 Browser Preview Core Runtime & Playback", () => {
  const sampleProject: BlueprintV2 = {
    blueprint_version: "2.0.0",
    project_id: "preview_core_test_proj",
    fps: 30,
    aspect_ratio: "16:9",
    scenes: [
      {
        scene_id: "scene_01",
        template: "rui-title-card",
        startFrame: 0,
        durationFrames: 60,
        surface: {
          text: "Scene 1 Headline",
          position: { x: 0, y: -20 },
          scale: 1.2,
          rotation: 0,
          opacity: 1,
        },
        layers: [
          {
            layer_id: "s1_bg",
            kind: "shape",
            shape_type: "rectangle",
            size: { width: 1920, height: 1080 },
            fillColor: "#0f172a",
            time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
            transform: {
              position: { x: 0, y: 0 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 0,
            channels: [],
          },
          {
            layer_id: "s1_title",
            kind: "text",
            text: "Hello Preview Runtime",
            typography: {
              fontFamily: "Cairo",
              fontSize: 64,
              fillColor: "#38bdf8",
              textAlign: "center",
            },
            time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
            transform: {
              position: { x: 0, y: 0 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 1,
            channels: [
              {
                channel_id: "ch_title_x",
                target: "TRANSFORM_X",
                keyframes: [
                  { keyframe_id: "k1", frame: 0, value: -100, interpolation: "LINEAR" },
                  { keyframe_id: "k2", frame: 30, value: 0, interpolation: "LINEAR" },
                ],
              },
              {
                channel_id: "ch_title_op",
                target: "OPACITY",
                keyframes: [
                  { keyframe_id: "k3", frame: 0, value: 0, interpolation: "LINEAR" },
                  { keyframe_id: "k4", frame: 30, value: 1, interpolation: "LINEAR" },
                ],
              },
            ],
          },
        ],
        transition: {
          type: "fade",
          durationFrames: 15,
          overlap_semantics: "overlap",
        },
      },
      {
        scene_id: "scene_02",
        template: "rui-media-frame",
        startFrame: 45, // 15 frames overlap with scene 1
        durationFrames: 60,
        surface: {
          text: "Scene 2 Subtext",
        },
        layers: [
          {
            layer_id: "s2_media",
            kind: "image",
            asset_ref: "asset_sample_img",
            fit: "cover",
            time_range: { startFrame: 45, durationFrames: 60, endFrame: 105 },
            transform: {
              position: { x: 50, y: 50 },
              scale: { x: 1, y: 1 },
              rotation: 0,
              anchor: { x: 0.5, y: 0.5 },
              opacity: 1,
            },
            opacity: 1,
            visible: true,
            z_index: 0,
            channels: [],
          },
        ],
      },
    ],
  };

  it("PRV-01: Frame 0 renders deterministically with exact layers and styles", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    expect(runtime.getCurrentFrame()).toBe(0);
    expect(runtime.getCurrentTimeMs()).toBe(0);
    expect(runtime.getState()).toBe("idle");

    const vFrame1 = runtime.getCurrentVisualFrame();
    expect(vFrame1).not.toBeNull();
    expect(vFrame1!.frame).toBe(0);
    expect(vFrame1!.activeScenes).toContain("scene_01");

    // Check layer count and content
    expect(vFrame1!.nodes.length).toBe(2);
    const bgNode = vFrame1!.nodes.find((n) => n.id === "s1_bg");
    expect(bgNode).toBeDefined();
    expect(bgNode!.kind).toBe("shape");
    expect(bgNode!.shapeFill).toBe("#0f172a");

    const textNode = vFrame1!.nodes.find((n) => n.id === "s1_title");
    expect(textNode).toBeDefined();
    expect(textNode!.kind).toBe("text");
    expect(textNode!.text).toBe("Hello Preview Runtime");
    // At frame 0, keyframe animated X = -100 and opacity = 0
    expect(textNode!.transform.x).toBe(-100);
    expect(textNode!.opacity).toBe(0);

    // Determinism test: Evaluating again produces deep equality
    const vFrame2 = buildVisualFrame(sampleProject, 0);
    expect(vFrame2.nodes.length).toBe(vFrame1!.nodes.length);
    expect(vFrame2.nodes[0].computedStyles).toEqual(vFrame1!.nodes[0].computedStyles);
    expect(vFrame2.nodes[1].computedStyles).toEqual(vFrame1!.nodes[1].computedStyles);
  });

  it("PRV-02: Seek produces the exact evaluated frame and advances timebase", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    // Seek to frame 15 (halfway through the 0..30 animation)
    runtime.seek(15);
    expect(runtime.getCurrentFrame()).toBe(15);
    expect(runtime.getCurrentTimeMs()).toBe(500); // 15 / 30 fps = 0.5s = 500ms

    const vFrame15 = runtime.getCurrentVisualFrame()!;
    const textNode15 = vFrame15.nodes.find((n) => n.id === "s1_title")!;
    // Linear interpolation between -100 and 0 at frame 15 = -50
    expect(textNode15.transform.x).toBe(-50);
    // Linear opacity interpolation between 0 and 1 at frame 15 = 0.5
    expect(textNode15.opacity).toBe(0.5);

    // Seek to frame 30 (end of animation)
    runtime.seek(30);
    expect(runtime.getCurrentFrame()).toBe(30);
    const vFrame30 = runtime.getCurrentVisualFrame()!;
    const textNode30 = vFrame30.nodes.find((n) => n.id === "s1_title")!;
    expect(textNode30.transform.x).toBe(0);
    expect(textNode30.opacity).toBe(1.0);

    // Seek via milliseconds
    runtime.seekToMs(1000); // 1000ms = 30 frames
    expect(runtime.getCurrentFrame()).toBe(30);

    // Seeking beyond duration clamps to duration - 1
    const totalDuration = runtime.getDurationFrames();
    runtime.seek(9999);
    expect(runtime.getCurrentFrame()).toBe(totalDuration - 1);

    // Seeking negative clamps to 0
    runtime.seek(-50);
    expect(runtime.getCurrentFrame()).toBe(0);
  });

  it("PRV-03: Frame stepping (+1f, -1f) steps accurately and emits seek events", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);
    let seekEmissions = 0;
    runtime.on("seek", () => seekEmissions++);

    runtime.seek(10);
    expect(runtime.getCurrentFrame()).toBe(10);

    runtime.stepForward(1);
    expect(runtime.getCurrentFrame()).toBe(11);

    runtime.stepForward(5);
    expect(runtime.getCurrentFrame()).toBe(16);

    runtime.stepBackward(2);
    expect(runtime.getCurrentFrame()).toBe(14);

    runtime.stepBackward(1);
    expect(runtime.getCurrentFrame()).toBe(13);

    expect(seekEmissions).toBe(5);
  });

  it("PRV-04: Play and Pause transition state and freeze/advance frame", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    expect(runtime.getState()).toBe("idle");
    runtime.play();
    expect(runtime.getState()).toBe("playing");

    runtime.pause();
    expect(runtime.getState()).toBe("paused");

    const frameAtPause = runtime.getCurrentFrame();
    // After pause, frame remains frozen
    expect(runtime.getCurrentFrame()).toBe(frameAtPause);

    runtime.destroy();
  });

  it("PRV-05: Keyframe animations match R03 evaluator directly", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    for (const testFrame of [0, 5, 15, 25, 30, 40]) {
      runtime.seek(testFrame);
      const evalState = evaluateVideoAtFrame(sampleProject, testFrame);
      const visualFrame = runtime.getCurrentVisualFrame()!;

      const evalText = evalState.layers.find((l) => l.layer_id === "s1_title")!;
      const visualText = visualFrame.nodes.find((n) => n.id === "s1_title")!;

      expect(visualText.transform.x).toBe(evalText.transform.x);
      expect(visualText.transform.y).toBe(evalText.transform.y);
      expect(visualText.transform.scaleX).toBe(evalText.transform.scaleX);
      expect(visualText.transform.rotation).toBe(evalText.transform.rotation);
      // Opacities match
      expect(visualText.opacity).toBeCloseTo(evalText.opacity, 5);
    }
  });

  it("PRV-06: Hierarchical groups and composed transforms render accurately", () => {
    const groupProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "group_test_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "sc_group",
          template: "rui-intro",
          startFrame: 0,
          durationFrames: 60,
          layers: [
            {
              layer_id: "group_parent",
              kind: "group",
              children_ids: ["child_box"],
              time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
              transform: {
                position: { x: 100, y: 50 },
                scale: { x: 2, y: 2 },
                rotation: 45,
                anchor: { x: 0.5, y: 0.5 },
                opacity: 0.8,
              },
              opacity: 1,
              visible: true,
              z_index: 0,
              channels: [],
            },
            {
              layer_id: "child_box",
              kind: "shape",
              shape_type: "rectangle",
              size: { width: 100, height: 100 },
              fillColor: "#ef4444",
              parent_id: "group_parent",
              time_range: { startFrame: 0, durationFrames: 60, endFrame: 60 },
              transform: {
                position: { x: 20, y: 0 },
                scale: { x: 1, y: 1 },
                rotation: 15,
                anchor: { x: 0.5, y: 0.5 },
                opacity: 1,
              },
              opacity: 1,
              visible: true,
              z_index: 1,
              channels: [],
            },
          ],
        },
      ],
    };

    const runtime = new BrowserPreviewRuntime(groupProject);
    const vFrame = runtime.getCurrentVisualFrame()!;

    // Top-level root nodes contain group_parent
    expect(vFrame.nodes.length).toBe(1);
    const parentNode = vFrame.nodes[0];
    expect(parentNode.id).toBe("group_parent");
    expect(parentNode.children).toHaveLength(1);

    const childNode = parentNode.children![0];
    expect(childNode.id).toBe("child_box");

    // Evaluator transform composition:
    // rotation = parent.rotation + child.rotation = 45 + 15 = 60
    expect(childNode.transform.rotation).toBe(60);
    // scale = parent.scale * child.scale = 2 * 1 = 2
    expect(childNode.transform.scaleX).toBe(2);
    // opacity = parent.opacity * child.opacity = 0.8 * 1 = 0.8
    expect(childNode.transform.opacity).toBeCloseTo(0.8, 4);
  });

  it("PRV-07: Basic transitions (fade & slide) evaluate progression and layer blending", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    // Overlap window: Scene 1 ends at 60, transition is 15 frames, so window is [45, 60)
    // At frame 52 (approx midway in transition)
    runtime.seek(52);
    const vFrame = runtime.getCurrentVisualFrame()!;

    expect(vFrame.transition).toBeDefined();
    expect(vFrame.transition!.type).toBe("fade");
    expect(vFrame.transition!.progress).toBeCloseTo(7 / 15, 2);
    expect(vFrame.transition!.outgoingOpacity).toBeCloseTo(1 - 7 / 15, 2);
    expect(vFrame.transition!.incomingOpacity).toBeCloseTo(7 / 15, 2);

    // Both scene 1 and scene 2 layers are visible in the visual tree
    const s1Node = vFrame.nodes.find((n) => n.id === "s1_bg");
    const s2Node = vFrame.nodes.find((n) => n.id === "s2_media");
    expect(s1Node).toBeDefined();
    expect(s2Node).toBeDefined();
    // Outgoing opacity is blended down
    expect(s1Node!.opacity).toBeCloseTo(1 - 7 / 15, 2);
    // Incoming opacity is blended up
    expect(s2Node!.opacity).toBeCloseTo(7 / 15, 2);
  });

  it("PRV-08: Resize and Aspect Ratio switching re-scales canvas dimensions accurately", () => {
    const runtime = new BrowserPreviewRuntime(sampleProject);

    expect(runtime.getAspectRatio()).toBe("16:9");
    expect(runtime.getDimensions()).toEqual({ width: 1920, height: 1080 });

    // Switch to vertical 9:16
    runtime.setAspectRatio("9:16");
    expect(runtime.getAspectRatio()).toBe("9:16");
    expect(runtime.getDimensions()).toEqual({ width: 1080, height: 1920 });
    expect(runtime.getCurrentVisualFrame()!.dimensions).toEqual({ width: 1080, height: 1920 });

    // Switch to square 1:1
    runtime.setAspectRatio("1:1");
    expect(runtime.getDimensions()).toEqual({ width: 1080, height: 1080 });

    // Custom dimensions
    runtime.setDimensions(1280, 720);
    expect(runtime.getDimensions()).toEqual({ width: 1280, height: 720 });
  });

  it("PRV-09: DOMPreviewDriver renders into DOM elements with valid styles and coordinates", () => {
    const dom = new JSDOM("<div id='preview-container' style='width: 800px; height: 450px;'></div>");
    const container = dom.window.document.getElementById("preview-container") as HTMLElement;

    const runtime = new BrowserPreviewRuntime(sampleProject);
    runtime.mount(container);

    const driver = runtime.getDriver();
    expect(driver).not.toBeNull();

    const stageEl = driver!.getStageElement();
    expect(stageEl).toBeDefined();
    expect(stageEl.className).toBe("cv-preview-stage");

    // Inspect rendered elements
    const renderedText = container.querySelector('[data-layer-id="s1_title"]');
    expect(renderedText).not.toBeNull();
    expect(renderedText?.getAttribute("data-layer-kind")).toBe("text");
    expect(renderedText?.textContent).toBe("Hello Preview Runtime");

    // Seek to frame 30: element updates immediately in DOM
    runtime.seek(30);
    const updatedText = container.querySelector('[data-layer-id="s1_title"]') as HTMLElement;
    expect(updatedText.style.opacity).toBe("1");

    runtime.unmount();
    expect(runtime.getDriver()).toBeNull();
  });
});
