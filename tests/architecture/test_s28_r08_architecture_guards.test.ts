/**
 * tests/architecture/test_s28_r08_architecture_guards.test.ts
 * Architecture Guards for S28-R08: Renderer Registry & Engine Abstraction.
 * Enforces:
 *   - Canonical contracts have ZERO renderer packages imports (Remotion, React, FFmpeg, Canvas, DOM, WebGL)
 *   - Mutation core has ZERO imports from RendererRegistry or adapters
 *   - TemplateSpec core has ZERO imports from concrete renderers or RendererRegistry
 *   - Renderer registry has ZERO imports of document mutation functions (applyMutation, EditorSession)
 *   - Preview runtime does NOT act as a renderer authority
 *   - Single Renderer Authority invariant (CANONICAL_RENDERER_REGISTRY is the single authority)
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R08 Architecture Guards: Renderer Abstraction & Engine Decoupling", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const previewDir = path.resolve(rootDir, "preview");

  it("R08-AG-01: Canonical contracts in contracts/ have ZERO renderer packages imports", () => {
    const contractFiles = fs.readdirSync(contractsDir).filter((f) => f.endsWith(".ts"));

    const forbiddenPackages = [
      "remotion",
      "@remotion/cli",
      "@remotion/bundler",
      "@remotion/renderer",
      "react",
      "react-dom",
      "fluent-ffmpeg",
      "@ffmpeg/ffmpeg",
      "canvas",
      "three",
      "maplibre-gl",
    ];

    for (const file of contractFiles) {
      const fullPath = path.join(contractsDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      for (const pkg of forbiddenPackages) {
        const importRegex = new RegExp(`from\\s+["']${pkg}(?:/.*)?["']`);
        expect(
          content,
          `File contracts/${file} must NOT import renderer package '${pkg}'`
        ).not.toMatch(importRegex);
      }
    }
  });

  it("R08-AG-02: Mutation Core and EditorSession have ZERO imports from RendererRegistry or adapters", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bRendererRegistry\b/);
    expect(mContent).not.toMatch(/\bCANONICAL_RENDERER_REGISTRY\b/);
    expect(mContent).not.toMatch(/\bRendererAdapter\b/);
    expect(mContent).not.toMatch(/from\s+["']\.\/renderer["']/);

    expect(sContent).not.toMatch(/\bRendererRegistry\b/);
    expect(sContent).not.toMatch(/\bCANONICAL_RENDERER_REGISTRY\b/);
    expect(sContent).not.toMatch(/\bRendererAdapter\b/);
    expect(sContent).not.toMatch(/from\s+["']\.\/renderer["']/);
  });

  it("R08-AG-03: TemplateSpec and Instantiator have ZERO imports from concrete renderers or RendererRegistry", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/\bRendererRegistry\b/);
    expect(specContent).not.toMatch(/\bRendererAdapter\b/);
    expect(specContent).not.toMatch(/from\s+["']\.\/renderer["']/);

    expect(instContent).not.toMatch(/\bRendererRegistry\b/);
    expect(instContent).not.toMatch(/\bRendererAdapter\b/);
    expect(instContent).not.toMatch(/from\s+["']\.\/renderer["']/);
  });

  it("R08-AG-04: Renderer Registry does NOT import or execute canonical document mutations", () => {
    const rendererContract = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererContract, "utf-8");

    expect(content).not.toMatch(/applyMutation/);
    expect(content).not.toMatch(/EditorSession/);
    expect(content).not.toMatch(/from\s+["']\.\/mutations["']/);
    expect(content).not.toMatch(/from\s+["']\.\/editor-session["']/);
  });

  it("R08-AG-05: BrowserPreviewRuntime does NOT act as Renderer Authority or define competing renderer registry", () => {
    const runtimePath = path.join(previewDir, "preview-runtime.ts");
    const content = fs.readFileSync(runtimePath, "utf-8");

    expect(content).not.toMatch(/class RendererRegistry/);
    expect(content).not.toMatch(/exportVideo/);
    expect(content).not.toMatch(/export const RENDERER_REGISTRY/);
  });

  it("R08-AG-06: Single Renderer Authority invariant (CANONICAL_RENDERER_REGISTRY is the single registry authority)", () => {
    const rendererContract = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererContract, "utf-8");

    expect(content).toMatch(/export const CANONICAL_RENDERER_REGISTRY/);
    expect(content).toMatch(/class RendererRegistry/);
  });
});
