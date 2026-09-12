import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import * as path from "path";

async function run() {
  const projectDir = process.argv[2];
  const outPath = process.argv[3];

  if (!projectDir || !outPath) {
    console.error("Usage: npx tsx scripts/dev_render_blueprint.ts <project_dir> <out.mp4>");
    process.exit(1);
  }

  const absProjectDir = path.resolve(projectDir);
  const absOutPath = path.resolve(outPath);

  console.log("Bundling project...");
  const bundleLocation = await bundle({
    entryPoint: path.resolve(__dirname, "../build/src/index.ts"),
    webpackOverride: (config: any) => config,
  });

  console.log("Loading project data in Node context...");
  const { loadProjectData } = require("../build/src/loadProjectData");
  const projectData = loadProjectData(absProjectDir);

  console.log("Selecting composition...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "BlueprintVideo",
    inputProps: { projectData },
  });

  console.log(`Starting render for composition ${composition.id}...`);
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: absOutPath,
    inputProps: { projectData },
    onProgress: ({ progress }) => {
      // Print every 25% (roughly)
      const p = Math.floor(progress * 100);
      if (p % 25 === 0 && p > 0) {
        console.log(`Render progress: ${p}%`);
      }
    },
  });

  console.log(`Render completed successfully: ${absOutPath}`);
}

run().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});
