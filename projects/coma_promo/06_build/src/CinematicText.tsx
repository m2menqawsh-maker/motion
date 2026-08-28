"use client";

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";

export type CinematicTextProps = {
  text: React.ReactNode;
  color?: string;
  fontSize?: string;
  fontFamily?: string;
};

export default function CinematicText({ 
  text, 
  color = "white",
  fontSize = "8rem",
  fontFamily = "Tajawal, sans-serif"
}: CinematicTextProps) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Cinematic fade in (smooth)
  const opacity = interpolate(frame, [0, fps * 1.5], [0, 1], {
    easing: Easing.out(Easing.ease),
    extrapolateRight: "clamp",
  });

  // Smooth slide up
  const translateY = interpolate(frame, [0, fps * 1.5], [30, 0], {
    easing: Easing.out(Easing.ease),
    extrapolateRight: "clamp",
  });

  // Cinematic slow scale in (continuous zoom over the whole duration)
  const scale = interpolate(frame, [0, durationInFrames], [0.95, 1.05]);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        dir="rtl" // Support Arabic
        style={{
          display: "flex",
          justifyContent: "center",
          maxWidth: "90%",
          textAlign: "center",
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
        }}
      >
        <span
          style={{
            color,
            fontSize,
            fontFamily,
            fontWeight: "bold",
            lineHeight: 1.4,
            textShadow: "0px 10px 30px rgba(0,0,0,0.15)"
          }}
        >
          {text}
        </span>
      </div>
    </div>
  );
}
