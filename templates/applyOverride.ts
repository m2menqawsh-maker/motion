/**
 * دالة تطبيق التجاوزات (Apply Override)
 * تقوم بفحص وتطبيق خصائص styleOverride بأمان على الأنماط الأساسية
 */

import React from "react";
import { validateStyleOverride } from "../contracts/override-validator";

/**
 * تطبيق التجاوزات على الأنماط الأساسية
 * @param base الأنماط الأساسية (كائن CSSProperties)
 * @param override التجاوزات القادمة من الواجهة/الخطة
 * @returns كائن الأنماط مدمجاً بأمان
 */
export function applyOverride(base: React.CSSProperties, override: unknown): React.CSSProperties {
  if (!override || typeof override !== "object") return base;

  const safeOverride: Record<string, any> = {};
  for (const [key, value] of Object.entries(override)) {
    const check = validateStyleOverride({ [key]: value });
    if (check.ok) {
      safeOverride[key] = value;
    } else {
      console.warn(`Ignoring invalid override key: ${key}`, check.errors);
    }
  }
  
  return { ...base, ...safeOverride };
}
