#!/usr/bin/env npx tsx
/**
 * scripts/render_via_adapter.ts
 * Production CLI bridge executing the canonical rendering sequence:
 * Canonical VideoDocument -> RenderRequest -> RendererRegistry -> RemotionRendererAdapter -> RenderResult
 * S28-R09: Renderer Independence Handover.
 */
import * as fs from "fs";
import * as path from "path";
import {
  CANONICAL_RENDERER_REGISTRY,
  type RenderRequest,
  type RenderContext,
} from "../contracts/renderer";
import { registerRemotionRenderer } from "../remotion/remotion-renderer-adapter";
import type { BlueprintV2 } from "../contracts/blueprint";
import { normalizeBlueprint } from "../contracts/normalization";

interface CliOptions {
  projectId: string;
  outputPath?: string;
  frame?: number;
  bundleLocation?: string;
}

function parseCliArgs(): CliOptions {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: npx tsx scripts/render_via_adapter.ts <project_id> [--out <path>] [--frame <num>] [--bundle <dir>]");
    process.exit(1);
  }

  const projectId = args[0];
  let outputPath: string | undefined;
  let frame: number | undefined;
  let bundleLocation: string | undefined;

  for (let i = 1; i < args.length; i++) {
    if (args[i] === "--out" && args[i + 1]) {
      outputPath = args[i + 1];
      i++;
    } else if (args[i] === "--frame" && args[i + 1]) {
      frame = parseInt(args[i + 1], 10);
      i++;
    } else if (args[i] === "--bundle" && args[i + 1]) {
      bundleLocation = args[i + 1];
      i++;
    }
  }

  return { projectId, outputPath, frame, bundleLocation };
}

async function run(): Promise<void> {
  const options = parseCliArgs();
  const rootDir = process.cwd();
  const projectDir = path.resolve(rootDir, "projects", options.projectId);

  if (!fs.existsSync(projectDir)) {
    console.error(`Project directory not found: ${projectDir}`);
    process.exit(1);
  }

  // Load blueprint
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
    console.error(`No 05_blueprint.json, render_props.json, or blueprint.json found in ${projectDir}`);
    process.exit(1);
  }

  // Ensure normalized blueprint
  const normalizedDoc = normalizeBlueprint(blueprint);

  // Load brand kit if present
  let brand: any;
  const manifestPath = path.join(projectDir, "manifest.json");
  if (fs.existsSync(manifestPath)) {
    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      brand = manifest.brand;
    } catch {}
  }

  // Register production Remotion renderer adapter
  const adapter = registerRemotionRenderer(CANONICAL_RENDERER_REGISTRY, {
    bundleLocation: options.bundleLocation,
  });

  const isFrame = options.frame !== undefined;
  const outPath =
    options.outputPath ||
    path.join(
      projectDir,
      isFrame ? `frame_${options.frame}.png` : "out.mp4"
    );

  const request: RenderRequest = {
    id: `render_${options.projectId}_${Date.now()}`,
    document: normalizedDoc,
    type: isFrame ? "frame" : "export",
    frame: options.frame,
    output: {
      path: outPath,
      format: isFrame ? "png" : "mp4",
      width: normalizedDoc.aspect_ratio === "9:16" ? 1080 : 1920,
      height: normalizedDoc.aspect_ratio === "9:16" ? 1920 : 1080,
      fps: normalizedDoc.fps || 30,
    },
    context: {
      projectId: options.projectId,
      metadata: { brand },
    },
  };

  // Select compatible renderer via single authority
  const selectedAdapter = CANONICAL_RENDERER_REGISTRY.selectRenderer(request);
  console.log(`[RendererRegistry] Selected adapter '${selectedAdapter.id}' (v${selectedAdapter.version}) for project '${options.projectId}'`);

  const context: RenderContext = {
    projectId: options.projectId,
    metadata: { brand },
    logger: {
      info: (msg) => console.log(`[INFO] ${msg}`),
      warn: (msg) => console.warn(`[WARN] ${msg}`),
      error: (msg) => console.error(`[ERROR] ${msg}`),
    },
  };

  if (isFrame) {
    const result = await selectedAdapter.renderFrame(request, context);
    console.log(JSON.stringify(result, null, 2));
  } else {
    const result = await selectedAdapter.exportVideo(request, context);
    console.log(JSON.stringify(result, null, 2));
  }
}

run().catch((err) => {
  console.error("Adapter Render Execution Failed:", err);
  process.exit(1);
});
