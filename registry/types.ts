import type { ComponentType } from "react";
import type { StyleSurface } from "../contracts/StyleSurface";

/** نوع الحقل في واجهة المستخدم (الـ GUI) */
export type SchemaFieldType =
  | "text"
  | "number"
  | "color"
  | "select"
  | "range"
  | "fontKey"
  | "animation"
  | "anchor"
  | "boolean"
  | "logo";

/** تعريف حقل واحد من حقول الخصائص */
export interface SchemaField {
  type: SchemaFieldType;
  label: { ar: string; en: string };
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  default?: any;
  placeholder?: string;
}

/** التصنيفات الأساسية للقوالب */
export type TemplateCategory = "text" | "media" | "brand" | "layout" | "effect" | "data" | "audio";

/**
 * مدخلة القالب في السجل
 * تمثل القالب، مكوناته، خصائصه، وتفاصيله للاستخدام في الواجهة.
 */
export interface TemplateEntry {
  /** معرّف القالب ويجب أن يطابق ^[a-z0-9-]+$ */
  id: string;
  /** اسم القالب (للعرض) */
  label: { ar: string; en: string };
  /** وصف قصير للقالب */
  description: { ar: string; en: string };
  /** تصنيف القالب */
  category: TemplateCategory;
  /** مكون React الفعلي للقالب */
  component: ComponentType<any>;
  /** المدة الافتراضية للقالب بالإطارات */
  defaultDurationFrames: number;
  /** اسم أيقونة القالب للواجهة (اختياري) */
  icon?: string;
  /** مسار الصورة المصغرة للقالب (يتم تعبئته لاحقاً) */
  thumbPath?: string;
  /** هيكل بيانات الخصائص (Props Schema) للقالب */
  schema: Record<string, SchemaField>;
  /** القيم الافتراضية المستندة لـ StyleSurface */
  defaults: Partial<StyleSurface>;
  /** الحد الأدنى للمدة بالإطارات */
  minDurationFrames?: number;
  /** الحد الأقصى للمدة بالإطارات */
  maxDurationFrames?: number;
  /** أنواع المحتوى التي يستهلكها هذا القالب من المراجع الخارجية */
  consumes?: ("lines"|"words"|"images"|"screen"|"numbers"|"range"|"path"|"icons"|"audioRef"|"spectrum")[];
  /** أصل القالب (مثل "docs") */
  origin?: string;
  /** تصنيف الجودة (A, B, C, unknown) */
  tier?: string;
  /** معرفات تأثيرات المحرك (effects-catalog) التي يعتمد عليها القالب جوهرياً */
  usesEffects?: string[];
}
