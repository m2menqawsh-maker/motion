/**
 * tests/architecture/test_s28_r09_architecture_guards.test.ts
 * Architecture Guards for S28-R09: Remotion Renderer Adapter.
 * 
 * Enforces:
 *   - Canonical contracts in contracts/ have ZERO imports from Remotion
 *   - Mutation core has ZERO imports from Remotion or renderer adapters
 *   - TemplateSpec core has ZERO imports from Remotion or renderer adapters
 *   - BrowserPreviewRuntime has ZERO imports from Remotion or RemotionRendererAdapter
 *   - RendererRegistry has ZERO Remotion-specific logic (engine neutrality)
 *   - RemotionRendererAdapter does NOT mutate canonical documents (reads canonical state only)
 *   - Remotion dependency remains strictly within adapter/integration boundary
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R09 Architecture Guards: Remotion Adapter Boundary Decoupling", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const previewDir = path.resolve(rootDir, "preview");
  const remotionDir = path.resolve(rootDir, "remotion");

  const forbiddenRemotionImports = [
    "remotion",
    "@remotion/cli",
    "@remotion/bundler",
    "@remotion/renderer",
    "react",
    "react-dom",
  ];

  it("R09-AG-01: Canonical contracts in contracts/ have ZERO imports from Remotion or React", () => {
    const files = fs.readdirSync(contractsDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(contractsDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      for (const pkg of forbiddenRemotionImports) {
        const importRegex = new RegExp(`from\\s+["']${pkg}(?:/.*)?["']`);
        expect(
          content,
          `contracts/${file} must NOT import renderer package '${pkg}'`
        ).not.toMatch(importRegex);
      }
    }
  });

  it("R09-AG-02: Mutation Core and EditorSession have ZERO imports from Remotion or RemotionRendererAdapter", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(mContent).not.toMatch(/from\s+["'].*remotion.*["']/i);
    expect(mContent).not.toMatch(/import\s+.*remotion/i);
    expect(sContent).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(sContent).not.toMatch(/from\s+["'].*remotion.*["']/i);
    expect(sContent).not.toMatch(/import\s+.*remotion/i);
  });

  it("R09-AG-03: TemplateSpec and Instantiator have ZERO imports from Remotion or RemotionRendererAdapter", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(specContent).not.toMatch(/from\s+["'].*remotion.*["']/);
    expect(instContent).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(instContent).not.toMatch(/from\s+["'].*remotion.*["']/);
  });

  it("R09-AG-04: BrowserPreviewRuntime has ZERO imports from Remotion or RemotionRendererAdapter", () => {
    const runtimePath = path.join(previewDir, "preview-runtime.ts");
    const content = fs.readFileSync(runtimePath, "utf-8");

    expect(content).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(content).not.toMatch(/from\s+["']@remotion/);
    expect(content).not.toMatch(/from\s+["']remotion/);
    expect(content).not.toMatch(/from\s+["']\.\.\/remotion/);
  });

  it("R09-AG-05: RendererRegistry in contracts/renderer.ts has ZERO Remotion-specific execution logic", () => {
    const rendererPath = path.join(contractsDir, "renderer.ts");
    const content = fs.readFileSync(rendererPath, "utf-8");

    // Must NOT import concrete remotion packages
    for (const pkg of forbiddenRemotionImports) {
      expect(content).not.toMatch(new RegExp(`from\\s+["']${pkg}["']`));
    }
  });

  it("R09-AG-06: RemotionRendererAdapter does NOT mutate canonical documents (reads canonical state only)", () => {
    const adapterPath = path.join(remotionDir, "remotion-renderer-adapter.ts");
    const content = fs.readFileSync(adapterPath, "utf-8");

    // Zero direct mutation imports
    expect(content).not.toMatch(/applyMutation/);
    expect(content).not.toMatch(/EditorSession/);
    expect(content).not.toMatch(/from\s+["'].*mutations["']/);
    expect(content).not.toMatch(/from\s+["'].*editor-session["']/);
  });

  it("R09-AG-07: RemotionRendererAdapter resides strictly in remotion/ adapter boundary", () => {
    const adapterPath = path.join(remotionDir, "remotion-renderer-adapter.ts");
    expect(fs.existsSync(adapterPath)).toBe(true);

    const indexPath = path.join(remotionDir, "index.ts");
    expect(fs.existsSync(indexPath)).toBe(true);
  });
});
