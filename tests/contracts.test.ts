import { describe, it, expect } from "vitest";
import { validateStyleSurface } from "../contracts/StyleSurface";
import { validateStyleOverride } from "../contracts/override-validator";
import { assertFontKey } from "../contracts/fonts";
import { ANIMATION_REGISTRY, applyAnimation, AnimationContext } from "../contracts/animations";

describe("Contracts Module", () => {
  // 1. StyleSurface سليمة تمر validateStyleSurface
  it("validates a correct StyleSurface object", () => {
    const validSurface = {
      text: "اختبار",
      fontSize: 24,
      lineHeight: 1.5,
      opacity: 0.8,
      speed: 1
    };
    const result = validateStyleSurface(validSurface);
    expect(result.ok).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  // 2. styleOverride بمفتاح zIndex يُرفض
  it("rejects styleOverride with disallowed key 'zIndex'", () => {
    const result = validateStyleOverride({ zIndex: 10 });
    expect(result.ok).toBe(false);
    expect(result.errors[0]).toMatch(/not allowed/);
  });

  // 3. styleOverride بمفتاح onclick يُرفض (قائمة بيضاء)
  it("rejects styleOverride with disallowed key 'onclick'", () => {
    const result = validateStyleOverride({ onclick: "alert('hi')" });
    expect(result.ok).toBe(false);
    expect(result.errors[0]).toMatch(/not allowed/);
  });

  // 4. styleOverride بقيمة "javascript:..." يُرفض (filter dangerous)
  it("rejects dangerous content in styleOverride values", () => {
    const result = validateStyleOverride({ filter: "javascript:alert(1)" });
    expect(result.ok).toBe(false);
    expect(result.errors[0]).toMatch(/dangerous content/);
  });

  // 5. assertFontKey("Cairo") ينجح
  it("assertFontKey successfully validates a correct font key", () => {
    expect(assertFontKey("Cairo")).toBe("Cairo");
  });

  // 6. assertFontKey("Comic Sans") يرمي
  it("assertFontKey throws on invalid font key", () => {
    expect(() => assertFontKey("Comic Sans")).toThrow(/Invalid font key/);
  });

  // 7. ANIMATION_REGISTRY يحتوي 13 قيمة بالضبط
  it("ANIMATION_REGISTRY contains exactly 13 animations", () => {
    expect(Object.keys(ANIMATION_REGISTRY)).toHaveLength(13);
  });

  // 8. applyAnimation("none", ctx) يرجع {progress:1, opacity:1}
  it("applyAnimation returns {progress:1, opacity:1} for 'none'", () => {
    const ctx: AnimationContext = { frame: 10, fps: 30 };
    const res = applyAnimation("none", ctx);
    expect(res).toEqual({ progress: 1, opacity: 1 });
  });

  // 9. applyAnimation("fade_in", ctx with frame=0) opacity=0
  it("applyAnimation 'fade_in' starts with opacity 0 at frame 0", () => {
    const ctx: AnimationContext = { frame: 0, fps: 30 };
    const res = applyAnimation("fade_in", ctx);
    expect(res.opacity).toBe(0);
  });

  // 10. applyAnimation("fade_in", ctx with frame=100) opacity=1
  it("applyAnimation 'fade_in' ends with opacity 1 at frame 100", () => {
    const ctx: AnimationContext = { frame: 100, fps: 30 };
    const res = applyAnimation("fade_in", ctx);
    expect(res.opacity).toBe(1);
  });
});
