import React from "react";
import { GradientTransition } from "remotion-bits";

export const GradientWrapper = ({ surface, template_props = {} }: any) => {
  const animProps = surface?.animation || {};
  
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      <GradientTransition
 {...template_props}         type={animProps.type || "linear"}
        colors={surface?.colors || ["#ff0000", "#0000ff"]}
        {...animProps}
      />
    </div>
  </div>
  );
};
