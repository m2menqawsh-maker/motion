import React from "react";
import { Composition } from "remotion";
import "./rtl.css";

// This is a placeholder Root until BlueprintVideo is integrated.
const Placeholder: React.FC = () => (
  <div style={{ flex: 1, backgroundColor: "black", color: "white", display: "flex", justifyContent: "center", alignItems: "center", fontSize: 40, fontFamily: "sans-serif" }}>
    Blueprint Video Not Loaded
  </div>
);

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={Placeholder}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
