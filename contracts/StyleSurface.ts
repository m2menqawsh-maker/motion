/**
 * عقد سطح الأنماط (StyleSurface)
 * يمثل خصائص العرض البصري المشتقة من المخطط التنفيذي (blueprint.schema.json).
 */

/** نوع الحركة المدعومة */
export type AnimationId =
  | "none"
  | "fade_in"
  | "fade_in_up"
  | "fade_out"
  | "zoom_in"
  | "zoom_in_bounce"
  | "slide_up"
  | "slide_down"
  | "slide_right"
  | "slide_left"
  | "typewriter"
  | "word_flip"
  | "text_swell";

/** الخطوط المعتمدة */
export type FontKey =
  | "Cairo"
  | "Tajawal"
  | "Almarai"
  | "IBMPlexSansArabic"
  | "NotoKufiArabic"
  | "Inter"
  | "Manrope"
  | "Fraunces"
  | "JetBrainsMono";

/** نقاط الارتكاز المتاحة (9 قيم) */
export type AnchorId =
  | "top-left"
  | "top-center"
  | "top-right"
  | "center-left"
  | "center"
  | "center-right"
  | "bottom-left"
  | "bottom-center"
  | "bottom-right";

/** تدرج لوني */
export interface Gradient {
  /** اللون الأول (HEX) */
  from: string;
  /** اللون الثاني (HEX) */
  to: string;
  /** زاوية التدرج بالدرجات */
  angle?: number;
}

/** الإزاحة والموقع المكاني */
export interface Position {
  /** نقطة الارتكاز الأساسية */
  anchor: AnchorId;
  /** الإزاحة الأفقية */
  x?: number;
  /** الإزاحة العمودية */
  y?: number;
}

/** تجاوزات الأنماط المسموحة من CSS */
export interface StyleOverride {
  borderRadius?: string | number;
  boxShadow?: string | number;
  textShadow?: string | number;
  filter?: string | number;
  backdropFilter?: string | number;
  border?: string | number;
  borderColor?: string | number;
  borderWidth?: string | number;
  textStroke?: string | number;
  textStrokeWidth?: string | number;
  padding?: string | number;
  gap?: string | number;
}

/** 
 * سطح الأنماط - العقد الأساسي 
 * كل خصائص العرض في كائن واحد
 */
export interface StyleSurface {
  text?: string;
  subtext?: string;
  emphasis?: string;
  fontSize?: number;
  fontWeight?: number | string;
  fontFamily?: FontKey;
  letterSpacing?: string;
  textAlign?: "right" | "center" | "left" | "start" | "end";
  lineHeight?: number;
  color?: string;
  background?: string;
  gradient?: Gradient;
  opacity?: number;
  position?: Position;
  scale?: number;
  rotation?: number;
  width?: number;
  height?: number;
  animation?: AnimationId;
  speed?: number;
  delay?: number;
  mode?: "light" | "dark";
  logoSrc?: string;
  brandName?: string;
  styleOverride?: StyleOverride;
}

import { StyleSurfaceSchema } from "./blueprint";

/**
 * فحص خصائص السطح (StyleSurface) بالاعتماد على Zod Schema
 */
export function validateStyleSurface(obj: unknown): { ok: boolean; errors: string[] } {
  const res = StyleSurfaceSchema.safeParse(obj);
  if (res.success) return { ok: true, errors: [] };
  return { ok: false, errors: (res.error as any).errors.map((e: any) => e.message) };
}
