/**
 * tests/architecture/test_s28_r07_architecture_guards.test.ts
 * Architecture Guards for S28-R07: Audio Preview, Synchronization & Waveform.
 * Enforces:
 *   - Canonical contracts have ZERO Web Audio API dependencies
 *   - Mutation core has ZERO AudioContext dependencies
 *   - Waveform core has ZERO React dependencies
 *   - Waveform core has ZERO Remotion dependencies
 *   - Audio preview does NOT create a second timeline authority
 *   - Audio preview does NOT perform direct Blueprint mutation
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R07 Architecture Guards: Audio Preview & Waveform Boundaries", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const previewDir = path.resolve(rootDir, "preview");

  it("R07-AG-01: Canonical contracts have ZERO Web Audio API references or imports", () => {
    const contractFiles = [
      "blueprint.ts",
      "canonical-video.ts",
      "evaluator.ts",
      "keyframes.ts",
      "layers.ts",
      "mutations.ts",
      "normalization.ts",
      "timeline.ts",
      "waveform.ts",
      "editor-session.ts",
    ];

    for (const file of contractFiles) {
      const fullPath = path.join(contractsDir, file);
      expect(fs.existsSync(fullPath), `${file} must exist`).toBe(true);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/\bAudioContext\b/);
      expect(content).not.toMatch(/\bwebkitAudioContext\b/);
      expect(content).not.toMatch(/\bAudioBufferSourceNode\b/);
      expect(content).not.toMatch(/\bGainNode\b/);
      expect(content).not.toMatch(/from\s+["']web-audio/);
    }
  });

  it("R07-AG-02: Mutation Core and EditorSession have ZERO AudioContext dependencies", () => {
    const mutationPath = path.join(contractsDir, "mutations.ts");
    const sessionPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutationPath, "utf-8");
    const sContent = fs.readFileSync(sessionPath, "utf-8");

    expect(mContent).not.toMatch(/\bAudioContext\b/);
    expect(sContent).not.toMatch(/\bAudioContext\b/);
    expect(mContent).not.toMatch(/\bcreateGain\b/);
    expect(sContent).not.toMatch(/\bcreateGain\b/);
  });

  it("R07-AG-03: Waveform core has ZERO imports from React or react-dom", () => {
    const waveformContract = path.join(contractsDir, "waveform.ts");
    const waveformAnalyzer = path.join(previewDir, "audio/waveform-analyzer.ts");

    const wcContent = fs.readFileSync(waveformContract, "utf-8");
    const waContent = fs.readFileSync(waveformAnalyzer, "utf-8");

    expect(wcContent).not.toMatch(/from\s+["']react["']/);
    expect(wcContent).not.toMatch(/from\s+["']react-dom["']/);
    expect(waContent).not.toMatch(/from\s+["']react["']/);
    expect(waContent).not.toMatch(/from\s+["']react-dom["']/);
  });

  it("R07-AG-04: Waveform core has ZERO imports from Remotion or @remotion/*", () => {
    const waveformContract = path.join(contractsDir, "waveform.ts");
    const waveformAnalyzer = path.join(previewDir, "audio/waveform-analyzer.ts");

    const wcContent = fs.readFileSync(waveformContract, "utf-8");
    const waContent = fs.readFileSync(waveformAnalyzer, "utf-8");

    expect(wcContent).not.toMatch(/from\s+["']remotion["']/);
    expect(wcContent).not.toMatch(/from\s+["']@remotion\//);
    expect(waContent).not.toMatch(/from\s+["']remotion["']/);
    expect(waContent).not.toMatch(/from\s+["']@remotion\//);
  });

  it("R07-AG-05: Audio preview does NOT create a second timeline authority or competing clock", () => {
    const audioRuntimePath = path.join(previewDir, "audio/audio-preview-runtime.ts");
    const content = fs.readFileSync(audioRuntimePath, "utf-8");

    // Must NOT define independent clock loops
    expect(content).not.toMatch(/\brequestAnimationFrame\b/);
    expect(content).not.toMatch(/\bsetInterval\b/);
    // Must NOT define competing duration or timeline calculation
    expect(content).not.toMatch(/function calculateTotalDuration/);
    expect(content).not.toMatch(/class Timeline/);
  });

  it("R07-AG-06: Audio preview does NOT mutate Blueprint directly (reads canonical state only)", () => {
    const audioRuntimePath = path.join(previewDir, "audio/audio-preview-runtime.ts");
    const content = fs.readFileSync(audioRuntimePath, "utf-8");

    // AudioPreviewRuntime must never modify blueprint properties
    expect(content).not.toMatch(/doc\.audio\s*=/);
    expect(content).not.toMatch(/draft\.scenes\s*=/);
    expect(content).not.toMatch(/blueprint\.revision\s*\+\+/);
  });
});
