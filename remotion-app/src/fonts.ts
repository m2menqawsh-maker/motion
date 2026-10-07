/**
 * remotion-app/src/fonts.ts — Remotion Google Fonts Loader Runtime.
 * Decoupled from contracts layer in S28-R02.
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

import type { FontKey } from "../../contracts/StyleSurface";
import { isRTL, assertFontKey, SUPPORTED_FONT_KEYS } from "../../contracts/fonts";

export { isRTL, assertFontKey, SUPPORTED_FONT_KEYS } from "../../contracts/fonts";
export type { FontKey } from "../../contracts/StyleSurface";

export interface FontEntry {
  load: () => void;
  rtl: boolean;
  script: string;
}

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

export async function loadFont(key: FontKey) {
  if (FONT_REGISTRY[key]) {
    await FONT_REGISTRY[key].load();
  }
}
