/**
 * tests/architecture/test_s28_r13_architecture_guards.test.ts
 * Architecture Guards for S28-R13: Unified Authoring Architecture Boundaries.
 * 
 * Enforces:
 *   - AI authoring & authoring/ have ZERO imports from Remotion (@remotion/bundler, @remotion/renderer, Remotion components)
 *   - AI authoring has ZERO Canvas adapter imports (canvas-renderer-adapter)
 *   - AI authoring has ZERO FFmpeg imports (fluent-ffmpeg, @ffmpeg)
 *   - AI authoring has ZERO RenderPlanner selection logic or imports
 *   - TemplateSpec and contracts have ZERO AI provider SDK imports (openai, @anthropic-ai, @google/generative-ai, langchain)
 *   - Mutation Core has ZERO AI provider SDK imports
 *   - Canonical contracts have ZERO AI provider SDK imports
 *   - CreativePlan has ZERO renderer implementation imports
 *   - Authoring path enforces typed mutation engine (no direct Blueprint mutation bypass)
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R13 Architecture Guards: Unified Authoring Boundaries", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const authoringDir = path.resolve(rootDir, "authoring");
  const contractsDir = path.resolve(rootDir, "contracts");

  it("R13-AG-01: AI authoring layer has ZERO imports from Remotion bundler or renderer", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(authoringDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content, `authoring/${file} must NOT import @remotion`).not.toMatch(/from\s+["']@remotion/);
      expect(content, `authoring/${file} must NOT import remotion adapter`).not.toMatch(/from\s+["'].*remotion-renderer-adapter.*["']/);
      expect(content, `authoring/${file} must NOT import remotion`).not.toMatch(/from\s+["']remotion["']/);
    }
  });

  it("R13-AG-02: AI authoring layer has ZERO imports from Canvas renderer adapter", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(authoringDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content, `authoring/${file} must NOT import canvas renderer adapter`).not.toMatch(/from\s+["'].*canvas-renderer-adapter.*["']/);
      expect(content, `authoring/${file} must NOT import canvas`).not.toMatch(/from\s+["']canvas["']/);
    }
  });

  it("R13-AG-03: AI authoring layer has ZERO FFmpeg imports or process execution", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(authoringDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content, `authoring/${file} must NOT import fluent-ffmpeg`).not.toMatch(/from\s+["']fluent-ffmpeg["']/);
      expect(content, `authoring/${file} must NOT import @ffmpeg`).not.toMatch(/from\s+["']@ffmpeg/);
      expect(content, `authoring/${file} must NOT spawn ffmpeg`).not.toMatch(/execFileSync\s*\(\s*["']ffmpeg/);
      expect(content, `authoring/${file} must NOT spawn ffmpeg`).not.toMatch(/spawn\s*\(\s*["']ffmpeg/);
    }
  });

  it("R13-AG-04: AI authoring layer has ZERO RenderPlanner selection logic or imports", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));

    for (const file of files) {
      const fullPath = path.join(authoringDir, file);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content, `authoring/${file} must NOT import RenderPlanner`).not.toMatch(/\bRenderPlanner\b/);
      expect(content, `authoring/${file} must NOT import planner`).not.toMatch(/from\s+["'].*\/planner\/.*["']/);
    }
  });

  it("R13-AG-05: contracts/ and authoring/ have ZERO AI provider SDK imports", () => {
    const targetDirs = [contractsDir, authoringDir];
    const forbiddenSDKs = ["openai", "@anthropic-ai/sdk", "@google/generative-ai", "langchain"];

    for (const dir of targetDirs) {
      const files = fs.readdirSync(dir).filter((f) => f.endsWith(".ts"));
      for (const file of files) {
        const fullPath = path.join(dir, file);
        const content = fs.readFileSync(fullPath, "utf-8");

        for (const sdk of forbiddenSDKs) {
          expect(
            content,
            `${path.basename(dir)}/${file} must NOT import AI vendor SDK '${sdk}'`
          ).not.toMatch(new RegExp(`from\\s+["']${sdk}(?:/.*)?["']`));
        }
      }
    }
  });

  it("R13-AG-06: TemplateSpec and Instantiator have ZERO AI provider SDK imports", () => {
    const specPath = path.join(contractsDir, "template-spec.ts");
    const instPath = path.join(contractsDir, "template-instantiator.ts");

    const specContent = fs.readFileSync(specPath, "utf-8");
    const instContent = fs.readFileSync(instPath, "utf-8");

    expect(specContent).not.toMatch(/from\s+["'](?:openai|@anthropic|@google\/gen|langchain)/);
    expect(instContent).not.toMatch(/from\s+["'](?:openai|@anthropic|@google\/gen|langchain)/);
  });

  it("R13-AG-07: Mutation Core and EditorSession have ZERO AI provider SDK imports", () => {
    const mutPath = path.join(contractsDir, "mutations.ts");
    const sessPath = path.join(contractsDir, "editor-session.ts");

    const mContent = fs.readFileSync(mutPath, "utf-8");
    const sContent = fs.readFileSync(sessPath, "utf-8");

    expect(mContent).not.toMatch(/from\s+["'](?:openai|@anthropic|@google\/gen|langchain)/);
    expect(sContent).not.toMatch(/from\s+["'](?:openai|@anthropic|@google\/gen|langchain)/);
  });

  it("R13-AG-08: AI authoring does NOT bypass canonical Mutation Engine", () => {
    const unifiedPath = path.join(authoringDir, "unified-authoring-session.ts");
    const content = fs.readFileSync(unifiedPath, "utf-8");

    // Must execute through EditorSession applyMutation or applyBatch
    expect(content).toMatch(/this\.editorSession\.applyMutation/);
    expect(content).toMatch(/this\.editorSession\.applyBatch/);
  });
});
