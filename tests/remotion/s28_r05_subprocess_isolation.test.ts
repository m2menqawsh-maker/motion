/**
 * tests/remotion/s28_r05_subprocess_isolation.test.ts
 * Critical Architectural Gate for S28-R05:
 * Proves that NATIVE templates load, validate, instantiate, normalize,
 * and evaluate in an isolated Node process where React and Remotion
 * are completely blocked at module loader level.
 */
import { describe, it, expect } from "vitest";
import { spawnSync } from "child_process";
import * as path from "path";

describe("S28-R05 Engine-Free Subprocess Isolation: TemplateSpec Instantiation", () => {
  const rootDir = path.resolve(__dirname, "../..");

  it("R05-ISO-01: Native templates instantiate and evaluate in pure isolated Node process with React/Remotion blocked", () => {
    const isolationScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = [
        "react",
        "react-dom",
        "remotion",
        "@remotion/transitions",
        "@remotion/core",
        "@remotion/cli",
        "@remotion/google-fonts"
      ];

      Module.prototype.require = function(id) {
        for (const b of blocked) {
          if (id === b || id.startsWith(b + "/")) {
            throw new Error("ISOLATION_VIOLATION_MODULE_LOADED: " + id);
          }
        }
        return origRequire.apply(this, arguments);
      };

      async function run() {
        const { getSemanticTemplateSpec, getAllSemanticTemplateSpecs } = await import("./registry/semantic-registry.ts");
        const { instantiateTemplate } = await import("./contracts/template-instantiator.ts");
        const { BlueprintSceneSchema } = await import("./contracts/blueprint.ts");
        const { validateLayerHierarchy } = await import("./contracts/layers.ts");
        const { normalizeCanonicalVideo } = await import("./contracts/normalization.ts");
        const { evaluateVideoAtFrame } = await import("./contracts/evaluator.ts");

        // 1. Verify registry loads without React or Remotion
        const allSpecs = getAllSemanticTemplateSpecs();
        if (!allSpecs || allSpecs.length !== 105) {
          throw new Error("Registry failed to load all 105 specs in isolated process: " + (allSpecs ? allSpecs.length : 0));
        }

        // 2. Instantiate representative native templates
        const nativeTemplatesToTest = [
          { id: "rui-title-card", inputs: { title: "Isolated Title", subtitle: "Isolated Subtitle" } },
          { id: "rui-stat-card", inputs: { label: "Isolated Metric", value: 42 } },
          { id: "rui-intro", inputs: { title: "Isolated Intro", tagline: "Tagline" } },
          { id: "rui-lower-third", inputs: { title: "Speaker Name", subtitle: "Role" } },
          { id: "fade-transition", inputs: { durationFrames: 15 } }
        ];

        const generatedScenes = [];

        for (const tpl of nativeTemplatesToTest) {
          const res = instantiateTemplate(tpl.id, tpl.inputs, {
            scene_id: "iso_" + tpl.id.replace(/-/g, "_"),
            startFrame: generatedScenes.length * 90,
            durationFrames: 90,
            fps: 30
          });

          if (!res.ok) throw new Error("Template " + tpl.id + " failed instantiation");
          if (res.classification !== "NATIVE") throw new Error("Template " + tpl.id + " unexpected classification " + res.classification);

          // Validate canonical scene schema
          BlueprintSceneSchema.parse(res.scene);

          // Validate canonical layer hierarchy
          const hier = validateLayerHierarchy(res.layers);
          if (!hier.ok) throw new Error("Hierarchy errors for " + tpl.id + ": " + hier.errors.join(", "));

          generatedScenes.push(res.scene);
        }

        // 3. Assemble and normalize complete canonical video document
        const canonicalVideoInput = {
          project: { title: "Isolated Subprocess Video", fps: 30 },
          blueprint: {
            blueprint_version: "2.0.0",
            project_id: "iso_project_01",
            fps: 30,
            aspect_ratio: "16:9",
            scenes: generatedScenes
          }
        };

        const normalized = normalizeCanonicalVideo(canonicalVideoInput);
        if (!normalized || normalized.scenes.length !== generatedScenes.length) {
          throw new Error("Normalization failed in isolated subprocess");
        }

        // 4. Deterministic frame evaluation across scenes
        for (let frame = 0; frame < 300; frame += 60) {
          const evalState = evaluateVideoAtFrame(normalized, frame);
          if (!evalState || typeof evalState.frame !== "number") {
            throw new Error("Frame evaluation failed at frame " + frame);
          }
        }

        console.log(JSON.stringify({
          success: true,
          specsLoaded: allSpecs.length,
          scenesInstantiated: generatedScenes.length,
          normalizedScenes: normalized.scenes.length,
          frameworkViolations: 0
        }));
      }

      run().catch((err) => {
        console.error("ISOLATION_FAILURE:", err.stack || err);
        process.exit(1);
      });
    `;

    const res = spawnSync("npx", ["tsx", "-e", isolationScript], {
      cwd: rootDir,
      encoding: "utf-8",
      env: { ...process.env, NODE_ENV: "production" },
      timeout: 10000,
    });

    if (res.status !== 0) {
      console.error("Subprocess stderr:", res.stderr);
      console.error("Subprocess stdout:", res.stdout);
    }

    expect(res.status, `Subprocess failed with status ${res.status}: ${res.stderr}`).toBe(0);
    const parsed = JSON.parse(res.stdout.trim().split("\n").pop()!);
    expect(parsed.success).toBe(true);
    expect(parsed.specsLoaded).toBe(105);
    expect(parsed.scenesInstantiated).toBe(5);
    expect(parsed.normalizedScenes).toBe(5);
    expect(parsed.frameworkViolations).toBe(0);
  }, 15000);
});
