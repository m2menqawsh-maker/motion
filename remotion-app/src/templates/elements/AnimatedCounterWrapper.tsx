import React from "react";
import { AnimatedCounter } from "remotion-bits";

export const AnimatedCounterWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const targetValue = content?.number || surface?.value || 1000;
  const startValue = surface?.startValue || 0;
  const animProps = surface?.animation || {};

  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <AnimatedCounter
 {...template_props}         from={startValue}
        to={targetValue}
        prefix={surface?.prefix || ""}
        suffix={surface?.suffix || ""}
        {...animProps}
        style={{
          color: surface?.color || "#fff",
          fontSize: surface?.fontSize || 120,
          fontWeight: "bold",
          fontFamily: surface?.fontFamily || "sans-serif",
        }}
      />
    </div>
  </div>
  );
};
