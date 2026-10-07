/**
 * contracts/brand.ts — Canonical Brand Contract.
 * S28-R02: Pure data definitions and token resolution for BrandKit.
 * ZERO React or Remotion dependencies (React Context lives in remotion-app/src/BrandContext.tsx).
 */

/** Authoritative BrandKit data model */
export interface BrandKit {
  /** اسم العلامة التجارية */
  brandName: string;
  /** مسار الشعار إن وجد */
  logoSrc: string | null;
  /** لوحة الألوان */
  colors: {
    primary: string;
    accent: string;
    background: string;
    text: string;
    surface?: string;
  };
  /** الخطوط الأساسية */
  fonts: {
    display: string;
    body: string;
  };
  /** نبرة التصميم (اختياري) */
  tone?: string;
}

export const DEFAULT_BRAND_KIT: BrandKit = {
  brandName: "Default",
  logoSrc: null,
  colors: {
    primary: "#00F5FF",
    accent: "#FFD700",
    background: "#1a2238",
    text: "#FFFFFF",
  },
  fonts: {
    display: "Cairo",
    body: "IBMPlexSansArabic",
  },
};

/**
 * تحليل رموز الهوية البصرية إلى قيمتها الفعلية
 * مثال: "brand.primary" يتحول للون الأساسي في الهوية
 * @param key مفتاح اللون (أو قيمة HEX مباشرة)
 * @param brand الهوية البصرية
 * @returns اللون الفعلي
 */
export function resolveBrandToken(key: string, brand: BrandKit): string {
  if (key === "brand.primary") return brand.colors.primary;
  if (key === "brand.accent") return brand.colors.accent;
  if (key === "brand.background") return brand.colors.background;
  if (key === "brand.text") return brand.colors.text;
  if (key === "brand.surface" && brand.colors.surface) return brand.colors.surface;
  if (key === "brand.display") return brand.fonts.display;
  if (key === "brand.body") return brand.fonts.body;
  if (key === "brand.logo" && brand.logoSrc) return brand.logoSrc;

  // إذا لم يكن من الرموز، إرجاع القيمة نفسها كما هي
  return key;
}
