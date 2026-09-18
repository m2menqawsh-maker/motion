import { Config } from "@remotion/cli/config";
import fs from "fs";
import path from "path";

Config.setOverwriteOutput(true);
Config.setVideoImageFormat("jpeg");

const appDir = process.cwd().endsWith("remotion-app") ? process.cwd() : path.join(process.cwd(), "remotion-app");

Config.overrideWebpackConfig((currentConfiguration) => {
  return {
    ...currentConfiguration,
    resolve: {
      ...currentConfiguration.resolve,
      modules: [
        path.resolve(appDir, "node_modules"),
        path.resolve(appDir, "..", "node_modules"),
        ...(currentConfiguration.resolve?.modules || ["node_modules"]),
      ],
      alias: {
        ...(currentConfiguration.resolve?.alias ?? {}),
        "@": path.resolve(appDir, "src"),
        "@registry": path.resolve(appDir, "..", "registry"),
        "@contracts": path.resolve(appDir, "..", "contracts"),
        "react": path.resolve(appDir, "node_modules", "react"),
        "react-dom": path.resolve(appDir, "node_modules", "react-dom"),
      },
    },
  };
});

// =========================================================================
// ## WARNING: DO NOT REMOVE THIS BLOCK ##
// Removing this check breaks all video quality guarantees. It enforces that
// the mechanical QC gates must be passed. MUST NOT BE REMOVED WITHOUT
// EXPLICIT USER CONSENT.
// =========================================================================
if (process.argv.includes("render") || process.argv.includes("studio")) {
  try {
    const rootUnlocked = path.join(appDir, "..", ".studio_unlocked");
    let unlocked = fs.existsSync(rootUnlocked);

    if (!unlocked) {
      // Check via PROJECT_ID env
      const projId = process.env.PROJECT_ID;
      if (projId && fs.existsSync(path.join(appDir, "..", "projects", projId, ".studio_unlocked"))) {
        unlocked = true;
      }
      
      // Check via --props path
      const propsIdx = process.argv.indexOf("--props");
      if (!unlocked && propsIdx !== -1 && process.argv[propsIdx + 1]) {
        const propsArg = process.argv[propsIdx + 1];
        const projDir = path.dirname(path.resolve(propsArg));
        if (fs.existsSync(path.join(projDir, ".studio_unlocked"))) {
          unlocked = true;
        }
      }
    }

    if (!unlocked) {
      throw new Error(`Probe-QC failed or hasn't run. Valid .studio_unlocked not found.`);
    }
    
    // Explicitly reject if --props is passed (Level 3 protection at runtime)
    // NOTE: Removed in Master Engine Architecture. --props is now mandatory.
  } catch (err) {
    console.error("\n=======================================================");
    console.error("❌ HARD STOP: Studio/Render access denied.");
    console.error("Reason: " + (err instanceof Error ? err.message : String(err)));
    console.error("You MUST complete Probe-QC (Stage 3) and generate .studio_unlocked");
    console.error("=======================================================\n");
    process.exit(1);
  }
}

// =========================================================================
// ASSET PIPELINE RULE
// Python tools generating assets for Remotion (audio, images, captions JSON)
// MUST output them to `remotion-app/public/` so `staticFile()` works natively.
// General pipeline artifacts go to `${PLUGIN_DATA}`.
// =========================================================================
