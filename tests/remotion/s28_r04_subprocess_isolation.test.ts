/**
 * tests/remotion/s28_r04_subprocess_isolation.test.ts
 * Critical Architectural Test: Mutation Core, Normalization and Evaluation execute
 * in an isolated subprocess with React and Remotion forcibly blocked at module loader level.
 */
import { describe, it, expect } from "vitest";
import { spawnSync } from "child_process";
import * as path from "path";

describe("S28-R04 Engine-Free Subprocess Isolation: Mutation Core", () => {
  const rootDir = path.resolve(__dirname, "../..");

  it("R04-ISO-01: Mutations apply and evaluate in pure isolated Node process with React/Remotion blocked", () => {
    const isolationScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = [
        "react",
        "react-dom",
        "remotion",
        "@remotion/transitions",
        "@remotion/core",
        "@remotion/cli",
        "@remotion/google-fonts"
      ];

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

      async function run() {
        const {
          parseCanonicalVideo,
          normalizeCanonicalVideo,
          evaluateVideoAtFrame,
          applyMutation,
          applyBatch
        } = await import("./contracts/index.ts");

        const fixturePath = path.resolve("./tests/fixtures/canonical/01_simple_text_scene.json");
        const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
        const originalBp = parseCanonicalVideo(raw);

        // 1. Single Mutation: UPDATE_TEXT
        const m1 = {
          mutation_id: "iso_mut_text_01",
          type: "UPDATE_TEXT",
          author: "ai",
          expected_revision: 0,
          target: { scene_id: "scene_text_01" },
          payload: { text: "Isolated Headless Update" }
        };
        const res1 = applyMutation(originalBp, m1);
        if (!res1.success || res1.revision !== 1) {
          throw new Error("Single mutation failed: " + JSON.stringify(res1.error));
        }

        // 2. Optimistic Concurrency: Stale expected_revision must return conflict
        const staleMut = {
          mutation_id: "iso_mut_stale",
          type: "UPDATE_TEXT",
          expected_revision: 0, // Stale! Revision is already 1
          target: { scene_text_01: "scene_text_01" },
          target: { scene_id: "scene_text_01" },
          payload: { text: "Should Conflict" }
        };
        const conflictRes = applyMutation(res1.blueprint, staleMut);
        if (conflictRes.success || conflictRes.error?.code !== "REVISION_CONFLICT") {
          throw new Error("Optimistic concurrency check failed");
        }

        // 3. Idempotency: Re-applying same mutation_id returns idempotent no-op
        const replayRes = applyMutation(res1.blueprint, m1);
        if (!replayRes.success || !replayRes.idempotent || replayRes.revision !== 1) {
          throw new Error("Idempotency replay check failed");
        }

        // 4. Batch Mutation: ADD_LAYER + UPDATE_TRANSFORM
        const batch = {
          batch_id: "iso_batch_01",
          expected_revision: 1,
          mutations: [
            {
              mutation_id: "iso_batch_m1",
              type: "ADD_LAYER",
              target: { scene_id: "scene_text_01" },
              payload: {
                layer: {
                  layer_id: "iso_layer_rect",
                  kind: "shape",
                  time_range: { startFrame: 0, durationFrames: 90, endFrame: 90 },
                  transform: {
                    position: { x: 200, y: 150 },
                    scale: { x: 1, y: 1 },
                    rotation: 0,
                    anchor: { x: 0.5, y: 0.5 },
                    opacity: 1
                  },
                  opacity: 1,
                  visible: true,
                  z_index: 0,
                  shape_type: "rectangle",
                  size: { width: 500, height: 300 },
                  fillColor: "#00eeff",
                  channels: []
                }
              }
            },
            {
              mutation_id: "iso_batch_m2",
              type: "UPDATE_TRANSFORM",
              target: { scene_id: "scene_text_01", layer_id: "iso_layer_rect" },
              payload: {
                transform: {
                  rotation: 30,
                  opacity: 0.9
                }
              }
            }
          ]
        };
        const batchRes = applyBatch(res1.blueprint, batch);
        if (!batchRes.success || batchRes.revision !== 2) {
          throw new Error("Batch execution failed: " + JSON.stringify(batchRes.error));
        }

        // 5. Normalization on mutated blueprint
        const normalized = normalizeCanonicalVideo({ blueprint: batchRes.blueprint });
        if (!normalized || normalized.scenes[0].surface.text !== "Isolated Headless Update") {
          throw new Error("Normalization on mutated blueprint failed");
        }

        // 6. Frame Evaluation on mutated blueprint
        const frameState = evaluateVideoAtFrame(batchRes.blueprint, 15);
        if (!frameState || frameState.layers.length < 1) {
          throw new Error("Frame evaluation on mutated blueprint failed");
        }

        const rectLayer = frameState.layers.find(l => l.layer_id === "iso_layer_rect");
        if (!rectLayer || rectLayer.transform.rotation !== 30) {
          throw new Error("Evaluated layer transform mismatch: " + JSON.stringify(rectLayer));
        }

        process.stdout.write(JSON.stringify({
          status: "PASS",
          revision: batchRes.revision,
          evaluatedLayersCount: frameState.layers.length,
          isolatedText: normalized.scenes[0].surface.text,
          rectRotation: rectLayer.transform.rotation
        }));
      }

      run().catch((err) => {
        console.error(err);
        process.exit(1);
      });
    `;

    const result = spawnSync(
      "npx",
      ["tsx", "-e", isolationScript],
      {
        cwd: rootDir,
        encoding: "utf-8",
        timeout: 10000,
        env: { ...process.env, NODE_ENV: "production" },
      }
    );

    if (result.status !== 0) {
      console.error("STDOUT:", result.stdout);
      console.error("STDERR:", result.stderr);
    }

    expect(result.status, `Subprocess must exit with 0. Stderr: ${result.stderr}`).toBe(0);

    const parsedOutput = JSON.parse(result.stdout.trim());
    expect(parsedOutput.status).toBe("PASS");
    expect(parsedOutput.revision).toBe(2);
    expect(parsedOutput.isolatedText).toBe("Isolated Headless Update");
    expect(parsedOutput.rectRotation).toBe(30);
  }, 15000);

  it("R04-ISO-02: Critical Gate — Full EditorSession lifecycle (USER -> AI -> Undo -> Redo -> Normalize -> Evaluate) in isolated subprocess", () => {
    const isolationScript = `
      const Module = require("node:module");
      const origRequire = Module.prototype.require;
      const blocked = [
        "react",
        "react-dom",
        "remotion",
        "@remotion/transitions",
        "@remotion/core",
        "@remotion/cli",
        "@remotion/google-fonts"
      ];

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

      async function run() {
        const {
          parseCanonicalVideo,
          normalizeCanonicalVideo,
          evaluateVideoAtFrame,
          EditorSession
        } = await import("./contracts/index.ts");

        const fixturePath = path.resolve("./tests/fixtures/canonical/10_layer_stack.json");
        const raw = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
        const initialBp = parseCanonicalVideo(raw);

        const session = new EditorSession(initialBp);
        if (session.getRevision() !== 0) throw new Error("Initial revision must be 0");

        // 1. USER mutation -> revision +1
        const userRes = session.applyMutation({
          mutation_id: "iso_session_user_01",
          type: "UPDATE_TEXT",
          author: "user",
          target: { scene_id: "sc_stack_01", layer_id: "layer_headline" },
          payload: { text: "User Headline Revision" }
        });
        if (!userRes.success || session.getRevision() !== 1) {
          throw new Error("User mutation failed: " + JSON.stringify(userRes.error));
        }

        // 2. AI mutation via SAME engine -> revision +1 (now revision 2)
        const aiRes = session.applyMutation({
          mutation_id: "iso_session_ai_01",
          type: "UPDATE_TRANSFORM",
          author: "ai",
          target: { scene_id: "sc_stack_01", layer_id: "layer_headline" },
          payload: { transform: { rotation: 15, opacity: 0.95 } }
        });
        if (!aiRes.success || session.getRevision() !== 2) {
          throw new Error("AI mutation failed: " + JSON.stringify(aiRes.error));
        }

        // 3. Undo AI mutation -> revision returns to 1
        const undoAiRes = session.undo();
        if (!undoAiRes.success || session.getRevision() !== 1) {
          throw new Error("Undo AI failed");
        }
        const hlAfterUndoAi = session.getBlueprint().scenes[0].layers.find(l => l.layer_id === "layer_headline");
        if (hlAfterUndoAi.transform.rotation !== 0 || hlAfterUndoAi.text !== "User Headline Revision") {
          throw new Error("Undo AI state mismatch: " + JSON.stringify(hlAfterUndoAi));
        }

        // 4. Redo AI mutation -> revision returns to 2
        const redoAiRes = session.redo();
        if (!redoAiRes.success || session.getRevision() !== 2) {
          throw new Error("Redo AI failed");
        }
        const hlAfterRedoAi = session.getBlueprint().scenes[0].layers.find(l => l.layer_id === "layer_headline");
        if (hlAfterRedoAi.transform.rotation !== 15 || hlAfterRedoAi.text !== "User Headline Revision") {
          throw new Error("Redo AI state mismatch: " + JSON.stringify(hlAfterRedoAi));
        }

        // 5. Normalize
        const normalized = normalizeCanonicalVideo({ blueprint: session.getBlueprint() });
        if (!normalized || normalized.scenes[0].layers.length !== 3) {
          throw new Error("Normalize failed");
        }

        // 6. evaluateVideoAtFrame()
        const frameState = evaluateVideoAtFrame(session.getBlueprint(), 30);
        if (!frameState || frameState.layers.length < 1) {
          throw new Error("evaluateVideoAtFrame failed");
        }
        const evalHeadline = frameState.layers.find(l => l.layer_id === "layer_headline");

        process.stdout.write(JSON.stringify({
          status: "PASS",
          revision: session.getRevision(),
          text: evalHeadline.properties?.text ?? evalHeadline.text,
          rotation: evalHeadline.transform.rotation,
          undoCount: session.getUndoStackSize(),
          redoCount: session.getRedoStackSize()
        }));
      }

      run().catch((err) => {
        console.error(err);
        process.exit(1);
      });
    `;

    const result = spawnSync(
      "npx",
      ["tsx", "-e", isolationScript],
      {
        cwd: rootDir,
        encoding: "utf-8",
        timeout: 10000,
        env: { ...process.env, NODE_ENV: "production" },
      }
    );

    if (result.status !== 0) {
      console.error("STDOUT:", result.stdout);
      console.error("STDERR:", result.stderr);
    }
    expect(result.status, `Subprocess must exit with 0. Stderr: ${result.stderr}`).toBe(0);

    const parsedOutput = JSON.parse(result.stdout.trim());
    expect(parsedOutput.status).toBe("PASS");
    expect(parsedOutput.revision).toBe(2);
    expect(parsedOutput.text).toBe("User Headline Revision");
    expect(parsedOutput.rotation).toBe(15);
    expect(parsedOutput.undoCount).toBe(2);
    expect(parsedOutput.redoCount).toBe(0);
  }, 15000);
});
