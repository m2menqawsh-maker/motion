/**
 * registry/semantic-registry.ts — Pure Semantic Template Registry.
 * S28-R02 & S28-R05: Canonical machine-readable template metadata and TemplateSpec resolution.
 * ZERO React or Remotion dependencies (no TSX component imports).
 */
import registryMetadata from "./template-registry-data.json";
import templateSpecsMetadata from "./template-specs-data.json";
import { resolveTemplateSchemas } from "../contracts/template-schemas";
import { type TemplateSpec } from "../contracts/template-spec";

export interface SemanticTemplateEntry {
  id: string;
  label: { ar: string; en: string };
  description: { ar: string; en: string };
  category: string;
  defaultDurationFrames: number;
  schema: Record<string, any>;
  defaults: Record<string, any>;
  contentSchema?: any;
  propsSchema?: any;
  surfaceSchema?: any;
  component_name?: string;
  aliases?: string[];
}

/** Authoritative Canonical Semantic Template Registry */
export const CANONICAL_SEMANTIC_REGISTRY: Record<string, SemanticTemplateEntry> = {};

/** Authoritative Template Alias Dictionary */
export const SEMANTIC_TEMPLATE_ALIASES: Record<string, string> = {};

for (const [id, tpl] of Object.entries((registryMetadata as any).templates)) {
  const t = tpl as any;
  const schemas = resolveTemplateSchemas(t.canonical_id, t.schema || {}, t.defaults || {});
  CANONICAL_SEMANTIC_REGISTRY[id] = {
    id: t.canonical_id,
    label: t.label,
    description: t.description,
    category: t.category,
    defaultDurationFrames: t.default_duration_frames,
    schema: t.schema || {},
    defaults: t.defaults || {},
    contentSchema: schemas.contentSchema,
    propsSchema: schemas.propsSchema,
    surfaceSchema: schemas.surfaceSchema,
    component_name: t.component_name,
    aliases: t.aliases,
  };
  if (Array.isArray(t.aliases)) {
    for (const alias of t.aliases) {
      SEMANTIC_TEMPLATE_ALIASES[alias] = t.canonical_id;
    }
  }
}

/** Proxied registry that transparently resolves aliases and canonical IDs */
export const SEMANTIC_TEMPLATE_REGISTRY: Record<string, SemanticTemplateEntry> = new Proxy(
  CANONICAL_SEMANTIC_REGISTRY,
  {
    get(target, prop, receiver) {
      if (typeof prop === "string" && !(prop in target)) {
        const canonicalId = SEMANTIC_TEMPLATE_ALIASES[prop];
        if (canonicalId && canonicalId in target) {
          return target[canonicalId];
        }
      }
      return Reflect.get(target, prop, receiver);
    },
    has(target, prop) {
      if (typeof prop === "string" && prop in SEMANTIC_TEMPLATE_ALIASES) {
        const canonicalId = SEMANTIC_TEMPLATE_ALIASES[prop];
        if (canonicalId && canonicalId in target) {
          return true;
        }
      }
      return Reflect.has(target, prop);
    },
  }
);

/**
 * Resolves a semantic template entry by canonical ID, ground-truth name, or component stem.
 * Fails closed (returns undefined) for unknown template names.
 */
export function getSemanticTemplateEntry(templateName: string): SemanticTemplateEntry | undefined {
  if (!templateName || typeof templateName !== "string") return undefined;
  if (templateName.trim() !== templateName) return undefined;
  return SEMANTIC_TEMPLATE_REGISTRY[templateName];
}

export function isKnownTemplate(templateName: string): boolean {
  return Boolean(getSemanticTemplateEntry(templateName));
}

export function getAllSemanticTemplateIds(): string[] {
  return Object.keys(CANONICAL_SEMANTIC_REGISTRY);
}

// ─── S28-R05: Authoritative Engine-Neutral TemplateSpec Registry ─────────────

/** Authoritative Canonical TemplateSpec Registry */
export const CANONICAL_TEMPLATE_SPEC_REGISTRY: Record<string, TemplateSpec> = {};

for (const [id, spec] of Object.entries((templateSpecsMetadata as any).templates)) {
  CANONICAL_TEMPLATE_SPEC_REGISTRY[id] = spec as TemplateSpec;
}

/** Proxied TemplateSpec registry that transparently resolves aliases */
export const TEMPLATE_SPEC_REGISTRY: Record<string, TemplateSpec> = new Proxy(
  CANONICAL_TEMPLATE_SPEC_REGISTRY,
  {
    get(target, prop, receiver) {
      if (typeof prop === "string" && !(prop in target)) {
        const canonicalId = SEMANTIC_TEMPLATE_ALIASES[prop];
        if (canonicalId && canonicalId in target) {
          return target[canonicalId];
        }
      }
      return Reflect.get(target, prop, receiver);
    },
    has(target, prop) {
      if (typeof prop === "string" && prop in SEMANTIC_TEMPLATE_ALIASES) {
        const canonicalId = SEMANTIC_TEMPLATE_ALIASES[prop];
        if (canonicalId && canonicalId in target) {
          return true;
        }
      }
      return Reflect.has(target, prop);
    },
  }
);

/**
 * Resolves a semantic TemplateSpec by canonical ID or alias.
 * Fails closed (returns undefined) for unknown or malformed template names.
 */
export function getSemanticTemplateSpec(templateIdOrAlias: string): TemplateSpec | undefined {
  if (!templateIdOrAlias || typeof templateIdOrAlias !== "string") return undefined;
  if (templateIdOrAlias.trim() !== templateIdOrAlias) return undefined;
  return TEMPLATE_SPEC_REGISTRY[templateIdOrAlias];
}

export function isKnownTemplateSpec(templateIdOrAlias: string): boolean {
  return Boolean(getSemanticTemplateSpec(templateIdOrAlias));
}

export function getAllSemanticTemplateSpecs(): TemplateSpec[] {
  return Object.values(CANONICAL_TEMPLATE_SPEC_REGISTRY);
}
