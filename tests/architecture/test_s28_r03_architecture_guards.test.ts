import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R03 Architecture Guards: Temporal & Evaluation Layer Decoupling", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");

  const r03Modules = [
    "timeline.ts",
    "layers.ts",
    "keyframes.ts",
    "evaluator.ts",
  ];

  it("R03-AG-01: R03 contract modules have ZERO imports from React or Remotion", () => {
    for (const mod of r03Modules) {
      const fullPath = path.join(contractsDir, mod);
      expect(fs.existsSync(fullPath), `${mod} must exist`).toBe(true);

      const content = fs.readFileSync(fullPath, "utf-8");
      expect(content).not.toMatch(/from\s+["']react["']/);
      expect(content).not.toMatch(/from\s+["']react-dom["']/);
      expect(content).not.toMatch(/from\s+["']remotion["']/);
      expect(content).not.toMatch(/from\s+["']@remotion\//);
      expect(content).not.toMatch(/\.tsx["']/);
    }
  });

  it("R03-AG-02: Evaluator and Keyframe modules have ZERO wall-clock or non-deterministic dependencies", () => {
    const modulesToCheck = ["keyframes.ts", "evaluator.ts"];
    for (const mod of modulesToCheck) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/Date\.now\(\)/);
      expect(content).not.toMatch(/performance\.now\(\)/);
      expect(content).not.toMatch(/Math\.random\(\)/);
    }
  });

  it("R03-AG-03: Frame evaluator has ZERO browser DOM or Canvas API dependencies", () => {
    const evaluatorPath = path.join(contractsDir, "evaluator.ts");
    const content = fs.readFileSync(evaluatorPath, "utf-8");

    expect(content).not.toMatch(/\bwindow\b/);
    expect(content).not.toMatch(/\bdocument\b/);
    expect(content).not.toMatch(/\bHTMLElement\b/);
    expect(content).not.toMatch(/\bHTMLCanvasElement\b/);
    expect(content).not.toMatch(/\bOffscreenCanvas\b/);
    expect(content).not.toMatch(/getContext\(["']2d["']\)/);
  });

  it("R03-AG-04: Keyframe math has zero CSS easing string execution dependency", () => {
    const keyframesPath = path.join(contractsDir, "keyframes.ts");
    const content = fs.readFileSync(keyframesPath, "utf-8");

    expect(content).not.toMatch(/cubic-bezier\(/);
    expect(content).not.toMatch(/CSS\./);
  });
});
