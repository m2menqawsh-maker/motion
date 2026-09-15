import React from "react";
import { MatrixRain } from "remotion-bits";

export const MatrixRainWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const animProps = surface?.animation || {};
  
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0, backgroundColor: surface?.background || "#000" }}>
      <MatrixRain
 {...template_props}         color={surface?.color || "#00ff00"}
        {...animProps}
      />
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center", color: "white", fontFamily: surface?.fontFamily || "sans-serif", direction: "rtl", width: "80%" }}>
         <div style={{ fontSize: surface?.fontSize || 60, fontWeight: "bold", color: surface?.color || "#00ff00" }}>{surface?.text || content?.lines?.[0]}</div>
         <div style={{ fontSize: (surface?.fontSize || 60) * 0.6, marginTop: 20 }}>{surface?.subtext || content?.lines?.[1]}</div>
      </div>
    </div>
  );
};
