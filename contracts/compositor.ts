/**
 * contracts/compositor.ts — Engine-Neutral Compositor Contracts & Output Normalization Model.
 * S28-R11: Authoritative abstraction decoupling final assembly from individual rendering engines.
 * 
 * Flow:
 * Intermediate Artifacts (Canvas / Remotion / External)
 *   ↓
 * Master Compositor
 *   ↓
 * Output Normalization
 *   ↓
 * Final Video Artifact
 *   ↓
 * Existing Final QC
 * 
 * Enforces:
 *   - Strict engine-neutrality: ZERO FFmpeg, React, Remotion, Canvas, DOM or WebGL imports
 *   - Canonical VideoDocument as the sole timing authority (no independent timeline clock)
 *   - Fail-closed deterministic composition and normalization (no silent fallbacks)
 *   - Explicit provenance metadata on intermediate artifacts (renderer, revision, fingerprint, scope)
 *   - Multi-renderer composition readiness (mixed canvas + remotion + external engines)
 */

import * as crypto from "crypto";
import { z } from "zod";
import type { BlueprintV2 } from "./blueprint";
import {
  calculateCanonicalDuration,
  frameToSeconds,
  secondsToFrame,
  type FrameNumber,
  type FrameDuration,
} from "./timeline";

// ────────────────────────────────────────────────────────────────────────────
// 1. Structured Fail-Closed Error Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const COMPOSITOR_ERROR_CODES = [
  "INCOMPATIBLE_INPUT",
  "INVALID_TIMEBASE",
  "MISSING_ARTIFACT",
  "UNSUPPORTED_FORMAT",
  "NORMALIZATION_FAILED",
  "COMPOSITION_FAILED",
  "AUDIO_SYNC_ERROR",
  "INVALID_COMPOSITOR_REQUEST",
  "CANCELLED",
] as const;

export type CompositorErrorCode = (typeof COMPOSITOR_ERROR_CODES)[number];

export const CompositorErrorCodeSchema = z.enum(COMPOSITOR_ERROR_CODES);

export class MasterCompositorError extends Error {
  readonly code: CompositorErrorCode;
  readonly details?: Record<string, unknown>;

  constructor(code: CompositorErrorCode, message: string, details?: Record<string, unknown>) {
    super(`[${code}] ${message}`);
    this.name = "MasterCompositorError";
    this.code = code;
    this.details = details;
    Object.setPrototypeOf(this, MasterCompositorError.prototype);
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Intermediate Artifact Model & Input Types
// ────────────────────────────────────────────────────────────────────────────

export const INTERMEDIATE_ARTIFACT_TYPES = [
  "video",
  "sequence",
  "image",
  "audio",
  "audio_stem",
  "overlay",
  "scene_render",
] as const;

export type IntermediateArtifactType = (typeof INTERMEDIATE_ARTIFACT_TYPES)[number];

export const IntermediateArtifactTypeSchema = z.enum(INTERMEDIATE_ARTIFACT_TYPES);

export const IntermediateArtifactScopeSchema = z.object({
  type: z.enum(["project", "scene", "layer", "stem"]),
  id: z.string().min(1),
});

export type IntermediateArtifactScope = z.infer<typeof IntermediateArtifactScopeSchema>;

export const IntermediateArtifactMediaInfoSchema = z.object({
  durationSec: z.number().nonnegative(),
  durationFrames: z.number().int().nonnegative().optional(),
  fps: z.number().positive(),
  width: z.number().int().nonnegative(),
  height: z.number().int().nonnegative(),
  pixelFormat: z.string().min(1),
  timebase: z.string().min(1),
  startTimeSec: z.number().nonnegative().default(0),
  startFrame: z.number().int().nonnegative().default(0),
  hasAlpha: z.boolean().default(false),
  videoCodec: z.string().optional(),
  audioCodec: z.string().optional(),
  audioSampleRate: z.number().int().positive().optional(),
  audioChannels: z.number().int().positive().optional(),
  audioChannelLayout: z.string().optional(),
  bitrate: z.number().positive().optional(),
});

export type IntermediateArtifactMediaInfo = z.infer<typeof IntermediateArtifactMediaInfoSchema>;

export const IntermediateArtifactSchema = z.object({
  artifactId: z.string().min(1),
  sourceRendererId: z.string().min(1),
  canonicalRevision: z.union([z.string(), z.number()]).optional(),
  scope: IntermediateArtifactScopeSchema,
  timeRange: z.object({
    startFrame: z.number().int().nonnegative(),
    durationFrames: z.number().int().positive(),
    startTimeSec: z.number().nonnegative().optional(),
    durationSec: z.number().positive().optional(),
  }),
  type: IntermediateArtifactTypeSchema,
  filePath: z.string().optional(),
  filePattern: z.string().optional(),
  directoryPath: z.string().optional(),
  mediaInfo: IntermediateArtifactMediaInfoSchema,
  contentFingerprint: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type IntermediateArtifact = z.infer<typeof IntermediateArtifactSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 3. Output Profile Contract & Normalization Model
// ────────────────────────────────────────────────────────────────────────────

export const OutputScalingPolicySchema = z.enum(["fit_pad", "crop_fill", "stretch"]);
export type OutputScalingPolicy = z.infer<typeof OutputScalingPolicySchema>;

export const OutputProfileSchema = z.object({
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  fps: z.number().int().positive(),
  aspectRatio: z.string().optional(),
  videoCodec: z.string().default("libx264"),
  pixelFormat: z.string().default("yuv420p"),
  container: z.string().default("mp4"),
  audioCodec: z.string().default("aac"),
  sampleRate: z.number().int().positive().default(48000),
  channels: z.number().int().positive().default(2),
  channelLayout: z.string().default("stereo"),
  videoBitrate: z.string().default("8M"),
  audioBitrate: z.string().default("192k"),
  scalingPolicy: OutputScalingPolicySchema.default("fit_pad"),
  backgroundColor: z.string().default("black"),
});

export type OutputProfile = z.infer<typeof OutputProfileSchema>;

export const NormalizedMediaInfoSchema = z.object({
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  fps: z.number().positive(),
  durationSec: z.number().nonnegative(),
  durationFrames: z.number().int().nonnegative(),
  videoCodec: z.string(),
  pixelFormat: z.string(),
  audioCodec: z.string().optional(),
  sampleRate: z.number().int().positive().optional(),
  channels: z.number().int().positive().optional(),
  fileSizeBytes: z.number().int().nonnegative(),
});

export type NormalizedMediaInfo = z.infer<typeof NormalizedMediaInfoSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 4. Compositor Inputs & Audio Stems
// ────────────────────────────────────────────────────────────────────────────

export const CompositorInputSchema = z.object({
  artifact: IntermediateArtifactSchema,
  canonicalSceneId: z.string().optional(),
  targetStartFrame: z.number().int().nonnegative().optional(),
  targetDurationFrames: z.number().int().positive().optional(),
  zIndex: z.number().int().default(0),
  opacity: z.number().min(0).max(1).default(1),
  blendMode: z.enum(["normal", "multiply", "screen", "overlay"]).default("normal"),
});

export type CompositorInput = z.infer<typeof CompositorInputSchema>;

export const AudioStemRoleSchema = z.enum(["voiceover", "music", "sfx", "scene_audio", "master"]);
export type AudioStemRole = z.infer<typeof AudioStemRoleSchema>;

export const AudioStemInputSchema = z.object({
  stemId: z.string().min(1),
  role: AudioStemRoleSchema,
  filePath: z.string().min(1),
  startFrame: z.number().int().nonnegative(),
  durationFrames: z.number().int().positive().optional(),
  volume: z.number().min(0).default(1.0),
  mute: z.boolean().default(false),
  loop: z.boolean().default(false),
  ducking: z
    .object({
      enabled: z.boolean().default(true),
      duckingVolume: z.number().min(0).max(1).default(0.1),
      duckUnderRoles: z.array(z.string()).default(["voiceover"]),
    })
    .optional(),
});

export type AudioStemInput = z.infer<typeof AudioStemInputSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 5. Compositor Request & Result Contracts
// ────────────────────────────────────────────────────────────────────────────

export interface CompositorContext {
  signal?: AbortSignal;
  onProgress?: (progress: number, stage: string) => void;
  tempDir?: string;
  logger?: {
    debug?: (msg: string) => void;
    info: (msg: string) => void;
    warn: (msg: string) => void;
    error: (msg: string) => void;
  };
}

export interface CompositorRequest {
  id: string;
  document: BlueprintV2;
  inputs: CompositorInput[];
  audioStems?: AudioStemInput[];
  outputProfile: OutputProfile;
  outputPath: string;
  context?: CompositorContext;
  metadata?: Record<string, unknown>;
}

export interface CompositorMetrics {
  totalDurationMs: number;
  normalizationTimeMs: number;
  assemblyTimeMs: number;
  audioProcessingTimeMs: number;
  finalPackagingTimeMs: number;
  inputCount: number;
  peakMemoryBytes?: number;
  temporaryDiskBytes?: number;
}

export interface CompositorResult {
  ok: boolean;
  requestId: string;
  outputPath?: string;
  outputProfile: OutputProfile;
  mediaInfo?: NormalizedMediaInfo;
  metrics: CompositorMetrics;
  error?: {
    code: CompositorErrorCode;
    message: string;
    details?: Record<string, unknown>;
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 6. Validation & Canonical Helpers
// ────────────────────────────────────────────────────────────────────────────

/**
 * Validates a CompositorRequest fail-closed.
 */
export function validateCompositorRequest(request: unknown): CompositorRequest {
  if (!request || typeof request !== "object") {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest must be a non-null object",
      { received: request }
    );
  }

  const req = request as Partial<CompositorRequest>;

  if (!req.id || typeof req.id !== "string") {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest missing required non-empty string 'id'",
      { request }
    );
  }

  if (!req.document || typeof req.document !== "object") {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest missing canonical VideoDocument 'document'",
      { request }
    );
  }

  if (!req.document.project_id || !req.document.fps || !Array.isArray(req.document.scenes)) {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest document does not conform to BlueprintV2 canonical structure",
      { request }
    );
  }

  if (!Array.isArray(req.inputs) || req.inputs.length === 0) {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest 'inputs' must be a non-empty array of CompositorInput",
      { request }
    );
  }

  if (!req.outputPath || typeof req.outputPath !== "string") {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      "CompositorRequest missing required string 'outputPath'",
      { request }
    );
  }

  // Validate inputs
  for (let i = 0; i < req.inputs.length; i++) {
    const input = req.inputs[i];
    const parsed = CompositorInputSchema.safeParse(input);
    if (!parsed.success) {
      throw new MasterCompositorError(
        "INCOMPATIBLE_INPUT",
        `Input at index ${i} failed schema validation: ${parsed.error.message}`,
        { inputIndex: i, errors: parsed.error.issues }
      );
    }
  }

  // Validate audio stems if present
  if (req.audioStems) {
    if (!Array.isArray(req.audioStems)) {
      throw new MasterCompositorError(
        "INCOMPATIBLE_INPUT",
        "CompositorRequest 'audioStems' must be an array if provided",
        { request }
      );
    }
    for (let i = 0; i < req.audioStems.length; i++) {
      const stem = req.audioStems[i];
      const parsed = AudioStemInputSchema.safeParse(stem);
      if (!parsed.success) {
        throw new MasterCompositorError(
          "INCOMPATIBLE_INPUT",
          `AudioStem at index ${i} failed schema validation: ${parsed.error.message}`,
          { stemIndex: i, errors: parsed.error.issues }
        );
      }
    }
  }

  // Validate outputProfile
  const profParsed = OutputProfileSchema.safeParse(req.outputProfile);
  if (!profParsed.success) {
    throw new MasterCompositorError(
      "INVALID_COMPOSITOR_REQUEST",
      `outputProfile failed schema validation: ${profParsed.error.message}`,
      { errors: profParsed.error.issues }
    );
  }

  return req as CompositorRequest;
}

/**
 * Creates a default standard OutputProfile.
 */
export function createDefaultOutputProfile(overrides?: Partial<OutputProfile>): OutputProfile {
  return {
    width: 1920,
    height: 1080,
    fps: 30,
    aspectRatio: "16:9",
    videoCodec: "libx264",
    pixelFormat: "yuv420p",
    container: "mp4",
    audioCodec: "aac",
    sampleRate: 48000,
    channels: 2,
    channelLayout: "stereo",
    videoBitrate: "8M",
    audioBitrate: "192k",
    scalingPolicy: "fit_pad",
    backgroundColor: "black",
    ...overrides,
  };
}

/**
 * Resolves an OutputProfile directly from a Canonical BlueprintV2 document.
 */
export function resolveProfileFromDocument(
  doc: BlueprintV2,
  overrides?: Partial<OutputProfile>
): OutputProfile {
  const fps = doc.fps || 30;
  const ratio = doc.aspect_ratio || "16:9";

  let width = 1920;
  let height = 1080;

  switch (ratio) {
    case "9:16":
      width = 1080;
      height = 1920;
      break;
    case "1:1":
      width = 1080;
      height = 1080;
      break;
    case "4:5":
      width = 1080;
      height = 1350;
      break;
    case "21:9":
      width = 2560;
      height = 1080;
      break;
    case "16:9":
    default:
      width = 1920;
      height = 1080;
      break;
  }

  return createDefaultOutputProfile({
    width,
    height,
    fps,
    aspectRatio: ratio,
    ...overrides,
  });
}

/**
 * Computes deterministic SHA-256 fingerprint for an intermediate artifact.
 */
export function computeArtifactFingerprint(input: {
  sourceRendererId: string;
  scope: IntermediateArtifactScope;
  timeRange: { startFrame: number; durationFrames: number };
  mediaInfo: IntermediateArtifactMediaInfo;
  canonicalRevision?: string | number;
}): string {
  const normalized = {
    renderer: input.sourceRendererId,
    scope: input.scope,
    timeRange: input.timeRange,
    mediaInfo: {
      w: input.mediaInfo.width,
      h: input.mediaInfo.height,
      fps: input.mediaInfo.fps,
      dur: input.mediaInfo.durationSec,
      fmt: input.mediaInfo.pixelFormat,
      tb: input.mediaInfo.timebase,
    },
    rev: input.canonicalRevision ?? 0,
  };

  return crypto
    .createHash("sha256")
    .update(JSON.stringify(normalized, Object.keys(normalized).sort()))
    .digest("hex");
}

/**
 * Factory to construct a complete IntermediateArtifact with validated metadata and fingerprint.
 */
export function createIntermediateArtifact(
  params: Omit<IntermediateArtifact, "contentFingerprint"> & { contentFingerprint?: string }
): IntermediateArtifact {
  const fingerprint =
    params.contentFingerprint ||
    computeArtifactFingerprint({
      sourceRendererId: params.sourceRendererId,
      scope: params.scope,
      timeRange: params.timeRange,
      mediaInfo: params.mediaInfo,
      canonicalRevision: params.canonicalRevision,
    });

  const artifact: IntermediateArtifact = {
    ...params,
    contentFingerprint: fingerprint,
  };

  const parsed = IntermediateArtifactSchema.safeParse(artifact);
  if (!parsed.success) {
    throw new MasterCompositorError(
      "INCOMPATIBLE_INPUT",
      `Failed to create IntermediateArtifact: ${parsed.error.message}`,
      { errors: parsed.error.issues }
    );
  }

  return parsed.data;
}
