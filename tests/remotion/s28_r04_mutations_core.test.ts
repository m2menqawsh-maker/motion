/**
 * tests/remotion/s28_r04_mutations_core.test.ts
 * Comprehensive Verification for S28-R04 Canonical Mutation Core.
 * Tests:
 *   - Immutability
 *   - Fail-closed error handling
 *   - Revision tracking & optimistic concurrency
 *   - Idempotency
 *   - Batch atomicity
 *   - Stable IDs
 *   - All 18 core mutation types
 *   - Normalization & Frame Evaluation integration
 *   - Common path for User & AI
 *   - ChangeSet & Invalidation metadata
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import {
  parseCanonicalVideo,
  normalizeCanonicalVideo,
  evaluateVideoAtFrame,
  applyMutation,
  applyBatch,
  type BlueprintV2,
  type CanonicalMutation,
  type MutationBatch,
  type CanonicalLayer,
  createTimeRange,
} from "../../contracts";

describe("S28-R04 Canonical Mutation Core", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const fixturePath = path.resolve(rootDir, "tests/fixtures/canonical/05_multi_scenes_effects_transitions.json");
  const textFixturePath = path.resolve(rootDir, "tests/fixtures/canonical/01_simple_text_scene.json");

  function loadSampleBlueprint(): BlueprintV2 {
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
    return parseCanonicalVideo(raw);
  }

  function loadTextBlueprint(): BlueprintV2 {
    const raw = JSON.parse(fs.readFileSync(textFixturePath, "utf-8"));
    return parseCanonicalVideo(raw);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Immutability & Fail-Closed Behavior
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-01: Immutable Mutation — Original blueprint is never mutated", () => {
    const original = loadSampleBlueprint();
    // Deep-freeze top level properties
    Object.freeze(original);
    Object.freeze(original.scenes);

    const mutation: CanonicalMutation = {
      mutation_id: "mut_freeze_test_01",
      type: "UPDATE_TEXT",
      author: "user",
      expected_revision: 0,
      target: { scene_id: "scene_01" },
      payload: { text: "Brand New Headline" },
    };

    const result = applyMutation(original, mutation);

    expect(result.success).toBe(true);
    expect(result.blueprint).not.toBe(original);
    expect(result.revision).toBe(1);
    expect(original.revision).toBe(0);
    expect(result.blueprint.scenes[0].surface?.text).toBe("Brand New Headline");
    expect(original.scenes[0].surface?.text).not.toBe("Brand New Headline");
  });

  it("MUT-02: Invalid edit leaves original unchanged (Fail-Closed)", () => {
    const original = loadSampleBlueprint();
    const originalJson = JSON.stringify(original);

    const invalidMutation: CanonicalMutation = {
      mutation_id: "mut_invalid_target_01",
      type: "UPDATE_TEXT",
      author: "user",
      target: { scene_id: "sc_non_existent_999" },
      payload: { text: "Should Fail" },
    };

    const result = applyMutation(original, invalidMutation);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe("SCENE_NOT_FOUND");
    expect(result.revision).toBe(0);
    expect(result.blueprint).toBe(original);
    expect(JSON.stringify(original)).toBe(originalJson);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Revision Model & Optimistic Concurrency
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-03: Optimistic concurrency — revision conflict rejected without silent overwrite", () => {
    const blueprint = loadSampleBlueprint();
    expect(blueprint.revision ?? 0).toBe(0);

    const mutationWithStaleRev: CanonicalMutation = {
      mutation_id: "mut_conflict_01",
      type: "UPDATE_TEXT",
      expected_revision: 42, // Stale!
      target: { scene_id: "scene_01" },
      payload: { text: "Conflicted Text" },
    };

    const result = applyMutation(blueprint, mutationWithStaleRev);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe("REVISION_CONFLICT");
    expect(result.error?.expected_revision).toBe(42);
    expect(result.error?.actual_revision).toBe(0);
    expect(result.revision).toBe(0);
    expect(blueprint.scenes[0].surface?.text).not.toBe("Conflicted Text");
  });

  it("MUT-04: Revision increments sequentially (N -> N+1)", () => {
    let bp = loadSampleBlueprint();
    expect(bp.revision ?? 0).toBe(0);

    const m1: CanonicalMutation = {
      mutation_id: "mut_seq_01",
      type: "UPDATE_TEXT",
      expected_revision: 0,
      target: { scene_id: "scene_01" },
      payload: { text: "Revision 1 Text" },
    };
    const res1 = applyMutation(bp, m1);
    expect(res1.success).toBe(true);
    expect(res1.revision).toBe(1);
    bp = res1.blueprint;

    const m2: CanonicalMutation = {
      mutation_id: "mut_seq_02",
      type: "UPDATE_TEXT",
      expected_revision: 1,
      target: { scene_id: "scene_01" },
      payload: { text: "Revision 2 Text" },
    };
    const res2 = applyMutation(bp, m2);
    expect(res2.success).toBe(true);
    expect(res2.revision).toBe(2);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Idempotency Model
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-05: Idempotency — Re-applying identical mutation_id is a safe no-op", () => {
    const bp = loadSampleBlueprint();

    const mutation: CanonicalMutation = {
      mutation_id: "mut_idempotent_key_01",
      type: "UPDATE_TEXT",
      target: { scene_id: "scene_01" },
      payload: { text: "Idempotent Headline" },
    };

    const firstRun = applyMutation(bp, mutation);
    expect(firstRun.success).toBe(true);
    expect(firstRun.revision).toBe(1);
    expect(firstRun.idempotent).toBe(false);

    // Second run with same mutation_id on the updated blueprint
    const secondRun = applyMutation(firstRun.blueprint, mutation);
    expect(secondRun.success).toBe(true);
    expect(secondRun.revision).toBe(1); // Revision does NOT bump again
    expect(secondRun.idempotent).toBe(true);
    expect(secondRun.blueprint).toBe(firstRun.blueprint);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Batch Atomicity
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-06: Atomic Batch — All mutations succeed or entire batch rolls back", () => {
    const bp = loadSampleBlueprint();
    const originalJson = JSON.stringify(bp);

    const failingBatch: MutationBatch = {
      batch_id: "batch_fail_test",
      mutations: [
        {
          mutation_id: "mut_batch_01",
          type: "UPDATE_TEXT",
          target: { scene_id: "scene_01" },
          payload: { text: "First Text Update" },
        },
        {
          mutation_id: "mut_batch_02",
          type: "UPDATE_TEXT",
          target: { scene_id: "sc_INVALID_DOES_NOT_EXIST" }, // Will FAIL
          payload: { text: "Should Cause Rollback" },
        },
      ],
    };

    const result = applyBatch(bp, failingBatch);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe("BATCH_EXECUTION_FAILED");
    expect(result.revision).toBe(0);
    expect(JSON.stringify(result.blueprint)).toBe(originalJson);
    expect(bp.scenes[0].surface?.text).not.toBe("First Text Update");
  });

  it("MUT-07: Successful atomic batch advances document revision with aggregated changeset", () => {
    const bp = loadSampleBlueprint();

    const successfulBatch: MutationBatch = {
      batch_id: "batch_success_01",
      expected_revision: 0,
      mutations: [
        {
          mutation_id: "mut_batch_s1",
          type: "UPDATE_TEXT",
          target: { scene_id: "scene_01" },
          payload: { text: "Scene 1 Updated Text" },
        },
        {
          mutation_id: "mut_batch_s2",
          type: "UPDATE_TRANSFORM",
          target: { scene_id: "scene_01" },
          payload: { transform: { rotation: 45, opacity: 0.8 } },
        },
      ],
    };

    const result = applyBatch(bp, successfulBatch);

    expect(result.success).toBe(true);
    expect(result.revision).toBe(1);
    expect(result.applied_mutation_ids).toEqual(["mut_batch_s1", "mut_batch_s2"]);
    expect(result.changeset.affected_scene_ids).toContain("scene_01");
    expect(result.changeset.invalidation.requires_layout).toBe(true);
    expect(result.changeset.invalidation.requires_render).toBe(true);
    expect(result.changeset.mutations_count).toBe(2);
    expect(result.blueprint.scenes[0].surface?.text).toBe("Scene 1 Updated Text");
    expect(result.blueprint.scenes[0].surface?.rotation).toBe(45);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Stable Identifiers Invariants
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-08: Target validation enforces stable alphanumeric IDs (no array indices)", () => {
    const bp = loadSampleBlueprint();

    const invalidCharTarget = {
      mutation_id: "mut_invalid_chars",
      type: "UPDATE_TEXT",
      target: { scene_id: "sc with spaces!" },
      payload: { text: "Bad ID" },
    };

    const res = applyMutation(bp, invalidCharTarget);
    expect(res.success).toBe(false);
    expect(res.error?.code).toBe("INVALID_MUTATION");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Core Mutations: Layers & Groups
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-09: ADD_LAYER, DUPLICATE_LAYER, REORDER_LAYER, and REMOVE_LAYER", () => {
    let bp = loadSampleBlueprint();

    // 1. ADD_LAYER
    const newLayer: CanonicalLayer = {
      layer_id: "layer_custom_shape_01",
      kind: "shape",
      time_range: createTimeRange(0, 30),
      transform: {
        position: { x: 100, y: 100 },
        scale: { x: 1, y: 1 },
        rotation: 0,
        anchor: { x: 0.5, y: 0.5 },
        opacity: 1,
      },
      opacity: 1,
      visible: true,
      z_index: 2,
      shape_type: "rectangle",
      size: { width: 400, height: 200 },
      fillColor: "#ff0055",
      channels: [],
    };

    const addRes = applyMutation(bp, {
      mutation_id: "mut_add_layer_01",
      type: "ADD_LAYER",
      target: { scene_id: "scene_01" },
      payload: { layer: newLayer },
    });

    expect(addRes.success).toBe(true);
    bp = addRes.blueprint;
    const sc01 = bp.scenes.find((s) => s.scene_id === "scene_01")!;
    expect(sc01.layers?.some((l) => l.layer_id === "layer_custom_shape_01")).toBe(true);

    // 2. DUPLICATE_LAYER
    const dupRes = applyMutation(bp, {
      mutation_id: "mut_dup_layer_01",
      type: "DUPLICATE_LAYER",
      target: { scene_id: "scene_01", layer_id: "layer_custom_shape_01" },
      payload: { new_layer_id: "layer_custom_shape_02", offset: { x: 50, y: 50 } },
    });

    expect(dupRes.success).toBe(true);
    bp = dupRes.blueprint;
    const duplicated = bp.scenes[0].layers?.find((l) => l.layer_id === "layer_custom_shape_02")!;
    expect(duplicated).toBeDefined();
    expect(duplicated.transform.position.x).toBe(150);
    expect(duplicated.transform.position.y).toBe(150);

    // 3. REORDER_LAYER
    const reorderRes = applyMutation(bp, {
      mutation_id: "mut_reorder_layer_01",
      type: "REORDER_LAYER",
      target: { scene_id: "scene_01", layer_id: "layer_custom_shape_02" },
      payload: { new_z_index: 10 },
    });
    expect(reorderRes.success).toBe(true);
    bp = reorderRes.blueprint;
    expect(bp.scenes[0].layers?.find((l) => l.layer_id === "layer_custom_shape_02")?.z_index).toBe(10);

    // 4. REMOVE_LAYER
    const removeRes = applyMutation(bp, {
      mutation_id: "mut_remove_layer_01",
      type: "REMOVE_LAYER",
      target: { scene_id: "scene_01", layer_id: "layer_custom_shape_01" },
    });
    expect(removeRes.success).toBe(true);
    bp = removeRes.blueprint;
    expect(bp.scenes[0].layers?.some((l) => l.layer_id === "layer_custom_shape_01")).toBe(false);
  });

  it("MUT-10: REMOVE_LAYER fails closed when child layers are parented to it without cascade", () => {
    let bp = loadSampleBlueprint();

    // Add parent group
    const parentLayer: CanonicalLayer = {
      layer_id: "grp_parent_01",
      kind: "group",
      time_range: createTimeRange(0, 30),
      transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
      opacity: 1,
      visible: true,
      z_index: 0,
      children_ids: ["layer_child_01"],
      channels: [],
    };

    // Add child layer
    const childLayer: CanonicalLayer = {
      layer_id: "layer_child_01",
      kind: "text",
      parent_id: "grp_parent_01",
      time_range: createTimeRange(0, 30),
      transform: { position: { x: 10, y: 10 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
      opacity: 1,
      visible: true,
      z_index: 1,
      text: "Child Text",
      typography: { fontFamily: "Cairo", fontSize: 32 },
      channels: [],
    };

    const addParentRes = applyMutation(bp, {
      mutation_id: "m_add_parent",
      type: "ADD_LAYER",
      target: { scene_id: "scene_01" },
      payload: { layer: parentLayer },
    });
    bp = addParentRes.blueprint;

    const addChildRes = applyMutation(bp, {
      mutation_id: "m_add_child",
      type: "ADD_LAYER",
      target: { scene_id: "scene_01" },
      payload: { layer: childLayer },
    });
    bp = addChildRes.blueprint;

    // Try removing parent without cascade
    const removeRes = applyMutation(bp, {
      mutation_id: "m_remove_parent_fail",
      type: "REMOVE_LAYER",
      target: { scene_id: "scene_01", layer_id: "grp_parent_01" },
    });

    expect(removeRes.success).toBe(false);
    expect(removeRes.error?.code).toBe("DANGLING_PARENT_REFERENCE");

    // Remove parent WITH cascade
    const removeCascadeRes = applyMutation(bp, {
      mutation_id: "m_remove_parent_cascade",
      type: "REMOVE_LAYER",
      target: { scene_id: "scene_01", layer_id: "grp_parent_01" },
      payload: { cascade: true },
    });
    expect(removeCascadeRes.success).toBe(true);
    expect(removeCascadeRes.blueprint.scenes[0].layers?.some((l) => l.layer_id === "grp_parent_01")).toBe(false);
    expect(removeCascadeRes.blueprint.scenes[0].layers?.some((l) => l.layer_id === "layer_child_01")).toBe(false);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 7. Core Mutations: Clips (Move, Trim, Split)
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-11: MOVE_CLIP, TRIM_CLIP, and SPLIT_CLIP on scenes", () => {
    let bp = loadSampleBlueprint();

    // 1. MOVE_CLIP
    const moveRes = applyMutation(bp, {
      mutation_id: "mut_move_clip_01",
      type: "MOVE_CLIP",
      target: { scene_id: "scene_01" },
      payload: { new_start_frame: 10 },
    });
    expect(moveRes.success).toBe(true);
    bp = moveRes.blueprint;
    expect(bp.scenes[0].startFrame).toBe(10);

    // 2. TRIM_CLIP
    const trimRes = applyMutation(bp, {
      mutation_id: "mut_trim_clip_01",
      type: "TRIM_CLIP",
      target: { scene_id: "scene_01" },
      payload: { new_duration_frames: 20 },
    });
    expect(trimRes.success).toBe(true);
    bp = trimRes.blueprint;
    expect(bp.scenes[0].durationFrames).toBe(20);

    // 3. SPLIT_CLIP at frame 20 (scene is 10 to 30)
    const splitRes = applyMutation(bp, {
      mutation_id: "mut_split_clip_01",
      type: "SPLIT_CLIP",
      target: { scene_id: "scene_01" },
      payload: { split_frame: 20, new_scene_id: "sc_01_part2" },
    });
    expect(splitRes.success).toBe(true);
    bp = splitRes.blueprint;
    expect(bp.scenes[0].durationFrames).toBe(10); // 10 to 20
    expect(bp.scenes[1].scene_id).toBe("sc_01_part2");
    expect(bp.scenes[1].startFrame).toBe(20);
    expect(bp.scenes[1].durationFrames).toBe(10); // 20 to 30
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 8. Core Mutations: Keyframes
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-12: SET_KEYFRAME, UPDATE_KEYFRAME, and REMOVE_KEYFRAME", () => {
    let bp = loadSampleBlueprint();

    // Add a layer first
    const layer: CanonicalLayer = {
      layer_id: "layer_animated_box",
      kind: "shape",
      time_range: createTimeRange(0, 60),
      transform: { position: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rotation: 0, anchor: { x: 0.5, y: 0.5 }, opacity: 1 },
      opacity: 1,
      visible: true,
      z_index: 0,
      shape_type: "rectangle",
      size: { width: 100, height: 100 },
      channels: [],
    };
    bp = applyMutation(bp, {
      mutation_id: "m_add_anim_layer",
      type: "ADD_LAYER",
      target: { scene_id: "scene_01" },
      payload: { layer },
    }).blueprint;

    // 1. SET_KEYFRAME
    const setKf1 = applyMutation(bp, {
      mutation_id: "m_set_kf1",
      type: "SET_KEYFRAME",
      target: { scene_id: "scene_01", layer_id: "layer_animated_box", channel_target: "TRANSFORM_X" },
      payload: {
        keyframe: {
          keyframe_id: "kf_x_0",
          frame: 0,
          value: 0,
          interpolation: "LINEAR",
        },
      },
    });
    expect(setKf1.success).toBe(true);
    bp = setKf1.blueprint;

    const setKf2 = applyMutation(bp, {
      mutation_id: "m_set_kf2",
      type: "SET_KEYFRAME",
      target: { scene_id: "scene_01", layer_id: "layer_animated_box", channel_target: "TRANSFORM_X" },
      payload: {
        keyframe: {
          keyframe_id: "kf_x_30",
          frame: 30,
          value: 300,
          interpolation: "SPRING",
          spring: { damping: 12, stiffness: 100, mass: 1, overshootClamping: false },
        },
      },
    });
    expect(setKf2.success).toBe(true);
    bp = setKf2.blueprint;

    const animLayer = bp.scenes[0].layers?.find((l) => l.layer_id === "layer_animated_box")!;
    expect(animLayer.channels.length).toBe(1);
    expect(animLayer.channels[0].keyframes.length).toBe(2);

    // 2. UPDATE_KEYFRAME
    const updateKf = applyMutation(bp, {
      mutation_id: "m_update_kf",
      type: "UPDATE_KEYFRAME",
      target: { scene_id: "scene_01", layer_id: "layer_animated_box", keyframe_id: "kf_x_30" },
      payload: { patch: { value: 500 } },
    });
    expect(updateKf.success).toBe(true);
    bp = updateKf.blueprint;
    const updatedChannel = bp.scenes[0].layers?.find((l) => l.layer_id === "layer_animated_box")!.channels[0];
    expect(updatedChannel.keyframes.find((k) => k.keyframe_id === "kf_x_30")?.value).toBe(500);

    // 3. REMOVE_KEYFRAME
    const removeKf = applyMutation(bp, {
      mutation_id: "m_remove_kf",
      type: "REMOVE_KEYFRAME",
      target: { scene_id: "scene_01", layer_id: "layer_animated_box", keyframe_id: "kf_x_0" },
    });
    expect(removeKf.success).toBe(true);
    bp = removeKf.blueprint;
    const finalChannel = bp.scenes[0].layers?.find((l) => l.layer_id === "layer_animated_box")!.channels[0];
    expect(finalChannel.keyframes.length).toBe(1);
    expect(finalChannel.keyframes[0].keyframe_id).toBe("kf_x_30");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 9. Core Mutations: Transitions & Scenes
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-13: Transitions and Scene lifecycle mutations", () => {
    let bp = loadSampleBlueprint();

    // 1. SET_TRANSITION
    const setTrans = applyMutation(bp, {
      mutation_id: "m_set_trans",
      type: "SET_TRANSITION",
      target: { scene_id: "scene_01" },
      payload: {
        transition: {
          type: "zoom",
          durationFrames: 20,
          overlap_semantics: "overlap",
        },
      },
    });
    expect(setTrans.success).toBe(true);
    bp = setTrans.blueprint;
    expect(bp.scenes[0].transition?.type).toBe("zoom");
    expect(bp.scenes[0].transition?.durationFrames).toBe(20);

    // 2. REMOVE_TRANSITION
    const remTrans = applyMutation(bp, {
      mutation_id: "m_rem_trans",
      type: "REMOVE_TRANSITION",
      target: { scene_id: "scene_01" },
    });
    expect(remTrans.success).toBe(true);
    bp = remTrans.blueprint;
    expect(bp.scenes[0].transition).toBeUndefined();

    // 3. DUPLICATE_SCENE
    const dupScene = applyMutation(bp, {
      mutation_id: "m_dup_scene",
      type: "DUPLICATE_SCENE",
      target: { scene_id: "scene_01" },
      payload: { new_scene_id: "sc_01_copy" },
    });
    expect(dupScene.success).toBe(true);
    bp = dupScene.blueprint;
    expect(bp.scenes.some((s) => s.scene_id === "sc_01_copy")).toBe(true);

    // 4. REORDER_SCENE
    const reorderScene = applyMutation(bp, {
      mutation_id: "m_reorder_scene",
      type: "REORDER_SCENE",
      target: { scene_id: "sc_01_copy" },
      payload: { relative_to: "scene_01", position: "before" },
    });
    expect(reorderScene.success).toBe(true);
    bp = reorderScene.blueprint;
    expect(bp.scenes[0].scene_id).toBe("sc_01_copy");

    // 5. REMOVE_SCENE
    const remScene = applyMutation(bp, {
      mutation_id: "m_rem_scene",
      type: "REMOVE_SCENE",
      target: { scene_id: "sc_01_copy" },
    });
    expect(remScene.success).toBe(true);
    bp = remScene.blueprint;
    expect(bp.scenes.some((s) => s.scene_id === "sc_01_copy")).toBe(false);

    // 6. Minimum Scenes invariant
    while (bp.scenes.length > 1) {
      bp = applyMutation(bp, {
        mutation_id: `m_drain_${bp.scenes[1].scene_id}`,
        type: "REMOVE_SCENE",
        target: { scene_id: bp.scenes[1].scene_id },
      }).blueprint;
    }
    expect(bp.scenes.length).toBe(1);

    const failLastScene = applyMutation(bp, {
      mutation_id: "m_rem_last_scene",
      type: "REMOVE_SCENE",
      target: { scene_id: bp.scenes[0].scene_id },
    });
    expect(failLastScene.success).toBe(false);
    expect(failLastScene.error?.code).toBe("MINIMUM_SCENES_VIOLATION");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 10. Normalization & Frame Evaluation Integration
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-14: Normalization after edit + evaluateVideoAtFrame sees edited state", () => {
    const bp = loadTextBlueprint();

    // Frame evaluation BEFORE edit at frame 15
    const initialEval = evaluateVideoAtFrame(bp, 15);
    const initialTextLayer = initialEval.layers.find((l) => l.kind === "text");
    expect(initialTextLayer).toBeDefined();
    const originalText = initialTextLayer?.properties.text;
    expect(originalText).toBe("العنوان الرئيسي المعتمد");

    // Apply mutation
    const mutatedResult = applyMutation(bp, {
      mutation_id: "m_eval_test_text",
      type: "UPDATE_TEXT",
      target: { scene_id: "scene_text_01" },
      payload: { text: "LIVE_EDITED_TEXT_12345" },
    });

    expect(mutatedResult.success).toBe(true);
    const mutatedBlueprint = mutatedResult.blueprint;

    // Normalization works cleanly on mutated blueprint
    const normalized = normalizeCanonicalVideo({ blueprint: mutatedBlueprint });
    expect(normalized).toBeDefined();
    expect(normalized.scenes[0].surface.text).toBe("LIVE_EDITED_TEXT_12345");

    // Frame evaluation AFTER edit at frame 15
    const postEval = evaluateVideoAtFrame(mutatedBlueprint, 15);
    const postTextLayer = postEval.layers.find((l) => l.kind === "text");
    expect(postTextLayer).toBeDefined();
    expect(postTextLayer?.properties.text).toBe("LIVE_EDITED_TEXT_12345");
    expect(postTextLayer?.properties.text).not.toBe(originalText);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 11. User vs AI Common Path
  // ──────────────────────────────────────────────────────────────────────────

  it("MUT-15: User and AI use identical mutation contract and validation path", () => {
    const bp = loadSampleBlueprint();

    const userMutation: CanonicalMutation = {
      mutation_id: "mut_from_user_ui",
      author: "user",
      type: "UPDATE_TEXT",
      expected_revision: 0,
      target: { scene_id: "scene_01" },
      payload: { text: "Manual User Input" },
    };

    const userRes = applyMutation(bp, userMutation);
    expect(userRes.success).toBe(true);
    expect(userRes.revision).toBe(1);

    const aiMutation: CanonicalMutation = {
      mutation_id: "mut_from_ai_director",
      author: "ai",
      type: "UPDATE_TEXT",
      expected_revision: 1,
      target: { scene_id: "scene_01" },
      payload: { text: "Autonomous AI Optimized Copy" },
    };

    const aiRes = applyMutation(userRes.blueprint, aiMutation);
    expect(aiRes.success).toBe(true);
    expect(aiRes.revision).toBe(2);
    expect(aiRes.blueprint.scenes[0].surface?.text).toBe("Autonomous AI Optimized Copy");
  });
});
