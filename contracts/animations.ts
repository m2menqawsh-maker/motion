/**
 * contracts/animations.ts — Canonical Declarative Animation Contract.
 * S28-R02: Pure declarative animation definitions and specifications.
 * ZERO Remotion runtime dependencies (interpolate/spring execution lives in renderer runtime).
 */
import type { AnimationId } from "./StyleSurface";

export type { AnimationId } from "./StyleSurface";

/** Easing curve types recognized by canonical animation contracts */
export type EasingType =
  | "linear"
  | "ease-in"
  | "ease-out"
  | "ease-in-out"
  | "spring";

/** Physical spring simulation configuration */
export interface SpringConfig {
  damping?: number;
  stiffness?: number;
  mass?: number;
}

/** Pure semantic specification of an animation */
export interface AnimationSpec {
  animation_id: AnimationId;
  type: "static" | "opacity" | "scale" | "translate_x" | "translate_y" | "transform_opacity" | "scale_opacity" | "scale_bounce" | "step" | "flip";
  start?: number;
  duration?: number;
  easing?: EasingType;
  spring?: SpringConfig;
}

/** Rich semantic definition of a canonical animation */
export interface AnimationDefinition {
  id: AnimationId;
  name: string;
  description: string;
  spec: AnimationSpec;
  defaultDurationFrames?: number;
}

/** Declarative registry of the 13 canonical animation definitions */
export const ANIMATION_DEFINITIONS: Record<AnimationId, AnimationDefinition> = {
  none: {
    id: "none",
    name: "None",
    description: "Static display without visual transition",
    spec: { animation_id: "none", type: "static", easing: "linear" },
    defaultDurationFrames: 0,
  },
  fade_in: {
    id: "fade_in",
    name: "Fade In",
    description: "Linear opacity transition from 0 to 1 over 15 frames",
    spec: { animation_id: "fade_in", type: "opacity", start: 0, duration: 15, easing: "linear" },
    defaultDurationFrames: 15,
  },
  fade_in_up: {
    id: "fade_in_up",
    name: "Fade In Up",
    description: "Combined spring upward translation with 10-frame opacity ramp",
    spec: {
      animation_id: "fade_in_up",
      type: "transform_opacity",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 12 },
    },
    defaultDurationFrames: 15,
  },
  fade_out: {
    id: "fade_out",
    name: "Fade Out",
    description: "Linear opacity transition from 1 to 0 over 15 frames",
    spec: { animation_id: "fade_out", type: "opacity", start: 0, duration: 15, easing: "linear" },
    defaultDurationFrames: 15,
  },
  zoom_in: {
    id: "zoom_in",
    name: "Zoom In",
    description: "Linear scale transition from 0 to 1 over 20 frames with opacity ramp",
    spec: { animation_id: "zoom_in", type: "scale_opacity", start: 0, duration: 20, easing: "linear" },
    defaultDurationFrames: 20,
  },
  zoom_in_bounce: {
    id: "zoom_in_bounce",
    name: "Zoom In Bounce",
    description: "Underdamped spring scale with bounce effect over 20 frames",
    spec: {
      animation_id: "zoom_in_bounce",
      type: "scale_bounce",
      start: 0,
      duration: 20,
      easing: "spring",
      spring: { damping: 12, stiffness: 100 },
    },
    defaultDurationFrames: 20,
  },
  slide_up: {
    id: "slide_up",
    name: "Slide Up",
    description: "Vertical upward translation governed by spring damping",
    spec: {
      animation_id: "slide_up",
      type: "translate_y",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 14 },
    },
    defaultDurationFrames: 15,
  },
  slide_down: {
    id: "slide_down",
    name: "Slide Down",
    description: "Vertical downward translation governed by spring damping",
    spec: {
      animation_id: "slide_down",
      type: "translate_y",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 14 },
    },
    defaultDurationFrames: 15,
  },
  slide_right: {
    id: "slide_right",
    name: "Slide Right",
    description: "Horizontal translation to the right governed by spring damping",
    spec: {
      animation_id: "slide_right",
      type: "translate_x",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 14 },
    },
    defaultDurationFrames: 15,
  },
  slide_left: {
    id: "slide_left",
    name: "Slide Left",
    description: "Horizontal translation to the left governed by spring damping",
    spec: {
      animation_id: "slide_left",
      type: "translate_x",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 14 },
    },
    defaultDurationFrames: 15,
  },
  typewriter: {
    id: "typewriter",
    name: "Typewriter",
    description: "Stepwise character reveal animation over 30 frames",
    spec: { animation_id: "typewriter", type: "step", start: 0, duration: 30, easing: "linear" },
    defaultDurationFrames: 30,
  },
  word_flip: {
    id: "word_flip",
    name: "Word Flip",
    description: "3D/2D spring flip transition on word boundary",
    spec: {
      animation_id: "word_flip",
      type: "flip",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 12 },
    },
    defaultDurationFrames: 15,
  },
  text_swell: {
    id: "text_swell",
    name: "Text Swell",
    description: "Heavy mass spring swell scale effect over 15 frames",
    spec: {
      animation_id: "text_swell",
      type: "scale",
      start: 0,
      duration: 15,
      easing: "spring",
      spring: { damping: 10, mass: 1.5 },
    },
    defaultDurationFrames: 15,
  },
};

/** All 13 canonical animation IDs */
export const CANONICAL_ANIMATION_IDS = Object.keys(ANIMATION_DEFINITIONS) as AnimationId[];

export function isKnownAnimation(id: string): id is AnimationId {
  return typeof id === "string" && id in ANIMATION_DEFINITIONS;
}

export function getKnownAnimationIds(): AnimationId[] {
  return [...CANONICAL_ANIMATION_IDS];
}

/** 
 * Animation evaluation context passed to execution engines
 */
export interface AnimationContext {
  frame: number;
  fps: number;
  startFrame?: number;
  durationFrames?: number;
  delay?: number;
  speed?: number;
}

/** 
 * Result of an animation evaluation
 */
export interface AnimationResult {
  progress: number;
  opacity: number;
}

/** Execution signature for renderer animation functions */
export type AnimationFn = (ctx: AnimationContext) => AnimationResult;
