/**
 * عقد الحركات (Animations)
 * يحوي الدوال التي تحول الإطارات إلى قيم للشفافية والحركة البصرية وغيرها.
 */

import { interpolate, spring } from "remotion";
import type { AnimationId } from "./StyleSurface";

/** 
 * سياق الحركة
 * الخصائص المتوفرة للعمليات الحسابية للحركة في كل إطار
 */
export interface AnimationContext {
  /** الإطار الحالي للمشهد (أو للقطة) */
  frame: number;
  /** الإطارات في الثانية للمشروع */
  fps: number;
  /** الإطار الذي يبدأ فيه المشهد/اللقطة (للاستخدام كمرجع إن لزم) */
  startFrame?: number;
  /** مدة المشهد/اللقطة */
  durationFrames?: number;
  /** التأخير قبل بدء الحركة (بالإطارات) */
  delay?: number;
  /** سرعة الحركة (عامل ضرب، 1 هو الطبيعي) */
  speed?: number;
}

/** 
 * نتيجة الحركة
 * تتضمن الشفافية والتقدم العام، يمكن لبعض الحركات إرجاع إزاحات معينة إن احتيج.
 * هنا تم تبسيطها للمطلوب: progress, opacity
 */
export interface AnimationResult {
  progress: number;
  opacity: number;
}

/** توقيع دالة الحركة */
export type AnimationFn = (ctx: AnimationContext) => AnimationResult;

const DEFAULT_SPEED = 1;
const DEFAULT_DELAY = 0;

/**
 * دالة مساعدة لحساب الإطار الفعال للحركة بعد طرح التأخير والضرب بالسرعة
 */
function getEffectiveFrame(ctx: AnimationContext): number {
  const delay = ctx.delay ?? DEFAULT_DELAY;
  const speed = ctx.speed ?? DEFAULT_SPEED;
  const rawFrame = ctx.frame - delay;
  if (rawFrame < 0) return 0;
  return rawFrame * speed;
}

/** سجل الحركات المعتمدة */
export const ANIMATION_REGISTRY: Record<AnimationId, AnimationFn> = {
  none: (ctx) => ({ progress: 1, opacity: 1 }),
  
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
    // افترض أن التلاشي يبدأ في آخر 15 إطار
    const duration = ctx.durationFrames ?? 30;
    const ef = getEffectiveFrame(ctx);
    // إذا استخدمنا الشفافية العكسية
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
 * تطبيق الحركة المحددة بناءً على السياق المعطى
 * @param id معرف الحركة
 * @param ctx سياق الحركة (الإطار، التأخير، السرعة، إلخ)
 * @returns نتيجة الحركة
 */
export function applyAnimation(id: AnimationId, ctx: AnimationContext): AnimationResult {
  if (!(id in ANIMATION_REGISTRY)) {
    throw new Error(`Unknown animation: ${id}`);
  }
  return ANIMATION_REGISTRY[id](ctx);
}
