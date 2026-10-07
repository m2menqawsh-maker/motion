import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

// Helper to recursively collect all module dependencies (package names and file paths)
function getTransitiveImports(
  entryFile: string,
  visited: Set<string> = new Set()
): { packages: Set<string>; localFiles: Set<string> } {
  const packages = new Set<string>();
  const localFiles = new Set<string>();

  const normalizedEntry = path.resolve(entryFile);
  if (visited.has(normalizedEntry) || !fs.existsSync(normalizedEntry)) {
    return { packages, localFiles };
  }
  visited.add(normalizedEntry);
  localFiles.add(normalizedEntry);

  const content = fs.readFileSync(normalizedEntry, "utf-8");
  // Match standard import and require statements
  const importRegex = /(?:import\s+(?:[\w*\s{},]*\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))/g;
  let match: RegExpExecArray | null;

  while ((match = importRegex.exec(content)) !== null) {
    const specifier = match[1] || match[2];
    if (!specifier) continue;

    if (specifier.startsWith(".") || specifier.startsWith("/")) {
      const dir = path.dirname(normalizedEntry);
      const possibleExts = ["", ".ts", ".tsx", ".js", ".jsx", ".json", "/index.ts", "/index.tsx", "/index.js"];
      let resolvedPath: string | null = null;
      for (const ext of possibleExts) {
        const candidate = path.resolve(dir, specifier + ext);
        if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
          resolvedPath = candidate;
          break;
        }
      }
      if (resolvedPath) {
        const sub = getTransitiveImports(resolvedPath, visited);
        for (const pkg of sub.packages) packages.add(pkg);
        for (const f of sub.localFiles) localFiles.add(f);
      }
    } else if (specifier.startsWith("@/")) {
      // Alias to remotion-app/src
      const subPath = specifier.slice(2);
      const rootDir = path.resolve(__dirname, "../../remotion-app/src");
      const possibleExts = ["", ".ts", ".tsx", ".js", ".jsx", ".json", "/index.ts", "/index.tsx"];
      let resolvedPath: string | null = null;
      for (const ext of possibleExts) {
        const candidate = path.resolve(rootDir, subPath + ext);
        if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
          resolvedPath = candidate;
          break;
        }
      }
      if (resolvedPath) {
        const sub = getTransitiveImports(resolvedPath, visited);
        for (const pkg of sub.packages) packages.add(pkg);
        for (const f of sub.localFiles) localFiles.add(f);
      }
    } else {
      packages.add(specifier);
    }
  }

  return { packages, localFiles };
}

describe("S28-R02 RED Tests: Canonical Contract Independence & Normalizer Extraction", () => {
  const rootDir = path.resolve(__dirname, "../..");

  // ──────────────────────────────────────────────────────────────────────────
  // RED-01: Canonical Blueprint contract must not import React
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-01: contracts/blueprint.ts must not transitively import React", () => {
    const blueprintPath = path.resolve(rootDir, "contracts/blueprint.ts");
    const { packages, localFiles } = getTransitiveImports(blueprintPath);
    const hasReact = packages.has("react") || packages.has("react-dom");
    const tsxFiles = Array.from(localFiles).filter((f) => f.endsWith(".tsx"));

    expect(
      hasReact,
      `contracts/blueprint.ts transitively imports React! TSX files found: ${tsxFiles.join(", ")}`
    ).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-02: Canonical Blueprint contract must not import Remotion
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-02: contracts/blueprint.ts must not transitively import remotion or @remotion/*", () => {
    const blueprintPath = path.resolve(rootDir, "contracts/blueprint.ts");
    const { packages } = getTransitiveImports(blueprintPath);
    const remotionPackages = Array.from(packages).filter(
      (pkg) => pkg === "remotion" || pkg.startsWith("@remotion/")
    );

    expect(
      remotionPackages,
      `contracts/blueprint.ts transitively imports Remotion packages: ${remotionPackages.join(", ")}`
    ).toEqual([]);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-03: animations contract must not depend on remotion runtime functions
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-03: contracts/animations.ts must not import remotion runtime functions (interpolate, spring)", () => {
    const animPath = path.resolve(rootDir, "contracts/animations.ts");
    const content = fs.readFileSync(animPath, "utf-8");
    const importsRemotion = /from\s+["']remotion["']/.test(content);

    expect(
      importsRemotion,
      "contracts/animations.ts directly imports 'remotion'!"
    ).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-04: effect semantic identity validation must work without loading effect React implementations
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-04: contracts/effects.ts must exist and validate effect semantic identity without React", () => {
    const effectsContractPath = path.resolve(rootDir, "contracts/effects.ts");
    expect(
      fs.existsSync(effectsContractPath),
      "contracts/effects.ts does not exist! Effect definitions must live in pure contracts layer."
    ).toBe(true);

    if (fs.existsSync(effectsContractPath)) {
      const { packages, localFiles } = getTransitiveImports(effectsContractPath);
      expect(packages.has("react")).toBe(false);
      expect(packages.has("remotion")).toBe(false);
      const tsxFiles = Array.from(localFiles).filter((f) => f.endsWith(".tsx"));
      expect(tsxFiles).toEqual([]);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-05: SceneOverride canonical type must be importable without remotion-app
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-05: contracts/render-input.ts must not import SceneOverride from remotion-app", () => {
    const renderInputPath = path.resolve(rootDir, "contracts/render-input.ts");
    const content = fs.readFileSync(renderInputPath, "utf-8");
    const importsFromRemotionApp = /from\s+["'][^"']*remotion-app[^"']*["']/.test(content);

    expect(
      importsFromRemotionApp,
      "contracts/render-input.ts imports from remotion-app! SceneOverride must be canonically owned by contracts."
    ).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-06: normalization of a valid canonical fixture must work without Remotion
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-06: contracts/normalization.ts must exist and normalize valid fixture with zero Remotion dependency", () => {
    const normPath = path.resolve(rootDir, "contracts/normalization.ts");
    expect(
      fs.existsSync(normPath),
      "contracts/normalization.ts does not exist! Core normalizer must be extracted from remotion-app/src/merge.ts."
    ).toBe(true);

    if (fs.existsSync(normPath)) {
      const { packages } = getTransitiveImports(normPath);
      const remotionPkgs = Array.from(packages).filter(
        (pkg) => pkg === "remotion" || pkg.startsWith("@remotion/")
      );
      expect(remotionPkgs).toEqual([]);
      expect(packages.has("react")).toBe(false);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // RED-07: parseRenderInput compatibility behavior must remain equivalent for existing fixtures
  // ──────────────────────────────────────────────────────────────────────────
  it("RED-07: parseRenderInput maintains compatibility on valid minimal fixture", async () => {
    const { parseRenderInput } = await import("../../contracts/render-input");
    const fixturePath = path.resolve(rootDir, "tests/fixtures/blueprint/valid_minimal_blueprint.json");
    const bp = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
    const envelope = {
      project: { title: "Test Project", fps: 30, project_id: "prj_minimal_01" },
      blueprint: bp,
    };
    const validated = parseRenderInput(envelope);
    expect(validated).toBeDefined();
    expect(validated.blueprint.project_id).toBe("prj_minimal_01");
    expect(validated.blueprint.scenes).toHaveLength(1);
  });
});
