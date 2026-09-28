import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { validateManifestV2 } from "../../contracts/manifest";

const FIXTURES_DIR = path.resolve(__dirname, "../fixtures/manifest");

function readFixture(name: string): any {
  const filePath = path.join(FIXTURES_DIR, name);
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

describe("Manifest v2 Cross-Language Contract (TypeScript)", () => {
  it("validates canonical valid_manifest_v2.json fixture successfully", () => {
    const fixture = readFixture("valid_manifest_v2.json");
    const result = validateManifestV2(fixture, "prj_canonical_01");

    expect(result.ok).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.manifest?.assets).toHaveLength(3);
    expect(result.manifest?.assets[0].kind).toBe("video");
    expect(result.manifest?.assets[0].provenance).toBe("user_upload");
    expect(result.manifest?.assets[0].status).toBe("ready");
  });

  it("rejects duplicate_id_manifest.json fixture with duplicate error", () => {
    const fixture = readFixture("duplicate_id_manifest.json");
    const result = validateManifestV2(fixture);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("Duplicate asset_id"))).toBe(true);
  });

  it("rejects invalid_kind_manifest.json fixture with invalid kind error", () => {
    const fixture = readFixture("invalid_kind_manifest.json");
    const result = validateManifestV2(fixture);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("kind") || e.includes("Invalid enum value"))).toBe(true);
  });

  it("rejects invalid_provenance_manifest.json fixture with invalid provenance error", () => {
    const fixture = readFixture("invalid_provenance_manifest.json");
    const result = validateManifestV2(fixture);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("provenance") || e.includes("Invalid enum value"))).toBe(true);
  });

  it("rejects invalid_status_manifest.json fixture with invalid status error", () => {
    const fixture = readFixture("invalid_status_manifest.json");
    const result = validateManifestV2(fixture);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("status") || e.includes("Invalid enum value"))).toBe(true);
  });

  it("rejects unsupported_version_manifest.json fixture", () => {
    const fixture = readFixture("unsupported_version_manifest.json");
    const result = validateManifestV2(fixture);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("manifest_version") || e.includes("Invalid enum value"))).toBe(true);
  });

  it("rejects project_id_mismatch_manifest.json fixture when expected project ID differs", () => {
    const fixture = readFixture("project_id_mismatch_manifest.json");
    const result = validateManifestV2(fixture, "prj_canonical_01");

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.includes("Project ID mismatch"))).toBe(true);
  });
});
