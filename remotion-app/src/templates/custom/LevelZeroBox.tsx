import React from "react";
import { z } from "zod";

export const schema = z.object({
  glowColor: z.string().optional(),
  borderWidth: z.number().optional()
});

export const LevelZeroBox = ({ surface, content, template_props }: any) => {
  const glow = template_props?.glowColor || "#0ff";
  const border = template_props?.borderWidth || 4;

  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", justifyContent: "center", alignItems: "center",
      backgroundColor: surface?.background || "#000"
    }}>
      <div style={{
        padding: 40,
        border: `${border}px solid ${glow}`,
        boxShadow: `0 0 40px ${glow}`,
        borderRadius: 20,
        color: surface?.color || "#fff",
        fontSize: surface?.fontSize || 60,
        fontFamily: surface?.fontFamily || "sans-serif"
      }}>
        {surface?.text || "Level 0 Custom Component"}
        {content?.text && <p style={{fontSize: 30}}>{content.text}</p>}
      </div>
    </div>
  );
};
