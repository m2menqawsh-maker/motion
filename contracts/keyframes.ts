/**
 * contracts/keyframes.ts — Canonical Keyframes, Channels & Pure Animation Mathematics.
 * S28-R03: Deterministic interpolation, easing curves, analytical spring physics, and channel evaluation.
 * ZERO React or Remotion dependencies.
 */
import { z } from "zod";
import { StableIdSchema } from "./timeline";

// ────────────────────────────────────────────────────────────────────────────
// 1. Types & Schemas
// ────────────────────────────────────────────────────────────────────────────

export const InterpolationTypeSchema = z.enum([
  "STEP",
  "LINEAR",
  "EASE",
  "SPRING",
  "CUBIC_BEZIER",
]);
export type InterpolationType = z.infer<typeof InterpolationTypeSchema>;

export const EasingTypeSchema = z.enum(["linear", "ease-in", "ease-out", "ease-in-out"]);
export type EasingType = z.infer<typeof EasingTypeSchema>;

export const ChannelTargetSchema = z.enum([
  "TRANSFORM_X",
  "TRANSFORM_Y",
  "SCALE_X",
  "SCALE_Y",
  "SCALE",
  "ROTATION",
  "OPACITY",
  "VOLUME",
]);
export type ChannelTarget = z.infer<typeof ChannelTargetSchema>;

export const SpringConfigSchema = z.object({
  damping: z.number().positive().default(10),
  stiffness: z.number().positive().default(100),
  mass: z.number().positive().default(1),
  overshootClamping: z.boolean().default(false),
});
export type SpringConfig = z.infer<typeof SpringConfigSchema>;

export const KeyframeSchema = z.object({
  keyframe_id: StableIdSchema,
  frame: z.number().min(0, "Keyframe frame must be non-negative"),
  value: z.number().refine((v) => !Number.isNaN(v) && Number.isFinite(v), "Keyframe value must be a finite number"),
  interpolation: InterpolationTypeSchema.default("LINEAR"),
  easing: EasingTypeSchema.optional(),
  bezier: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional(),
  spring: SpringConfigSchema.optional(),
});
export type Keyframe = z.infer<typeof KeyframeSchema>;

export const AnimationChannelSchema = z.object({
  channel_id: StableIdSchema,
  target: ChannelTargetSchema,
  keyframes: z.array(KeyframeSchema),
});
export type AnimationChannel = z.infer<typeof AnimationChannelSchema>;

export const AnimationClassificationSchema = z.enum([
  "CANONICAL_PRIMITIVE",
  "CANONICAL_PRESET",
  "REMOTION_COMPATIBILITY_PRESET",
  "TEMPLATE_INTERNAL_LEGACY",
]);
export type AnimationClassification = z.infer<typeof AnimationClassificationSchema>;

export const AnimationPresetSchema = z.object({
  preset_id: StableIdSchema,
  name: z.string().min(1),
  description: z.string(),
  classification: AnimationClassificationSchema,
  channels: z.array(AnimationChannelSchema),
  defaultDurationFrames: z.number().int().min(0),
});
export type AnimationPreset = z.infer<typeof AnimationPresetSchema>;

export const AnimationInstanceSchema = z.object({
  animation_id: StableIdSchema,
  preset_id: StableIdSchema,
  target_layer_id: StableIdSchema,
  startFrame: z.number().int().min(0),
  durationFrames: z.number().int().min(1),
  overrides: z.record(z.string(), z.any()).optional(),
});
export type AnimationInstance = z.infer<typeof AnimationInstanceSchema>;

// ────────────────────────────────────────────────────────────────────────────
// 2. Validation & Ordering
// ────────────────────────────────────────────────────────────────────────────

export function validateKeyframes(keyframes: Keyframe[]): void {
  if (!Array.isArray(keyframes)) {
    throw new Error("Keyframes must be an array");
  }

  const seenIds = new Set<string>();
  let lastFrame = -Infinity;

  for (let i = 0; i < keyframes.length; i++) {
    const kf = keyframes[i];
    if (seenIds.has(kf.keyframe_id)) {
      throw new Error(`Duplicate keyframe_id '${kf.keyframe_id}' at index ${i}`);
    }
    seenIds.add(kf.keyframe_id);

    if (Number.isNaN(kf.frame) || !Number.isFinite(kf.frame) || kf.frame < 0) {
      throw new Error(`Invalid keyframe frame ${kf.frame} at index ${i}: must be finite number >= 0`);
    }

    if (Number.isNaN(kf.value) || !Number.isFinite(kf.value)) {
      throw new Error(`Invalid keyframe value ${kf.value} at index ${i}: must be finite number`);
    }

    if (kf.frame < lastFrame) {
      throw new Error(`Keyframes out of order at index ${i}: frame ${kf.frame} is less than preceding frame ${lastFrame}`);
    }
    if (kf.frame === lastFrame && i > 0) {
      throw new Error(`Ambiguous duplicate keyframe timestamp ${kf.frame} at indices ${i - 1} and ${i}`);
    }

    lastFrame = kf.frame;
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Pure Easing Mathematics
// ────────────────────────────────────────────────────────────────────────────

export function evaluateLinear(t: number): number {
  return t;
}

export function evaluateEaseIn(t: number): number {
  return t * t;
}

export function evaluateEaseOut(t: number): number {
  return 1 - (1 - t) * (1 - t);
}

export function evaluateEaseInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export function evaluateEasing(type: EasingType, t: number): number {
  const clamped = Math.max(0, Math.min(1, t));
  switch (type) {
    case "linear":
      return evaluateLinear(clamped);
    case "ease-in":
      return evaluateEaseIn(clamped);
    case "ease-out":
      return evaluateEaseOut(clamped);
    case "ease-in-out":
      return evaluateEaseInOut(clamped);
    default:
      return evaluateLinear(clamped);
  }
}

/**
 * Pure cubic bezier solver using Newton-Raphson with bisection fallback.
 * Solves B_x(u) = t for u, then returns B_y(u).
 */
export function solveCubicBezier(t: number, x1: number, y1: number, x2: number, y2: number): number {
  if (t <= 0) return 0;
  if (t >= 1) return 1;

  // Bezier curve equations: B(u) = 3*(1-u)^2*u*P1 + 3*(1-u)*u^2*P2 + u^3
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;

  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;

  function sampleX(u: number): number {
    return ((ax * u + bx) * u + cx) * u;
  }

  function sampleY(u: number): number {
    return ((ay * u + by) * u + cy) * u;
  }

  function sampleDerivativeX(u: number): number {
    return (3 * ax * u + 2 * bx) * u + cx;
  }

  // Newton-Raphson iteration
  let u = t;
  for (let i = 0; i < 8; i++) {
    const currentX = sampleX(u) - t;
    if (Math.abs(currentX) < 1e-7) return sampleY(u);
    const dX = sampleDerivativeX(u);
    if (Math.abs(dX) < 1e-6) break;
    u -= currentX / dX;
  }

  // Bisection fallback
  let low = 0;
  let high = 1;
  u = t;
  while (low < high) {
    const currentX = sampleX(u);
    if (Math.abs(currentX - t) < 1e-7) return sampleY(u);
    if (t > currentX) low = u;
    else high = u;
    u = (high + low) / 2;
  }

  return sampleY(u);
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Analytical Spring Physics Reference Evaluator
// ────────────────────────────────────────────────────────────────────────────

/**
 * Pure engine-neutral spring physics evaluator.
 * Solves the damped harmonic oscillator with bit-level numeric parity to Remotion spring.
 */
export function evaluateSpring(frame: number, fps: number, config?: SpringConfig): number {
  if (fps <= 0) throw new Error(`Invalid fps ${fps}: must be > 0`);

  const damping = config?.damping ?? 10;
  const mass = config?.mass ?? 1;
  const stiffness = config?.stiffness ?? 100;
  const overshootClamping = config?.overshootClamping ?? false;

  if (damping <= 0) throw new Error("Spring damping must be greater than 0");
  if (mass <= 0) throw new Error("Spring mass must be greater than 0");
  if (stiffness <= 0) throw new Error("Spring stiffness must be greater than 0");

  let current = 0;
  let velocity = 0;
  let lastTimestamp = 0;
  const toValue = 1;

  const c = damping;
  const m = mass;
  const k = stiffness;

  const zeta = c / (2 * Math.sqrt(k * m));
  const omega0 = Math.sqrt(k / m);
  const omega1 = zeta < 1 ? omega0 * Math.sqrt(1 - zeta * zeta) : 0;

  const frameClamped = Math.max(0, frame);
  const floorF = Math.floor(frameClamped);
  const unevenRest = frameClamped % 1;

  for (let f = 0; f <= floorF; f++) {
    const now = (f / fps) * 1000;
    const deltaTime = Math.min(now - lastTimestamp, 64);
    const t = deltaTime / 1000;
    const v0 = -velocity;
    const x0 = toValue - current;

    if (zeta < 1) {
      const sin1 = Math.sin(omega1 * t);
      const cos1 = Math.cos(omega1 * t);
      const underDampedEnvelope = Math.exp(-zeta * omega0 * t);
      const underDampedFrag1 =
        underDampedEnvelope * (sin1 * ((v0 + zeta * omega0 * x0) / omega1) + x0 * cos1);
      current = toValue - underDampedFrag1;
      velocity =
        zeta * omega0 * underDampedFrag1 -
        underDampedEnvelope * (cos1 * (v0 + zeta * omega0 * x0) - omega1 * x0 * sin1);
    } else {
      const criticallyDampedEnvelope = Math.exp(-omega0 * t);
      current = toValue - criticallyDampedEnvelope * (x0 + (v0 + omega0 * x0) * t);
      velocity = criticallyDampedEnvelope * (v0 * (t * omega0 - 1) + t * x0 * omega0 * omega0);
    }
    lastTimestamp = now;
  }

  if (unevenRest > 0) {
    const now = (frameClamped / fps) * 1000;
    const deltaTime = Math.min(now - lastTimestamp, 64);
    const t = deltaTime / 1000;
    const v0 = -velocity;
    const x0 = toValue - current;

    if (zeta < 1) {
      const sin1 = Math.sin(omega1 * t);
      const cos1 = Math.cos(omega1 * t);
      const underDampedEnvelope = Math.exp(-zeta * omega0 * t);
      const underDampedFrag1 =
        underDampedEnvelope * (sin1 * ((v0 + zeta * omega0 * x0) / omega1) + x0 * cos1);
      current = toValue - underDampedFrag1;
    } else {
      const criticallyDampedEnvelope = Math.exp(-omega0 * t);
      current = toValue - criticallyDampedEnvelope * (x0 + (v0 + omega0 * x0) * t);
    }
  }

  return overshootClamping ? Math.min(current, 1) : current;
}

// ────────────────────────────────────────────────────────────────────────────
// 5. Channel & Keyframe Evaluation
// ────────────────────────────────────────────────────────────────────────────

export function evaluateKeyframes(keyframes: Keyframe[], localFrame: number, fps: number): number {
  if (!keyframes || keyframes.length === 0) return 0;
  if (keyframes.length === 1) return keyframes[0].value;

  // Clamping outside keyframe bounds
  if (localFrame <= keyframes[0].frame) return keyframes[0].value;
  const lastKf = keyframes[keyframes.length - 1];
  if (localFrame >= lastKf.frame) return lastKf.value;

  // Locate active segment [k0, k1]
  let k0 = keyframes[0];
  let k1 = keyframes[1];
  for (let i = 0; i < keyframes.length - 1; i++) {
    if (localFrame >= keyframes[i].frame && localFrame <= keyframes[i + 1].frame) {
      k0 = keyframes[i];
      k1 = keyframes[i + 1];
      break;
    }
  }

  const segmentDuration = k1.frame - k0.frame;
  if (segmentDuration <= 0) return k0.value;

  const segmentFrame = localFrame - k0.frame;
  const t = segmentFrame / segmentDuration;

  switch (k0.interpolation) {
    case "STEP":
      return t >= 1 ? k1.value : k0.value;

    case "LINEAR":
      return k0.value + (k1.value - k0.value) * t;

    case "EASE": {
      const progress = evaluateEasing(k0.easing ?? "ease-in-out", t);
      return k0.value + (k1.value - k0.value) * progress;
    }

    case "CUBIC_BEZIER": {
      const b = k0.bezier ?? [0.42, 0, 0.58, 1];
      const progress = solveCubicBezier(t, b[0], b[1], b[2], b[3]);
      return k0.value + (k1.value - k0.value) * progress;
    }

    case "SPRING": {
      const springProgress = evaluateSpring(segmentFrame, fps, k0.spring);
      return k0.value + (k1.value - k0.value) * springProgress;
    }

    default:
      return k0.value + (k1.value - k0.value) * t;
  }
}

export function evaluateChannelAtFrame(channel: AnimationChannel, localFrame: number, fps: number): number {
  return evaluateKeyframes(channel.keyframes, localFrame, fps);
}

// ────────────────────────────────────────────────────────────────────────────
// 6. 13 Canonical Animation Presets Catalog
// ────────────────────────────────────────────────────────────────────────────

export const CANONICAL_ANIMATION_PRESETS: Record<string, AnimationPreset> = {
  none: {
    preset_id: "none",
    name: "None",
    description: "Static element without animated transition",
    classification: "CANONICAL_PRIMITIVE",
    defaultDurationFrames: 0,
    channels: [],
  },
  fade_in: {
    preset_id: "fade_in",
    name: "Fade In",
    description: "Linear opacity ramp from 0 to 1 over 15 frames",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_fade_in_opacity",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_fade_in_0", frame: 0, value: 0, interpolation: "LINEAR" },
          { keyframe_id: "kf_fade_in_15", frame: 15, value: 1, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  fade_out: {
    preset_id: "fade_out",
    name: "Fade Out",
    description: "Linear opacity transition from 1 to 0 over 15 frames",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_fade_out_opacity",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_fade_out_0", frame: 0, value: 1, interpolation: "LINEAR" },
          { keyframe_id: "kf_fade_out_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  fade_in_up: {
    preset_id: "fade_in_up",
    name: "Fade In Up",
    description: "Spring upward translation with 10-frame opacity ramp",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_fade_in_up_y",
        target: "TRANSFORM_Y",
        keyframes: [
          {
            keyframe_id: "kf_up_0",
            frame: 0,
            value: 40,
            interpolation: "SPRING",
            spring: { damping: 12, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_up_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
      {
        channel_id: "ch_fade_in_up_opacity",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_up_op_0", frame: 0, value: 0, interpolation: "LINEAR" },
          { keyframe_id: "kf_up_op_10", frame: 10, value: 1, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  zoom_in: {
    preset_id: "zoom_in",
    name: "Zoom In",
    description: "Linear scale transition from 0 to 1 over 20 frames with opacity ramp",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 20,
    channels: [
      {
        channel_id: "ch_zoom_scale",
        target: "SCALE",
        keyframes: [
          { keyframe_id: "kf_zoom_0", frame: 0, value: 0, interpolation: "LINEAR" },
          { keyframe_id: "kf_zoom_20", frame: 20, value: 1, interpolation: "LINEAR" },
        ],
      },
      {
        channel_id: "ch_zoom_opacity",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_zoom_op_0", frame: 0, value: 0, interpolation: "LINEAR" },
          { keyframe_id: "kf_zoom_op_10", frame: 10, value: 1, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  zoom_in_bounce: {
    preset_id: "zoom_in_bounce",
    name: "Zoom In Bounce",
    description: "Underdamped spring scale with bounce effect over 20 frames",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 20,
    channels: [
      {
        channel_id: "ch_bounce_scale",
        target: "SCALE",
        keyframes: [
          {
            keyframe_id: "kf_bounce_0",
            frame: 0,
            value: 0,
            interpolation: "SPRING",
            spring: { damping: 12, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_bounce_20", frame: 20, value: 1, interpolation: "LINEAR" },
        ],
      },
      {
        channel_id: "ch_bounce_opacity",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_bounce_op_0", frame: 0, value: 0, interpolation: "LINEAR" },
          { keyframe_id: "kf_bounce_op_5", frame: 5, value: 1, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  slide_up: {
    preset_id: "slide_up",
    name: "Slide Up",
    description: "Vertical upward translation governed by spring damping 14",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_slide_up_y",
        target: "TRANSFORM_Y",
        keyframes: [
          {
            keyframe_id: "kf_slide_up_0",
            frame: 0,
            value: 50,
            interpolation: "SPRING",
            spring: { damping: 14, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_slide_up_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  slide_down: {
    preset_id: "slide_down",
    name: "Slide Down",
    description: "Vertical downward translation governed by spring damping 14",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_slide_down_y",
        target: "TRANSFORM_Y",
        keyframes: [
          {
            keyframe_id: "kf_slide_down_0",
            frame: 0,
            value: -50,
            interpolation: "SPRING",
            spring: { damping: 14, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_slide_down_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  slide_right: {
    preset_id: "slide_right",
    name: "Slide Right",
    description: "Horizontal rightward translation governed by spring damping 14",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_slide_right_x",
        target: "TRANSFORM_X",
        keyframes: [
          {
            keyframe_id: "kf_slide_right_0",
            frame: 0,
            value: -50,
            interpolation: "SPRING",
            spring: { damping: 14, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_slide_right_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  slide_left: {
    preset_id: "slide_left",
    name: "Slide Left",
    description: "Horizontal leftward translation governed by spring damping 14",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_slide_left_x",
        target: "TRANSFORM_X",
        keyframes: [
          {
            keyframe_id: "kf_slide_left_0",
            frame: 0,
            value: 50,
            interpolation: "SPRING",
            spring: { damping: 14, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_slide_left_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  typewriter: {
    preset_id: "typewriter",
    name: "Typewriter",
    description: "Stepwise character reveal animation over 30 frames",
    classification: "REMOTION_COMPATIBILITY_PRESET",
    defaultDurationFrames: 30,
    channels: [
      {
        channel_id: "ch_typewriter_step",
        target: "OPACITY",
        keyframes: [
          { keyframe_id: "kf_type_0", frame: 0, value: 0, interpolation: "STEP" },
          { keyframe_id: "kf_type_30", frame: 30, value: 1, interpolation: "STEP" },
        ],
      },
    ],
  },
  word_flip: {
    preset_id: "word_flip",
    name: "Word Flip",
    description: "Word rotation flip governed by spring damping 12",
    classification: "REMOTION_COMPATIBILITY_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_word_flip_rot",
        target: "ROTATION",
        keyframes: [
          {
            keyframe_id: "kf_flip_0",
            frame: 0,
            value: 90,
            interpolation: "SPRING",
            spring: { damping: 12, stiffness: 100, mass: 1, overshootClamping: false },
          },
          { keyframe_id: "kf_flip_15", frame: 15, value: 0, interpolation: "LINEAR" },
        ],
      },
    ],
  },
  text_swell: {
    preset_id: "text_swell",
    name: "Text Swell",
    description: "Heavy mass spring swell scale effect over 15 frames",
    classification: "CANONICAL_PRESET",
    defaultDurationFrames: 15,
    channels: [
      {
        channel_id: "ch_swell_scale",
        target: "SCALE",
        keyframes: [
          {
            keyframe_id: "kf_swell_0",
            frame: 0,
            value: 0.5,
            interpolation: "SPRING",
            spring: { damping: 10, stiffness: 100, mass: 1.5, overshootClamping: false },
          },
          { keyframe_id: "kf_swell_15", frame: 15, value: 1, interpolation: "LINEAR" },
        ],
      },
    ],
  },
};
