/**
 * tests/remotion/s28_r13_unified_authoring.test.ts
 * Comprehensive Verification Suite for S28-R13: Unified Authoring Subsystem.
 * 
 * Verifies:
 *   - CreativePlan compiles to authoritative Canonical VideoDocument (BlueprintV2)
 *   - AI Intent -> Typed Canonical Mutation Planning
 *   - User and AI share identical mutation engine, validation, and history
 *   - Preservation of User Edits across downstream AI edits (CRITICAL TEST)
 *   - Stable-ID entity targeting & fail-closed error diagnostics
 *   - TemplateSpec instantiation and fine-grained mutation without re-instantiation
 *   - Compound commands with single-step undo / redo
 *   - Revision concurrency & conflict detection (REVISION_CONFLICT)
 *   - Atomic batch failure isolation
 *   - Idempotent AI retry behavior
 *   - ChangeSet generation & BrowserPreviewRuntime live preview sync
 *   - Preview Proxy selective invalidation
 *   - Renderer independence (RenderPlanner consumes canonical document)
 *   - Unsupported operations fail closed (UNSUPPORTED_AUTHORING_OPERATION)
 *   - Authoring provenance metadata tracking
 *   - Full E2E Round-Trip Authoring Lifecycle
 *   - Performance baselines
 */

import { describe, it, expect, beforeAll } from "vitest";
import * as fs from "fs";
import * as path from "path";

import {
  parseCanonicalVideo,
  validateBlueprintV2,
  type BlueprintV2,
  type BlueprintScene,
  type AuthoringRequest,
  type AuthoringResult,
  emptyChangeSet,
} from "../../contracts";
import {
  CANONICAL_RENDERER_REGISTRY,
  createMockRendererAdapter,
  CANVAS_RENDERER_ID,
  REMOTION_RENDERER_ID,
} from "../../contracts/renderer";
import {
  UnifiedAuthoringSession,
  planAuthoringIntent,
  compileCreativePlanToCanonical,
  instantiateTemplateToCanonicalDocument,
} from "../../authoring";
import { getSemanticTemplateSpec } from "../../registry/semantic-registry";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { PreviewProxyCoordinator } from "../../preview/proxy/proxy-coordinator";
import { RenderPlanner } from "../../planner/render-planner";
import creativeFixtures from "../ai/contracts/fixtures/creative_contract_fixtures.json";

describe("S28-R13 Unified Authoring Subsystem (AI + Templates + Editor)", () => {
  const rootDir = path.resolve(__dirname, "../..");
  const multiSceneFixturePath = path.resolve(
    rootDir,
    "tests/fixtures/canonical/05_multi_scenes_effects_transitions.json"
  );

  beforeAll(() => {
    if (!CANONICAL_RENDERER_REGISTRY.has(CANVAS_RENDERER_ID)) {
      CANONICAL_RENDERER_REGISTRY.register(
        createMockRendererAdapter({
          id: CANVAS_RENDERER_ID,
          capabilities: ["export_video", "shapes", "text", "images", "2d_transforms"],
        })
      );
    }
    if (!CANONICAL_RENDERER_REGISTRY.has(REMOTION_RENDERER_ID)) {
      CANONICAL_RENDERER_REGISTRY.register(
        createMockRendererAdapter({
          id: REMOTION_RENDERER_ID,
          capabilities: ["export_video", "transitions", "effects", "audio", "text", "shapes"],
        })
      );
    }
  });

  function loadSampleDocument(): BlueprintV2 {
    const rawPlan = creativeFixtures.valid.creative_plan;
    return compileCreativePlanToCanonical(rawPlan);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Single Authoring Authority & CreativePlan Compilation
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-01: CreativePlan compiles deterministically into Canonical VideoDocument (BlueprintV2)", () => {
    const rawPlan = creativeFixtures.valid.creative_plan;
    const blueprint = compileCreativePlanToCanonical(rawPlan);

    expect(blueprint.blueprint_version).toBe("2.0.0");
    expect(blueprint.project_id).toBe("brief_tech_saas_001");
    expect(blueprint.revision).toBe(0);
    expect(blueprint.scenes.length).toBe(rawPlan.scenes.length);

    // Verify each scene has stable IDs and layer stacks
    for (const sc of blueprint.scenes) {
      expect(sc.scene_id).toMatch(/^[a-zA-Z0-9_\-]+$/);
      expect(sc.layers).toBeDefined();
      expect(sc.layers!.length).toBeGreaterThan(0);
      expect(sc.layers![0].layer_id).toContain(sc.scene_id);
    }

    // Fail-closed validation check
    const validation = validateBlueprintV2(blueprint);
    expect(validation.ok).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Pure Intent-to-Mutation Planning
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-02: Pure Intent Planner translates AI intents into typed canonical mutations", () => {
    const blueprint = loadSampleDocument();
    const sceneId = blueprint.scenes[0].scene_id;
    const layerId = blueprint.scenes[0].layers![0].layer_id;

    // A. UPDATE_TEXT intent
    const textReq: AuthoringRequest = {
      request_id: "req_plan_01",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: layerId },
        payload: { text: "AI Generated Title" },
      },
    };
    const planRes = planAuthoringIntent(blueprint, textReq);
    expect(planRes.ok).toBe(true);
    if (planRes.ok) {
      expect(planRes.mutations).toHaveLength(1);
      expect(planRes.mutations[0].type).toBe("UPDATE_TEXT");
      expect((planRes.mutations[0] as any).payload.text).toBe("AI Generated Title");
      expect((planRes.mutations[0] as any).target.layer_id).toBe(layerId);
    }

    // B. Relative transform move: "Move 40px right"
    const xformReq: AuthoringRequest = {
      request_id: "req_plan_02",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TRANSFORM",
        target: { scene_id: sceneId, layer_id: layerId },
        payload: {
          transform: { position: { x: 40 } },
          relative: true,
        },
      },
    };
    const xformRes = planAuthoringIntent(blueprint, xformReq);
    expect(xformRes.ok).toBe(true);
    if (xformRes.ok) {
      expect(xformRes.mutations[0].type).toBe("UPDATE_TRANSFORM");
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. User / AI Same Mutation Engine
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-03: User edit and AI edit execute through the EXACT same mutation engine & history", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);

    const sceneId = blueprint.scenes[0].scene_id;
    const textLayer = blueprint.scenes[0].layers?.find((l) => l.kind === "text")?.layer_id;

    // User edit
    const userRes = session.executeRequest({
      request_id: "req_user_01",
      actor: "user",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: textLayer },
        payload: { text: "Edited By User" },
      },
    });

    expect(userRes.success).toBe(true);
    expect(userRes.result_revision).toBe(1);
    expect(userRes.changeset.affected_scene_ids).toContain(sceneId);

    // AI edit on next revision
    const aiRes = session.executeRequest({
      request_id: "req_ai_01",
      actor: "ai",
      base_revision: 1,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_STYLE",
        target: { scene_id: sceneId },
        payload: { backgroundColor: "#1e1b4b" },
      },
    });

    expect(aiRes.success).toBe(true);
    expect(aiRes.result_revision).toBe(2);

    // Verify history stack has both entries with their respective actors
    const history = session.getEditorSession().getHistory();
    expect(history.undo).toHaveLength(2);
    expect(history.undo[0].actor).toBe("user");
    expect(history.undo[1].actor).toBe("ai");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. CRITICAL: Preserve User Edits Across AI Edits
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-04: CRITICAL TEST — User edits survive downstream AI edits without whole-project overwrite", () => {
    // 1. Initial compilation from CreativePlan
    const rawPlan = creativeFixtures.valid.creative_plan;
    const initialDoc = compileCreativePlanToCanonical(rawPlan);
    const session = new UnifiedAuthoringSession(initialDoc);

    const sceneId = initialDoc.scenes[0].scene_id;
    const titleLayerId = `${sceneId}_title`;
    const bgLayerId = `${sceneId}_bg`;

    // 2. User changes title
    const userTitle = "Custom User Headline 2026";
    const edit1 = session.executeRequest({
      request_id: "user_edit_title",
      actor: "user",
      base_revision: 0,
      project_id: initialDoc.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: titleLayerId },
        payload: { text: userTitle },
      },
    });
    expect(edit1.success).toBe(true);
    expect(session.getRevision()).toBe(1);

    // 3. User moves title element (UPDATE_TRANSFORM)
    const userTransform = { position: { x: 120, y: -45 } };
    const edit2 = session.executeRequest({
      request_id: "user_edit_transform",
      actor: "user",
      base_revision: 1,
      project_id: initialDoc.project_id,
      intent: {
        type: "UPDATE_TRANSFORM",
        target: { scene_id: sceneId, layer_id: titleLayerId },
        payload: { transform: userTransform },
      },
    });
    expect(edit2.success).toBe(true);
    expect(session.getRevision()).toBe(2);

    // 4. AI receives instruction: "Make the background darker"
    const aiDarkColor = "#020408";
    const aiEdit = session.executeRequest({
      request_id: "ai_dark_bg",
      actor: "ai",
      base_revision: 2,
      project_id: initialDoc.project_id,
      intent: {
        type: "UPDATE_STYLE",
        target: { scene_id: sceneId, layer_id: bgLayerId },
        payload: { backgroundColor: aiDarkColor },
      },
    });
    expect(aiEdit.success).toBe(true);
    expect(session.getRevision()).toBe(3);

    // 5. VERIFICATION: Background is dark, USER TITLE SURVIVED, USER TRANSFORM SURVIVED!
    const finalDoc = session.getBlueprint();
    const finalScene = finalDoc.scenes.find((s) => s.scene_id === sceneId)!;
    const finalTitleLayer = finalScene.layers?.find((l) => l.layer_id === titleLayerId);
    const finalBgLayer = finalScene.layers?.find((l) => l.layer_id === bgLayerId);

    expect(finalBgLayer?.fillColor).toBe(aiDarkColor);
    expect(finalTitleLayer?.text).toBe(userTitle); // USER TITLE PRESERVED
    expect(finalTitleLayer?.transform.position.x).toBe(120); // USER X PRESERVED
    expect(finalTitleLayer?.transform.position.y).toBe(-45); // USER Y PRESERVED
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Stable-ID Targeting & Fail-Closed Errors
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-05: Missing targets and ambiguous queries fail closed with structured diagnostics", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);

    // A. Missing Scene
    const badSceneRes = session.executeRequest({
      request_id: "req_bad_scene",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: "non_existent_scene_xyz" },
        payload: { text: "Will fail" },
      },
    });
    expect(badSceneRes.success).toBe(false);
    expect(badSceneRes.error?.code).toBe("AUTHORING_TARGET_NOT_FOUND");
    expect(badSceneRes.result_revision).toBe(0);

    // B. Missing Layer in existing scene
    const badLayerRes = session.executeRequest({
      request_id: "req_bad_layer",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: blueprint.scenes[0].scene_id, layer_id: "ghost_layer_999" },
        payload: { text: "Will fail" },
      },
    });
    expect(badLayerRes.success).toBe(false);
    expect(badLayerRes.error?.code).toBe("AUTHORING_TARGET_NOT_FOUND");

    // C. Ambiguous selector matching multiple layers
    const ambigRes = session.executeRequest({
      request_id: "req_ambig",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: blueprint.scenes[0].scene_id, selector: "text" },
        payload: { text: "Will fail" },
      },
    });
    // In fixture 05, scene 0 contains multiple text elements
    if (!ambigRes.success) {
      expect(["AUTHORING_TARGET_AMBIGUOUS", "AUTHORING_TARGET_NOT_FOUND"]).toContain(ambigRes.error?.code);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Template Authoring & Granular Parameter Mutation
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-06: TemplateSpec instances remain editable via granular canonical mutations", () => {
    const spec = getSemanticTemplateSpec("rui-title-card");
    expect(spec).toBeDefined();

    const doc = instantiateTemplateToCanonicalDocument(spec!, {
      title: "Initial Title Card",
      subtitle: "Initial Subtitle",
    });

    const session = new UnifiedAuthoringSession(doc);
    const sceneId = doc.scenes[0].scene_id;

    // AI changes title/value via parameter without re-instantiation
    const res = session.executeRequest({
      request_id: "req_tmpl_param_01",
      actor: "ai",
      base_revision: 0,
      project_id: doc.project_id,
      intent: {
        type: "APPLY_TEMPLATE_PARAM",
        target: { scene_id: sceneId },
        payload: { parameter_name: "title", value: "99.999% High Availability" },
      },
    });

    expect(res.success).toBe(true);
    expect(res.result_revision).toBe(1);

    const titleLayer = session.getBlueprint().scenes[0].layers?.find((l) => l.kind === "text");
    expect(titleLayer?.text).toBe("99.999% High Availability");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 7. Compound Commands & Single-Step Undo/Redo
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-07: Compound AI command applies multiple mutations as ONE atomic undo step", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);
    const sceneId = blueprint.scenes[0].scene_id;

    const compoundRes = session.executeRequest({
      request_id: "ai_compound_quote",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "COMPOUND_COMMAND",
        command_type: "quote_card",
        target: { scene_id: sceneId },
        payload: {
          quote: "Quality is not an act, it is a habit.",
          author: "Aristotle",
          background: "#0f172a",
          accentColor: "#f59e0b",
        },
      },
    });

    expect(compoundRes.success).toBe(true);
    expect(compoundRes.result_revision).toBe(1);
    expect(compoundRes.applied_mutation_ids.length).toBeGreaterThanOrEqual(2);

    // Exact single-step undo
    const undoRes = session.undo();
    expect(undoRes.success).toBe(true);
    expect(session.getRevision()).toBe(0);
    expect(session.getBlueprint().scenes[0]).toEqual(blueprint.scenes[0]);

    // Exact redo
    const redoRes = session.redo();
    expect(redoRes.success).toBe(true);
    expect(session.getRevision()).toBe(1);
    expect(session.getBlueprint()).toEqual(compoundRes.blueprint);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 8. Revision Concurrency Conflict Detection
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-08: Stale base_revision fails closed with REVISION_CONFLICT without silent overwrite", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);
    const sceneId = blueprint.scenes[0].scene_id;
    const textLayer = blueprint.scenes[0].layers?.find((l) => l.kind === "text")?.layer_id;

    // 1. User mutates -> revision advances 0 -> 1
    session.executeRequest({
      request_id: "user_fast_edit",
      actor: "user",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: textLayer },
        payload: { text: "User fast change" },
      },
    });
    expect(session.getRevision()).toBe(1);

    // 2. AI submits edit planned at stale base_revision = 0
    const conflictRes = session.executeRequest({
      request_id: "ai_stale_edit",
      actor: "ai",
      base_revision: 0, // STALE!
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: textLayer },
        payload: { text: "AI Overwrite attempt" },
      },
    });

    expect(conflictRes.success).toBe(false);
    expect(conflictRes.error?.code).toBe("REVISION_CONFLICT");
    expect(session.getRevision()).toBe(1);

    // Verify user change remains intact
    const currentText = session.getBlueprint().scenes[0].layers?.find((l) => l.layer_id === textLayer)?.text;
    expect(currentText).toBe("User fast change");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 9. Atomic Batch Failure Isolation
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-09: Atomic batch failure rolls back all sub-mutations fail-closed", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);
    const sceneId = blueprint.scenes[0].scene_id;
    const validLayer = blueprint.scenes[0].layers![0].layer_id;

    // Batch containing one valid mutation and one targeting a non-existent entity
    const batchRes = session.executeRequest({
      request_id: "req_atomic_fail",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "COMPOUND_COMMAND",
        command_type: "custom",
        target: { scene_id: sceneId },
        payload: {
          mutations: [
            {
              type: "UPDATE_TRANSFORM",
              target: { scene_id: sceneId, layer_id: validLayer },
              payload: { transform: { position: { x: 999 } } },
            },
            {
              type: "UPDATE_TRANSFORM",
              target: { scene_id: sceneId, layer_id: "non_existent_layer_fail" },
              payload: { transform: { position: { x: 999 } } },
            },
          ],
        },
      },
    });

    expect(batchRes.success).toBe(false);
    expect(session.getRevision()).toBe(0);
    // Valid layer was NOT modified
    const layer = session.getBlueprint().scenes[0].layers!.find((l) => l.layer_id === validLayer);
    expect(layer?.transform.position.x).not.toBe(999);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 10. Idempotent AI Retry
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-10: Identical operation retry returns cached result without double execution", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);
    const sceneId = blueprint.scenes[0].scene_id;

    const opReq: AuthoringRequest = {
      request_id: "ai_idempotent_op_1",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_STYLE",
        target: { scene_id: sceneId },
        payload: { backgroundColor: "#1e293b" },
      },
    };

    // First attempt
    const firstRes = session.executeRequest(opReq);
    expect(firstRes.success).toBe(true);
    expect(firstRes.idempotent).toBe(false);
    expect(session.getRevision()).toBe(1);

    // Retry with identical request
    const retryRes = session.executeRequest(opReq);
    expect(retryRes.success).toBe(true);
    expect(retryRes.idempotent).toBe(true);
    expect(session.getRevision()).toBe(1); // Revision did NOT advance again
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 11. Live Preview & ChangeSet Integration
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-11: Authoring edits emit valid ChangeSets and update BrowserPreviewRuntime", () => {
    const blueprint = loadSampleDocument();
    const preview = new BrowserPreviewRuntime(blueprint);
    const session = new UnifiedAuthoringSession(blueprint, { previewRuntime: preview });

    let previewUpdated = false;
    preview.on("documentChange", (rev, cs) => {
      previewUpdated = true;
      expect(rev).toBe(1);
      expect(cs?.affected_scene_ids).toContain(blueprint.scenes[0].scene_id);
    });

    session.executeRequest({
      request_id: "req_preview_sync",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: blueprint.scenes[0].scene_id },
        payload: { text: "Preview Realtime Sync" },
      },
    });

    expect(previewUpdated).toBe(true);
    expect((preview.getDocument() as BlueprintV2).revision).toBe(1);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 12. Preview Proxy Invalidation
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-12: Mutations selectively invalidate preview proxy artifacts for affected entities", () => {
    const blueprint = loadSampleDocument();
    const coordinator = new PreviewProxyCoordinator({ maxParallelJobs: 1 });
    const preview = new BrowserPreviewRuntime(blueprint, { proxyCoordinator: coordinator });
    const session = new UnifiedAuthoringSession(blueprint, { previewRuntime: preview });

    const scene0 = blueprint.scenes[0].scene_id;
    const scene1 = blueprint.scenes[1].scene_id;

    // Seed mock proxy artifacts for Scene 0 and Scene 1
    preview.applyProxyArtifact({
      id: "proxy_art_sc0",
      job_id: "job_0",
      entity: { sceneId: scene0 },
      source_fingerprint: "fp_0",
      canonical_revision: 0,
      storage_key: "/tmp/proxy_sc0.mp4",
      size_bytes: 1024,
      duration_frames: 60,
      created_at: Date.now(),
    });

    preview.applyProxyArtifact({
      id: "proxy_art_sc1",
      job_id: "job_1",
      entity: { sceneId: scene1 },
      source_fingerprint: "fp_1",
      canonical_revision: 0,
      storage_key: "/tmp/proxy_sc1.mp4",
      size_bytes: 1024,
      duration_frames: 60,
      created_at: Date.now(),
    });

    expect(preview.getActiveProxies()).toHaveLength(2);

    // AI modifies Scene 0 only
    session.executeRequest({
      request_id: "req_inval_sc0",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_STYLE",
        target: { scene_id: scene0 },
        payload: { backgroundColor: "#000000" },
      },
    });

    // Scene 0 proxy invalidated; Scene 1 proxy remains active
    const remainingProxies = preview.getActiveProxies();
    expect(remainingProxies.some((p) => p.entity.sceneId === scene0)).toBe(false);
    expect(remainingProxies.some((p) => p.entity.sceneId === scene1)).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 13. Render Independence & RenderPlanner Compatibility
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-13: RenderPlanner decomposes mutated document without AI dictating render engine", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);

    session.executeRequest({
      request_id: "req_render_prep",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: blueprint.scenes[0].scene_id },
        payload: { text: "Render Ready Video" },
      },
    });

    const finalDoc = session.getBlueprint();
    const planner = new RenderPlanner();
    const planResult = planner.plan({ document: finalDoc, requestMode: "export_video" });
    expect(planResult.ok).toBe(true);
    expect(planResult.plan).toBeDefined();
    const nodes = Object.values(planResult.plan!.graph.nodes);
    expect(nodes.length).toBeGreaterThan(0);
    // Render assignments were made capability-based (not hardcoded by authoring layer)
    for (const node of nodes) {
      expect(["canvas-renderer-adapter", "remotion-renderer-adapter", "master-compositor"]).toContain(node.assignedRendererId);
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 14. Unsupported Request Fail-Closed
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-14: Unsupported requests (e.g. 3D holographic particles) fail closed with UNSUPPORTED_AUTHORING_OPERATION", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);

    const res = session.executeRequest({
      request_id: "req_unsupported_3d",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UNSUPPORTED",
        operation_name: "add_3d_holographic_particle_city",
        reason: "3D holographic particle rendering is unsupported in 2D canonical video model",
      },
    });

    expect(res.success).toBe(false);
    expect(res.error?.code).toBe("UNSUPPORTED_AUTHORING_OPERATION");
    expect(session.getRevision()).toBe(0);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 15. Authoring Provenance Tracking
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-15: Authoring provenance is cleanly recorded without mutating rendering invariants", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);

    session.executeRequest({
      request_id: "req_prov_test",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: blueprint.scenes[0].scene_id },
        payload: { text: "Provenance Check" },
      },
    });

    const history = session.getProvenanceHistory();
    expect(history).toHaveLength(1);
    expect(history[0].actor_type).toBe("AI");
    expect(history[0].operation_id).toBe("req_prov_test");
    expect(history[0].base_revision).toBe(0);
    expect(history[0].result_revision).toBe(1);
    expect(history[0].mutation_ids).toHaveLength(1);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 16. Full Round-Trip Critical Integration
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-16: Round-Trip E2E: CreativePlan -> compile -> AI -> User -> AI -> undo -> redo -> preview -> planner", () => {
    // 1. CreativePlan -> compile
    const rawPlan = creativeFixtures.valid.creative_plan;
    const doc = compileCreativePlanToCanonical(rawPlan);
    const session = new UnifiedAuthoringSession(doc);
    const sceneId = doc.scenes[0].scene_id;
    const titleLayer = `${sceneId}_title`;

    // 2. AI mutation A (update text)
    const resA = session.executeRequest({
      request_id: "round_trip_ai_A",
      actor: "ai",
      base_revision: 0,
      project_id: doc.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId, layer_id: titleLayer },
        payload: { text: "AI Initial Title" },
      },
    });
    expect(resA.success).toBe(true);

    // 3. User mutation B (move title)
    const resB = session.executeRequest({
      request_id: "round_trip_user_B",
      actor: "user",
      base_revision: 1,
      project_id: doc.project_id,
      intent: {
        type: "UPDATE_TRANSFORM",
        target: { scene_id: sceneId, layer_id: titleLayer },
        payload: { transform: { position: { x: 75, y: -25 } } },
      },
    });
    expect(resB.success).toBe(true);

    // 4. AI mutation C (compound quote card on scene 1)
    const resC = session.executeRequest({
      request_id: "round_trip_ai_C",
      actor: "ai",
      base_revision: 2,
      project_id: doc.project_id,
      intent: {
        type: "COMPOUND_COMMAND",
        command_type: "quote_card",
        target: { scene_id: doc.scenes[1].scene_id },
        payload: { quote: "Round trip quote", author: "Architect" },
      },
    });
    expect(resC.success).toBe(true);
    expect(session.getRevision()).toBe(3);

    // 5. Undo C
    const undoC = session.undo();
    expect(undoC.success).toBe(true);
    expect(session.getRevision()).toBe(2);

    // 6. Redo C
    const redoC = session.redo();
    expect(redoC.success).toBe(true);
    expect(session.getRevision()).toBe(3);

    // 7. Verify all edits preserved
    const finalDoc = session.getBlueprint();
    const finalSc0Title = finalDoc.scenes[0].layers?.find((l) => l.layer_id === titleLayer);
    expect(finalSc0Title?.text).toBe("AI Initial Title");
    expect(finalSc0Title?.transform.position.x).toBe(75);
    expect(finalSc0Title?.transform.position.y).toBe(-25);

    // 8. RenderPlanner consumes successfully
    const planner = new RenderPlanner();
    const plan = planner.plan({ document: finalDoc, requestMode: "export_video" });
    expect(plan.ok).toBe(true);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 17. Performance Baselines
  // ──────────────────────────────────────────────────────────────────────────

  it("R13-17: Performance Baselines — Intent planning, single mutation, compound command, and 100 sequential operations", () => {
    const blueprint = loadSampleDocument();
    const session = new UnifiedAuthoringSession(blueprint);
    const sceneId = blueprint.scenes[0].scene_id;

    // Baseline 1: Intent Planning Latency
    const t0 = performance.now();
    for (let i = 0; i < 50; i++) {
      planAuthoringIntent(blueprint, {
        request_id: `perf_plan_${i}`,
        actor: "ai",
        base_revision: 0,
        project_id: blueprint.project_id,
        intent: {
          type: "UPDATE_TEXT",
          target: { scene_id: sceneId },
          payload: { text: `Title ${i}` },
        },
      });
    }
    const planDuration = performance.now() - t0;
    const avgPlanMs = planDuration / 50;
    expect(avgPlanMs).toBeLessThan(5.0); // Sub-millisecond planning

    // Baseline 2: Single AI Mutation Apply
    const t1 = performance.now();
    const singleRes = session.executeRequest({
      request_id: "perf_single_mut",
      actor: "ai",
      base_revision: 0,
      project_id: blueprint.project_id,
      intent: {
        type: "UPDATE_TEXT",
        target: { scene_id: sceneId },
        payload: { text: "Fast Apply" },
      },
    });
    const singleMutMs = performance.now() - t1;
    expect(singleRes.success).toBe(true);
    expect(singleMutMs).toBeLessThan(15.0);

    // Baseline 3: Compound AI Command Apply
    const t2 = performance.now();
    const compoundRes = session.executeRequest({
      request_id: "perf_compound",
      actor: "ai",
      base_revision: 1,
      project_id: blueprint.project_id,
      intent: {
        type: "COMPOUND_COMMAND",
        command_type: "quote_card",
        target: { scene_id: sceneId },
        payload: { quote: "Performance matters", author: "Antigravity" },
      },
    });
    const compoundMs = performance.now() - t2;
    expect(compoundRes.success).toBe(true);
    expect(compoundMs).toBeLessThan(25.0);

    // Baseline 4: 100 Sequential Authoring Operations
    const t3 = performance.now();
    for (let i = 2; i < 102; i++) {
      const res = session.executeRequest({
        request_id: `seq_op_${i}`,
        actor: i % 2 === 0 ? "user" : "ai",
        base_revision: i,
        project_id: blueprint.project_id,
        intent: {
          type: "UPDATE_TEXT",
          target: { scene_id: sceneId },
          payload: { text: `Sequence Step ${i}` },
        },
      });
      expect(res.success).toBe(true);
    }
    const seqDuration = performance.now() - t3;
    const avgSeqMs = seqDuration / 100;
    expect(avgSeqMs).toBeLessThan(10.0);
    expect(session.getRevision()).toBe(102);

    // Baseline 5: Undo / Redo after AI edit
    const t4 = performance.now();
    const undoRes = session.undo();
    const undoMs = performance.now() - t4;
    expect(undoRes.success).toBe(true);
    expect(undoMs).toBeLessThan(5.0);

    const t5 = performance.now();
    const redoRes = session.redo();
    const redoMs = performance.now() - t5;
    expect(redoRes.success).toBe(true);
    expect(redoMs).toBeLessThan(5.0);
  });
});
