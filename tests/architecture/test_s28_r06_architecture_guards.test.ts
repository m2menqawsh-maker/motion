/**
 * tests/architecture/test_s28_r06_architecture_guards.test.ts
 * Architecture Guards for S28-R06: Browser Live Preview Runtime.
 * Enforces:
 *   - Core preview runtime modules have ZERO Remotion imports
 *   - Core preview runtime modules have ZERO React imports
 *   - Preview delegates all timeline & evaluation math to contracts/
 *   - No competing secondary timeline math in preview runtime
 *   - Single Canonical VideoDocument authority preserved
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R06 Architecture Guards: Preview Independence & Canonical Authority", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const previewDir = path.resolve(rootDir, "preview");

  const coreModules = [
    "types.ts",
    "capabilities.ts",
    "visual-frame.ts",
    "dom-driver.ts",
    "preview-runtime.ts",
  ];

  it("R06-AG-01: Core preview modules have ZERO imports from Remotion or @remotion/*", () => {
    for (const mod of coreModules) {
      const fullPath = path.join(previewDir, mod);
      expect(fs.existsSync(fullPath), `${mod} must exist in preview/`).toBe(true);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/from\s+["']remotion["']/);
      expect(content).not.toMatch(/from\s+["']@remotion\//);
      expect(content).not.toMatch(/\bremotion\b(?!\-)/);
    }
  });

  it("R06-AG-02: Core preview modules have ZERO imports from React or react-dom", () => {
    for (const mod of coreModules) {
      const fullPath = path.join(previewDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/from\s+["']react["']/);
      expect(content).not.toMatch(/from\s+["']react-dom["']/);
      expect(content).not.toMatch(/\buseState\b/);
      expect(content).not.toMatch(/\buseEffect\b/);
      expect(content).not.toMatch(/\buseMemo\b/);
    }
  });

  it("R06-AG-03: Preview runtime delegates timeline and frame evaluation to contracts/ (no duplicate math)", () => {
    const runtimePath = path.join(previewDir, "preview-runtime.ts");
    const visualFramePath = path.join(previewDir, "visual-frame.ts");

    const runtimeContent = fs.readFileSync(runtimePath, "utf-8");
    const visualContent = fs.readFileSync(visualFramePath, "utf-8");

    // Must import evaluateVideoAtFrame and timeline primitives from contracts/
    expect(visualContent).toMatch(/evaluateVideoAtFrame/);
    expect(runtimeContent).toMatch(/calculateCanonicalDuration/);
    expect(runtimeContent).toMatch(/frameToMs/);

    // Must NOT define independent spring or bezier differential equations
    expect(runtimeContent).not.toMatch(/solveCubicBezier/);
    expect(visualContent).not.toMatch(/evaluateSpring/);
  });

  it("R06-AG-04: Canonical VideoDocument remains the single authority (no persistent Editor/Preview document schema)", () => {
    const forbiddenSchemas = [
      "PreviewDocumentSchema",
      "PlayerDocumentSchema",
      "DraftPreviewSchema",
    ];

    for (const mod of coreModules) {
      const fullPath = path.join(previewDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      for (const forbidden of forbiddenSchemas) {
        expect(content).not.toContain(forbidden);
      }
    }
  });

  it("R06-AG-05: React wrapper component LivePreviewPlayer imports core runtime without leaking React inwards", () => {
    const reactComponentPath = path.join(previewDir, "components/LivePreviewPlayer.tsx");
    expect(fs.existsSync(reactComponentPath)).toBe(true);

    const reactContent = fs.readFileSync(reactComponentPath, "utf-8");
    // Must wrap BrowserPreviewRuntime
    expect(reactContent).toMatch(/BrowserPreviewRuntime/);

    // Must NOT contain canonical normalization or frame evaluation math
    expect(reactContent).not.toMatch(/evaluateVideoAtFrame/);
    expect(reactContent).not.toMatch(/normalizeCanonicalVideo/);
  });
});
