/**
 * عقد الهوية البصرية (Brand Contract)
 * يوفر Context وحاويات للعلامة التجارية في التطبيق
 */

import React, { createContext, useContext } from "react";

/** الهوية البصرية المطابقة لعقد brand.schema.json */
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

/** سياق العلامة التجارية */
export const BrandContext = createContext<BrandKit | null>(null);

/**
 * المزود الذي يمرر الهوية البصرية لكامل المشروع
 * @param props خصائص المزود
 */
export const BrandProvider = ({ brand, children }: { brand: BrandKit; children: React.ReactNode }) => {
  return React.createElement(BrandContext.Provider, { value: brand }, children);
};

/**
 * الحصول على الهوية البصرية الحالية
 * @returns الهوية البصرية
 * @throws إذا تم الاستدعاء خارج BrandProvider
 */
export function useBrand(): BrandKit {
  const ctx = useContext(BrandContext);
  if (!ctx) {
    throw new Error("useBrand must be used within a BrandProvider");
  }
  return ctx;
}

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
  
  // إذا لم يكن من الرموز، إرجاع القيمة نفسها كما هي
  return key;
}
