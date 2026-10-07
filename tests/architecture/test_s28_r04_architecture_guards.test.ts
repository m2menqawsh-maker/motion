import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R04 Architecture Guards: Mutation Core & Editor Session Purity", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const modulesToCheck = ["mutations.ts", "editor-session.ts"];

  it("R04-AG-01: mutations.ts and editor-session.ts exist and have ZERO imports from React or Remotion", () => {
    for (const mod of modulesToCheck) {
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

  it("R04-AG-02: R04 modules have ZERO wall-clock or non-deterministic dependencies", () => {
    for (const mod of modulesToCheck) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/Date\.now\(\)/);
      expect(content).not.toMatch(/new\s+Date\(\)/);
      expect(content).not.toMatch(/performance\.now\(\)/);
      expect(content).not.toMatch(/Math\.random\(\)/);
    }
  });

  it("R04-AG-03: R04 modules have ZERO browser DOM, Canvas, or UI rendering dependencies", () => {
    for (const mod of modulesToCheck) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/\bwindow\b/);
      expect(content).not.toMatch(/\bdocument\b/);
      expect(content).not.toMatch(/\bHTMLElement\b/);
      expect(content).not.toMatch(/\bHTMLCanvasElement\b/);
      expect(content).not.toMatch(/\bOffscreenCanvas\b/);
      expect(content).not.toMatch(/getContext\(["']2d["']\)/);
    }
  });

  it("R04-AG-04: R04 modules have ZERO network, database, or filesystem I/O dependencies", () => {
    for (const mod of modulesToCheck) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/from\s+["']fs["']/);
      expect(content).not.toMatch(/from\s+["']node:fs["']/);
      expect(content).not.toMatch(/from\s+["']http["']/);
      expect(content).not.toMatch(/from\s+["']https["']/);
      expect(content).not.toMatch(/from\s+["']node:http["']/);
      expect(content).not.toMatch(/\bfetch\(/);
      expect(content).not.toMatch(/\bXMLHttpRequest\b/);
    }
  });

  it("R04-AG-05: R04 modules have ZERO unconstrained 'any' types in their implementations", () => {
    for (const mod of modulesToCheck) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/:\s*any\b/);
      expect(content).not.toMatch(/<any>/);
      expect(content).not.toMatch(/as\s+any\b/);
    }
  });
});
