/**
 * فاحص التجاوزات (Override Validator)
 * للتحقق من أمان وصحة خصائص styleOverride المرسلة في المشاهد
 */

const ALLOWED_KEYS = new Set([
  "borderRadius",
  "boxShadow",
  "textShadow",
  "filter",
  "backdropFilter",
  "border",
  "borderColor",
  "borderWidth",
  "textStroke",
  "textStrokeWidth",
  "padding",
  "gap"
]);

/**
 * فحص تجاوزات الأنماط للتحقق من توافقها مع القائمة البيضاء وأمانها
 * @param obj الكائن المراد فحصه
 * @returns نتيجة الفحص تتضمن حالة الموافقة وقائمة الأخطاء
 */
export function validateStyleOverride(obj: unknown): { ok: boolean; errors: string[] } {
  const errors: string[] = [];

  // 1. يجب أن يكون كائنًا
  if (typeof obj !== "object" || obj === null) {
    return { ok: false, errors: ["styleOverride must be a valid object"] };
  }

  const entries = Object.entries(obj);
  for (const [key, value] of entries) {
    // 2. التحقق من وجود المفتاح في القائمة البيضاء
    if (!ALLOWED_KEYS.has(key)) {
      errors.push(`Key '${key}' is not allowed in styleOverride`);
    }

    // 3. القيم يجب أن تكون نصوص أو أرقام فقط
    if (typeof value !== "string" && typeof value !== "number") {
      errors.push(`Value for '${key}' must be a string or a number`);
      continue;
    }

    // 4. حظر القيم الخطيرة للوقاية من الحقن
    if (typeof value === "string") {
      const lower = value.toLowerCase();
      if (lower.includes("javascript:") || lower.includes("expression(") || lower.includes("url(")) {
        errors.push(`Value for '${key}' contains dangerous content`);
      }
    }
  }

  return { ok: errors.length === 0, errors };
}
