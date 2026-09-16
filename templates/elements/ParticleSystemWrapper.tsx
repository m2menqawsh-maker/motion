import React from "react";
import { Particles, Spawner, Behavior } from "remotion-bits";

export const ParticleSystemWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const animProps = surface?.animation || {};
  const particleCount = animProps.count || 100;
  const B: any = Behavior;
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0, backgroundColor: surface?.background || "#000" }}>
      <Particles>
        <Spawner  {...template_props} rate={particleCount} />
        <B.Gravity force={animProps.gravity || 9.8} />
        <B.Drag friction={animProps.friction || 0.1} />
      </Particles>
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center", color: surface?.color || "white", fontFamily: surface?.fontFamily || "sans-serif", direction: "rtl", width: "80%" }}>
         <div style={{ fontSize: surface?.fontSize || 60, fontWeight: "bold" }}>{surface?.text || content?.lines?.[0]}</div>
         <div style={{ fontSize: (surface?.fontSize || 60) * 0.6, marginTop: 20 }}>{surface?.subtext || content?.lines?.[1]}</div>
      </div>
    </div>
  );
};
