/**
 * RTL Hook
 * يحدد ما إذا كان النص يجب أن يعرض من اليمين لليسار (RTL) بناءً على الخط المستخدم.
 */

import { isRTL } from "../contracts/fonts";
import type { FontKey } from "../contracts/StyleSurface";

/**
 * يحدد اتجاه النص بناءً على الخط
 * @param fontFamily اسم الخط (FontKey) أو مفتاح آخر
 * @returns قيمة منطقية، true إذا كان RTL
 */
export function useRTL(fontFamily: string | undefined): boolean {
  if (!fontFamily) return true; // الافتراضي RTL لدعم اللغة العربية
  
  // نفترض أن fontFamily هو FontKey، الدالة isRTL ستتعامل معه أو ترجع false
  return isRTL(fontFamily as FontKey);
}
