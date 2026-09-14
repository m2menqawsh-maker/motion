import React from "react";
import { AnimatedText } from "remotion-bits";

export const AnimatedTextWrapper = ({ surface, content }: any) => {
  // text comes from content.text or surface.text
  const text = content?.text || surface?.text || "REMOTION BITS";
  const animProps = surface?.animation || {};

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <AnimatedText
        transition={{
          ...animProps
        }}
        style={{
          color: surface?.color || "#fff",
          fontSize: surface?.fontSize || 80,
          fontWeight: "bold",
          fontFamily: surface?.fontFamily || "monospace",
          textAlign: "center"
        }}
      >
        {text}
      </AnimatedText>
    </div>
  );
};
