import React from "react";
import { Scene3D, Step, Element3D } from "remotion-bits";

export const Scene3DWrapper = ({ surface, content }: any) => {
  const animProps = surface?.animation || {};
  // Minimal Scene3D wrapper implementation
  // A true 3D scene would require nested elements from the blueprint, 
  // but we can render generic content mapped into 3D steps.
  
  return (
    <div style={{ width: "100%", height: "100%", backgroundColor: surface?.background || "#000" }}>
      <Scene3D
        camera={{ position: [0, 0, animProps.cameraZ || 1000] }}
        {...animProps}
      >
        <Step id="step1" position={[0, 0, 0]} rotation={[0, 0, 0]}>
          <Element3D>
             <div style={{ color: "white", fontSize: 60, fontFamily: "sans-serif" }}>
                {content?.text || surface?.text || "3D Scene"}
             </div>
          </Element3D>
        </Step>
      </Scene3D>
    </div>
  );
};
