#!/usr/bin/env npx tsx
/**
 * scripts/render_via_planner.ts
 * Production CLI bridge executing Multi-Engine RenderPlan via ProductionRenderGraphExecutor.
 * S28-R14: Production Integration of Multi-Engine Rendering & Master Compositor.
 * 
 * Execution Flow:
 * Canonical VideoDocument (Exact Source Revision)
 *   ↓
 * RenderPlanner (Capability Matching & DAG Decomposition)
 *   ↓
 * ProductionRenderGraphExecutor (Sandboxing, Timeout Policy, Failure Isolation)
 *   ↓
 * Multi-Engine Node Dispatch (Canvas, Remotion, External)
 *   ↓
 * MasterCompositor (Audio/Video/FPS Normalization)
 *   ↓
 * Output Validation & StorageService Upload
 */

import * as fs from "fs";
import * as path from "path";

import type { BlueprintV2 } from "../contracts/blueprint";
import { normalizeBlueprint } from "../contracts/normalization";
import {
  CANONICAL_RENDERER_REGISTRY,
  CANVAS_RENDERER_ID,
  REMOTION_RENDERER_ID,
} from "../contracts/renderer";
import { registerRemotionRenderer } from "../remotion/remotion-renderer-adapter";
import { registerCanvasRenderer } from "../canvas/canvas-renderer-adapter";
import { RenderPlanner } from "../planner/render-planner";
import { ProductionRenderGraphExecutor } from "../planner/production-render-graph-executor";
import { LocalStorageService } from "../contracts/storage-service";

interface CliArgs {
  projectId: string;
  outputPath?: string;
  runId?: string;
  workspaceId?: string;
  revision?: number;
  bundleLocation?: string;
}

function parseArgs(): CliArgs {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: npx tsx scripts/render_via_planner.ts <project_id> [--out <path>] [--run-id <id>] [--workspace <ws>] [--revision <rev>] [--bundle <dir>]");
    process.exit(1);
  }

  const projectId = args[0];
  let outputPath: string | undefined;
  let runId: string | undefined;
  let workspaceId: string | undefined;
  let revision: number | undefined;
  let bundleLocation: string | undefined;

  for (let i = 1; i < args.length; i++) {
    if (args[i] === "--out" && args[i + 1]) {
      outputPath = args[i + 1];
      i++;
    } else if (args[i] === "--run-id" && args[i + 1]) {
      runId = args[i + 1];
      i++;
    } else if (args[i] === "--workspace" && args[i + 1]) {
      workspaceId = args[i + 1];
      i++;
    } else if (args[i] === "--revision" && args[i + 1]) {
      revision = parseInt(args[i + 1], 10);
      i++;
    } else if (args[i] === "--bundle" && args[i + 1]) {
      bundleLocation = args[i + 1];
      i++;
    }
  }

  return { projectId, outputPath, runId, workspaceId, revision, bundleLocation };
}

async function main(): Promise<void> {
  const options = parseArgs();
  const rootDir = process.cwd();
  const projectDir = path.resolve(rootDir, "projects", options.projectId);

  if (!fs.existsSync(projectDir)) {
    console.error(JSON.stringify({ ok: false, error: `Project directory not found: ${projectDir}` }));
    process.exit(1);
  }

  // Load canonical blueprint
  let blueprint: BlueprintV2;
  const bpPath = path.join(projectDir, "05_blueprint.json");
  const fallbackBpPath = path.join(projectDir, "blueprint.json");
  const propsPath = path.join(projectDir, "render_props.json");

  if (fs.existsSync(bpPath)) {
    blueprint = JSON.parse(fs.readFileSync(bpPath, "utf-8"));
  } else if (fs.existsSync(propsPath)) {
    const rawProps = JSON.parse(fs.readFileSync(propsPath, "utf-8"));
    blueprint = rawProps.blueprint || rawProps.projectData?.blueprint || rawProps;
  } else if (fs.existsSync(fallbackBpPath)) {
    blueprint = JSON.parse(fs.readFileSync(fallbackBpPath, "utf-8"));
  } else {
    console.error(JSON.stringify({ ok: false, error: `No blueprint found in ${projectDir}` }));
    process.exit(1);
  }

  const normalizedDoc = normalizeBlueprint(blueprint);
  const docRevision = options.revision ?? normalizedDoc.revision ?? 1;

  // Register production renderers in registry
  if (!CANONICAL_RENDERER_REGISTRY.has(REMOTION_RENDERER_ID)) {
    registerRemotionRenderer(CANONICAL_RENDERER_REGISTRY, {
      bundleLocation: options.bundleLocation,
    });
  }
  if (!CANONICAL_RENDERER_REGISTRY.has(CANVAS_RENDERER_ID)) {
    registerCanvasRenderer(CANONICAL_RENDERER_REGISTRY);
  }

  // 1. Plan Multi-Engine RenderGraph
  const planner = new RenderPlanner({
    registry: CANONICAL_RENDERER_REGISTRY,
  });

  const finalOutPath = options.outputPath || path.join(projectDir, "out.mp4");
  const planResult = planner.plan({
    document: blueprint,
    outputPath: finalOutPath,
  });

  if (!planResult.ok || !planResult.plan) {
    console.error(JSON.stringify({
      ok: false,
      error: `RenderPlanning failed: ${planResult.error?.message}`,
    }));
    process.exit(1);
  }

  // 2. Execute RenderGraph via ProductionRenderGraphExecutor
  const storage = new LocalStorageService(path.join(rootDir, "data/storage"));
  const executor = new ProductionRenderGraphExecutor({
    registry: CANONICAL_RENDERER_REGISTRY,
    storageService: storage,
    baseTempDir: path.join(rootDir, "scratch"),
    eventPublisher: (eventType, payload) => {
      // Stream structured JSON event to stdout
      console.log(JSON.stringify({ _event: eventType, ...payload }));
    },
  });

  const execResult = await executor.execute(planResult.plan, {
    workspaceId: options.workspaceId || "ws_default",
    projectId: options.projectId,
    runId: options.runId,
    canonicalRevision: docRevision,
  });

  if (!execResult.ok) {
    console.error(JSON.stringify({
      ok: false,
      error: execResult.error?.message || "Render execution failed",
      code: (execResult.error as any)?.code || "RENDER_FAILED",
    }));
    process.exit(1);
  }

  // Copy final output to expected outputPath if needed
  if (!fs.existsSync(finalOutPath)) {
    if (execResult.outputPath && fs.existsSync(execResult.outputPath)) {
      fs.copyFileSync(execResult.outputPath, finalOutPath);
    } else if (execResult.outputStorageKey) {
      const stored = await storage.get(execResult.outputStorageKey);
      if (stored) {
        fs.mkdirSync(path.dirname(finalOutPath), { recursive: true });
        fs.writeFileSync(finalOutPath, stored);
      }
    }
  }

  console.log(JSON.stringify({
    ok: true,
    planId: planResult.plan.id,
    runId: options.runId,
    outputPath: finalOutPath,
    outputStorageKey: execResult.outputStorageKey,
    totalDurationMs: execResult.totalDurationMs,
  }));
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: err.message || String(err) }));
  process.exit(1);
});
