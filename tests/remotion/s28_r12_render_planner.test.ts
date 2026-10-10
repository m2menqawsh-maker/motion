/**
 * tests/remotion/s28_r12_render_planner.test.ts
 * Verification Suite for S28-R12: Multi-Engine RenderGraph & Render Planner.
 * 
 * Verifies:
 *   - Engine-neutral RenderGraph & RenderPlan contracts
 *   - Deterministic planning (identical inputs produce identical plan & fingerprint)
 *   - Scene decomposition into renderable DAG units
 *   - Capability-based renderer assignment (Zero hardcoded branching)
 *   - Critical Multi-Engine E2E: Canvas (Scene A) + Remotion (Scene B) + Canvas (Scene C) -> MasterCompositor -> Final MP4
 *   - Dependency graph validation & Kahn cycle rejection (RENDER_GRAPH_CYCLE)
 *   - Missing dependency fail-closed detection (MISSING_DEPENDENCY)
 *   - Parallel execution groups (Topological levels)
 *   - Deterministic cacheability & selective invalidation (only changed scene re-renders)
 *   - Fallback policy & quality requirements
 *   - Engine failure isolation (failure in node B halts C, but A completes cleanly)
 *   - Renderer outage simulation (disabling Remotion isolates failure to video-heavy scenes)
 *   - Artifact provenance tracking
 *   - Cancellation propagation via AbortSignal
 *   - Performance baselines
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

import type { BlueprintV2 } from "../../contracts/blueprint";
import {
  type OutputProfile,
  createDefaultOutputProfile,
  createIntermediateArtifact,
} from "../../contracts/compositor";
import {
  type RendererAdapter,
  RendererRegistry,
  CANONICAL_RENDERER_REGISTRY,
  createMockRendererAdapter,
  CANVAS_RENDERER_ID,
  REMOTION_RENDERER_ID,
} from "../../contracts/renderer";
import {
  type RenderPlan,
  type RenderGraph,
  RenderPlanningError,
  validateRenderGraph,
  computePlanFingerprint,
} from "../../contracts/render-graph";
import {
  RenderPlanner,
  deriveSceneRequiredCapabilities,
  buildExecutionGroups,
} from "../../planner/render-planner";
import {
  RenderGraphExecutor,
  type ExecutionResult,
} from "../../planner/render-graph-executor";
import {
  evaluatePlanCache,
  computeSceneFingerprint,
} from "../../planner/cache-evaluator";
import { resolveCompatibleRenderer } from "../../planner/planning-policy";
import {
  CANVAS_COST_PROFILE,
  REMOTION_COST_PROFILE,
  estimateTotalPlanCost,
} from "../../planner/cost-estimator";
import { createCanvasRendererAdapter } from "../../canvas/canvas-renderer-adapter";
import { createRemotionRendererAdapter } from "../../remotion/remotion-renderer-adapter";
import { MasterCompositor, probeMediaFile } from "../../compositor";

describe("S28-R12 Multi-Engine RenderGraph & Render Planner", () => {
  const testWorkspace = path.join(os.tmpdir(), `r12_test_workspace_${Date.now()}`);

  beforeAll(() => {
    fs.mkdirSync(testWorkspace, { recursive: true });

    // Ensure standard production adapters are registered in the canonical registry
    if (!CANONICAL_RENDERER_REGISTRY.has(CANVAS_RENDERER_ID)) {
      CANONICAL_RENDERER_REGISTRY.register(createCanvasRendererAdapter());
    }
    if (!CANONICAL_RENDERER_REGISTRY.has(REMOTION_RENDERER_ID)) {
      CANONICAL_RENDERER_REGISTRY.register(createRemotionRendererAdapter());
    }
  });

  afterAll(() => {
    if (fs.existsSync(testWorkspace)) {
      try {
        fs.rmSync(testWorkspace, { recursive: true, force: true });
      } catch {
        // ignore
      }
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Engine-Neutral Contracts & Validation (Section 1)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-01: Engine-neutral contracts validate RenderGraph and RenderPlan fail-closed", () => {
    const validGraph: RenderGraph = {
      id: "graph_test_1",
      documentRevision: "2.0.0",
      nodes: {
        node_1: {
          id: "node_1",
          scope: { type: "scene", id: "s1" },
          timeRange: { startFrame: 0, durationFrames: 30 },
          requiredCapabilities: ["text", "export_video"],
          dependencies: [],
          cacheability: {
            cacheable: true,
            contentFingerprint: "fp1",
            invalidationScope: "scene:s1",
          },
          preferredExecutionProfile: {
            costProfile: CANVAS_COST_PROFILE,
            memoryClass: "low",
          },
          outputArtifactType: "video",
          status: "pending",
        },
      },
      edges: [],
      executionGroups: [{ level: 0, nodeIds: ["node_1"], parallel: false }],
    };

    const validated = validateRenderGraph(validGraph);
    expect(validated.id).toBe("graph_test_1");

    // Invalid graph missing timeRange fails closed
    expect(() =>
      validateRenderGraph({
        ...validGraph,
        nodes: {
          node_1: {
            ...validGraph.nodes.node_1,
            timeRange: { startFrame: -5, durationFrames: 0 },
          },
        },
      })
    ).toThrow(RenderPlanningError);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Deterministic Scene Decomposition (Section 3 & 5)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-02: Deterministic Scene Decomposition produces identical plan and fingerprint", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "decomp_test_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_1",
          startFrame: 0,
          durationFrames: 30,
          surface: { text: "Scene 1" },
        },
        {
          scene_id: "scene_2",
          startFrame: 30,
          durationFrames: 60,
          surface: { text: "Scene 2" },
        },
      ],
    };

    const planner = new RenderPlanner();
    const res1 = planner.plan({ document: doc });
    const res2 = planner.plan({ document: doc });

    expect(res1.ok).toBe(true);
    expect(res2.ok).toBe(true);
    expect(res1.plan?.planFingerprint).toBe(res2.plan?.planFingerprint);
    expect(res1.plan?.estimatedTotalCost).toBe(res2.plan?.estimatedTotalCost);

    // 2 scenes -> 2 scene nodes + 1 master compositor node = 3 nodes
    const nodeKeys = Object.keys(res1.plan!.graph.nodes);
    expect(nodeKeys).toHaveLength(3);
    expect(nodeKeys).toContain("node_scene_scene_1");
    expect(nodeKeys).toContain("node_scene_scene_2");
    expect(nodeKeys).toContain("node_master_compositor");

    // Time ranges are contiguous and correct
    expect(res1.plan!.graph.nodes["node_scene_scene_1"].timeRange.startFrame).toBe(0);
    expect(res1.plan!.graph.nodes["node_scene_scene_1"].timeRange.durationFrames).toBe(30);
    expect(res1.plan!.graph.nodes["node_scene_scene_2"].timeRange.startFrame).toBe(30);
    expect(res1.plan!.graph.nodes["node_scene_scene_2"].timeRange.durationFrames).toBe(60);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Capability-Based Renderer Assignment (Section 4 & 12)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-03: Renderer assignment is 100% capability-based with ZERO hardcoding", () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "cap_assign_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_2d",
          durationFrames: 30,
          surface: { text: "2D Canvas Title" },
        },
        {
          scene_id: "scene_video",
          durationFrames: 30,
          layers: [
            {
              id: "v1",
              kind: "video",
              src: "test.mp4",
            },
          ],
        },
      ],
    };

    const planner = new RenderPlanner();
    const planRes = planner.plan({ document: doc });

    expect(planRes.ok).toBe(true);
    const plan = planRes.plan!;

    // 2D scene assigned to Canvas (lower cost)
    const node2d = plan.graph.nodes["node_scene_scene_2d"];
    expect(node2d.assignedRendererId).toBe(CANVAS_RENDERER_ID);

    // Video scene assigned to Remotion (only Remotion has "video" capability)
    const nodeVideo = plan.graph.nodes["node_scene_scene_video"];
    expect(nodeVideo.assignedRendererId).toBe(REMOTION_RENDERER_ID);
  });

  it("R12-03b: Unsupported 3D / map capabilities fail-closed with NO_COMPATIBLE_RENDERER", () => {
    const docWithMap: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "unsupported_cap_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_map",
          template: "rui-map-flight", // Requires "map", "webgl"
          durationFrames: 30,
        },
      ],
    };

    const planner = new RenderPlanner();
    const planRes = planner.plan({ document: docWithMap });

    expect(planRes.ok).toBe(false);
    expect(planRes.error?.code).toBe("NO_COMPATIBLE_RENDERER");
    expect(planRes.error?.message).toContain("No registered renderer satisfies all required capabilities");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Critical Test — Multi-Engine E2E (Section 16)
  // ──────────────────────────────────────────────────────────────────────────

  it(
    "R12-04: Critical Test — Multi-Engine E2E: Scene A (Canvas) + Scene B (Remotion) + Scene C (Canvas) -> MasterCompositor -> Final MP4",
    async () => {
      const finalOut = path.join(testWorkspace, "multi_engine_e2e_final.mp4");

      const doc: BlueprintV2 = {
        blueprint_version: "2.0.0",
        project_id: "multi_engine_critical",
        fps: 30,
        aspect_ratio: "16:9",
        scenes: [
          {
            scene_id: "scene_a",
            template: "rui-title-card",
            durationFrames: 30, // 1.0s
            surface: { text: "Scene A (Canvas 2D Native)" },
          },
          {
            scene_id: "scene_b",
            template: "rui-stat-card",
            durationFrames: 30, // 1.0s
            surface: { text: "Scene B (Remotion Production Engine)" },
          },
          {
            scene_id: "scene_c",
            template: "rui-title-card",
            durationFrames: 30, // 1.0s
            surface: { text: "Scene C (Canvas 2D Native)" },
          },
        ],
      };

      // 1. Plan document
      const planner = new RenderPlanner();
      const planRes = planner.plan({
        document: doc,
        outputPath: finalOut,
      });

      expect(planRes.ok).toBe(true);
      const plan = planRes.plan!;

      // 2. Verify engine assignments: A -> Canvas, B -> Remotion (if forced or video, or Remotion priority/fallback), C -> Canvas
      expect(plan.graph.nodes["node_scene_scene_a"].assignedRendererId).toBe(CANVAS_RENDERER_ID);
      expect(plan.graph.nodes["node_scene_scene_c"].assignedRendererId).toBe(CANVAS_RENDERER_ID);

      // Force Remotion on scene_b if not already selected to explicitly test multi-engine execution
      plan.graph.nodes["node_scene_scene_b"].assignedRendererId = REMOTION_RENDERER_ID;

      // 3. Execute plan end-to-end via RenderGraphExecutor
      const executor = new RenderGraphExecutor({ tempDir: testWorkspace });
      const execRes: ExecutionResult = await executor.execute(plan);

      expect(execRes.ok).toBe(true);
      expect(fs.existsSync(finalOut)).toBe(true);

      // 4. Probe final MP4
      const probe = probeMediaFile(finalOut);
      expect(probe.width).toBe(1920);
      expect(probe.height).toBe(1080);
      expect(Math.abs(probe.fps - 30)).toBeLessThan(0.1);
      // Total duration 3 scenes * 1.0s = 3.0s
      expect(Math.abs(probe.durationSec - 3.0)).toBeLessThan(0.15);

      // 5. Verify node execution metrics
      expect(execRes.metrics.executedNodes).toBe(4); // 3 scenes + 1 compositor
      expect(execRes.metrics.failedNodes).toBe(0);
      expect(execRes.metrics.parallelGroups).toBeGreaterThanOrEqual(1);
    },
    120000
  );

  // ──────────────────────────────────────────────────────────────────────────
  // 5. Dependency Graph & Kahn Cycle Rejection (Section 6 & 14)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-05: Dependency graph detects missing dependencies and rejects cycles fail-closed", () => {
    // Missing dependency
    const graphMissingDep: RenderGraph = {
      id: "graph_missing",
      documentRevision: "2.0.0",
      nodes: {
        node_a: {
          id: "node_a",
          scope: { type: "scene", id: "sa" },
          timeRange: { startFrame: 0, durationFrames: 30 },
          requiredCapabilities: ["text", "export_video"],
          dependencies: ["non_existent_node"],
          cacheability: { cacheable: true, contentFingerprint: "fpA", invalidationScope: "scene:sa" },
          preferredExecutionProfile: { costProfile: CANVAS_COST_PROFILE, memoryClass: "low" },
          outputArtifactType: "video",
          status: "pending",
        },
      },
      edges: [],
      executionGroups: [{ level: 0, nodeIds: ["node_a"], parallel: false }],
    };

    expect(() => validateRenderGraph(graphMissingDep)).toThrow(RenderPlanningError);
    try {
      validateRenderGraph(graphMissingDep);
    } catch (err: any) {
      expect(err.code).toBe("MISSING_DEPENDENCY");
    }

    // Cyclic graph: A -> B -> A
    const cyclicGraph: RenderGraph = {
      id: "graph_cyclic",
      documentRevision: "2.0.0",
      nodes: {
        node_a: {
          id: "node_a",
          scope: { type: "scene", id: "sa" },
          timeRange: { startFrame: 0, durationFrames: 30 },
          requiredCapabilities: ["text", "export_video"],
          dependencies: ["node_b"],
          cacheability: { cacheable: true, contentFingerprint: "fpA", invalidationScope: "scene:sa" },
          preferredExecutionProfile: { costProfile: CANVAS_COST_PROFILE, memoryClass: "low" },
          outputArtifactType: "video",
          status: "pending",
        },
        node_b: {
          id: "node_b",
          scope: { type: "scene", id: "sb" },
          timeRange: { startFrame: 0, durationFrames: 30 },
          requiredCapabilities: ["text", "export_video"],
          dependencies: ["node_a"],
          cacheability: { cacheable: true, contentFingerprint: "fpB", invalidationScope: "scene:sb" },
          preferredExecutionProfile: { costProfile: CANVAS_COST_PROFILE, memoryClass: "low" },
          outputArtifactType: "video",
          status: "pending",
        },
      },
      edges: [
        { fromNodeId: "node_b", toNodeId: "node_a", type: "dependency" },
        { fromNodeId: "node_a", toNodeId: "node_b", type: "dependency" },
      ],
      executionGroups: [],
    };

    expect(() => validateRenderGraph(cyclicGraph)).toThrow(RenderPlanningError);
    try {
      validateRenderGraph(cyclicGraph);
    } catch (err: any) {
      expect(err.code).toBe("RENDER_GRAPH_CYCLE");
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Parallel Execution Groups (Section 7)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-06: Parallel execution groups identify concurrent nodes and respect dependency order", () => {
    const depsMap = new Map<string, string[]>();
    depsMap.set("node_scene_a", []);
    depsMap.set("node_scene_b", []);
    depsMap.set("node_scene_c", []);
    depsMap.set("node_compositor", ["node_scene_a", "node_scene_b", "node_scene_c"]);

    const groups = buildExecutionGroups(
      ["node_scene_a", "node_scene_b", "node_scene_c", "node_compositor"],
      depsMap
    );

    expect(groups).toHaveLength(2);
    // Level 0: 3 parallel scenes
    expect(groups[0].level).toBe(0);
    expect(groups[0].parallel).toBe(true);
    expect(groups[0].nodeIds).toEqual(["node_scene_a", "node_scene_b", "node_scene_c"]);

    // Level 1: Compositor assembly depending on Level 0
    expect(groups[1].level).toBe(1);
    expect(groups[1].parallel).toBe(false);
    expect(groups[1].nodeIds).toEqual(["node_compositor"]);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 7. Cacheability & Selective Invalidation (Section 8 & 18)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-07: Selective Invalidation: changed Scene B invalidates only B and Compositor, keeping A & C cached", async () => {
    const docOriginal: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "cache_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        { scene_id: "sc_a", durationFrames: 30, surface: { text: "Scene A text" } },
        { scene_id: "sc_b", durationFrames: 30, surface: { text: "Scene B original text" } },
        { scene_id: "sc_c", durationFrames: 30, surface: { text: "Scene C text" } },
      ],
    };

    const planner = new RenderPlanner();
    const planOriginal = planner.plan({ document: docOriginal }).plan!;

    // Simulate pre-cached artifacts
    const artifactCache = new Map<string, any>();
    for (const [id, node] of Object.entries(planOriginal.graph.nodes)) {
      artifactCache.set(node.cacheability.contentFingerprint, {
        artifactId: `art_${id}`,
        sourceRendererId: node.assignedRendererId || "canvas",
        scope: node.scope,
        timeRange: node.timeRange,
        type: "video",
        mediaInfo: { durationSec: 1, fps: 30, width: 1920, height: 1080, pixelFormat: "yuv420p", timebase: "1/30" },
        contentFingerprint: node.cacheability.contentFingerprint,
      });
    }

    // 1. Initial run: 100% cache hit
    const eval1 = evaluatePlanCache(planOriginal, artifactCache);
    expect(eval1.get("node_scene_sc_a")?.cacheHit).toBe(true);
    expect(eval1.get("node_scene_sc_b")?.cacheHit).toBe(true);
    expect(eval1.get("node_scene_sc_c")?.cacheHit).toBe(true);
    expect(eval1.get("node_master_compositor")?.cacheHit).toBe(true);

    // 2. Modify Scene B only
    const docModified: BlueprintV2 = {
      ...docOriginal,
      scenes: [
        docOriginal.scenes[0],
        { ...docOriginal.scenes[1], surface: { text: "Scene B MODIFIED text" } },
        docOriginal.scenes[2],
      ],
    };

    const planModified = planner.plan({ document: docModified }).plan!;
    const eval2 = evaluatePlanCache(planModified, artifactCache);

    // Scene A & Scene C remain cache hits
    expect(eval2.get("node_scene_sc_a")?.cacheHit).toBe(true);
    expect(eval2.get("node_scene_sc_c")?.cacheHit).toBe(true);

    // Scene B is a cache miss (fingerprint changed)
    expect(eval2.get("node_scene_sc_b")?.cacheHit).toBe(false);
    expect(eval2.get("node_scene_sc_b")?.invalidationReason).toBe("fingerprint_miss");

    // Master Compositor is invalidated due to dependency invalidation
    expect(eval2.get("node_master_compositor")?.cacheHit).toBe(false);
    expect(eval2.get("node_master_compositor")?.invalidationReason).toBe("dependency_invalidated");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 8. Fallback Policy & Quality Requirements (Section 10 & 13)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-08: Fallback Policy falls back to compatible renderer or fails closed when disabled", () => {
    const reg = new RendererRegistry();
    const adapterA = createMockRendererAdapter({
      id: "renderer-alpha",
      priority: 10,
      capabilities: ["text", "export_video"],
    });
    const adapterB = createMockRendererAdapter({
      id: "renderer-beta",
      priority: 20,
      capabilities: ["text", "image", "export_video"],
    });
    reg.register(adapterA);
    reg.register(adapterB);

    // Preferred adapter doesn't have image capability, but fallback is enabled
    const resWithFallback = resolveCompatibleRenderer({
      nodeId: "node_test",
      requiredCapabilities: ["text", "image", "export_video"],
      policy: { preferredRendererId: "renderer-alpha", allowFallback: true },
      registry: reg,
    });

    expect(resWithFallback.ok).toBe(true);
    expect(resWithFallback.adapter?.id).toBe("renderer-beta");

    // Fallback disabled fails closed
    const resNoFallback = resolveCompatibleRenderer({
      nodeId: "node_test",
      requiredCapabilities: ["text", "image", "export_video"],
      policy: { preferredRendererId: "renderer-alpha", allowFallback: false },
      registry: reg,
    });

    expect(resNoFallback.ok).toBe(false);
    expect(resNoFallback.error?.code).toBe("QUALITY_REQUIREMENT_UNSATISFIED");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 9. Failure Isolation (Section 19)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-09: Failure in node B isolates failure: node A succeeds, node C (compositor) skipped without corrupt output", async () => {
    const customRegistry = new RendererRegistry();
    const goodAdapter = createCanvasRendererAdapter();
    const failingAdapter = createMockRendererAdapter({
      id: "failing-engine",
      capabilities: ["text", "shapes", "export_video"],
      onExportVideo: async () => {
        throw new Error("Simulated engine crash");
      },
    });
    customRegistry.register(goodAdapter);
    customRegistry.register(failingAdapter);

    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "failure_iso_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        { scene_id: "sc_good", durationFrames: 30, surface: { text: "Good scene" } },
        { scene_id: "sc_fail", durationFrames: 30, surface: { text: "Failing scene" } },
      ],
    };

    const planner = new RenderPlanner({ registry: customRegistry });
    const plan = planner.plan({ document: doc }).plan!;

    // Assign failing adapter explicitly to sc_fail and canvas to sc_good
    plan.graph.nodes["node_scene_sc_fail"].assignedRendererId = "failing-engine";
    plan.graph.nodes["node_scene_sc_good"].assignedRendererId = CANVAS_RENDERER_ID;

    const executor = new RenderGraphExecutor({ registry: customRegistry, tempDir: testWorkspace });
    const result = await executor.execute(plan);

    expect(result.ok).toBe(false);
    expect(result.nodeResults["node_scene_sc_good"].ok).toBe(true);
    expect(result.nodeResults["node_scene_sc_fail"].ok).toBe(false);
    expect(result.nodeResults["node_master_compositor"].ok).toBe(false);
    // Node C was skipped due to missing upstream dependency
    expect(result.nodeResults["node_master_compositor"].error?.message).toContain("upstream dependency");
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 10. Renderer Outage Simulation (Section 20)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-10: Renderer outage simulation: Canvas-only projects succeed, video-requiring projects fail explicitly", () => {
    // Registry with ONLY Canvas (Remotion simulated down / unregistered)
    const canvasOnlyRegistry = new RendererRegistry();
    canvasOnlyRegistry.register(createCanvasRendererAdapter());

    const planner = new RenderPlanner({ registry: canvasOnlyRegistry });

    // 1. Canvas-only 2D project
    const docCanvasOnly: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "canvas_only_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        { scene_id: "scene_1", durationFrames: 30, surface: { text: "Canvas Text" } },
      ],
    };
    const resCanvas = planner.plan({ document: docCanvasOnly });
    expect(resCanvas.ok).toBe(true);
    expect(resCanvas.plan?.graph.nodes["node_scene_scene_1"].assignedRendererId).toBe(CANVAS_RENDERER_ID);

    // 2. Video-requiring project
    const docNeedingVideo: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "video_req_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_video",
          durationFrames: 30,
          layers: [{ id: "l1", kind: "video", src: "clip.mp4" }],
        },
      ],
    };
    const resVideo = planner.plan({ document: docNeedingVideo });
    expect(resVideo.ok).toBe(false);
    expect(resVideo.error?.code).toBe("NO_COMPATIBLE_RENDERER");
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 11. Artifact Provenance (Section 23)
  // ──────────────────────────────────────────────────────────────────────────

  it(
    "R12-11: Artifact provenance is explicitly attached to intermediate and final artifacts",
    async () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "provenance_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        { scene_id: "scene_prov", durationFrames: 30, surface: { text: "Provenance check" } },
      ],
    };

    const planner = new RenderPlanner();
    const plan = planner.plan({ document: doc }).plan!;

    const executor = new RenderGraphExecutor({ tempDir: testWorkspace });
    const result = await executor.execute(plan);

    expect(result.ok).toBe(true);
    const finalArt = result.finalArtifact!;
    expect(finalArt).toBeDefined();

    const prov = (finalArt.metadata as any)?.provenance;
    expect(prov).toBeDefined();
    expect(prov.rendererId).toBe("master-compositor");
    expect(prov.canonicalRevision).toBe("2.0.0");
    expect(prov.dependencyLineage).toContain("node_scene_scene_prov");
  }, 30000);

  // ──────────────────────────────────────────────────────────────────────────
  // 12. Cancellation Propagation (Section 26)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-12: AbortSignal immediately halts RenderGraph execution cleanly", async () => {
    const doc: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "cancel_proj",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        { scene_id: "sc_1", durationFrames: 30, surface: { text: "Scene 1" } },
      ],
    };

    const planner = new RenderPlanner();
    const plan = planner.plan({ document: doc }).plan!;

    const controller = new AbortController();
    controller.abort(); // Abort upfront

    const executor = new RenderGraphExecutor({ tempDir: testWorkspace });
    const res = await executor.execute(plan, { signal: controller.signal });

    expect(res.ok).toBe(false);
    expect(res.error?.message).toMatch(/abort|cancel/i);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 13. Performance Baselines (Section 25)
  // ──────────────────────────────────────────────────────────────────────────

  it("R12-13: Performance baselines measured for 10 scenes, 100 nodes, validation and sort", () => {
    // 1. Planning 10 scenes
    const doc10: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "perf_10_scenes",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: Array.from({ length: 10 }, (_, i) => ({
        scene_id: `scene_${i}`,
        durationFrames: 30,
        surface: { text: `Scene ${i}` },
      })),
    };

    const planner = new RenderPlanner();
    const start10 = performance.now();
    const res10 = planner.plan({ document: doc10 });
    const duration10Ms = performance.now() - start10;

    expect(res10.ok).toBe(true);
    expect(duration10Ms).toBeLessThan(100); // Expect sub-100ms planning for 10 scenes

    // 2. Planning 100 nodes
    const doc100: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "perf_100_scenes",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: Array.from({ length: 99 }, (_, i) => ({
        scene_id: `scene_${i}`,
        durationFrames: 30,
        surface: { text: `Scene ${i}` },
      })),
    };

    const start100 = performance.now();
    const res100 = planner.plan({ document: doc100 });
    const duration100Ms = performance.now() - start100;

    expect(res100.ok).toBe(true);
    expect(duration100Ms).toBeLessThan(500); // Expect sub-500ms planning for 100 nodes
    expect(Object.keys(res100.plan!.graph.nodes)).toHaveLength(100); // 99 scenes + 1 compositor

    // 3. Graph validation & topological sort
    const startVal = performance.now();
    validateRenderGraph(res100.plan!.graph);
    const valMs = performance.now() - startVal;

    expect(valMs).toBeLessThan(20);
  });
});
