import { z } from "zod";

// ==========================================
// Manifest v2 Canonical Vocabularies & Schemas (S11)
// ==========================================

export const AssetKindSchema = z.enum([
  "image",
  "video",
  "audio",
  "sfx",
  "music",
  "vo",
  "logo",
  "icon",
  "font",
  "json",
  "other",
]);
export type AssetKind = z.infer<typeof AssetKindSchema>;

export const ProvenanceSchema = z.enum([
  "user_upload",
  "mcp_fetch",
  "generated",
  "cache_reuse",
]);
export type Provenance = z.infer<typeof ProvenanceSchema>;

export const AssetStatusSchema = z.enum([
  "incoming",
  "processing",
  "ready",
  "failed",
]);
export type AssetStatus = z.infer<typeof AssetStatusSchema>;

export const AssetV2Schema = z.object({
  asset_id: z.string().regex(/^[a-zA-Z0-9_\-\.]+$/, "Invalid asset_id format"),
  kind: AssetKindSchema,
  provenance: ProvenanceSchema,
  status: AssetStatusSchema,
  source_path: z.string().nullable().optional(),
  processed_path: z.string().nullable().optional(),
  content_hash: z.string().nullable().optional(),
  processing_spec_hash: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.any()).optional().default({}),
});
export type AssetV2 = z.infer<typeof AssetV2Schema>;

export const ManifestV2Schema = z.object({
  manifest_version: z.enum(["2.0.0", "2.0"]),
  project_id: z.string().regex(/^[a-zA-Z0-9_\-]+$/, "Invalid project_id format"),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
  assets: z.array(AssetV2Schema).default([]),
  metadata: z.record(z.string(), z.any()).optional().default({}),
});
export type ManifestV2 = z.infer<typeof ManifestV2Schema>;

export interface ManifestValidationResult {
  ok: boolean;
  errors: string[];
  manifest?: ManifestV2;
}

export function validateManifestV2(data: unknown, expectedProjectId?: string): ManifestValidationResult {
  const parseResult = ManifestV2Schema.safeParse(data);
  if (!parseResult.success) {
    return {
      ok: false,
      errors: parseResult.error.errors.map(
        (e) => `[${e.path.join(".")}] ${e.message}`
      ),
    };
  }

  const manifest = parseResult.data;
  const errors: string[] = [];

  // Semantic Invariant: Project ID Match
  if (expectedProjectId && manifest.project_id !== expectedProjectId) {
    errors.push(
      `Project ID mismatch: manifest contains '${manifest.project_id}' but expected '${expectedProjectId}'`
    );
  }

  // Semantic Invariant: Duplicate Asset IDs
  const seenIds = new Set<string>();
  for (const asset of manifest.assets) {
    if (seenIds.has(asset.asset_id)) {
      errors.push(`Duplicate asset_id detected: '${asset.asset_id}'`);
    }
    seenIds.add(asset.asset_id);

    // Semantic Invariant: Path requirements based on status
    if (asset.status === "ready" && !asset.source_path && !asset.processed_path) {
      errors.push(
        `Asset '${asset.asset_id}' has status 'ready' but neither source_path nor processed_path is specified`
      );
    } else if (asset.status === "incoming" && !asset.source_path) {
      errors.push(
        `Asset '${asset.asset_id}' has status 'incoming' but source_path is missing`
      );
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return { ok: true, errors: [], manifest };
}
