/**
 * عقد سجل الخطوط (Fonts Registry)
 * يحمّل خطوط Google المطلوبة، ويوفر دوال مساعدة لاتجاه النص (RTL/LTR) والتحقق من الأسماء.
 */

import { loadFont as loadCairo } from "@remotion/google-fonts/Cairo";
import { loadFont as loadTajawal } from "@remotion/google-fonts/Tajawal";
import { loadFont as loadAlmarai } from "@remotion/google-fonts/Almarai";
import { loadFont as loadIBMPlexSansArabic } from "@remotion/google-fonts/IBMPlexSansArabic";
import { loadFont as loadNotoKufiArabic } from "@remotion/google-fonts/NotoKufiArabic";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadManrope } from "@remotion/google-fonts/Manrope";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

import type { FontKey } from "./StyleSurface";

/** بيانات الخط المسجل */
export interface FontEntry {
  /** دالة تحميل الخط من Remotion */
  load: () => void;
  /** هل الخط يدعم وتتجه نصوصه من اليمين لليسار؟ */
  rtl: boolean;
  /** نظام الكتابة */
  script: string;
}

/** سجل الخطوط المعتمدة */
export const FONT_REGISTRY: Record<FontKey, FontEntry> = {
  Cairo: { load: loadCairo, rtl: true, script: "Arabic" },
  Tajawal: { load: loadTajawal, rtl: true, script: "Arabic" },
  Almarai: { load: loadAlmarai, rtl: true, script: "Arabic" },
  IBMPlexSansArabic: { load: loadIBMPlexSansArabic, rtl: true, script: "Arabic" },
  NotoKufiArabic: { load: loadNotoKufiArabic, rtl: true, script: "Arabic" },
  Inter: { load: loadInter, rtl: false, script: "Latin" },
  Manrope: { load: loadManrope, rtl: false, script: "Latin" },
  Fraunces: { load: loadFraunces, rtl: false, script: "Latin" },
  JetBrainsMono: { load: loadJetBrainsMono, rtl: false, script: "Latin" },
};

/**
 * تحميل الخط للبرنامج
 * @param key مفتاح الخط المراد تحميله
 */
export async function loadFont(key: FontKey) {
  if (FONT_REGISTRY[key]) {
    await FONT_REGISTRY[key].load();
  }
}

/**
 * معرفة هل الخط يعتمد الكتابة من اليمين لليسار
 * @param key مفتاح الخط
 * @returns قيمة منطقية true إن كان يعتمد RTL
 */
export function isRTL(key: FontKey): boolean {
  return FONT_REGISTRY[key]?.rtl ?? false;
}

/**
 * تحقق من أن السلسلة النصية هي مفتاح خط صالح
 * @param s السلسلة المراد فحصها
 * @returns مفتاح الخط الصالح أو يرمي خطأ
 */
export function assertFontKey(s: string): FontKey {
  if (s in FONT_REGISTRY) {
    return s as FontKey;
  }
  throw new Error(`Invalid font key: ${s}`);
}
