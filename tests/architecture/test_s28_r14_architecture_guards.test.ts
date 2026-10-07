/**
 * tests/architecture/test_s28_r14_architecture_guards.test.ts
 * Vitest Architecture Guards for S28-R14: Production Integration Boundaries.
 * 
 * Enforces Section 23 invariants:
 *   1. API router directly mutating VideoDocument -> forbidden
 *   2. Renderer adapter importing/writing project repository directly -> forbidden
 *   3. Renderer adapter bypassing StorageService for persistent artifacts -> forbidden
 *   4. Renderer code changing lifecycle directly -> forbidden
 *   5. Authoring layer selecting concrete render engine -> forbidden
 *   6. AI authoring importing Remotion/FFmpeg renderer code -> forbidden
 *   7. Production code relying on process-local lock for document CAS -> forbidden
 *   8. Production idempotency implemented only with in-memory cache -> forbidden
 *   9. Worker using local workspace as persistent project truth -> forbidden
 *   10. Cross-layer direct provider calls that bypass approved adapter boundaries -> forbidden
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("S28-R14 Architecture Guards: Production Integration", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const authoringDir = path.resolve(rootDir, "authoring");
  const contractsDir = path.resolve(rootDir, "contracts");
  const plannerDir = path.resolve(rootDir, "planner");
  const compositorDir = path.resolve(rootDir, "compositor");

  it("R14-AG-01: API CLI bridge delegates exclusively to AuthoringService/repo; no direct file bypass", () => {
    const bridgePath = path.resolve(rootDir, "scripts/execute_authoring_mutation.ts");
    if (fs.existsSync(bridgePath)) {
      const content = fs.readFileSync(bridgePath, "utf-8");
      expect(content).toMatch(/applyMutation|Authoring/);
      expect(content).not.toMatch(/UPDATE\s+project_states/i);
    }
  });

  it("R14-AG-02: Renderer adapters have ZERO direct database or project repo imports", () => {
    const adapterFiles = [
      path.resolve(contractsDir, "renderer.ts"),
      path.resolve(contractsDir, "remotion-renderer-adapter.ts"),
      path.resolve(contractsDir, "canvas-renderer-adapter.ts"),
    ];

    for (const f of adapterFiles) {
      if (fs.existsSync(f)) {
        const content = fs.readFileSync(f, "utf-8");
        expect(content, `${path.basename(f)} must not import database`).not.toMatch(/from\s+["'].*database.*["']/);
        expect(content, `${path.basename(f)} must not reference project repo`).not.toMatch(/\bProjectRepository\b/);
        expect(content, `${path.basename(f)} must not reference tenant repo`).not.toMatch(/\bTenantRepository\b/);
      }
    }
  });

  it("R14-AG-03: Production executor publishes persistent artifacts through StorageService", () => {
    const executorPath = path.resolve(plannerDir, "production-render-graph-executor.ts");
    const content = fs.readFileSync(executorPath, "utf-8");

    expect(content).toMatch(/this\.storage\.put/);
    expect(content).toMatch(/buildStorageKey/);
    expect(content).not.toMatch(/INSERT\s+INTO\s+project_artifact_versions/i);
  });

  it("R14-AG-04: Renderer and compositor code never directly transitions lifecycle states", () => {
    const targetDirs = [plannerDir, compositorDir];
    for (const d of targetDirs) {
      const files = fs.readdirSync(d).filter((f) => f.endsWith(".ts"));
      for (const file of files) {
        const content = fs.readFileSync(path.join(d, file), "utf-8");
        expect(content, `${file} must not reference LifecycleService`).not.toMatch(/\bLifecycleService\b/);
        expect(content, `${file} must not call transition_to`).not.toMatch(/\btransition_to\b/);
      }
    }
  });

  it("R14-AG-05: Authoring layer does NOT import concrete renderers or registries", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));
    for (const file of files) {
      const content = fs.readFileSync(path.join(authoringDir, file), "utf-8");
      expect(content, `authoring/${file} must not reference renderer registry`).not.toMatch(/CANONICAL_RENDERER_REGISTRY/);
      expect(content, `authoring/${file} must not reference Remotion renderer adapter`).not.toMatch(/RemotionRendererAdapter/);
      expect(content, `authoring/${file} must not call selectRenderer`).not.toMatch(/\bselectRenderer\b/);
    }
  });

  it("R14-AG-06: Authoring layer has ZERO imports from Remotion or FFmpeg", () => {
    const files = fs.readdirSync(authoringDir).filter((f) => f.endsWith(".ts"));
    for (const file of files) {
      const content = fs.readFileSync(path.join(authoringDir, file), "utf-8");
      expect(content, `authoring/${file} must not import @remotion`).not.toMatch(/from\s+["']@remotion/);
      expect(content, `authoring/${file} must not import fluent-ffmpeg`).not.toMatch(/from\s+["']fluent-ffmpeg["']/);
      expect(content, `authoring/${file} must not import @ffmpeg`).not.toMatch(/from\s+["']@ffmpeg/);
    }
  });

  it("R14-AG-07: Production document CAS in Python relies on transactional SQL, not process locks", () => {
    const pyCasPath = path.resolve(rootDir, "scripts/core/canonical_document_repository.py");
    const content = fs.readFileSync(pyCasPath, "utf-8");

    expect(content).not.toMatch(/threading\.Lock/);
    expect(content).not.toMatch(/asyncio\.Lock/);
    expect(content).toMatch(/transaction\(/);
    expect(content).toMatch(/WHERE project_id = \? AND revision = \?/);
  });

  it("R14-AG-08: Production idempotency repository persists to durable database table", () => {
    const pyIdempPath = path.resolve(rootDir, "scripts/core/authoring_idempotency_repository.py");
    const content = fs.readFileSync(pyIdempPath, "utf-8");

    expect(content).toMatch(/authoring_idempotency_records/);
    expect(content).toMatch(/INSERT INTO authoring_idempotency_records/);
    expect(content).toMatch(/UPDATE authoring_idempotency_records/);
  });

  it("R14-AG-09: Worker uses ephemeral sandboxed directory with guaranteed cleanup", () => {
    const executorPath = path.resolve(plannerDir, "production-render-graph-executor.ts");
    const content = fs.readFileSync(executorPath, "utf-8");

    expect(content).toMatch(/render_sandbox_/);
    expect(content).toMatch(/fs\.rmSync\(workDir,\s*\{\s*recursive:\s*true,\s*force:\s*true\s*\}\)/);
  });

  it("R14-AG-10: Cross-layer boundaries prohibit direct renderer execution in API routers", () => {
    const apiRouterDir = path.resolve(rootDir, "api/routers");
    if (fs.existsSync(apiRouterDir)) {
      const files = fs.readdirSync(apiRouterDir).filter((f) => f.endsWith(".py"));
      for (const file of files) {
        const content = fs.readFileSync(path.join(apiRouterDir, file), "utf-8");
        expect(content, `api/routers/${file} must not call subprocess`).not.toMatch(/subprocess\.(?:run|Popen|call)/);
        expect(content, `api/routers/${file} must not call remotion`).not.toMatch(/npx\s+remotion/);
      }
    }
  });
});
