import React from "react";
import { TemplateWrapper } from "./TemplateWrapper";
import type { StyleSurface } from "../contracts/StyleSurface";

export interface KaraokeCaptionsProps {
  surface: StyleSurface;
}

/**
 * قالب كابشن كاريوكي (Karaoke Captions)
 * يستفيد من الألوان المهيأة والأنماط من الغلاف الموحد
 */
export const KaraokeCaptions: React.FC<KaraokeCaptionsProps> = ({ surface }) => {
  return (
    <TemplateWrapper surface={surface}>
      {({ text, fontSize, fontWeight, fontFamily, color, opacity, position, animation, styleOverride, isRTL }) => {
        // محاكاة تقسيم الكلمات وعرضها بالكاريوكي باستخدام progress للحركة
        const words = text.split(" ");
        const progressIndex = Math.floor(animation.progress * words.length);

        return (
          <div
            style={{
              ...position,
              fontSize,
              fontWeight,
              fontFamily,
              color,
              opacity,
              direction: isRTL ? "rtl" : "ltr",
              textAlign: isRTL ? "right" : "left",
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5em",
              ...styleOverride,
            }}
          >
            {words.map((word, i) => (
              <span
                key={i}
                style={{
                  color: i <= progressIndex ? color : "rgba(128, 128, 128, 0.5)",
                  transition: "color 0.1s ease",
                }}
              >
                {word}
              </span>
            ))}
          </div>
        );
      }}
    </TemplateWrapper>
  );
};
