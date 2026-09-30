import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { getRegistryEntry, TEMPLATE_REGISTRY } from "../../registry/template-registry";
import { TEMPLATE_ALIASES } from "../../registry/template-aliases";

const ROOT = path.resolve(__dirname, "../..");
const CONTRACT_PATH = path.join(ROOT, "contracts/template-runtime-contract.json");

interface TemplateContractData {
  contract_version: string;
  stats: {
    canonical_count: number;
    alias_count: number;
    total_identities: number;
  };
  templates: Record<
    string,
    {
      canonical_id: string;
      category: string;
      component_name: string;
      default_duration_frames: number;
      runtime_available: boolean;
      aliases: string[];
    }
  >;
  aliases: Record<string, string>;
}

const contract: TemplateContractData = JSON.parse(
  fs.readFileSync(CONTRACT_PATH, "utf-8")
);

describe("S15: Template Runtime Contract Parity & Canonical Identity", () => {
  describe("1. Contract Integrity & Canonical ID Invariants", () => {
    it("has 105 canonical templates and matching stats", () => {
      const canonicalIds = Object.keys(contract.templates);
      expect(canonicalIds.length).toBe(105);
      expect(contract.stats.canonical_count).toBe(105);
      expect(Object.keys(contract.aliases).length).toBe(contract.stats.alias_count);
    });

    it("enforces canonical ID naming regex on all entries", () => {
      const canonicalRegex = /^[a-z0-9]+(-[a-z0-9]+)*$/;
      for (const [id, entry] of Object.entries(contract.templates)) {
        expect(canonicalRegex.test(id), `Canonical ID '${id}' violates kebab-case regex`).toBe(true);
        expect(entry.canonical_id).toBe(id);
      }
    });

    it("verifies all registered templates are runtime_available", () => {
      for (const [id, entry] of Object.entries(contract.templates)) {
        expect(entry.runtime_available, `Template '${id}' is marked unavailable`).toBe(true);
      }
    });
  });

  describe("2. Bidirectional Bijection between Contract and Runtime Registry", () => {
    it("every canonical template in contract resolves in runtime registry to itself", () => {
      for (const [canonicalId, contractEntry] of Object.entries(contract.templates)) {
        const runtimeEntry = getRegistryEntry(canonicalId);
        expect(runtimeEntry, `Canonical '${canonicalId}' not found in runtime registry`).toBeDefined();
        expect(runtimeEntry?.id).toBe(canonicalId);
        expect(typeof runtimeEntry?.component).toBe("function");
      }
    });

    it("every alias in contract resolves in runtime registry to the expected canonical ID", () => {
      for (const [alias, expectedCanonical] of Object.entries(contract.aliases)) {
        const runtimeEntry = getRegistryEntry(alias);
        expect(runtimeEntry, `Alias '${alias}' not found in runtime registry`).toBeDefined();
        expect(runtimeEntry?.id).toBe(expectedCanonical);
        expect(typeof runtimeEntry?.component).toBe("function");
      }
    });

    it("every runtime alias in TEMPLATE_ALIASES is registered in contract", () => {
      for (const [alias, canonicalId] of Object.entries(TEMPLATE_ALIASES)) {
        expect(contract.aliases[alias], `Runtime alias '${alias}' missing in contract`).toBe(canonicalId);
      }
    });
  });

  describe("3. Fail-Closed Resolution Semantics (LED-039)", () => {
    it("returns undefined for unknown template IDs", () => {
      expect(getRegistryEntry("UnknownFakeTemplate123")).toBeUndefined();
      expect(getRegistryEntry("non-existent-template")).toBeUndefined();
    });

    it("returns undefined for non-template metadata names", () => {
      expect(getRegistryEntry("Background")).toBeUndefined();
      expect(getRegistryEntry("Color")).toBeUndefined();
      expect(getRegistryEntry("Width")).toBeUndefined();
      expect(getRegistryEntry("misc")).toBeUndefined();
    });

    it("returns undefined for malformed or whitespace identifiers", () => {
      expect(getRegistryEntry("")).toBeUndefined();
      expect(getRegistryEntry("   ")).toBeUndefined();
      expect(getRegistryEntry("  rui-hero-device-assemble  ")).toBeUndefined();
      expect(getRegistryEntry("rui-hero-device-assemble\n")).toBeUndefined();
    });
  });

  describe("4. Concrete Exemplars (LED-037, LED-040, LED-042)", () => {
    it("rui-hero-device-assemble resolves identically by canonical and by alias", () => {
      const byCanonical = getRegistryEntry("rui-hero-device-assemble");
      const byAlias = getRegistryEntry("HeroDeviceAssembleWrapper");
      expect(byCanonical).toBeDefined();
      expect(byAlias).toBeDefined();
      expect(byCanonical?.id).toBe("rui-hero-device-assemble");
      expect(byAlias?.id).toBe("rui-hero-device-assemble");
      expect(byCanonical).toBe(byAlias);
    });

    it("animatedtext-element is canonical and resolves existing aliases seamlessly", () => {
      const byCanonical = getRegistryEntry("animatedtext-element");
      const byPascal = getRegistryEntry("AnimatedTextWrapper");
      const byLegacy = getRegistryEntry("Animatedtextwrapper");

      expect(byCanonical).toBeDefined();
      expect(byCanonical?.id).toBe("animatedtext-element");

      expect(byPascal).toBeDefined();
      expect(byPascal?.id).toBe("animatedtext-element");

      expect(byLegacy).toBeDefined();
      expect(byLegacy?.id).toBe("animatedtext-element");

      expect(byPascal).toBe(byCanonical);
      expect(byLegacy).toBe(byCanonical);
    });
  });
});
