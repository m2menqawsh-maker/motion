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

/**
 * فحص قيم السطح (Runtime Validator)
 * @param obj الكائن المراد فحصه
 * @returns نتيجة الفحص
 */
export function validateStyleSurface(obj: any): { ok: boolean; errors: string[] } {
  const errors: string[] = [];
  if (typeof obj !== "object" || obj === null) {
    return { ok: false, errors: ["obj is not an object"] };
  }

  // Basic numeric validations based on schema
  if (obj.fontSize !== undefined && (typeof obj.fontSize !== "number" || obj.fontSize < 8 || obj.fontSize > 400)) {
    errors.push("fontSize must be a number between 8 and 400");
  }
  if (obj.lineHeight !== undefined && (typeof obj.lineHeight !== "number" || obj.lineHeight < 0.5 || obj.lineHeight > 4)) {
    errors.push("lineHeight must be a number between 0.5 and 4");
  }
  if (obj.opacity !== undefined && (typeof obj.opacity !== "number" || obj.opacity < 0 || obj.opacity > 1)) {
    errors.push("opacity must be a number between 0 and 1");
  }
  if (obj.scale !== undefined && (typeof obj.scale !== "number" || obj.scale < 0.1 || obj.scale > 10)) {
    errors.push("scale must be a number between 0.1 and 10");
  }
  if (obj.rotation !== undefined && (typeof obj.rotation !== "number" || obj.rotation < -360 || obj.rotation > 360)) {
    errors.push("rotation must be a number between -360 and 360");
  }
  if (obj.width !== undefined && (typeof obj.width !== "number" || obj.width < 1)) {
    errors.push("width must be a number >= 1");
  }
  if (obj.height !== undefined && (typeof obj.height !== "number" || obj.height < 1)) {
    errors.push("height must be a number >= 1");
  }
  if (obj.speed !== undefined && (typeof obj.speed !== "number" || obj.speed < 0.1 || obj.speed > 5)) {
    errors.push("speed must be a number between 0.1 and 5");
  }
  if (obj.delay !== undefined && (typeof obj.delay !== "number" || obj.delay < 0)) {
    errors.push("delay must be a number >= 0");
  }

  return { ok: errors.length === 0, errors };
}
