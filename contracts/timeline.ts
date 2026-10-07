/**
 * contracts/timeline.ts — Pure Canonical Timeline, Timebase, Tracks & Clips Model.
 * S28-R03: Formal temporal specification and deterministic time conversion mathematics.
 * ZERO React or Remotion dependencies.
 */
import { z } from "zod";

export const SUPPORTED_TRANSITION_TYPES = [
  "fade",
  "slide",
  "wipe",
  "flip",
  "zoom",
  "cross-zoom",
  "film-burn",
  "dissolve",
  "iris",
  "none",
] as const;

export const TransitionTypeSchema = z.enum(SUPPORTED_TRANSITION_TYPES);
export type TransitionType = z.infer<typeof TransitionTypeSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 1. Stable Identity Invariants
// ────────────────────────────────────────────────────────────────────────────

export const STABLE_ID_REGEX = /^[a-zA-Z0-9_\-]+$/;

export const StableIdSchema = z
  .string()
  .min(1)
  .regex(STABLE_ID_REGEX, "Must be alphanumeric characters, underscores, or hyphens");

export function isStableId(id: unknown): boolean {
  return typeof id === "string" && STABLE_ID_REGEX.test(id);
}

export function assertStableId(id: string, scope = "entity"): void {
  if (!isStableId(id)) {
    throw new Error(`Invalid stable ID for ${scope}: '${id}'. Must match ${STABLE_ID_REGEX}`);
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Pure Time Primitives & Range Invariants
// ────────────────────────────────────────────────────────────────────────────

export const FrameNumberSchema = z.number().int().min(0, "Frame must be non-negative integer");
export type FrameNumber = z.infer<typeof FrameNumberSchema>;

export const FrameDurationSchema = z.number().int().min(1, "Duration must be positive integer >= 1");
export type FrameDuration = z.infer<typeof FrameDurationSchema>;

export const MillisecondsSchema = z.number().min(0, "Milliseconds must be non-negative");
export type Milliseconds = z.infer<typeof MillisecondsSchema>;

export const RoundingPolicySchema = z.enum(["ROUND", "FLOOR", "CEIL", "EXACT_WHERE_POSSIBLE"]);
export type RoundingPolicy = z.infer<typeof RoundingPolicySchema>;

export const TimeRangeSchema = z
  .object({
    startFrame: FrameNumberSchema,
    durationFrames: FrameDurationSchema,
    endFrame: z.number().int().min(1),
  })
  .refine((data) => data.endFrame === data.startFrame + data.durationFrames, {
    message: "Invariant violated: endFrame must equal startFrame + durationFrames",
  });
export type TimeRange = z.infer<typeof TimeRangeSchema>;

export function createTimeRange(startFrame: number, durationFrames: number): TimeRange {
  if (!Number.isInteger(startFrame) || startFrame < 0) {
    throw new Error(`Invalid startFrame ${startFrame}: must be integer >= 0`);
  }
  if (!Number.isInteger(durationFrames) || durationFrames <= 0) {
    throw new Error(`Invalid durationFrames ${durationFrames}: must be integer >= 1`);
  }
  return {
    startFrame,
    durationFrames,
    endFrame: startFrame + durationFrames,
  };
}

export function validateTimeRange(range: unknown): { ok: boolean; errors: string[] } {
  const result = TimeRangeSchema.safeParse(range);
  if (!result.success) {
    return {
      ok: false,
      errors: result.error.issues.map((i) => `[${i.path.join(".")}] ${i.message}`),
    };
  }
  return { ok: true, errors: [] };
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Time Conversion Mathematics & Policies
// ────────────────────────────────────────────────────────────────────────────

function applyRounding(val: number, policy: RoundingPolicy): number {
  switch (policy) {
    case "FLOOR":
      return Math.floor(val);
    case "CEIL":
      return Math.ceil(val);
    case "EXACT_WHERE_POSSIBLE":
      return val;
    case "ROUND":
    default:
      return Math.round(val);
  }
}

export function frameToMs(frame: number, fps: number, policy: RoundingPolicy = "ROUND"): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  const raw = (frame * 1000) / fps;
  return applyRounding(raw, policy);
}

export function msToFrame(ms: number, fps: number, policy: RoundingPolicy = "ROUND"): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  const raw = (ms * fps) / 1000;
  return applyRounding(raw, policy);
}

export function frameToSeconds(frame: number, fps: number): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  return frame / fps;
}

export function secondsToFrame(seconds: number, fps: number, policy: RoundingPolicy = "ROUND"): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);
  const raw = seconds * fps;
  return applyRounding(raw, policy);
}

export function localFrameToGlobal(localFrame: number, parentStartFrame: number): number {
  return parentStartFrame + localFrame;
}

export function globalFrameToLocal(globalFrame: number, parentStartFrame: number): number {
  return globalFrame - parentStartFrame;
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Track, Clip & Transition Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const TrackKindSchema = z.enum(["video", "audio", "text", "overlay", "caption", "effect"]).or(z.string());
export type TrackKind = z.infer<typeof TrackKindSchema>;

export const CanonicalClipSchema = z.object({
  clip_id: StableIdSchema,
  track_id: StableIdSchema,
  time_range: TimeRangeSchema,
  source_ref: z.string().optional(),
  scene_id: z.string().optional(),
  layer_ids: z.array(z.string()).default([]),
});
export type CanonicalClip = z.infer<typeof CanonicalClipSchema>;

export const CanonicalTrackSchema = z.object({
  track_id: StableIdSchema,
  kind: TrackKindSchema,
  name: z.string().optional(),
  order: z.number().int(),
  muted: z.boolean().default(false),
  visible: z.boolean().default(true),
  clips: z.array(CanonicalClipSchema).default([]),
});
export type CanonicalTrack = z.infer<typeof CanonicalTrackSchema>;

export const TransitionOverlapSemanticsSchema = z.enum(["overlap", "insert"]);
export type TransitionOverlapSemantics = z.infer<typeof TransitionOverlapSemanticsSchema>;

export const CanonicalTransitionSpecSchema = z.object({
  transition_id: StableIdSchema,
  type: z.enum(SUPPORTED_TRANSITION_TYPES),
  durationFrames: FrameDurationSchema,
  overlap_semantics: TransitionOverlapSemanticsSchema.default("overlap"),
  from_scene_id: z.string().optional(),
  to_scene_id: z.string().optional(),
});
export type CanonicalTransitionSpec = z.infer<typeof CanonicalTransitionSpecSchema>;

export const CanonicalTimelineSchema = z.object({
  timeline_id: StableIdSchema,
  fps: z.number().int().min(1).max(120),
  totalDurationFrames: FrameDurationSchema,
  tracks: z.array(CanonicalTrackSchema),
  transitions: z.array(CanonicalTransitionSpecSchema).default([]),
});
export type CanonicalTimeline = z.infer<typeof CanonicalTimelineSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 5. Canonical Duration Authority Function
// ────────────────────────────────────────────────────────────────────────────

export interface SceneDurationItem {
  startFrame?: number;
  durationFrames: number;
  transition?: {
    durationFrames: number;
    overlap_semantics?: "overlap" | "insert";
  };
}

export function calculateCanonicalDuration(
  scenes: SceneDurationItem[] | { scenes?: SceneDurationItem[] },
  options?: {
    transitionMode?: "overlap" | "insert";
    explicitTransitions?: Array<{ durationFrames?: number; overlap_semantics?: "overlap" | "insert" }>;
  }
): number {
  const sceneList = Array.isArray(scenes) ? scenes : (scenes?.scenes ?? []);
  if (!sceneList || sceneList.length === 0) return 0;

  const mode = options?.transitionMode;

  // If explicit transitions or transitions inside scenes are provided with overlap mode
  let totalOverlapFrames = 0;
  let totalInsertFrames = 0;

  for (let i = 0; i < sceneList.length; i++) {
    const s = sceneList[i];
    const trans = s.transition;
    if (trans && trans.durationFrames > 0 && i < sceneList.length - 1) {
      const semantics = trans.overlap_semantics ?? mode ?? "overlap";
      if (semantics === "overlap") {
        totalOverlapFrames += trans.durationFrames;
      } else if (semantics === "insert") {
        totalInsertFrames += trans.durationFrames;
      }
    }
  }

  // If options passed explicit transitions list
  if (options?.explicitTransitions) {
    totalOverlapFrames = 0;
    totalInsertFrames = 0;
    for (const t of options.explicitTransitions) {
      const d = t.durationFrames ?? 0;
      const semantics = t.overlap_semantics ?? mode ?? "overlap";
      if (semantics === "overlap") totalOverlapFrames += d;
      else if (semantics === "insert") totalInsertFrames += d;
    }
  }

  // Sum of raw scene durations
  const sumSceneDurations = sceneList.reduce((acc, s) => acc + s.durationFrames, 0);

  if (totalOverlapFrames > 0 || totalInsertFrames > 0 || mode === "overlap" || mode === "insert") {
    const calculated = sumSceneDurations - totalOverlapFrames + totalInsertFrames;
    return Math.max(calculated, 1);
  }

  // Non-overlapped fallback: maximum endFrame of all scenes
  return sceneList.reduce((max, s) => {
    const start = s.startFrame ?? 0;
    const end = start + s.durationFrames;
    return end > max ? end : max;
  }, 0);
}
