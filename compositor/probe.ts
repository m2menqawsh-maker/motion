/**
 * compositor/probe.ts — Media Inspection & Artifact Provenance Constructor.
 * Uses ffprobe to probe intermediate video, audio, image, and sequence artifacts,
 * establishing explicit provenance and technical metadata.
 */

import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import {
  type IntermediateArtifact,
  type IntermediateArtifactMediaInfo,
  type IntermediateArtifactScope,
  type IntermediateArtifactType,
  MasterCompositorError,
  createIntermediateArtifact,
} from "../contracts/compositor";
import type { RenderResult } from "../contracts/renderer";

export interface ProbeOptions {
  ffprobePath?: string;
  defaultFps?: number;
}

export function findSystemFfprobe(): string {
  const candidates = ["ffprobe", "/usr/bin/ffprobe", "/usr/local/bin/ffprobe"];
  for (const c of candidates) {
    try {
      execFileSync(c, ["-version"], { stdio: "ignore" });
      return c;
    } catch {
      // continue
    }
  }
  return "ffprobe";
}

/**
 * Parses fractional rate string like "30/1", "24000/1001" or decimal "30".
 */
export function parseFps(rateStr?: string, fallback = 30): number {
  if (!rateStr || rateStr === "0/0" || rateStr === "N/A") return fallback;
  if (rateStr.includes("/")) {
    const parts = rateStr.split("/");
    const num = parseFloat(parts[0]);
    const den = parseFloat(parts[1]);
    if (!isNaN(num) && !isNaN(den) && den > 0) {
      return Math.round((num / den) * 1000) / 1000;
    }
  }
  const parsed = parseFloat(rateStr);
  return !isNaN(parsed) && parsed > 0 ? parsed : fallback;
}

/**
 * Inspects any media file using ffprobe and extracts IntermediateArtifactMediaInfo.
 */
export function probeMediaFile(
  filePath: string,
  options?: ProbeOptions
): IntermediateArtifactMediaInfo {
  if (!fs.existsSync(filePath)) {
    throw new MasterCompositorError(
      "MISSING_ARTIFACT",
      `Cannot probe media file: path does not exist '${filePath}'`,
      { filePath }
    );
  }

  const ffprobe = options?.ffprobePath || findSystemFfprobe();

  let rawJson: string;
  try {
    rawJson = execFileSync(
      ffprobe,
      ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filePath],
      { encoding: "utf-8", maxBuffer: 10 * 1024 * 1024 }
    );
  } catch (err: any) {
    throw new MasterCompositorError(
      "UNSUPPORTED_FORMAT",
      `ffprobe failed to inspect media '${filePath}': ${err?.message || String(err)}`,
      { filePath, error: String(err) }
    );
  }

  let data: any;
  try {
    data = JSON.parse(rawJson);
  } catch (err: any) {
    throw new MasterCompositorError(
      "UNSUPPORTED_FORMAT",
      `Failed to parse ffprobe json output for '${filePath}'`,
      { filePath, raw: rawJson }
    );
  }

  const streams: any[] = data.streams ?? [];
  const format: any = data.format ?? {};

  const vStream = streams.find((s) => s.codec_type === "video");
  const aStream = streams.find((s) => s.codec_type === "audio");

  const durationSec = parseFloat(format.duration || vStream?.duration || aStream?.duration || "0");
  const fps = vStream ? parseFps(vStream.r_frame_rate || vStream.avg_frame_rate, options?.defaultFps ?? 30) : (options?.defaultFps ?? 30);
  const width = vStream ? parseInt(vStream.width, 10) : 0;
  const height = vStream ? parseInt(vStream.height, 10) : 0;
  const pixelFormat = vStream?.pix_fmt || "unknown";

  const alphaPixFmts = new Set(["yuva420p", "yuva422p", "yuva444p", "rgba", "bgra", "argb", "abgr", "gbrpa"]);
  const hasAlpha = alphaPixFmts.has(pixelFormat) || Boolean(vStream?.has_b_frames && pixelFormat.includes("a"));

  const timebase = vStream?.time_base || `1/${Math.round(fps)}`;
  const durationFrames = Math.max(1, Math.round(durationSec * fps));

  const audioSampleRate = aStream ? parseInt(aStream.sample_rate, 10) : undefined;
  const audioChannels = aStream ? parseInt(aStream.channels, 10) : undefined;
  const audioChannelLayout = aStream?.channel_layout;
  const audioCodec = aStream?.codec_name;
  const videoCodec = vStream?.codec_name;
  const bitrate = format.bit_rate ? parseInt(format.bit_rate, 10) : undefined;

  return {
    durationSec,
    durationFrames,
    fps,
    width,
    height,
    pixelFormat,
    timebase,
    startTimeSec: 0,
    startFrame: 0,
    hasAlpha,
    videoCodec,
    audioCodec,
    audioSampleRate,
    audioChannels,
    audioChannelLayout,
    bitrate,
  };
}

/**
 * Constructs an IntermediateArtifact from a concrete disk file using ffprobe inspection.
 */
export function createArtifactFromFile(params: {
  artifactId: string;
  sourceRendererId: string;
  scope: IntermediateArtifactScope;
  timeRange: { startFrame: number; durationFrames: number; startTimeSec?: number; durationSec?: number };
  type: IntermediateArtifactType;
  filePath: string;
  canonicalRevision?: string | number;
  metadata?: Record<string, unknown>;
  options?: ProbeOptions;
}): IntermediateArtifact {
  const mediaInfo = probeMediaFile(params.filePath, params.options);

  return createIntermediateArtifact({
    artifactId: params.artifactId,
    sourceRendererId: params.sourceRendererId,
    canonicalRevision: params.canonicalRevision,
    scope: params.scope,
    timeRange: params.timeRange,
    type: params.type,
    filePath: params.filePath,
    mediaInfo,
    metadata: params.metadata,
  });
}

/**
 * Constructs an IntermediateArtifact directly from a RenderResult produced by Remotion or Canvas.
 */
export function createArtifactFromRenderResult(params: {
  artifactId: string;
  renderResult: RenderResult;
  scope: IntermediateArtifactScope;
  timeRange: { startFrame: number; durationFrames: number };
  canonicalRevision?: string | number;
  type?: IntermediateArtifactType;
  options?: ProbeOptions;
}): IntermediateArtifact {
  const res = params.renderResult;
  if (!res.ok) {
    throw new MasterCompositorError(
      "INCOMPATIBLE_INPUT",
      `Cannot construct IntermediateArtifact from failed RenderResult: ${res.error?.message}`,
      { renderResult: res }
    );
  }

  const filePath = res.output?.filePath;
  if (!filePath || !fs.existsSync(filePath)) {
    throw new MasterCompositorError(
      "MISSING_ARTIFACT",
      `RenderResult output filePath does not exist: '${filePath}'`,
      { renderResult: res }
    );
  }

  const detectedType: IntermediateArtifactType =
    params.type || (res.type === "export" ? "video" : res.type === "sequence" ? "sequence" : "image");

  return createArtifactFromFile({
    artifactId: params.artifactId,
    sourceRendererId: res.rendererId,
    scope: params.scope,
    timeRange: params.timeRange,
    type: detectedType,
    filePath,
    canonicalRevision: params.canonicalRevision,
    options: params.options,
  });
}
