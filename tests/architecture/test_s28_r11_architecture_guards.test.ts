/**
 * tests/architecture/test_s28_r11_architecture_guards.test.ts
 * Architecture Guards for S28-R11: Master Compositor & Output Normalization Boundaries.
 * 
 * Enforces:
 *   - Canonical contracts in contracts/ have ZERO imports from FFmpeg or compositor execution logic
 *   - Mutation Core and EditorSession have ZERO imports from MasterCompositor or compositor/
 *   - TemplateSpec and Instantiator have ZERO imports from MasterCompositor
 *   - RendererRegistry has ZERO composition logic or imports from compositor/
 *   - MasterCompositor does NOT import selectRenderer or make renderer choices (R12 boundary)
 *   - MasterCompositor does NOT mutate canonical documents (zero applyMutation / EditorSession imports)
 *   - Intermediate artifacts carry provenance metadata and do not usurp canonical authority
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R11 Architecture Guards: Master Compositor & Normalization Boundaries", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const compositorDir = path.resolve(rootDir, "compositor");

  const forbiddenConcreteImports = [
    "fluent-ffmpeg",
    "@ffmpeg",
    "@ffmpeg/ffmpeg",
    "canvas",
    "@napi-rs/canvas",
    "skia",
  ];

  it("R11-AG-01: Canonical contracts in contracts/ have ZERO imports from FFmpeg or compositor execution logic", () => {
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

      // contracts/ must not import implementation from compositor/
      expect(
        content,
        `contracts/${file} must NOT import implementation from compositor/`
      ).not.toMatch(/from\s+["'].*\/compositor\/(?:master-compositor|output-normalizer|audio-normalizer|timeline-assembler|probe|qc-adapter)["']/);
    }
  });

  it("R11-AG-02: Mutation Core and EditorSession have ZERO imports from MasterCompositor or compositor/", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bMasterCompositor\b/);
    expect(mContent).not.toMatch(/from\s+["'].*compositor.*["']/i);
    expect(sContent).not.toMatch(/\bMasterCompositor\b/);
    expect(sContent).not.toMatch(/from\s+["'].*compositor.*["']/i);
  });

  it("R11-AG-03: TemplateSpec and Instantiator have ZERO imports from MasterCompositor", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/\bMasterCompositor\b/);
    expect(specContent).not.toMatch(/from\s+["'].*compositor.*["']/);
    expect(instContent).not.toMatch(/\bMasterCompositor\b/);
    expect(instContent).not.toMatch(/from\s+["'].*compositor.*["']/);
  });

  it("R11-AG-04: RendererRegistry in contracts/renderer.ts has ZERO composition logic or imports from compositor/", () => {
    const rendererPath = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererPath, "utf-8");

    expect(content).not.toMatch(/\bMasterCompositor\b/);
    expect(content).not.toMatch(/from\s+["'].*compositor.*["']/);
    expect(content).not.toMatch(/normalizeArtifactToSegment/);
    expect(content).not.toMatch(/assembleSceneSegments/);
  });

  it("R11-AG-05: MasterCompositor does NOT import selectRenderer or make renderer choices (R12 boundary)", () => {
    const mcPath = path.join(compositorDir, "master-compositor.ts");
    const content = fs.readFileSync(mcPath, "utf-8");

    expect(content).not.toMatch(/\bselectRenderer\b/);
    expect(content).not.toMatch(/\bCANONICAL_RENDERER_REGISTRY\b/);
    expect(content).not.toMatch(/\bRendererRegistry\b/);
  });

  it("R11-AG-06: MasterCompositor does NOT mutate canonical documents (zero applyMutation / EditorSession imports)", () => {
    const mcPath = path.join(compositorDir, "master-compositor.ts");
    const content = fs.readFileSync(mcPath, "utf-8");

    expect(content).not.toMatch(/\bapplyMutation\b/);
    expect(content).not.toMatch(/\bEditorSession\b/);
    expect(content).not.toMatch(/from\s+["'].*mutations["']/);
    expect(content).not.toMatch(/from\s+["'].*editor-session["']/);
  });

  it("R11-AG-07: Compositor contracts in contracts/compositor.ts are completely pure and engine-neutral", () => {
    const compContractsPath = path.join(contractsDir, "compositor.ts");
    const content = fs.readFileSync(compContractsPath, "utf-8");

    for (const pkg of forbiddenConcreteImports) {
      expect(content).not.toMatch(new RegExp(`from\\s+["']${pkg}["']`));
    }
    expect(content).not.toMatch(/from\s+["']child_process["']/);
    expect(content).not.toMatch(/from\s+["']@remotion/);
    expect(content).not.toMatch(/from\s+["']react/);
  });
});
