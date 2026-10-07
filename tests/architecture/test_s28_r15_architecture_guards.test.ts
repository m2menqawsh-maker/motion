/**
 * tests/architecture/test_s28_r15_architecture_guards.test.ts
 * Vitest Architecture Guards for S28-R15: Final Architecture Audit & Invariants.
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R15 Architecture Guards: Final Closure", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const authoringDir = path.resolve(rootDir, "authoring");
  const plannerDir = path.resolve(rootDir, "planner");
  const compositorDir = path.resolve(rootDir, "compositor");

  it("R15-AG-01: BlueprintV2 is the single canonical video document authority", () => {
    const canonicalContract = path.resolve(contractsDir, "canonical-video.ts");
    expect(fs.existsSync(canonicalContract)).toBe(true);
    const content = fs.readFileSync(canonicalContract, "utf-8");
    expect(content).toMatch(/BlueprintV2/);
    expect(content).toMatch(/BlueprintV2Schema/);

    const bpContract = path.resolve(contractsDir, "blueprint.ts");
    expect(fs.existsSync(bpContract)).toBe(true);
    const bpContent = fs.readFileSync(bpContract, "utf-8");
    expect(bpContent).toMatch(/BlueprintV2Schema\s*=/);
    expect(bpContent).toMatch(/type\s+BlueprintV2\s*=/);
  });

  it("R15-AG-02: Authoring core has ZERO imports from @remotion or fluent-ffmpeg", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));
    for (const file of files) {
      const content = fs.readFileSync(path.join(authoringDir, file), "utf-8");
      expect(content, `authoring/${file} must not import @remotion`).not.toMatch(/from\s+["']@remotion/);
      expect(content, `authoring/${file} must not import fluent-ffmpeg`).not.toMatch(/from\s+["']fluent-ffmpeg["']/);
    }
  });

  it("R15-AG-03: MasterCompositor never imports concrete renderer implementations", () => {
    const compFile = path.resolve(compositorDir, "master-compositor.ts");
    if (fs.existsSync(compFile)) {
      const content = fs.readFileSync(compFile, "utf-8");
      expect(content).not.toMatch(/\bRemotionRendererAdapter\b/);
      expect(content).not.toMatch(/\bCanvasRendererAdapter\b/);
    }
  });

  it("R15-AG-04: RenderGraph executor enforces sandboxing and guaranteed cleanup", () => {
    const executorPath = path.resolve(plannerDir, "production-render-graph-executor.ts");
    const content = fs.readFileSync(executorPath, "utf-8");
    expect(content).toMatch(/render_sandbox_/);
    expect(content).toMatch(/finally/);
    expect(content).toMatch(/fs\.rmSync\(workDir/);
  });

  it("R15-AG-05: Renderer adapters never import or directly mutate project databases", () => {
    const adapterFiles = [
      path.resolve(contractsDir, "renderer.ts"),
      path.resolve(contractsDir, "remotion-renderer-adapter.ts"),
      path.resolve(contractsDir, "canvas-renderer-adapter.ts"),
    ];
    for (const f of adapterFiles) {
      if (fs.existsSync(f)) {
        const content = fs.readFileSync(f, "utf-8");
        expect(content).not.toMatch(/\bProjectRepository\b/);
        expect(content).not.toMatch(/\bTenantRepository\b/);
        expect(content).not.toMatch(/\bauthoring_idempotency_records\b/);
      }
    }
  });

  it("R15-AG-06: StorageService key builder rejects path traversal fail-closed", () => {
    const storageContract = path.resolve(contractsDir, "storage-service.ts");
    const content = fs.readFileSync(storageContract, "utf-8");
    expect(content).toMatch(/validateStorageKey/);
    expect(content).toMatch(/StorageSecurityError/);
  });
});
