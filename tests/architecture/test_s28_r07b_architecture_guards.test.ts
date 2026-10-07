/**
 * tests/architecture/test_s28_r07b_architecture_guards.test.ts
 * Architecture Guards for S28-R07B: Preview Fidelity, Cache & Proxy Decoupling.
 * 
 * Enforces:
 *   - Canonical contracts (contracts/preview-fidelity.ts, contracts/preview-proxy.ts) have ZERO imports
 *     from concrete renderer packages (Remotion, Canvas, FFmpeg, React).
 *   - BrowserPreviewRuntime has ZERO hardcoded imports of Remotion or Canvas adapters.
 *   - ProxyCache has ZERO imports of mutation execution engines (applyMutation, EditorSession).
 *   - ProxyCoordinator has ZERO imports of concrete adapters (RemotionRendererAdapter, CanvasRendererAdapter).
 *   - AudioPreviewRuntime has ZERO dependency on proxy state (timeline clock remains independent of proxies).
 *   - Proxy artifacts do NOT act as canonical document authority.
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R07B Architecture Guards: Preview Fidelity & Proxy Isolation", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const previewDir = path.resolve(rootDir, "preview");
  const proxyDir = path.resolve(previewDir, "proxy");
  const audioDir = path.resolve(previewDir, "audio");

  const forbiddenConcretePackages = [
    "remotion",
    "@remotion/renderer",
    "@remotion/bundler",
    "@remotion/google-fonts",
    "canvas",
    "@napi-rs/canvas",
    "fluent-ffmpeg",
    "@ffmpeg",
    "react",
    "react-dom",
  ];

  it("R07B-AG-01: Canonical contracts (preview-fidelity & preview-proxy) have ZERO imports from concrete renderer packages", () => {
    const targetFiles = ["preview-fidelity.ts", "preview-proxy.ts"];

    for (const file of targetFiles) {
      const fullPath = path.join(contractsDir, file);
      expect(fs.existsSync(fullPath), `${file} must exist in contracts/`).toBe(true);
      const content = fs.readFileSync(fullPath, "utf-8");

      for (const pkg of forbiddenConcretePackages) {
        const importRegex = new RegExp(`from\\s+["']${pkg}(?:/.*)?["']`);
        expect(
          content,
          `contracts/${file} must NOT import concrete engine package '${pkg}'`
        ).not.toMatch(importRegex);
      }
    }
  });

  it("R07B-AG-02: BrowserPreviewRuntime has ZERO hardcoded imports of Remotion or Canvas adapters", () => {
    const runtimePath = path.join(previewDir, "preview-runtime.ts");
    const content = fs.readFileSync(runtimePath, "utf-8");

    // Zero Remotion / Canvas adapter imports
    expect(content).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(content).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(content).not.toMatch(/from\s+["'].*remotion-renderer-adapter.*["']/);
    expect(content).not.toMatch(/from\s+["'].*canvas-renderer-adapter.*["']/);
  });

  it("R07B-AG-03: ProxyCache has ZERO imports of mutation execution engines (applyMutation, EditorSession)", () => {
    const cachePath = path.join(proxyDir, "proxy-cache.ts");
    expect(fs.existsSync(cachePath)).toBe(true);
    const content = fs.readFileSync(cachePath, "utf-8");

    expect(content).not.toMatch(/\bapplyMutation\b/);
    expect(content).not.toMatch(/\bapplyBatch\b/);
    expect(content).not.toMatch(/\bEditorSession\b/);
  });

  it("R07B-AG-04: ProxyCoordinator routes 100% via RendererRegistry and has ZERO concrete adapter imports", () => {
    const coordinatorPath = path.join(proxyDir, "proxy-coordinator.ts");
    expect(fs.existsSync(coordinatorPath)).toBe(true);
    const content = fs.readFileSync(coordinatorPath, "utf-8");

    expect(content).not.toMatch(/\bRemotionRendererAdapter\b/);
    expect(content).not.toMatch(/\bCanvasRendererAdapter\b/);
    expect(content).not.toMatch(/from\s+["'].*remotion-renderer-adapter.*["']/);
    expect(content).not.toMatch(/from\s+["'].*canvas-renderer-adapter.*["']/);

    // ZERO hardcoded engine branching: "if remotion ... else if canvas ..."
    expect(content).not.toMatch(/if\s*\([^)]*===\s*["']remotion["']/i);
    expect(content).not.toMatch(/if\s*\([^)]*===\s*["']canvas["']/i);
  });

  it("R07B-AG-05: ProxyCoordinator does NOT mutate canonical video documents directly", () => {
    const coordinatorPath = path.join(proxyDir, "proxy-coordinator.ts");
    const content = fs.readFileSync(coordinatorPath, "utf-8");

    expect(content).not.toMatch(/\bapplyMutation\b/);
    expect(content).not.toMatch(/\bapplyBatch\b/);
  });

  it("R07B-AG-06: AudioPreviewRuntime has ZERO dependency on preview proxy state", () => {
    const audioFiles = fs.readdirSync(audioDir).filter((f) => f.endsWith(".ts"));

    for (const file of audioFiles) {
      const fullPath = path.join(audioDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/from\s+["'].*proxy.*["']/);
      expect(content).not.toMatch(/\bPreviewProxy\b/);
      expect(content).not.toMatch(/\bProxyCoordinator\b/);
    }
  });

  it("R07B-AG-07: Preview proxy modules reside strictly within preview/proxy boundary", () => {
    expect(fs.existsSync(path.join(proxyDir, "proxy-cache.ts"))).toBe(true);
    expect(fs.existsSync(path.join(proxyDir, "proxy-coordinator.ts"))).toBe(true);
    expect(fs.existsSync(path.join(proxyDir, "index.ts"))).toBe(true);
  });
});
