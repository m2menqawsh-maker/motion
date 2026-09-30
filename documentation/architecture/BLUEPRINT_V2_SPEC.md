# Blueprint v2 Canonical Specification (S12)

## 1. Overview & Authority
Blueprint v2 establishes a single authoritative contract for video scene composition, visual timing, aspect ratio, frame rate, asset binding, and audio orchestration across Python, TypeScript, and JSON Schema domains.

- **Canonical Physical Artifact**: `05_blueprint.json` in the project root.
- **Python Canonical Authority**: `scripts.core.blueprint_model.BlueprintV2`.
- **TypeScript / Remotion Authority**: `contracts/blueprint.ts` (`BlueprintV2Schema`).
- **JSON Schema Authority**: `schemas/blueprint.schema.json` (compiled from canonical TypeScript Zod contract).
- **Authoritative Loader**: `scripts.core.blueprint_loader.load_blueprint` across all Python entrypoints.
- **Remotion Ingestion**: `remotion-app/src/loadProjectData.ts` and `remotion-app/src/merge.ts`.

---

## 2. Structural Schema & Core Fields

### Top-Level Blueprint (`BlueprintV2`)
| Field | Type | Required | Description |
|---|---|---|---|
| `blueprint_version` | string | Yes | Canonical version, must be `"2.0.0"` or `"2.0"`. |
| `project_id` | string | Yes | Matches `^[a-zA-Z0-9_-]+$` and project identity invariant. |
| `fps` | integer | Yes | Frame rate (supported: 24, 25, 30, 60). Canonical single location. |
| `aspect_ratio` | string | Yes | Format ratio (e.g. `"16:9"`, `"9:16"`, `"1:1"`). Canonical single location. |
| `scenes` | list[BlueprintSceneV2] | Yes | Ordered array of scene definitions (non-empty). |
| `audio` | AudioPlan / null | No | Canonical audio plan (voiceover, music, global SFX). |
| `assets` | list[BlueprintAssetDefinition] | No | Inline asset declarations or references. |
| `metadata` | dict | No | Extensible project-level non-timing metadata (title, author, tags). |

### Scene Element (`BlueprintSceneV2`)
| Field | Type | Required | Description |
|---|---|---|---|
| `scene_id` | string | Yes | Unique scene identifier (`^[a-zA-Z0-9_-]+$`). |
| `template` | string | Yes | Remotion template or element component identifier. |
| `startFrame` | integer | Yes | Non-negative start frame index (`>= 0`). |
| `durationFrames` | integer | Yes | Positive duration in frames (`> 0`). |
| `content` | dict | No | Scene template parameters, text, raw values, or media references. |
| `template_props` | dict | No | Direct template property pass-through dictionary. |
| `style` | dict / StyleSurface | No | Surface design tokens (theme, colors, typography). |
| `transition` | TransitionRef / null | No | Scene exit transition envelope (`type`, `durationFrames`, `timing`). |
| `effects` | list[EffectRef] | No | Visual effect pipeline wrappers (`type`, `params`). |

---

## 3. Timing Authority Model

1. **Single Source of Truth**:
   All scene timing is dictated strictly by `startFrame` (non-negative integer) and `durationFrames` (positive integer).
2. **Derived Project Duration**:
   Total project duration is derived from the maximum scene end frame:
   $$\text{total\_duration\_frames} = \max_{s \in \text{scenes}} (s.\text{startFrame} + s.\text{durationFrames})$$
   $$\text{total\_duration\_seconds} = \frac{\text{total\_duration\_frames}}{\text{fps}}$$
   Project duration is never redundantly or conflictingly stored at the root level.
3. **No Drift / No Ghost Fields**:
   `meta.fps`, `meta.aspect_ratio`, `meta.duration_sec`, and top-level `duration_sec` are strictly prohibited in canonical v2 payloads.

---

## 4. Aspect Ratio & FPS Single Authority

- **FPS Authority**: `blueprint.fps` is the sole source of truth.
  - Consumers (`probe_qc`, `validate_blueprint`, `merge.ts`, `loadProjectData.ts`) must never inspect `meta.fps`.
  - Permitted values: 24, 25, 30, 60.
- **Aspect Ratio Authority**: `blueprint.aspect_ratio` is the sole source of truth.
  - Consumers (`final_qc`, `validate_blueprint`, Remotion Root) must never inspect `meta.aspect_ratio`.
  - Permitted canonical formats: `"16:9"`, `"9:16"`, `"1:1"`, `"4:5"`, `"21:9"`.

---

## 5. AssetKind Alignment & Media References

1. **Zero AssetKind Drift**:
   Blueprint directly reuses the canonical `AssetKind` enum established in Manifest v2 (S11):
   - `image`, `video`, `audio`, `sfx`, `music`, `vo`, `logo`, `icon`, `font`, `json`, `other`.
   - Blueprint contracts import `AssetKind` from `manifest_model.py` (Python) and `contracts/manifest.ts` (TypeScript).
2. **Logical Asset References (`AssetRef`)**:
   Media references within scenes or AudioPlan point to `asset_id` strings declared in Manifest v2.
   - When Manifest v2 is supplied to validator, asset references are validated against manifest asset IDs.
   - Kind compatibility is strictly enforced (e.g. voiceover requires `vo` or `audio`; music requires `music` or `audio`).
   - Full disk path resolution is deferred to S14.

---

## 6. Canonical AudioPlan

The historical fragmentation across `voiceover.*`, `bgm`, `bgmVolume`, and `content.audioRef` is replaced by the canonical `AudioPlan`:

### Track Specifications
- **Voiceover (`VoiceoverTrack`)**:
  - `asset_id`: String reference to manifest asset (`kind in ["vo", "audio"]`).
  - `startFrame`: Optional integer offset (defaults to `0`).
  - `durationFrames`: Optional duration limit in frames.
  - `volume`: Float in range `[0.0, 1.0]` (defaults to `1.0`).
- **Music (`MusicTrack`)**:
  - `asset_id`: String reference to manifest asset (`kind in ["music", "audio"]`).
  - `startFrame`: Optional integer offset (defaults to `0`).
  - `durationFrames`: Optional duration limit in frames.
  - `volume`: Float in range `[0.0, 1.0]` (defaults to `0.3`).
  - `loop`: Boolean indicating whether track loops across total duration.
  - `ducking`: Optional ducking configuration (`duck_volume`: `0.0..1.0`, `fade_frames`: non-negative integer).
- **Global SFX (`GlobalSfxTrack`)**:
  - `asset_id`: String reference to manifest asset (`kind in ["sfx", "audio"]`).
  - `startFrame`: Non-negative start frame index.
  - `durationFrames`: Optional duration in frames.
  - `volume`: Float in range `[0.0, 1.0]` (defaults to `0.5`).

---

## 7. Transition & Effect Boundaries

Blueprint v2 defines typed boundary envelopes for scene transitions and effects without pre-empting the runtime implementation:
- **`TransitionRef`**:
  - `type`: Supported transition identifier (`"fade"`, `"dissolve"`, `"slide-left"`, `"slide-right"`, `"zoom-in"`, `"wipe"`).
  - `durationFrames`: Positive transition duration in frames (defaults to 15).
  - `timing`: Easing identifier (`"linear"`, `"ease-in-out"`).
- **`EffectRef`**:
  - `type`: Effect identifier (e.g. `"blur"`, `"color-grade"`, `"film-grain"`).
  - `params`: Extensible effect-specific parameters dictionary.
- **Boundary Guarantee**: Blueprint v2 validates contract syntax and types. Full runtime transition rendering and shader integration are deferred to S16.

---

## 8. Semantic Invariants & Fail-Closed Enforcement

1. **Project Identity Invariant**:
   `blueprint.project_id` must match expected project identity (`project_id == state.project_id == manifest.project_id`). Mismatches immediately raise `BlueprintProjectMismatchError`.
2. **Scene ID Uniqueness**:
   No duplicate `scene_id` values are permitted in `scenes[]`. Violations raise `BlueprintValidationError(code="DUPLICATE_SCENE_ID")`.
3. **Fail-Closed on Missing / Invalid Blueprint**:
   - `scripts/render_project.py` strictly exits 1 with typed failure if `05_blueprint.json` is missing or invalid.
   - `scripts/gates/probe_qc.py` and `scripts/gates/final_qc.py` fail closed on invalid blueprint schemas.
   - APIs return HTTP 404 / 422 with structured typed error payloads.
4. **Volume Boundaries**:
   All audio track volumes must satisfy $0.0 \le \text{volume} \le 1.0$. Out-of-range volumes fail validation.

---

## 9. Migration Policy & Legacy Support

- **Canonical Version**: `"2.0.0"` or `"2.0"`.
- **Legacy v1 Migration**:
  - Legacy v1 format (containing `version: "1.0"`, `timeline[]`, `meta.fps`, `meta.aspect_ratio`, `bgm`, `bgmVolume`, `voiceover`) is detected via `is_legacy_blueprint_v1()`.
  - Migrated deterministically to v2 via `migrate_blueprint_to_v2()` (Python) and `migrateBlueprintToV2()` (TypeScript).
  - Migration promotes `timeline` to `scenes`, extracts `fps` and `aspect_ratio` to top level, and maps legacy audio into canonical `AudioPlan`.
- **Unsupported Versions**: Any version other than 2.x or detectable 1.x raises `BlueprintVersionError` and fails closed immediately.

---

## 10. Deferred Responsibilities (Out of Scope for S12)

- **S13 (Transactional Materialization)**: Writing materializer locks, staging directories, and rollback transactions.
- **S14 (Runtime Asset Resolution)**: Resolving `AssetRef` to physical file paths or URLs at render time.
- **S15 (Template Registry Authority)**: Formalizing template registry schemas and discovery.
- **S16 (Per-Template Runtime Schemas & Transitions)**: Runtime rendering implementation of `TransitionRef` and per-template props validation.
- **S17 (Unified Render Payload)**: Standardizing composition bundles across CLI and API.
- **S18 / S19 (Probe & Final QC Rewrite)**: Full end-to-end QC rewrite on top of S12/S14/S16 contracts.
