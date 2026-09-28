# Asset Manifest v2 Canonical Specification (S11)

## 1. Overview & Authority
Manifest v2 eliminates the historical contract split across the asset pipeline, unifying:
- `02_asset_manifest.json` as the canonical physical artifact.
- `scripts.core.manifest_model.ManifestV2` as the Python canonical authority.
- `schemas/manifest.v2.schema.json` as the canonical JSON Schema.
- `contracts/manifest.ts` as the TypeScript/Remotion contract.
- `scripts.core.manifest_loader.load_manifest` as the single authoritative loader across all live paths.

---

## 2. Core Separation of Concerns

### A. `provenance != status`
Historically, `source` conflated storage states (`incoming`, `cache`, `ready`) with acquisition origins (`user_upload`, `mcp_fetch`, `generated`). Manifest v2 strictly separates them:

- **`provenance` (Acquisition Origin)**:
  - `user_upload`: Directly supplied by user.
  - `mcp_fetch`: Retrieved from external providers via MCP servers (Pixabay, Pexels, Icons, etc.).
  - `generated`: Dynamically synthesized (e.g. TTS, AI imagery).
  - `cache_reuse`: Reused from the local system asset cache without re-downloading.

- **`status` (Operational / Storage Lifecycle)**:
  - `incoming`: Awaiting normalization or preprocessing.
  - `processing`: Under active transcoding/normalization.
  - `ready`: Fully normalized, checked, and ready for composition.
  - `failed`: Failed processing or validation.

### B. Canonical `AssetKind` Vocabulary
Uniform enum across Python, TypeScript, and JSON schemas:
- `image`: Visual raster/vector graphic.
- `video`: Video visual motion footage.
- `audio`: Generic audio track.
- `sfx`: Sound effects.
- `music`: Background musical score.
- `vo`: Voiceover narration track.
- `logo`: Brand or sponsor insignia.
- `icon`: Symbolic icon element.
- `font`: Typography typeface file.
- `json`: Structured animation/data asset.
- `other`: Uncategorized media element.

Legacy aliases (e.g. `voiceover` -> `vo`, `bgm` -> `music`, `graphic` -> `image`) are deterministically normalized during migration. Unsupported kinds fail closed immediately.

---

## 3. Data Model Schema

### Top-Level Manifest
| Field | Type | Required | Description |
|---|---|---|---|
| `manifest_version` | string | Yes | Must be `"2.0.0"` or `"2.0"`. |
| `project_id` | string | Yes | Matches `^[a-zA-Z0-9_-]+$` and project identity. |
| `created_at` | string (ISO-8601) | Yes | Creation timestamp. |
| `updated_at` | string (ISO-8601) | No | Last update timestamp. |
| `assets` | list[AssetV2] | Yes | Declared assets array. |
| `metadata` | dict | No | Extensible project-level asset metadata. |

### Asset Element (`AssetV2`)
| Field | Type | Required | Description |
|---|---|---|---|
| `asset_id` | string | Yes | Unique asset identifier (`^[a-zA-Z0-9_\\-\\.]+$`). |
| `kind` | AssetKind | Yes | Canonical asset kind enum. |
| `provenance` | Provenance | Yes | Canonical provenance enum. |
| `status` | AssetStatus | Yes | Canonical status enum. |
| `source_path` | string / null | Optional | Raw or source reference file path. |
| `processed_path` | string / null | Optional | Normalized, ready-to-render asset path. |
| `content_hash` | string / null | Optional | SHA-256 digest of media content. |
| `processing_spec_hash` | string / null | Optional | Digest of preprocessing parameters (LUFS, resolution). |
| `metadata` | dict | No | Dimensions, duration frames, cache_checked, etc. |

---

## 4. Semantic Invariants & Fail-Closed Enforcement

1. **Asset ID Uniqueness**: No two assets in `assets[]` may share the same `asset_id`. Duplicate IDs raise `ManifestValidationError(code="DUPLICATE_ASSET_ID")` prior to any disk or cache operations.
2. **Status Path Invariant**:
   - `status == "ready"` requires either `processed_path` or `source_path` to be non-empty.
   - `status == "incoming"` requires `source_path` to be non-empty.
3. **Project Identity Invariant**:
   `directory project ID == state.project_id == project.json project_id == manifest.project_id == blueprint.project_id`
   Verified via `validate_project_identity(project_dir)`. Mismatches raise `ProjectIdentityMismatchError`.
4. **Unsupported Version**: Any unknown version raises `ManifestValidationError(code="UNSUPPORTED_VERSION")`. Best-effort parsing of unknown versions is strictly prohibited.
5. **No Fail-Open Defaulting**: Missing manifests raise `ManifestNotFoundError`. APIs return `manifest: null` (never `{}`).

---

## 5. Migration Policy & Idempotency
- **Engine**: `scripts/core/manifest_migration.py`.
- **Command**: `python -m scripts.core.manifest_migration <path_or_id> [--dry-run] [--no-backup]`.
- **Idempotency**: Running migration on an already compliant v2 manifest produces zero mutations and returns `was_migrated = False`.
- **Ambiguous Data**: Unrecognized or incomplete legacy payloads raise `ManifestMigrationError` and are never silently guessed.
