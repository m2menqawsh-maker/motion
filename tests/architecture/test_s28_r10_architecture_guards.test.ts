/**
 * tests/architecture/test_s28_r10_architecture_guards.test.ts
 * Architecture Guards for S28-R10: Canvas Renderer Adapter & Engine Isolation.
 * 
 * Enforces:
 *   - Canonical contracts in contracts/ have ZERO imports from Canvas or FFmpeg packages
 *   - Mutation Core and EditorSession have ZERO imports from CanvasRendererAdapter
 *   - TemplateSpec and Instantiator have ZERO imports from CanvasRendererAdapter
 *   - BrowserPreviewRuntime has ZERO imports from CanvasRendererAdapter
 *   - RendererRegistry has ZERO engine-specific execution logic
 *   - CanvasRendererAdapter does NOT mutate canonical documents (reads canonical state only)
 *   - Concrete dependencies stay strictly inside adapter boundary (canvas/)
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R10 Architecture Guards: Canvas Adapter Boundary & Multi-Engine Decoupling", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const previewDir = path.resolve(rootDir, "preview");
  const canvasDir = path.resolve(rootDir, "canvas");

  const forbiddenConcreteImports = [
    "fluent-ffmpeg",
    "@ffmpeg",
    "canvas",
    "@napi-rs/canvas",
    "skia",
  ];

  it("R10-AG-01: Canonical contracts in contracts/ have ZERO imports from Canvas or FFmpeg packages", () => {
    const files = fs.readdirSync(contractsDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(contractsDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      for (const pkg of forbiddenConcreteImports) {
        const importRegex = new RegExp(`from\\s+["']${pkg}(?:/.*)?["']`);
        expect(
          content,
          `contracts/${file} must NOT import concrete engine package '${pkg}'`
        ).not.toMatch(importRegex);
      }
    }
  });

  it("R10-AG-02: Mutation Core and EditorSession have ZERO imports from CanvasRendererAdapter", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(mContent).not.toMatch(/from\s+["'].*canvas.*["']/i);
    expect(sContent).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(sContent).not.toMatch(/from\s+["'].*canvas.*["']/i);
  });

  it("R10-AG-03: TemplateSpec and Instantiator have ZERO imports from CanvasRendererAdapter", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(specContent).not.toMatch(/from\s+["'].*canvas.*["']/);
    expect(instContent).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(instContent).not.toMatch(/from\s+["'].*canvas.*["']/);
  });

  it("R10-AG-04: BrowserPreviewRuntime has ZERO imports from CanvasRendererAdapter", () => {
    const runtimePath = path.join(previewDir, "preview-runtime.ts");
    const content = fs.readFileSync(runtimePath, "utf-8");

    expect(content).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(content).not.toMatch(/from\s+["'].*canvas.*["']/);
  });

  it("R10-AG-05: RendererRegistry in contracts/renderer.ts has ZERO Canvas-specific execution logic", () => {
    const rendererPath = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererPath, "utf-8");

    for (const pkg of forbiddenConcreteImports) {
      expect(content).not.toMatch(new RegExp(`from\\s+["']${pkg}["']`));
    }
  });

  it("R10-AG-06: CanvasRendererAdapter does NOT mutate canonical documents (reads canonical state only)", () => {
    const adapterPath = path.join(canvasDir, "canvas-renderer-adapter.ts");
    const content = fs.readFileSync(adapterPath, "utf-8");

    // Zero direct mutation imports
    expect(content).not.toMatch(/applyMutation/);
    expect(content).not.toMatch(/EditorSession/);
    expect(content).not.toMatch(/from\s+["'].*mutations["']/);
    expect(content).not.toMatch(/from\s+["'].*editor-session["']/);
  });

  it("R10-AG-07: CanvasRendererAdapter resides strictly in canvas/ adapter boundary", () => {
    const adapterPath = path.join(canvasDir, "canvas-renderer-adapter.ts");
    expect(fs.existsSync(adapterPath)).toBe(true);

    const indexPath = path.join(canvasDir, "index.ts");
    expect(fs.existsSync(indexPath)).toBe(true);
  });
});
