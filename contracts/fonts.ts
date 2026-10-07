/**
 * contracts/fonts.ts — Canonical Font Contract.
 * S28-R02: Pure declarative font metadata, RTL rules, and key validation.
 * ZERO Remotion runtime dependencies (font asset loading lives in renderer runtime).
 */

import type { FontKey } from "./StyleSurface";

export type { FontKey } from "./StyleSurface";

/** Supported typography keys */
export const SUPPORTED_FONT_KEYS: readonly FontKey[] = [
  "Cairo",
  "Tajawal",
  "Almarai",
  "IBMPlexSansArabic",
  "NotoKufiArabic",
  "Inter",
  "Manrope",
  "Fraunces",
  "JetBrainsMono",
] as const;

/** Canonical font metadata */
export interface FontMetadata {
  rtl: boolean;
  script: "Arabic" | "Latin";
}

export const FONT_METADATA: Record<FontKey, FontMetadata> = {
  Cairo: { rtl: true, script: "Arabic" },
  Tajawal: { rtl: true, script: "Arabic" },
  Almarai: { rtl: true, script: "Arabic" },
  IBMPlexSansArabic: { rtl: true, script: "Arabic" },
  NotoKufiArabic: { rtl: true, script: "Arabic" },
  Inter: { rtl: false, script: "Latin" },
  Manrope: { rtl: false, script: "Latin" },
  Fraunces: { rtl: false, script: "Latin" },
  JetBrainsMono: { rtl: false, script: "Latin" },
};

/**
 * Checks whether a font key uses Right-to-Left (RTL) script direction.
 */
export function isRTL(key: FontKey): boolean {
  return FONT_METADATA[key]?.rtl ?? false;
}

/**
 * Validates and asserts that a string is a valid canonical FontKey fail-closed.
 */
export function assertFontKey(key: string): FontKey {
  if (!SUPPORTED_FONT_KEYS.includes(key as FontKey)) {
    throw new Error(
      `Invalid font key: '${key}'. Supported fonts: ${SUPPORTED_FONT_KEYS.join(", ")}`
    );
  }
  return key as FontKey;
}

/**
 * Pure contract stub for loadFont; renderer runtime binds actual font loading.
 */
export async function loadFont(_key: FontKey): Promise<void> {
  // Pure declarative contract stub
}
