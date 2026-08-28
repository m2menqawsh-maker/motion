import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const FadeOut: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
}> = ({ children, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { durationInFrames: sequenceDuration } = useVideoConfig();

  // Fade out starts `durationInFrames` before the sequence ends
  const opacity = interpolate(
    frame,
    [sequenceDuration - durationInFrames, sequenceDuration],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return <div style={{ flex: 1, width: "100%", height: "100%", opacity }}>{children}</div>;
};
