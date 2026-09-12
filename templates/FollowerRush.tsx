import React from "react";
import { TemplateWrapper } from "./TemplateWrapper";
import type { StyleSurface } from "../contracts/StyleSurface";
import type { SceneContent } from "../contracts/SceneContent";

export interface FollowerRushProps {
  surface: StyleSurface;
  content?: SceneContent;
}

export const FollowerRush: React.FC<FollowerRushProps> = ({ surface, content }) => {
  return (
    <TemplateWrapper surface={surface}>
      {({ text, fontSize, fontWeight, fontFamily, color, background, opacity, position, animation, styleOverride, isRTL, subtext, emphasis }) => (
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
            transform: `${position.transform || ""} scale(${animation.progress})`,
            ...styleOverride,
          }}
        >
          <div>{text}</div>
          {subtext && <div>{subtext}</div>}
          {emphasis && <div>{emphasis}</div>}
          {content?.lines && <div>{content.lines.join(", ")}</div>}
          {content?.words && <div>{content.words.length} words</div>}
          {content?.images && <div>{content.images.length} images</div>}
          {content?.screen && <div>Screen: {content.screen}</div>}
        </div>
      )}
    </TemplateWrapper>
  );
};
