/**
 * محلل الهوية البصرية (Brand Resolver)
 * يترجم مفاتيح الألوان والخطوط والشعار من BrandKit
 */

import type { BrandKit } from "../contracts/brand";

/**
 * تحليل رموز الهوية البصرية إلى قيمتها الفعلية
 * مثال: "brand.primary" يتحول للون الأساسي في الهوية
 * @param key مفتاح الرمز (أو قيمة مباشرة)
 * @param brand الهوية البصرية
 * @returns القيمة الفعلية
 */
export function resolveBrandToken(key: string, brand: BrandKit): string {
  // الألوان
  if (key === "brand.primary") return brand.colors.primary;
  if (key === "brand.accent") return brand.colors.accent;
  if (key === "brand.background") return brand.colors.background;
  if (key === "brand.text") return brand.colors.text;
  if (key === "brand.surface" && brand.colors.surface) return brand.colors.surface;
  
  // الخطوط
  if (key === "brand.display") return brand.fonts.display;
  if (key === "brand.body") return brand.fonts.body;
  
  // الشعار
  if (key === "brand.logo" && brand.logoSrc) return brand.logoSrc;
  
  // إذا لم يطابق الرموز المدعومة، يتم إرجاع المفتاح نفسه كما هو
  return key;
}
