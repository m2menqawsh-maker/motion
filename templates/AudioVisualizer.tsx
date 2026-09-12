import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { StyleSurface } from "../contracts/StyleSurface";
import type { SceneContent } from "../contracts/SceneContent";

export interface AudioVisualizerProps {
  surface: StyleSurface;
  content: SceneContent;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ surface, content }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Use pre-calculated spectrum
  const spectrum = content.spectrum || [];
  
  // Deterministic fallbacks if no spectrum is provided (e.g. preview)
  const currentBands = spectrum[frame % Math.max(1, spectrum.length)] || new Array(16).fill(0.1);
  
  const color = surface.color || "#00FF00";
  const opacity = surface.opacity ?? 1;

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-end",
        justifyContent: "center",
        gap: "4px",
        padding: "20px",
        opacity,
      }}
    >
      {currentBands.map((val, i) => (
        <div
          key={i}
          style={{
            width: "20px",
            height: `${Math.max(5, val * 100)}%`,
            backgroundColor: color,
            borderRadius: "10px 10px 0 0",
            transition: "height 0.1s ease",
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
