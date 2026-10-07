import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";

// Helper to recursively collect all module dependencies (packages and files)
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
  const importRegex = /(?:import\s+(?:[\w*\s{},]*\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))/g;
  let match: RegExpExecArray | null;

  while ((match = importRegex.exec(content)) !== null) {
    const specifier = match[1] || match[2];
    if (!specifier) continue;

    if (specifier.startsWith(".") || specifier.startsWith("/")) {
      const dir = path.dirname(normalizedEntry);
      const possibleExts = ["", ".ts", ".tsx", ".js", ".jsx", ".json", "/index.ts", "/index.tsx"];
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
    } else {
      packages.add(specifier);
    }
  }

  return { packages, localFiles };
}

describe("S28-R02 Architecture Guards: Boundary & Purity Enforcement", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const contractsDir = path.resolve(rootDir, "contracts");

  // ──────────────────────────────────────────────────────────────────────────
  // Guard 1: contracts/** must never import React or Remotion
  // ──────────────────────────────────────────────────────────────────────────
  it("AG-01: contracts/** imports zero React or Remotion packages", () => {
    const contractFiles = fs
      .readdirSync(contractsDir)
      .filter((f) => f.endsWith(".ts"))
      .map((f) => path.join(contractsDir, f));

    for (const file of contractFiles) {
      const relPath = path.relative(rootDir, file);
      const { packages, localFiles } = getTransitiveImports(file);

      const forbiddenPackages = Array.from(packages).filter(
        (pkg) =>
          pkg === "react" ||
          pkg === "react-dom" ||
          pkg === "remotion" ||
          pkg.startsWith("@remotion/")
      );

      const tsxFiles = Array.from(localFiles).filter((f) => f.endsWith(".tsx"));

      expect(
        forbiddenPackages,
        `Contract file '${relPath}' transitively imports forbidden packages: ${forbiddenPackages.join(", ")}`
      ).toEqual([]);

      expect(
        tsxFiles,
        `Contract file '${relPath}' transitively imports runtime TSX files: ${tsxFiles.join(", ")}`
      ).toEqual([]);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Guard 2: Core Normalizer must never import renderer libraries
  // ──────────────────────────────────────────────────────────────────────────
  it("AG-02: contracts/normalization.ts imports zero renderer libraries or TSX", () => {
    const normPath = path.resolve(contractsDir, "normalization.ts");
    const { packages, localFiles } = getTransitiveImports(normPath);

    const forbidden = Array.from(packages).filter(
      (pkg) =>
        pkg === "react" ||
        pkg === "react-dom" ||
        pkg === "remotion" ||
        pkg.startsWith("@remotion/")
    );
    expect(forbidden).toEqual([]);

    const tsxFiles = Array.from(localFiles).filter((f) => f.endsWith(".tsx"));
    expect(tsxFiles).toEqual([]);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Guard 3: Semantic Registry must never import React or Remotion
  // ──────────────────────────────────────────────────────────────────────────
  it("AG-03: registry/semantic-registry.ts imports zero React or Remotion", () => {
    const semanticRegistryPath = path.resolve(rootDir, "registry/semantic-registry.ts");
    const { packages, localFiles } = getTransitiveImports(semanticRegistryPath);

    const forbidden = Array.from(packages).filter(
      (pkg) =>
        pkg === "react" ||
        pkg === "react-dom" ||
        pkg === "remotion" ||
        pkg.startsWith("@remotion/")
    );
    expect(forbidden).toEqual([]);

    const tsxFiles = Array.from(localFiles).filter((f) => f.endsWith(".tsx"));
    expect(tsxFiles).toEqual([]);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Guard 4: Canonical Schemas must never import templates/effects/engine-bridge
  // ──────────────────────────────────────────────────────────────────────────
  it("AG-04: contracts/** does not import engine-bridge or concrete TSX registries", () => {
    const contractFiles = fs
      .readdirSync(contractsDir)
      .filter((f) => f.endsWith(".ts"))
      .map((f) => path.join(contractsDir, f));

    for (const file of contractFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(content).not.toMatch(/engine-bridge/);
      expect(content).not.toMatch(/template-registry\.tsx/);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Guard 5: Critical Compatibility Test (Section 34)
  // Executes Canonical Parser & Normalizer in isolated child process with React/Remotion blocked
  // ──────────────────────────────────────────────────────────────────────────
  it("AG-05: Critical Compatibility Test: Parser and Normalizer execute in isolated process with React/Remotion blocked", () => {
    const isolationScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = ["react", "react-dom", "remotion", "@remotion/transitions", "@remotion/core", "@remotion/cli"];

      Module.prototype.require = function(id) {
        for (const b of blocked) {
          if (id === b || id.startsWith(b + "/")) {
            throw new Error("ISOLATION_VIOLATION_MODULE_LOADED: " + id);
          }
        }
        return origRequire.apply(this, arguments);
      };

      const fs = require("node:fs");
      const path = require("node:path");

      // Dynamic import to execute under the strict interceptor
      async function run() {
        const { parseCanonicalVideo } = await import("./contracts/canonical-video.ts");
        const { normalizeCanonicalVideo } = await import("./contracts/normalization.ts");

        const fixturePath = path.resolve("./tests/fixtures/canonical/01_simple_text_scene.json");
        const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));

        const parsed = parseCanonicalVideo(raw);
        if (!parsed || parsed.blueprint_version !== "2.0.0") {
          throw new Error("Invalid parsed output");
        }

        const normalized = normalizeCanonicalVideo({ blueprint: parsed });
        if (!normalized || normalized.scenes.length !== 1 || normalized.totalDurationFrames !== 90) {
          throw new Error("Invalid normalized output");
        }

        process.stdout.write(JSON.stringify({ status: "PASS", duration: normalized.totalDurationFrames }));
      }

      run().catch((err) => {
        console.error(err);
        process.exit(1);
      });
    `;

    const result = execFileSync("npx", ["tsx", "-e", isolationScript], {
      cwd: rootDir,
      encoding: "utf-8",
    });

    const parsedOutput = JSON.parse(result);
    expect(parsedOutput.status).toBe("PASS");
    expect(parsedOutput.duration).toBe(90);
  }, 20000);
});
