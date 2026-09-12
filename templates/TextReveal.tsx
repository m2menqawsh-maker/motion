import React from "react";
import { TemplateWrapper } from "./TemplateWrapper";
import type { StyleSurface } from "../contracts/StyleSurface";

export interface TextRevealProps {
  surface: StyleSurface;
}

/**
 * قالب ظهور النص (Text Reveal)
 * تم بناءه بنظام الغلاف الموحد لدعم RTL والأنماط التلقائية
 */
export const TextReveal: React.FC<TextRevealProps> = ({ surface }) => {
  return (
    <TemplateWrapper surface={surface}>
      {({ text, fontSize, fontWeight, fontFamily, color, background, opacity, position, animation, styleOverride, isRTL }) => (
        <div
          style={{
            ...position,
            fontSize,
            fontWeight,
            fontFamily,
            color,
            backgroundColor: background !== "transparent" ? background : undefined,
            opacity,
            direction: isRTL ? "rtl" : "ltr",
            textAlign: isRTL ? "right" : "left",
            // تطبيق تقدم الحركة عبر Transform (كمثال لدعم Animation)
            transform: `${position.transform || ""} translateY(${(1 - animation.progress) * 20}px)`,
            ...styleOverride,
          }}
        >
          {text}
        </div>
      )}
    </TemplateWrapper>
  );
};
