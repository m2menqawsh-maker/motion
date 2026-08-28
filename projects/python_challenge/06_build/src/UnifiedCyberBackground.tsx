import React from "react";
import { AbsoluteFill } from "remotion";
import MatrixRain from "./templates/matrix-rain";

export const UnifiedCyberBackground: React.FC = () => {
  return (
    <AbsoluteFill
  style={{
    backgroundColor: "#060913",
    overflow: "hidden",
    pointerEvents: "none",
    zIndex: 0,
  }}
  from={-108}>
      {/* 1. Continuous Matrix Code Streams (Uninterrupted across all scenes) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.42,
          zIndex: 1,
        }}
      >
        <MatrixRain />
      </div>

      {/* 2. Global Ambient Neon Radial Halos */}
      {/* Cyan Cyber Glow (Top-Left) */}
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(0, 229, 255, 0.22) 0%, rgba(6, 9, 19, 0) 70%)",
          top: "10%",
          left: "5%",
          zIndex: 2,
        }}
      />

      {/* Deep Purple / Gold Ambient Glow (Bottom-Right) */}
      <div
        style={{
          position: "absolute",
          width: 850,
          height: 850,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(168, 85, 247, 0.18) 0%, rgba(6, 9, 19, 0) 70%)",
          bottom: "10%",
          right: "5%",
          zIndex: 2,
        }}
      />

      {/* Subtle Dark Vignette Border */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at center, transparent 40%, rgba(4, 6, 12, 0.8) 100%)",
          zIndex: 3,
        }}
      />
    </AbsoluteFill>
  );
};
