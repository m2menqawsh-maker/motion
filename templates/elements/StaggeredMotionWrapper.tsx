import React from "react";
import { StaggeredMotion } from "remotion-bits";

export const StaggeredMotionWrapper = ({ surface, content }: any) => {
  const animProps = surface?.animation || {};
  // Render dummy children for staggered motion based on text lines or images
  const items = content?.lines || content?.images || ["Item 1", "Item 2", "Item 3"];

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <StaggeredMotion
        staggerDuration={animProps.staggerDuration || 15}
        {...animProps}
      >
        {items.map((item: string, i: number) => (
          <div key={i} style={{ 
            fontSize: surface?.fontSize || 40, 
            color: surface?.color || "#fff",
            marginBottom: 20,
            padding: 20,
            backgroundColor: surface?.background || "rgba(255,255,255,0.1)",
            borderRadius: 10
          }}>
            {item}
          </div>
        ))}
      </StaggeredMotion>
    </div>
  );
};
