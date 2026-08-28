import { Config } from "@remotion/cli/config";
import fs from "fs";
import path from "path";

Config.setOverwriteOutput(true);
Config.setVideoImageFormat("jpeg");

// =========================================================================
// ## WARNING: DO NOT REMOVE THIS BLOCK ##
// Removing this check breaks all video quality guarantees. It enforces that
// the mechanical QC gates must be passed. MUST NOT BE REMOVED WITHOUT
// EXPLICIT USER CONSENT.
// =========================================================================
if (process.argv.includes("render") || process.argv.includes("studio")) {
  try {
    const unlockedPath = path.join(process.cwd(), "..", ".studio_unlocked");
    
    if (!fs.existsSync(unlockedPath)) {
      throw new Error(`Probe-QC failed or hasn't run. ${unlockedPath} not found.`);
    }
    
    // Explicitly reject if --props is passed (Level 3 protection at runtime)
    const hasPropsArg = process.argv.some(arg => arg.startsWith("--props"));
    if (hasPropsArg) {
      throw new Error("Bypassing lock via --props is strictly forbidden.");
    }
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
// MUST output them to `remotion-template/public/` so `staticFile()` works natively.
// General pipeline artifacts go to `${PLUGIN_DATA}`.
// =========================================================================
