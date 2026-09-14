import React from "react";
import { MatrixRain } from "remotion-bits";

export const MatrixRainWrapper = ({ surface }: any) => {
  const animProps = surface?.animation || {};
  
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      <MatrixRain
        color={surface?.color || "#00ff00"}
        {...animProps}
      />
    </div>
  );
};
