/**
 * tests/remotion/s28_r04_editor_session.test.ts
 * Comprehensive test suite for EditorSession, History, Undo/Redo,
 * Transient Editing, Coalescing, and Persistence semantics.
 */
import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import {
  parseCanonicalVideo,
  normalizeCanonicalVideo,
  evaluateVideoAtFrame,
  EditorSession,
  computeInverseMutation,
  type CanonicalMutation,
  type MutationBatch,
  type BlueprintV2,
} from "../../contracts/canonical-video";

function loadFixture(name: string): BlueprintV2 {
  const p = path.resolve(__dirname, `../fixtures/canonical/${name}`);
  const raw = JSON.parse(fs.readFileSync(p, "utf-8"));
  return parseCanonicalVideo(raw);
}

describe("S28-R04 Part 2: Editor State, History & Undo/Redo Engine", () => {
  it("R04-ED-01: EditorSession wraps pure BlueprintV2 exclusively with single canonical authority", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const session = new EditorSession(bp, { maxHistorySize: 50, author: "user" });

    expect(session.getRevision()).toBe(0);
    expect(session.canUndo()).toBe(false);
    expect(session.canRedo()).toBe(false);
    expect(session.isDirty()).toBe(false);
    expect(session.getBlueprint().blueprint_id).toBe(bp.blueprint_id);
    expect(session.getPreviewBlueprint().blueprint_id).toBe(bp.blueprint_id);
  });

  it("R04-ED-02: Exact Undo (A -> B -> A) and Redo (A -> B) for committed mutations", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const session = new EditorSession(bp);

    const initialText = bp.scenes[0].surface?.text ?? "";
    const updatedText = "New Brand Headline";

    const mut: CanonicalMutation = {
      mutation_id: "mut_text_edit_01",
      type: "UPDATE_TEXT",
      author: "user",
      expected_revision: 0,
      target: { scene_id: "scene_text_01" },
      payload: { text: updatedText },
    };

    const res = session.applyMutation(mut);
    expect(res.success).toBe(true);
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(updatedText);
    expect(session.canUndo()).toBe(true);
    expect(session.canRedo()).toBe(false);

    // Undo -> A
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getRevision()).toBe(0);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(initialText);
    expect(session.canUndo()).toBe(false);
    expect(session.canRedo()).toBe(true);

    // Redo -> B
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(updatedText);
    expect(session.canUndo()).toBe(true);
    expect(session.canRedo()).toBe(false);
  });

  it("R04-ED-03: Redo branch invalidation on new branch fork (A -> B -> undo -> C => redo cleared)", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const initialText = bp.scenes[0].surface?.text;
    const session = new EditorSession(bp);

    // 1. A -> B
    session.applyMutation({
      mutation_id: "mut_b",
      type: "UPDATE_TEXT",
      author: "user",
      target: { scene_id: "scene_text_01" },
      payload: { text: "Branch B" },
    });
    expect(session.getRevision()).toBe(1);

    // 2. Undo -> A
    session.undo();
    expect(session.getRevision()).toBe(0);
    expect(session.canRedo()).toBe(true);
    expect(session.getRedoStackSize()).toBe(1);

    // 3. New mutation C on branch fork
    session.applyMutation({
      mutation_id: "mut_c",
      type: "UPDATE_TEXT",
      author: "user",
      target: { scene_id: "scene_text_01" },
      payload: { text: "Branch C" },
    });

    // Redo branch MUST be completely purged
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("Branch C");
    expect(session.canRedo()).toBe(false);
    expect(session.getRedoStackSize()).toBe(0);
    expect(session.canUndo()).toBe(true);

    // Undoing now restores A (not B)
    session.undo();
    expect(session.getRevision()).toBe(0);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(initialText);
  });

  it("R04-ED-04: Bounded history enforces maxHistorySize without unbounded memory growth", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const maxEntries = 5;
    const session = new EditorSession(bp, { maxHistorySize: maxEntries });

    for (let i = 1; i <= 15; i++) {
      session.applyMutation({
        mutation_id: `mut_step_${i}`,
        type: "UPDATE_TEXT",
        author: "user",
        target: { scene_id: "scene_text_01" },
        payload: { text: `Step ${i}` },
      });
      expect(session.getUndoStackSize()).toBeLessThanOrEqual(maxEntries);
    }

    expect(session.getUndoStackSize()).toBe(maxEntries);
    expect(session.getRevision()).toBe(15);

    // Undo 5 times should reach the bound limit
    for (let u = 0; u < maxEntries; u++) {
      expect(session.canUndo()).toBe(true);
      session.undo();
    }
    expect(session.canUndo()).toBe(false);
    // At revision 10 (15 - 5)
    expect(session.getRevision()).toBe(10);
  });

  it("R04-ED-05: Transient editing handles 500 drag updates at 60fps without polluting undo stack", () => {
    const bp = loadFixture("10_layer_stack.json");
    const session = new EditorSession(bp);

    const gestureId = "drag_gesture_layer_headline_01";
    const initialRev = session.getRevision();
    const initialX = session.getBlueprint().scenes[0].layers?.find((l) => l.layer_id === "layer_headline")?.transform.position.x ?? 0;

    // Simulate 500 high-frequency drag events
    for (let i = 1; i <= 500; i++) {
      const transientMut: CanonicalMutation = {
        mutation_id: `drag_move_${i}`,
        type: "UPDATE_TRANSFORM",
        author: "user",
        target: { scene_id: "sc_stack_01", layer_id: "layer_headline" },
        payload: {
          transform: {
            position: { x: initialX + i, y: 800 },
          },
        },
      };

      const transRes = session.applyTransientMutation(transientMut, gestureId);
      expect(transRes.success).toBe(true);

      // Committed blueprint revision MUST NOT advance during active drag
      expect(session.getRevision()).toBe(initialRev);
      // Undo stack MUST NOT be polluted by transient mouse moves
      expect(session.getUndoStackSize()).toBe(0);

      // Preview blueprint reflects the current drag position in real-time
      const previewLayer = transRes.previewBlueprint.scenes[0].layers?.find(
        (l) => l.layer_id === "layer_headline"
      );
      expect(previewLayer?.transform.position.x).toBe(initialX + i);
    }

    // Now commit the gesture on mouse up
    const commitRes = session.commitGesture(gestureId, "Mouse drag layer headline");
    expect(commitRes).not.toBeNull();
    expect(commitRes!.success).toBe(true);

    // Exactly ONE revision advance (+1)
    expect(session.getRevision()).toBe(initialRev + 1);
    // Exactly ONE history entry for all 500 drag updates
    expect(session.getUndoStackSize()).toBe(1);

    const finalLayer = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_headline"
    );
    expect(finalLayer?.transform.position.x).toBe(initialX + 500);

    // Exact undo restores initial start position before gesture
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getRevision()).toBe(initialRev);

    const restoredLayer = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_headline"
    );
    expect(restoredLayer?.transform.position.x).toBe(initialX);

    // Exact redo restores committed position
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getRevision()).toBe(initialRev + 1);
    const redoneLayer = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_headline"
    );
    expect(redoneLayer?.transform.position.x).toBe(initialX + 500);
  });

  it("R04-ED-06: Transient editing cancellation discards drag state cleanly", () => {
    const bp = loadFixture("10_layer_stack.json");
    const session = new EditorSession(bp);
    const initialX = session.getBlueprint().scenes[0].layers![0].transform.position.x;

    const gestureId = "cancelled_drag_01";
    session.applyTransientMutation(
      {
        mutation_id: "drag_temp",
        type: "UPDATE_TRANSFORM",
        target: { scene_id: "sc_stack_01", layer_id: "layer_bg" },
        payload: { transform: { position: { x: 999, y: 999 } } },
      },
      gestureId
    );

    expect(session.getPreviewBlueprint().scenes[0].layers![0].transform.position.x).toBe(999);

    session.cancelGesture(gestureId);

    // Preview returns to committed state
    expect(session.getPreviewBlueprint().scenes[0].layers![0].transform.position.x).toBe(initialX);
    expect(session.getBlueprint().scenes[0].layers![0].transform.position.x).toBe(initialX);
    expect(session.getUndoStackSize()).toBe(0);
  });

  it("R04-ED-07: Safe mutation coalescing merges identical target/actor/gesture mutations", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const initialText = bp.scenes[0].surface?.text;
    const session = new EditorSession(bp);

    // Three rapid updates with coalesce=true and same gesture
    const gestureId = "typewriter_gesture";
    session.applyMutation(
      {
        mutation_id: "type_01",
        type: "UPDATE_TEXT",
        author: "user",
        target: { scene_id: "scene_text_01" },
        payload: { text: "H" },
      },
      { coalesce: true, gestureId }
    );
    expect(session.getUndoStackSize()).toBe(1);

    session.applyMutation(
      {
        mutation_id: "type_02",
        type: "UPDATE_TEXT",
        author: "user",
        target: { scene_id: "scene_text_01" },
        payload: { text: "He" },
      },
      { coalesce: true, gestureId }
    );
    expect(session.getUndoStackSize()).toBe(1); // Coalesced!

    session.applyMutation(
      {
        mutation_id: "type_03",
        type: "UPDATE_TEXT",
        author: "user",
        target: { scene_id: "scene_text_01" },
        payload: { text: "Hello" },
      },
      { coalesce: true, gestureId }
    );
    expect(session.getUndoStackSize()).toBe(1); // Still coalesced!
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("Hello");

    // Single undo reverts all coalesced keystrokes cleanly back to original state
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(initialText);

    // Single redo restores full word "Hello"
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("Hello");
  });

  it("R04-ED-08: Compound batch mutations apply, undo, and redo atomically", () => {
    const bp = loadFixture("10_layer_stack.json");
    const session = new EditorSession(bp);

    const batch: MutationBatch = {
      batch_id: "compound_hero_update",
      author: "user",
      description: "Batch update text and add shape",
      mutations: [
        {
          mutation_id: "m_txt",
          type: "UPDATE_TEXT",
          target: { scene_id: "sc_stack_01", layer_id: "layer_headline" },
          payload: { text: "Compound Headline" },
        },
        {
          mutation_id: "m_lyr",
          type: "ADD_LAYER",
          target: { scene_id: "sc_stack_01" },
          payload: {
            layer: {
              layer_id: "layer_circle_new",
              kind: "shape",
              time_range: { startFrame: 0, durationFrames: 90, endFrame: 90 },
              transform: {
                position: { x: 300, y: 300 },
                scale: { x: 1, y: 1 },
                rotation: 0,
                anchor: { x: 0.5, y: 0.5 },
                opacity: 1,
              },
              opacity: 1,
              visible: true,
              z_index: 5,
              shape_type: "ellipse",
              size: { width: 100, height: 100 },
              fillColor: "#ff0088",
              channels: [],
            },
          },
        },
      ],
    };

    const res = session.applyBatch(batch);
    expect(res.success).toBe(true);
    expect(session.getRevision()).toBe(1);
    expect(session.getUndoStackSize()).toBe(1);

    const scene = session.getBlueprint().scenes[0];
    expect(scene.layers?.find((l) => l.layer_id === "layer_circle_new")).toBeDefined();
    expect(
      (scene.layers?.find((l) => l.layer_id === "layer_headline") as { text: string }).text
    ).toBe("Compound Headline");

    // Undo batch atomically
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getRevision()).toBe(0);
    const undoneScene = session.getBlueprint().scenes[0];
    expect(undoneScene.layers?.find((l) => l.layer_id === "layer_circle_new")).toBeUndefined();
    expect(
      (undoneScene.layers?.find((l) => l.layer_id === "layer_headline") as { text: string }).text
    ).toBe("Layer Stacking Heading");

    // Redo batch atomically
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getRevision()).toBe(1);
    const redoneScene = session.getBlueprint().scenes[0];
    expect(redoneScene.layers?.find((l) => l.layer_id === "layer_circle_new")).toBeDefined();
  });

  it("R04-ED-09: Persistence and autosave semantics track dirty state accurately", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const session = new EditorSession(bp);

    expect(session.isDirty()).toBe(false);

    // Edit 1
    session.applyMutation({
      mutation_id: "persist_m1",
      type: "UPDATE_TEXT",
      target: { scene_id: "scene_text_01" },
      payload: { text: "Edit 1" },
    });
    expect(session.isDirty()).toBe(true);

    // Save to durable persistence
    session.markSaved();
    expect(session.isDirty()).toBe(false);

    // Edit 2
    session.applyMutation({
      mutation_id: "persist_m2",
      type: "UPDATE_TEXT",
      target: { scene_id: "scene_text_01" },
      payload: { text: "Edit 2" },
    });
    expect(session.isDirty()).toBe(true);

    // Undo back to saved state -> dirty flag resets to false
    session.undo();
    expect(session.isDirty()).toBe(false);

    // Undo past saved state -> dirty again
    session.undo();
    expect(session.isDirty()).toBe(true);
  });

  it("R04-ED-10: USER and AI mutations execute via identical engine with unified history", () => {
    const bp = loadFixture("01_simple_text_scene.json");
    const initialText = bp.scenes[0].surface?.text;
    const session = new EditorSession(bp);

    // USER Mutation
    const userRes = session.applyMutation({
      mutation_id: "user_edit_01",
      type: "UPDATE_TEXT",
      author: "user",
      target: { scene_id: "scene_text_01" },
      payload: { text: "User Edited Text" },
    });
    expect(userRes.success).toBe(true);
    expect(session.getRevision()).toBe(1);

    // AI Mutation (e.g. style suggestion / autolayout)
    const aiRes = session.applyMutation({
      mutation_id: "ai_edit_01",
      type: "UPDATE_TEXT",
      author: "ai",
      target: { scene_id: "scene_text_01" },
      payload: { text: "AI Optimized Text" },
    });
    expect(aiRes.success).toBe(true);
    expect(session.getRevision()).toBe(2);

    expect(session.getUndoStackSize()).toBe(2);

    // Undo 1: reverts AI edit
    session.undo();
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("User Edited Text");

    // Undo 2: reverts USER edit
    session.undo();
    expect(session.getRevision()).toBe(0);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe(initialText);

    // Redo 1: restores USER edit
    session.redo();
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("User Edited Text");

    // Redo 2: restores AI edit
    session.redo();
    expect(session.getRevision()).toBe(2);
    expect(session.getBlueprint().scenes[0].surface?.text).toBe("AI Optimized Text");
  });

  it("R04-ED-11: Normalization and frame evaluation integrate faithfully after mutations, undo, and redo", () => {
    const bp = loadFixture("10_layer_stack.json");
    const session = new EditorSession(bp);

    // Apply layer transform mutation
    session.applyMutation({
      mutation_id: "eval_mut_rot",
      type: "UPDATE_TRANSFORM",
      target: { scene_id: "sc_stack_01", layer_id: "layer_bg" },
      payload: {
        transform: {
          rotation: 45,
          opacity: 0.8,
        },
      },
    });

    // 1. Post-mutation evaluation
    const evalMutated = evaluateVideoAtFrame(session.getBlueprint(), 15);
    const rectMutated = evalMutated.layers.find((l) => l.layer_id === "layer_bg");
    expect(rectMutated?.transform.rotation).toBe(45);
    expect(rectMutated?.transform.opacity).toBe(0.8);

    // 2. Undo evaluation
    session.undo();
    const evalUndone = evaluateVideoAtFrame(session.getBlueprint(), 15);
    const rectUndone = evalUndone.layers.find((l) => l.layer_id === "layer_bg");
    expect(rectUndone?.transform.rotation).toBe(0);
    expect(rectUndone?.transform.opacity).toBe(1);

    // 3. Redo evaluation
    session.redo();
    const evalRedone = evaluateVideoAtFrame(session.getBlueprint(), 15);
    const rectRedone = evalRedone.layers.find((l) => l.layer_id === "layer_bg");
    expect(rectRedone?.transform.rotation).toBe(45);
  });

  it("R04-ED-12: Keyframe mutations undo and redo with full parameter fidelity", () => {
    const bp = loadFixture("10_layer_stack.json");
    const session = new EditorSession(bp);

    // Add keyframe
    const kfMut: CanonicalMutation = {
      mutation_id: "kf_add_01",
      type: "SET_KEYFRAME",
      target: { scene_id: "sc_stack_01", layer_id: "layer_bg", channel_target: "OPACITY" },
      payload: {
        keyframe: {
          keyframe_id: "kf_op_test_01",
          frame: 30,
          value: 0.25,
          interpolation: "CUBIC_BEZIER",
          bezier: [0.25, 0.1, 0.25, 1.0],
        },
      },
    };

    const res = session.applyMutation(kfMut);
    expect(res.success).toBe(true);

    const layerAfter = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_bg"
    );
    const opChan = layerAfter?.channels?.find((c) => c.target === "OPACITY");
    expect(opChan?.keyframes.find((k) => k.keyframe_id === "kf_op_test_01")).toBeDefined();

    // Undo removes keyframe
    session.undo();
    const layerUndone = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_bg"
    );
    const chanUndone = layerUndone?.channels?.find((c) => c.target === "OPACITY");
    expect(chanUndone?.keyframes.find((k) => k.keyframe_id === "kf_op_test_01")).toBeUndefined();

    // Redo restores keyframe
    session.redo();
    const layerRedone = session.getBlueprint().scenes[0].layers?.find(
      (l) => l.layer_id === "layer_bg"
    );
    const chanRedone = layerRedone?.channels?.find((c) => c.target === "OPACITY");
    expect(chanRedone?.keyframes.find((k) => k.keyframe_id === "kf_op_test_01")?.value).toBe(0.25);
  });

  it("R04-ED-13: Scene structural mutations (ADD_SCENE, SPLIT_CLIP) undo and redo accurately", () => {
    const bp = loadFixture("05_multi_scenes_effects_transitions.json");
    const session = new EditorSession(bp);
    const origScenesCount = bp.scenes.length;

    // SPLIT_CLIP
    const splitMut: CanonicalMutation = {
      mutation_id: "split_m1",
      type: "SPLIT_CLIP",
      target: { scene_id: "scene_01" },
      payload: {
        split_frame: 45,
        new_scene_id: "scene_01_part2",
      },
    };

    const splitRes = session.applyMutation(splitMut);
    expect(splitRes.success).toBe(true);
    expect(session.getBlueprint().scenes.length).toBe(origScenesCount + 1);

    // Undo SPLIT_CLIP restores original scene count and duration
    session.undo();
    expect(session.getBlueprint().scenes.length).toBe(origScenesCount);
    expect(session.getBlueprint().scenes[0].durationFrames).toBe(90);

    // Redo SPLIT_CLIP splits again
    session.redo();
    expect(session.getBlueprint().scenes.length).toBe(origScenesCount + 1);
  });
});
