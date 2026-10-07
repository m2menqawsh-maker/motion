/**
 * remotion-app/src/animations.ts — Remotion Animation Execution Engine.
 * Implements concrete spring() and interpolate() evaluations for the 13 canonical animations.
 */
import { interpolate, spring } from "remotion";
import type {
  AnimationId,
  AnimationContext,
  AnimationResult,
  AnimationFn,
} from "../../contracts/animations";

export type { AnimationContext, AnimationResult, AnimationFn, AnimationId } from "../../contracts/animations";

const DEFAULT_SPEED = 1;
const DEFAULT_DELAY = 0;

function getEffectiveFrame(ctx: AnimationContext): number {
  const delay = ctx.delay ?? DEFAULT_DELAY;
  const speed = ctx.speed ?? DEFAULT_SPEED;
  const rawFrame = ctx.frame - delay;
  if (rawFrame < 0) return 0;
  return rawFrame * speed;
}

/** Remotion-specific runtime animation execution registry */
export const ANIMATION_REGISTRY: Record<AnimationId, AnimationFn> = {
  none: (_ctx) => ({ progress: 1, opacity: 1 }),

  fade_in: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const opacity = interpolate(ef, [0, 15], [0, 1], { extrapolateRight: "clamp" });
    return { progress: opacity, opacity };
  },

  fade_in_up: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 12 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  fade_out: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const opacity = interpolate(ef, [0, 15], [1, 0], { extrapolateRight: "clamp" });
    return { progress: 1 - opacity, opacity };
  },

  zoom_in: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = interpolate(ef, [0, 20], [0, 1], { extrapolateRight: "clamp" });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  zoom_in_bounce: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 12, stiffness: 100 } });
    const opacity = interpolate(ef, [0, 5], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  slide_up: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 14 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  slide_down: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 14 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  slide_right: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 14 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  slide_left: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 14 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  typewriter: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = interpolate(ef, [0, 30], [0, 1], { extrapolateRight: "clamp" });
    const opacity = ef >= 0 ? 1 : 0;
    return { progress, opacity };
  },

  word_flip: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 12 } });
    const opacity = interpolate(ef, [0, 10], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },

  text_swell: (ctx) => {
    const ef = getEffectiveFrame(ctx);
    const progress = spring({ fps: ctx.fps, frame: ef, config: { damping: 10, mass: 1.5 } });
    const opacity = interpolate(ef, [0, 15], [0, 1], { extrapolateRight: "clamp" });
    return { progress, opacity };
  },
};

/**
 * Execute animation calculations via Remotion runtime primitives
 */
export function applyAnimation(id: AnimationId, ctx: AnimationContext): AnimationResult {
  if (!(id in ANIMATION_REGISTRY)) {
    throw new Error(`Unknown animation: ${id}`);
  }
  return ANIMATION_REGISTRY[id](ctx);
}
