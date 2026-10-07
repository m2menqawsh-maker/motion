/**
 * tests/architecture/test_s28_r12_architecture_guards.test.ts
 * Architecture Guards for S28-R12: Multi-Engine RenderGraph & Render Planner Boundaries.
 * 
 * Enforces:
 *   - Canonical contracts in contracts/ have ZERO imports from planner/ implementation
 *   - Mutation Core and EditorSession have ZERO imports from RenderGraph or RenderPlanner
 *   - TemplateSpec has ZERO imports from concrete renderers
 *   - RenderPlanner has ZERO direct rendering implementation imports (Remotion bundler, Canvas drawing)
 *   - RenderPlanner has ZERO imports from FFmpeg
 *   - RendererRegistry has ZERO planning policy or imports from planner/
 *   - MasterCompositor has ZERO renderer selection logic (selectRenderer)
 *   - RenderGraphExecutor has ZERO canonical mutation logic (applyMutation / EditorSession)
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R12 Architecture Guards: RenderGraph & Planner Boundaries", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const plannerDir = path.resolve(rootDir, "planner");
  const compositorDir = path.resolve(rootDir, "compositor");

  it("R12-AG-01: Canonical contracts in contracts/ have ZERO imports from planner/ implementation", () => {
    const files = fs.readdirSync(contractsDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(contractsDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(
        content,
        `contracts/${file} must NOT import implementation from planner/`
      ).not.toMatch(/from\s+["'].*\/planner\/(?:render-planner|render-graph-executor|planning-policy|cache-evaluator|cost-estimator)["']/);
    }
  });

  it("R12-AG-02: Mutation Core and EditorSession have ZERO imports from RenderGraph or RenderPlanner", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bRenderPlanner\b/);
    expect(mContent).not.toMatch(/\bRenderGraph\b/);
    expect(mContent).not.toMatch(/from\s+["'].*planner.*["']/i);

    expect(sContent).not.toMatch(/\bRenderPlanner\b/);
    expect(sContent).not.toMatch(/\bRenderGraph\b/);
    expect(sContent).not.toMatch(/from\s+["'].*planner.*["']/i);
  });

  it("R12-AG-03: TemplateSpec and Instantiator have ZERO imports from concrete renderers", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/from\s+["'].*remotion-renderer-adapter.*["']/);
    expect(specContent).not.toMatch(/from\s+["'].*canvas-renderer-adapter.*["']/);

    expect(instContent).not.toMatch(/from\s+["'].*remotion-renderer-adapter.*["']/);
    expect(instContent).not.toMatch(/from\s+["'].*canvas-renderer-adapter.*["']/);
  });

  it("R12-AG-04: RenderPlanner has ZERO direct rendering implementation imports (Remotion bundler / Canvas)", () => {
    const plannerPath = path.join(plannerDir, "render-planner.ts");
    const content = fs.readFileSync(plannerPath, "utf-8");

    expect(content).not.toMatch(/from\s+["']@remotion\/bundler["']/);
    expect(content).not.toMatch(/from\s+["']@remotion\/renderer["']/);
    expect(content).not.toMatch(/from\s+["'].*canvas-renderer-adapter["']/);
    expect(content).not.toMatch(/\bcreateCanvasRendererAdapter\b/);
    expect(content).not.toMatch(/\bcreateRemotionRendererAdapter\b/);
  });

  it("R12-AG-05: RenderPlanner has ZERO FFmpeg imports or direct execution", () => {
    const plannerFiles = fs.readdirSync(plannerDir).filter((f) => f.endsWith(".ts"));

    for (const file of plannerFiles) {
      if (file === "render-graph-executor.ts") continue; // Executor calls MasterCompositor and adapters
      const fullPath = path.join(plannerDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content, `planner/${file} must NOT import fluent-ffmpeg`).not.toMatch(/from\s+["']fluent-ffmpeg["']/);
      expect(content, `planner/${file} must NOT import @ffmpeg`).not.toMatch(/from\s+["']@ffmpeg/);
      expect(content, `planner/${file} must NOT execute ffmpeg directly`).not.toMatch(/execFileSync\s*\(\s*["']ffmpeg/);
      expect(content, `planner/${file} must NOT execute ffmpeg directly`).not.toMatch(/spawn\s*\(\s*["']ffmpeg/);
    }
  });

  it("R12-AG-06: RendererRegistry in contracts/renderer.ts has ZERO planning policy or imports from planner/", () => {
    const rendererPath = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererPath, "utf-8");

    expect(content).not.toMatch(/from\s+["'].*planner.*["']/i);
    expect(content).not.toMatch(/\bRenderPlanner\b/);
    expect(content).not.toMatch(/\bPlanningPolicy\b/);
    expect(content).not.toMatch(/\bRenderGraph\b/);
  });

  it("R12-AG-07: MasterCompositor has ZERO renderer selection logic (selectRenderer)", () => {
    const mcPath = path.join(compositorDir, "master-compositor.ts");
    const content = fs.readFileSync(mcPath, "utf-8");

    expect(content).not.toMatch(/\bselectRenderer\b/);
    expect(content).not.toMatch(/\bCANONICAL_RENDERER_REGISTRY\b/);
    expect(content).not.toMatch(/\bRendererRegistry\b/);
  });

  it("R12-AG-08: RenderGraphExecutor has ZERO canonical mutation logic (applyMutation / EditorSession)", () => {
    const execPath = path.join(plannerDir, "render-graph-executor.ts");
    const content = fs.readFileSync(execPath, "utf-8");

    expect(content).not.toMatch(/\bapplyMutation\b/);
    expect(content).not.toMatch(/\bEditorSession\b/);
    expect(content).not.toMatch(/from\s+["'].*mutations["']/);
    expect(content).not.toMatch(/from\s+["'].*editor-session["']/);
  });
});
