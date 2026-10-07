/**
 * compositor/timeline-assembler.ts — Canonical Timeline Scene & Transition Assembler.
 * S28-R11: Concatenates and stitches intermediate scene artifacts adhering strictly
 * to the Canonical VideoDocument timeline, transitions, and duration authority.
 */

import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import {
  calculateCanonicalDuration,
  frameToSeconds,
} from "../contracts/timeline";
import {
  type OutputProfile,
  MasterCompositorError,
} from "../contracts/compositor";
import { findSystemFfmpeg } from "./output-normalizer";

export interface TimelineAssemblerOptions {
  ffmpegPath?: string;
}

export interface AssembledSceneSegment {
  sceneId: string;
  segmentPath: string;
  durationSec: number;
  durationFrames: number;
  transition?: {
    type: string;
    durationSec: number;
    durationFrames: number;
  };
}

/**
 * Maps canonical transition types to FFmpeg xfade transition names.
 */
const XFADE_TRANSITION_MAP: Record<string, string> = {
  fade: "fade",
  dissolve: "dissolve",
  wipe: "wipeleft",
  slide: "slideleft",
  zoom: "circlecrop",
  crosswarp: "radial",
  "dreamy-zoom": "zoomin",
  "book-flip": "fadeblack",
  "linear-blur": "fade",
};

/**
 * Stitches normalized scene video segments together into a single continuous video stream.
 */
export function assembleSceneSegments(params: {
  document: BlueprintV2;
  segments: AssembledSceneSegment[];
  profile: OutputProfile;
  outputPath: string;
  signal?: AbortSignal;
  options?: TimelineAssemblerOptions;
}): void {
  if (params.signal?.aborted) {
    throw new MasterCompositorError("CANCELLED", "Timeline assembly aborted via signal");
  }

  const ffmpeg = params.options?.ffmpegPath || findSystemFfmpeg();
  const segments = params.segments;
  if (segments.length === 0) {
    throw new MasterCompositorError(
      "COMPOSITION_FAILED",
      "Cannot assemble video: zero scene segments provided"
    );
  }

  fs.mkdirSync(path.dirname(params.outputPath), { recursive: true });

  // Single segment case: direct remux / re-wrap
  if (segments.length === 1) {
    const seg = segments[0];
    const ffmpegArgs = [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      seg.segmentPath,
      "-c:v",
      "copy",
      "-an",
      params.outputPath,
    ];
    try {
      execFileSync(ffmpeg, ffmpegArgs, { stdio: "pipe" });
      return;
    } catch (err: any) {
      throw new MasterCompositorError(
        "COMPOSITION_FAILED",
        `Failed to package single segment: ${err?.message || String(err)}`,
        { error: String(err) }
      );
    }
  }

  // Check if any transitions exist between scenes
  const hasTransitions = segments.some(
    (s, idx) => idx < segments.length - 1 && s.transition && s.transition.durationSec > 0
  );

  if (!hasTransitions) {
    // Fast, deterministic concatenation via concat demuxer
    assembleViaConcatDemuxer({
      segments,
      outputPath: params.outputPath,
      ffmpeg,
      profile: params.profile,
      signal: params.signal,
    });
  } else {
    // Transition-aware concatenation via FFmpeg xfade filter
    assembleViaXfadeFilter({
      segments,
      outputPath: params.outputPath,
      ffmpeg,
      profile: params.profile,
      signal: params.signal,
    });
  }

  if (!fs.existsSync(params.outputPath)) {
    throw new MasterCompositorError(
      "COMPOSITION_FAILED",
      `Assembled video stream not found at '${params.outputPath}'`,
      { outputPath: params.outputPath }
    );
  }
}

/**
 * Concatenates segments via Concat Demuxer (instant, zero-loss).
 */
function assembleViaConcatDemuxer(params: {
  segments: AssembledSceneSegment[];
  outputPath: string;
  ffmpeg: string;
  profile: OutputProfile;
  signal?: AbortSignal;
}): void {
  const listFile = path.join(
    path.dirname(params.outputPath),
    `concat_list_${Date.now()}_${Math.random().toString(36).substring(2, 7)}.txt`
  );

  const fileLines = params.segments.map((s) => `file '${path.resolve(s.segmentPath)}'`);
  fs.writeFileSync(listFile, fileLines.join("\n"), "utf-8");

  const ffmpegArgs = [
    "-y",
    "-hide_banner",
    "-loglevel",
    "error",
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    listFile,
    "-c:v",
    params.profile.videoCodec,
    "-pix_fmt",
    params.profile.pixelFormat,
    "-r",
    String(params.profile.fps),
    "-an",
    params.outputPath,
  ];

  try {
    execFileSync(params.ffmpeg, ffmpegArgs, { stdio: "pipe" });
  } catch (err: any) {
    if (params.signal?.aborted) {
      throw new MasterCompositorError("CANCELLED", "Concat demuxer aborted via signal");
    }
    throw new MasterCompositorError(
      "COMPOSITION_FAILED",
      `Concat demuxer failed: ${err?.message || String(err)}`,
      { args: ffmpegArgs, error: String(err) }
    );
  } finally {
    if (fs.existsSync(listFile)) {
      try {
        fs.unlinkSync(listFile);
      } catch {
        // ignore
      }
    }
  }
}

/**
 * Concatenates segments with transitions using FFmpeg xfade filter.
 */
function assembleViaXfadeFilter(params: {
  segments: AssembledSceneSegment[];
  outputPath: string;
  ffmpeg: string;
  profile: OutputProfile;
  signal?: AbortSignal;
}): void {
  const ffmpegArgs: string[] = ["-y", "-hide_banner", "-loglevel", "error"];

  // Add inputs
  for (const s of params.segments) {
    ffmpegArgs.push("-i", s.segmentPath);
  }

  const filterNodes: string[] = [];
  let currentLabel = "[0:v]";
  let currentOffsetSec = 0;

  for (let i = 0; i < params.segments.length - 1; i++) {
    const s1 = params.segments[i];
    const s2 = params.segments[i + 1];
    const trans = s1.transition;
    const transSec = trans ? trans.durationSec : 0;
    const transType = trans ? XFADE_TRANSITION_MAP[trans.type] || "fade" : "fade";

    const nextInputLabel = `[${i + 1}:v]`;
    const outLabel = `[xfade_${i}]`;

    // Compute offset: previous duration minus transition duration
    currentOffsetSec += s1.durationSec - transSec;

    filterNodes.push(
      `${currentLabel}${nextInputLabel}xfade=transition=${transType}:duration=${transSec.toFixed(
        3
      )}:offset=${Math.max(0, currentOffsetSec).toFixed(3)}${outLabel}`
    );

    currentLabel = outLabel;
  }

  ffmpegArgs.push(
    "-filter_complex",
    filterNodes.join(";"),
    "-map",
    currentLabel,
    "-c:v",
    params.profile.videoCodec,
    "-pix_fmt",
    params.profile.pixelFormat,
    "-r",
    String(params.profile.fps),
    "-an",
    params.outputPath
  );

  try {
    execFileSync(params.ffmpeg, ffmpegArgs, { stdio: "pipe" });
  } catch (err: any) {
    if (params.signal?.aborted) {
      throw new MasterCompositorError("CANCELLED", "xfade assembly aborted via signal");
    }
    throw new MasterCompositorError(
      "COMPOSITION_FAILED",
      `xfade transition assembly failed: ${err?.message || String(err)}`,
      { args: ffmpegArgs, error: String(err) }
    );
  }
}
