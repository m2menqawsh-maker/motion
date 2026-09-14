import React from "react";
import { GradientTransition } from "remotion-bits";

export const GradientWrapper = ({ surface }: any) => {
  const animProps = surface?.animation || {};
  
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      <GradientTransition
        type={animProps.type || "linear"}
        colors={surface?.colors || ["#ff0000", "#0000ff"]}
        {...animProps}
      />
    </div>
  );
};
