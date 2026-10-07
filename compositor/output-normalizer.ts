/**
 * compositor/output-normalizer.ts — Deterministic Video & Audio Normalization Engine.
 * S28-R11: Unifies resolution, fps, timebase, pixel format, codecs, and audio layout.
 */

import * as fs from "fs";
import * as path from "path";
import { execFileSync, spawn } from "child_process";
import {
  type IntermediateArtifact,
  type OutputProfile,
  type NormalizedMediaInfo,
  MasterCompositorError,
} from "../contracts/compositor";
import { probeMediaFile } from "./probe";

export interface NormalizerOptions {
  ffmpegPath?: string;
  ffprobePath?: string;
}

export function findSystemFfmpeg(): string {
  const candidates = ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"];
  for (const c of candidates) {
    try {
      execFileSync(c, ["-version"], { stdio: "ignore" });
      return c;
    } catch {
      // continue
    }
  }
  return "ffmpeg";
}

/**
 * Builds FFmpeg video filtergraph string to normalize dimensions and framerate deterministically.
 */
export function buildVideoFilterGraph(
  input: { width: number; height: number; fps: number; pixelFormat?: string },
  profile: OutputProfile
): string {
  const filters: string[] = [];

  // 1. Framerate normalization (deterministic nearest-neighbor frame matching)
  if (Math.abs(input.fps - profile.fps) > 0.01) {
    filters.push(`fps=fps=${profile.fps}:round=near`);
  }

  // 2. Scaling & Aspect Ratio Normalization
  const tw = profile.width;
  const th = profile.height;
  const policy = profile.scalingPolicy || "fit_pad";
  const bg = profile.backgroundColor || "black";

  if (input.width !== tw || input.height !== th) {
    if (policy === "fit_pad") {
      // Scale maintaining aspect ratio, pad to exact target box
      filters.push(
        `scale=w=${tw}:h=${th}:force_original_aspect_ratio=decrease`,
        `pad=${tw}:${th}:(ow-iw)/2:(oh-ih)/2:color=${bg}`
      );
    } else if (policy === "crop_fill") {
      // Scale to cover, crop excess centered
      filters.push(
        `scale=w=${tw}:h=${th}:force_original_aspect_ratio=increase`,
        `crop=${tw}:${th}`
      );
    } else if (policy === "stretch") {
      filters.push(`scale=w=${tw}:h=${th}`);
    }
  }

  // 3. Pixel format normalization
  filters.push(`format=${profile.pixelFormat}`);

  // 4. Timestamp normalization
  filters.push("setpts=PTS-STARTPTS");

  return filters.join(",");
}

/**
 * Normalizes a single intermediate artifact into a standard normalized segment MP4.
 */
export function normalizeArtifactToSegment(
  artifact: IntermediateArtifact,
  profile: OutputProfile,
  outputSegmentPath: string,
  options?: {
    signal?: AbortSignal;
    targetDurationSec?: number;
    options?: NormalizerOptions;
  }
): NormalizedMediaInfo {
  if (options?.signal?.aborted) {
    throw new MasterCompositorError("CANCELLED", "Normalization aborted via signal");
  }

  const ffmpeg = options?.options?.ffmpegPath || findSystemFfmpeg();
  const vf = buildVideoFilterGraph(
    {
      width: artifact.mediaInfo.width,
      height: artifact.mediaInfo.height,
      fps: artifact.mediaInfo.fps,
      pixelFormat: artifact.mediaInfo.pixelFormat,
    },
    profile
  );

  const durationSec =
    options?.targetDurationSec ??
    (artifact.timeRange.durationFrames / profile.fps);

  fs.mkdirSync(path.dirname(outputSegmentPath), { recursive: true });

  const ffmpegArgs: string[] = ["-y", "-hide_banner", "-loglevel", "error"];

  if (artifact.type === "image") {
    // Static image input looped for duration
    if (!artifact.filePath || !fs.existsSync(artifact.filePath)) {
      throw new MasterCompositorError(
        "MISSING_ARTIFACT",
        `Image artifact file not found: '${artifact.filePath}'`,
        { artifact }
      );
    }
    ffmpegArgs.push(
      "-loop", "1",
      "-framerate", String(profile.fps),
      "-t", String(durationSec),
      "-i", artifact.filePath,
      // Add silent audio stream for uniform concat
      "-f", "lavfi",
      "-t", String(durationSec),
      "-i", `anullsrc=r=${profile.sampleRate}:cl=${profile.channelLayout}`
    );
  } else if (artifact.type === "sequence") {
    // Frame sequence input
    const pattern =
      artifact.filePattern ||
      (artifact.directoryPath ? path.join(artifact.directoryPath, "frame_%06d.png") : undefined);

    if (!pattern) {
      throw new MasterCompositorError(
        "INCOMPATIBLE_INPUT",
        "Sequence artifact missing filePattern or directoryPath",
        { artifact }
      );
    }

    ffmpegArgs.push(
      "-framerate", String(artifact.mediaInfo.fps || profile.fps),
      "-i", pattern,
      "-t", String(durationSec),
      "-f", "lavfi",
      "-t", String(durationSec),
      "-i", `anullsrc=r=${profile.sampleRate}:cl=${profile.channelLayout}`
    );
  } else if (artifact.type === "video" || artifact.type === "scene_render") {
    // Video input
    if (!artifact.filePath || !fs.existsSync(artifact.filePath)) {
      throw new MasterCompositorError(
        "MISSING_ARTIFACT",
        `Video artifact file not found: '${artifact.filePath}'`,
        { artifact }
      );
    }

    ffmpegArgs.push("-i", artifact.filePath, "-t", String(durationSec));

    // Check if input has audio stream
    if (!artifact.mediaInfo.audioCodec) {
      ffmpegArgs.push(
        "-f", "lavfi",
        "-t", String(durationSec),
        "-i", `anullsrc=r=${profile.sampleRate}:cl=${profile.channelLayout}`
      );
    }
  } else {
    throw new MasterCompositorError(
      "UNSUPPORTED_FORMAT",
      `Cannot normalize visual artifact of type '${artifact.type}'`,
      { artifact }
    );
  }

  // Filter graphs
  ffmpegArgs.push("-vf", vf);

  // Audio filtering if present or synthesized
  ffmpegArgs.push(
    "-af",
    `aresample=${profile.sampleRate}:async=1,pan=${profile.channelLayout}|c0=c0|c1=c1,asetpts=PTS-STARTPTS`
  );

  // Codecs and encoding
  ffmpegArgs.push(
    "-c:v", profile.videoCodec,
    "-pix_fmt", profile.pixelFormat,
    "-r", String(profile.fps),
    "-c:a", profile.audioCodec,
    "-b:a", profile.audioBitrate,
    "-ar", String(profile.sampleRate),
    "-movflags", "+faststart",
    outputSegmentPath
  );

  try {
    execFileSync(ffmpeg, ffmpegArgs, { stdio: "pipe" });
  } catch (err: any) {
    if (options?.signal?.aborted) {
      throw new MasterCompositorError("CANCELLED", "Normalization aborted via signal");
    }
    throw new MasterCompositorError(
      "NORMALIZATION_FAILED",
      `FFmpeg normalization failed for artifact '${artifact.artifactId}': ${err?.message || String(err)}`,
      { artifact, args: ffmpegArgs, error: String(err) }
    );
  }

  if (!fs.existsSync(outputSegmentPath)) {
    throw new MasterCompositorError(
      "NORMALIZATION_FAILED",
      `Normalized segment was not produced at '${outputSegmentPath}'`,
      { outputSegmentPath }
    );
  }

  // Probe output to ensure exact normalized properties
  const probed = probeMediaFile(outputSegmentPath, { ffprobePath: options?.options?.ffprobePath });
  const stat = fs.statSync(outputSegmentPath);

  return {
    width: probed.width,
    height: probed.height,
    fps: probed.fps,
    durationSec: probed.durationSec,
    durationFrames: probed.durationFrames || Math.round(probed.durationSec * profile.fps),
    videoCodec: probed.videoCodec || profile.videoCodec,
    pixelFormat: probed.pixelFormat,
    audioCodec: probed.audioCodec,
    sampleRate: probed.audioSampleRate,
    channels: probed.audioChannels,
    fileSizeBytes: stat.size,
  };
}
