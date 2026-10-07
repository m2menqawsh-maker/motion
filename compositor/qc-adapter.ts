/**
 * compositor/qc-adapter.ts — Adapter Bridging Compositor Results to Canonical QC Gate.
 * S28-R11: Seamlessly connects CompositorResult to existing Final QC validation boundary (scripts/gates/final_qc.py).
 */

import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import type { BlueprintV2 } from "../contracts/blueprint";
import {
  type CompositorResult,
  MasterCompositorError,
} from "../contracts/compositor";
import { calculateCanonicalDuration } from "../contracts/timeline";
import { probeMediaFile } from "./probe";

export interface CompositorQcCheck {
  name: string;
  status: "PASS" | "FAIL";
  message?: string;
  details?: Record<string, unknown>;
}

export interface CompositorQcReport {
  passed: boolean;
  checks: CompositorQcCheck[];
  canonicalDurationSec: number;
  actualDurationSec: number;
  durationDeltaMs: number;
  videoValid: boolean;
  audioValid: boolean;
  avSyncValid: boolean;
  pythonQcReport?: any;
}

/**
 * Runs Quality Control verification on a CompositorResult against canonical document invariants.
 */
export function runQcForCompositorResult(
  result: CompositorResult,
  document: BlueprintV2,
  options?: {
    toleranceMs?: number;
    workspaceRoot?: string;
    runPythonGate?: boolean;
    pythonPath?: string;
  }
): CompositorQcReport {
  const checks: CompositorQcCheck[] = [];
  const toleranceMs = options?.toleranceMs ?? 150; // max allowed drift

  if (!result.ok || !result.outputPath) {
    throw new MasterCompositorError(
      "NORMALIZATION_FAILED",
      "Cannot run QC on failed or missing CompositorResult",
      { result }
    );
  }

  if (!fs.existsSync(result.outputPath)) {
    throw new MasterCompositorError(
      "MISSING_ARTIFACT",
      `Compositor output file does not exist: '${result.outputPath}'`,
      { outputPath: result.outputPath }
    );
  }

  // 1. Inspect output media with ffprobe
  const probe = probeMediaFile(result.outputPath);
  const stat = fs.statSync(result.outputPath);

  // File integrity check
  const fileValid = stat.size > 1024;
  checks.push({
    name: "file_integrity",
    status: fileValid ? "PASS" : "FAIL",
    message: fileValid ? `File size ${stat.size} bytes` : `File too small: ${stat.size} bytes`,
    details: { sizeBytes: stat.size },
  });

  // 2. Canonical Duration Authority Check
  const canonicalFrames =
    (document as any).totalDurationFrames ?? calculateCanonicalDuration(document.scenes);
  const canonicalFps = document.fps || 30;
  const canonicalDurationSec = canonicalFrames / canonicalFps;
  const actualDurationSec = probe.durationSec;
  const durationDeltaMs = Math.abs(actualDurationSec - canonicalDurationSec) * 1000;

  const durationValid = durationDeltaMs <= toleranceMs;
  checks.push({
    name: "duration_parity",
    status: durationValid ? "PASS" : "FAIL",
    message: `Expected ${canonicalDurationSec.toFixed(3)}s, actual ${actualDurationSec.toFixed(3)}s (delta: ${durationDeltaMs.toFixed(1)}ms)`,
    details: { canonicalDurationSec, actualDurationSec, durationDeltaMs, toleranceMs },
  });

  // 3. Resolution & Aspect Ratio Check
  const targetW = result.outputProfile.width;
  const targetH = result.outputProfile.height;
  const resolutionValid = probe.width === targetW && probe.height === targetH;
  checks.push({
    name: "resolution_compliance",
    status: resolutionValid ? "PASS" : "FAIL",
    message: `Expected ${targetW}x${targetH}, actual ${probe.width}x${probe.height}`,
    details: { targetW, targetH, actualW: probe.width, actualH: probe.height },
  });

  // 4. Framerate Normalization Check
  const targetFps = result.outputProfile.fps;
  const fpsValid = Math.abs(probe.fps - targetFps) < 0.5;
  checks.push({
    name: "framerate_compliance",
    status: fpsValid ? "PASS" : "FAIL",
    message: `Expected ${targetFps}fps, actual ${probe.fps}fps`,
    details: { targetFps, actualFps: probe.fps },
  });

  // 5. Audio Subsystem Compliance Check
  const hasAudioTrack = Boolean(probe.audioCodec);
  const targetSampleRate = result.outputProfile.sampleRate;
  const sampleRateValid = !probe.audioSampleRate || probe.audioSampleRate === targetSampleRate;

  checks.push({
    name: "audio_normalization",
    status: hasAudioTrack && sampleRateValid ? "PASS" : "FAIL",
    message: hasAudioTrack
      ? `Audio codec ${probe.audioCodec}, sampleRate ${probe.audioSampleRate}Hz, channels ${probe.audioChannels}`
      : "Audio track missing or invalid",
    details: {
      codec: probe.audioCodec,
      sampleRate: probe.audioSampleRate,
      channels: probe.audioChannels,
    },
  });

  // 6. AV Sync Check
  const avSyncValid = Math.abs((probe.startTimeSec || 0)) < 0.05 && durationValid;
  checks.push({
    name: "av_sync",
    status: avSyncValid ? "PASS" : "FAIL",
    message: avSyncValid ? "Audio and video streams aligned" : "AV sync drift detected",
    details: { startTimeSec: probe.startTimeSec, durationDeltaMs },
  });

  // 7. Optional Python QC Gate (scripts/gates/final_qc.py)
  let pythonQcReport: any = undefined;
  if (options?.runPythonGate && options?.workspaceRoot) {
    const pythonExe = options.pythonPath || ".venv/bin/python";
    const scriptPath = path.resolve(options.workspaceRoot, "scripts/gates/final_qc.py");

    if (fs.existsSync(scriptPath) && fs.existsSync(pythonExe)) {
      try {
        const out = execFileSync(
          pythonExe,
          [scriptPath, document.project_id || "default", "--workspace-root", options.workspaceRoot],
          { encoding: "utf-8", stdio: "pipe" }
        );
        pythonQcReport = JSON.parse(out);
      } catch (err: any) {
        checks.push({
          name: "python_final_qc_gate",
          status: "FAIL",
          message: `Python QC script execution failed: ${err?.message || String(err)}`,
        });
      }
    }
  }

  const passed = checks.every((c) => c.status === "PASS");

  return {
    passed,
    checks,
    canonicalDurationSec,
    actualDurationSec,
    durationDeltaMs,
    videoValid: fileValid && resolutionValid && fpsValid,
    audioValid: hasAudioTrack && sampleRateValid,
    avSyncValid,
    pythonQcReport,
  };
}
