import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import {
  BlueprintV2Schema,
  validateBlueprintV2,
  isLegacyBlueprintV1,
  migrateBlueprintToV2,
} from "../../contracts/blueprint";
import { ManifestV2 } from "../../contracts/manifest";

const FIXTURES_DIR = path.resolve(__dirname, "../fixtures/blueprint");

function loadFixture(filename: string): any {
  const p = path.join(FIXTURES_DIR, filename);
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

describe("Blueprint Canonical Contract & Validator (S12)", () => {
  // 1. Valid Minimal Blueprint
  it("accepts valid_minimal_blueprint.json", () => {
    const data = loadFixture("valid_minimal_blueprint.json");
    const res = validateBlueprintV2(data, { expectedProjectId: "prj_minimal_01" });
    expect(res.ok).toBe(true);
    expect(res.errors).toHaveLength(0);
    expect(res.blueprint?.blueprint_version).toBe("2.0.0");
    expect(res.blueprint?.fps).toBe(30);
  });

  // 2. Valid Multi-scene Blueprint
  it("accepts valid_multi_scene_blueprint.json", () => {
    const data = loadFixture("valid_multi_scene_blueprint.json");
    const res = validateBlueprintV2(data, { expectedProjectId: "prj_multi_02" });
    expect(res.ok).toBe(true);
    expect(res.blueprint?.scenes).toHaveLength(2);
    expect(res.blueprint?.scenes[0].transition?.type).toBe("fade");
    expect(res.blueprint?.scenes[1].effects[0].effect).toBe("blur_reveal");
  });

  // 3. Valid AudioPlan Blueprint with Manifest
  it("accepts valid_audio_plan_blueprint.json with matching manifest", () => {
    const data = loadFixture("valid_audio_plan_blueprint.json");
    const mockManifest: ManifestV2 = {
      manifest_version: "2.0.0",
      project_id: "prj_audio_03",
      created_at: "2026-09-28T12:00:00Z",
      assets: [
        { asset_id: "ast_vo_lead", kind: "vo", provenance: "user_upload", status: "ready" },
        { asset_id: "ast_music_ambient", kind: "music", provenance: "cache_reuse", status: "ready" },
        { asset_id: "ast_sfx_impact", kind: "sfx", provenance: "mcp_fetch", status: "ready" },
        { asset_id: "ast_sfx_whoosh", kind: "sfx", provenance: "cache_reuse", status: "ready" },
      ],
    };

    const res = validateBlueprintV2(data, { expectedProjectId: "prj_audio_03", manifest: mockManifest });
    expect(res.ok).toBe(true);
    expect(res.blueprint?.audio?.voiceover?.asset_ref).toBe("ast_vo_lead");
    expect(res.blueprint?.audio?.music?.volume).toBe(0.2);
    expect(res.blueprint?.audio?.global_sfx).toHaveLength(1);
  });

  // 4. Invalid Version
  it("rejects invalid_version_blueprint.json", () => {
    const data = loadFixture("invalid_version_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("blueprint_version"))).toBe(true);
  });

  // 5. Invalid Project ID
  it("rejects invalid_project_id_blueprint.json", () => {
    const data = loadFixture("invalid_project_id_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("project_id"))).toBe(true);
  });

  // 6. Invalid FPS
  it("rejects invalid_fps_blueprint.json", () => {
    const data = loadFixture("invalid_fps_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("fps"))).toBe(true);
  });

  // 7. Invalid Aspect Ratio
  it("rejects invalid_aspect_ratio_blueprint.json", () => {
    const data = loadFixture("invalid_aspect_ratio_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("aspect_ratio"))).toBe(true);
  });

  // 8. Invalid Start Frame
  it("rejects invalid_start_frame_blueprint.json", () => {
    const data = loadFixture("invalid_start_frame_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("startFrame"))).toBe(true);
  });

  // 9. Invalid Duration Frames
  it("rejects invalid_duration_frames_blueprint.json", () => {
    const data = loadFixture("invalid_duration_frames_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("durationFrames"))).toBe(true);
  });

  // 10. Invalid Audio Volume
  it("rejects invalid_audio_volume_blueprint.json", () => {
    const data = loadFixture("invalid_audio_volume_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("volume"))).toBe(true);
  });

  // 11. Invalid Audio Asset Kind
  it("rejects invalid_audio_asset_kind_blueprint.json when slot expects vo but kind is image", () => {
    const data = loadFixture("invalid_audio_asset_kind_blueprint.json");
    const mockManifest: ManifestV2 = {
      manifest_version: "2.0.0",
      project_id: "prj_bad_kind",
      created_at: "2026-09-28T12:00:00Z",
      assets: [
        { asset_id: "ast_image_as_vo", kind: "image", provenance: "user_upload", status: "ready" },
      ],
    };

    const res = validateBlueprintV2(data, { expectedProjectId: "prj_bad_kind", manifest: mockManifest });
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("kind") && (e.includes("vo") || e.includes("audio")))).toBe(true);
  });

  // 12. Invalid Transition Type
  it("rejects invalid_transition_type_blueprint.json", () => {
    const data = loadFixture("invalid_transition_type_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("transition.type"))).toBe(true);
  });

  // 13. Missing Required Fields
  it("rejects missing_required_fields_blueprint.json", () => {
    const data = loadFixture("missing_required_fields_blueprint.json");
    const res = validateBlueprintV2(data);
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("project_id"))).toBe(true);
    expect(res.errors.some((e) => e.includes("aspect_ratio"))).toBe(true);
    expect(res.errors.some((e) => e.includes("scenes"))).toBe(true);
  });

  // 14. Legacy v1 Migration
  it("migrates legacy_v1_blueprint.json to canonical v2", () => {
    const data = loadFixture("legacy_v1_blueprint.json");
    expect(isLegacyBlueprintV1(data)).toBe(true);

    const migrated = migrateBlueprintToV2(data);
    expect(migrated.blueprint_version).toBe("2.0.0");
    expect(migrated.version).toBeUndefined();
    expect(migrated.audio?.voiceover?.asset_ref).toBe("ast_vo_01");
    expect(migrated.audio?.music?.asset_ref).toBe("ast_music_01");
    expect(migrated.audio?.music?.ducking?.enabled).toBe(true);
    expect(migrated.scenes[0].transition?.type).toBe("fade");

    const res = validateBlueprintV2(migrated, { expectedProjectId: "prj_legacy_01" });
    expect(res.ok).toBe(true);
  });

  // 15. Project ID Mismatch
  it("rejects project_id mismatch against expectedProjectId", () => {
    const data = loadFixture("valid_minimal_blueprint.json");
    const res = validateBlueprintV2(data, { expectedProjectId: "prj_other_id" });
    expect(res.ok).toBe(false);
    expect(res.errors.some((e) => e.includes("Project ID mismatch"))).toBe(true);
  });
});
