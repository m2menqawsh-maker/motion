/**
 * tests/architecture/test_s28_r05_architecture_guards.test.ts
 * Architecture Guards for S28-R05: Engine-Neutral TemplateSpec & Migration.
 * Enforces framework independence, single registry authority, zero subprocess/renderer
 * execution in instantiator, complete 105-template classification, and fail-closed boundaries.
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { validateTemplateSpec } from "../../contracts/template-spec";
import { getSemanticTemplateSpec, getAllSemanticTemplateSpecs } from "../../registry/semantic-registry";

describe("S28-R05 Architecture Guards: Framework Decoupling & Authority Invariants", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");
  const r05Modules = ["template-spec.ts", "template-instantiator.ts"];

  it("R05-AG-01: R05 contract modules have ZERO imports from React, Remotion, or UI frameworks", () => {
    for (const mod of r05Modules) {
      const fullPath = path.join(contractsDir, mod);
      expect(fs.existsSync(fullPath), `${mod} must exist`).toBe(true);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/from\s+["']react["']/);
      expect(content).not.toMatch(/from\s+["']react-dom["']/);
      expect(content).not.toMatch(/from\s+["']remotion["']/);
      expect(content).not.toMatch(/from\s+["']@remotion\//);
      expect(content).not.toMatch(/\bReact\./);
      expect(content).not.toMatch(/\bJSX\./);
    }
  });

  it("R05-AG-02: Native TemplateSpec data contracts contain ZERO executable code containers, TSX references, or frame hooks", () => {
    for (const mod of r05Modules) {
      const fullPath = path.join(contractsDir, mod);
      const content = fs.readFileSync(fullPath, "utf-8");

      expect(content).not.toMatch(/useCurrentFrame\(/);
      expect(content).not.toMatch(/interpolate\(/);
      expect(content).not.toMatch(/spring\(/);
      expect(content).not.toMatch(/\.tsx["']/);
      expect(content).not.toMatch(/\bAbsoluteFill\b/);
      expect(content).not.toMatch(/\bSequence\b/);
    }
  });

  it("R05-AG-03: TemplateInstantiator cannot call renderer, spawn subprocesses, or perform network/fs I/O", () => {
    const instPath = path.join(contractsDir, "template-instantiator.ts");
    const content = fs.readFileSync(instPath, "utf-8");

    // Zero subprocess
    expect(content).not.toMatch(/from\s+["']child_process["']/);
    expect(content).not.toMatch(/from\s+["']node:child_process["']/);
    expect(content).not.toMatch(/\bspawn\b/);
    expect(content).not.toMatch(/\bexec\b/);
    expect(content).not.toMatch(/\bspawnSync\b/);
    expect(content).not.toMatch(/\bexecSync\b/);

    // Zero filesystem mutation
    expect(content).not.toMatch(/from\s+["']fs["']/);
    expect(content).not.toMatch(/from\s+["']node:fs["']/);
    expect(content).not.toMatch(/\bwriteFileSync\b/);
    expect(content).not.toMatch(/\bunlinkSync\b/);

    // Zero network
    expect(content).not.toMatch(/\bfetch\(/);
    expect(content).not.toMatch(/from\s+["']http["']/);
    expect(content).not.toMatch(/from\s+["']https["']/);

    // Zero renderer invocation
    expect(content).not.toMatch(/\brenderMedia\b/);
    expect(content).not.toMatch(/\brenderStill\b/);
  });

  it("R05-AG-04: Single Canonical Template Registry authority is strictly preserved (no second registry created)", () => {
    const forbiddenDirs = [
      "new-template-registry",
      "template-registry-v2",
      "editor-template-registry",
      "templates-v2",
    ];

    for (const d of forbiddenDirs) {
      const dirPath = path.join(rootDir, d);
      expect(fs.existsSync(dirPath), `Forbidden parallel registry '${d}' detected`).toBe(false);
    }

    // Single authority metadata file remains registry/template-registry-data.json
    const authorityPath = path.join(rootDir, "registry/template-registry-data.json");
    expect(fs.existsSync(authorityPath), "Single authority file must exist").toBe(true);
  });

  it("R05-AG-05: Machine-readable migration manifest has exactly 105 templates, 0 unknown, and all classifications valid", () => {
    const manifestPath = path.join(rootDir, "registry/template-migration-manifest.json");
    expect(fs.existsSync(manifestPath), "Manifest file must exist").toBe(true);

    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    expect(manifest.counts.total).toBe(105);
    expect(manifest.counts.unknown).toBe(0);
    expect(manifest.counts.native).toBe(29);
    expect(manifest.counts.hybrid).toBe(14);
    expect(manifest.counts.engine_backed).toBe(3);
    expect(manifest.counts.legacy_compatibility).toBe(59);

    const validClassifications = new Set(["NATIVE", "ENGINE_BACKED", "HYBRID", "LEGACY_COMPATIBILITY"]);

    for (const [tid, entry] of Object.entries(manifest.entries as Record<string, any>)) {
      expect(validClassifications.has(entry.classification), `Template ${tid} has invalid classification: ${entry.classification}`).toBe(true);
      expect(typeof entry.reason).toBe("string");
      expect(entry.reason.length).toBeGreaterThan(0);
    }
  });

  it("R05-AG-06: No silent fallback: ENGINE_BACKED and unknown templates fail closed with structured errors", async () => {
    const { instantiateTemplate, EngineBackedTemplateError } = await import("../../contracts/template-instantiator");
    const { UnknownTemplateError } = await import("../../contracts/render-input");

    // ENGINE_BACKED does not fallback to TSX or mock silently
    expect(() => {
      instantiateTemplate("rui-map-flight", {});
    }).toThrow(EngineBackedTemplateError);

    // Unknown template does not fallback silently
    expect(() => {
      instantiateTemplate("random_missing_template", {});
    }).toThrow(UnknownTemplateError);
  });

  it("R05-AG-07: All 105 TemplateSpecs pass validation and strict structural purity checks", () => {
    const allSpecs = getAllSemanticTemplateSpecs();
    expect(allSpecs).toHaveLength(105);

    for (const spec of allSpecs) {
      const val = validateTemplateSpec(spec);
      expect(val.ok, `TemplateSpec ${spec.template_id} failed purity check: ${val.errors.join(", ")}`).toBe(true);
    }
  });
});
