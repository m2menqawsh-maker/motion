/**
 * الغلاف الموحد للقوالب (TemplateWrapper)
 * يضمن تطبيق عقد StyleSurface بدقة وتمريره كمخرجات موحدة للقوالب.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { useBrand, BrandKit } from "../contracts/brand";
import { usePosition } from "./position-rtl";
import { applyAnimation, AnimationContext } from "../contracts/animations";
import { applyOverride } from "./applyOverride";
import { resolveBrandToken } from "./brand-resolver";
import { useRTL } from "./useRTL";
import type { StyleSurface, AnimationId } from "../contracts/StyleSurface";

export interface TemplateWrapperProps {
  surface: StyleSurface;
  children: (resolved: ResolvedStyle) => React.ReactNode;
}

export interface ResolvedStyle {
  text: string;
  subtext?: string;
  emphasis?: string;
  fontSize: number;
  fontWeight: number | string;
  fontFamily: string;
  color: string;
  background: string;
  opacity: number;
  position: React.CSSProperties;
  animation: { progress: number; opacity: number };
  styleOverride: React.CSSProperties;
  isRTL: boolean;
}

export const TemplateWrapper: React.FC<TemplateWrapperProps> = ({ surface, children }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const brand = useBrand();
  
  // تحديد الخط وحالة الـ RTL
  const fontKey = surface.fontFamily ?? brand.fonts.display;
  const resolvedFontFamily = resolveBrandToken(fontKey, brand);
  const isRTL = useRTL(resolvedFontFamily); // RTL hook will resolve based on font
  
  // معالجة الألوان من الـ Brand Provider
  const color = resolveBrandToken(surface.color || "brand.text", brand);
  const background = resolveBrandToken(surface.background || "transparent", brand);
  
  // استخراج وتحليل المواضع
  const position = usePosition(surface.position, { w: width, h: height }, isRTL);
  
  // استخراج الحركة
  const animationCtx: AnimationContext = {
    frame,
    fps,
    delay: surface.delay,
    speed: surface.speed
  };
  const animId: AnimationId = surface.animation || "none";
  const animationResult = applyAnimation(animId, animationCtx);
  
  // تطبيق الشفافية (Opacity) المدمجة من الأنماط + الحركة
  const baseOpacity = surface.opacity !== undefined ? surface.opacity : 1;
  const finalOpacity = baseOpacity * animationResult.opacity;
  
  // تطبيق التجاوزات
  const styleOverride = applyOverride({}, surface.styleOverride);
  
  const resolved: ResolvedStyle = {
    text: surface.text || "",
    subtext: surface.subtext,
    emphasis: surface.emphasis,
    fontSize: surface.fontSize || 60,
    fontWeight: surface.fontWeight || 700,
    fontFamily: resolvedFontFamily,
    color,
    background,
    opacity: finalOpacity,
    position,
    animation: animationResult,
    styleOverride,
    isRTL,
  };
  
  return React.createElement(React.Fragment, null, children(resolved));
};
