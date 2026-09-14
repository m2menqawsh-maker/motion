import React from "react";
import { Particles, Spawner, Behavior } from "remotion-bits";

export const ParticleSystemWrapper = ({ surface }: any) => {
  const animProps = surface?.animation || {};
  const particleCount = animProps.count || 100;
  
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      <Particles>
        <Spawner rate={particleCount} />
        <Behavior.Gravity force={animProps.gravity || 9.8} />
        <Behavior.Drag friction={animProps.friction || 0.1} />
        {/* We can map generic behaviors based on animProps if needed */}
      </Particles>
    </div>
  );
};
