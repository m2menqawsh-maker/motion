"use client";

import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export type AnimatedTextProps = {
  text: string;
  entrance_direction?: "up" | "down" | "left" | "right";
  camera_track?: "pan_right" | "pan_left" | "zoom_in" | "zoom_out";
  color?: string;
  fontSize?: string;
};

export default function AnimatedText({ 
  text = "نص تجريبي", 
  entrance_direction = "up",
  camera_track,
  color = "white",
  fontSize = "5rem"
}: AnimatedTextProps) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = text.split(" ");

  // DYNAMIC_MONTAGE_PLAYBOOK: camera_track influences entrance
  // If camera is panning right, text might enter from left to create parallax
  let effective_entrance = entrance_direction;
  if (camera_track === "pan_right") effective_entrance = "left";
  if (camera_track === "pan_left") effective_entrance = "right";
  if (camera_track === "zoom_in") effective_entrance = "down";

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
          flexWrap: "wrap", // Prevent breaking text
          justifyContent: "center",
          gap: "1rem",
          maxWidth: "80%",
          textAlign: "center",
        }}
      >
        {words.map((word, wIdx) => {
          const delay = wIdx * 3; // Word stagger

          const opacity = spring({
            frame: frame - delay,
            fps,
            from: 0,
            to: 1,
            config: { mass: 0.5, damping: 10 },
          });

          let fromX = 0;
          let fromY = 0;

          if (effective_entrance === "up") fromY = 50;
          if (effective_entrance === "down") fromY = -50;
          if (effective_entrance === "left") fromX = -50;
          if (effective_entrance === "right") fromX = 50;

          const x = spring({
            frame: frame - delay,
            fps,
            from: fromX,
            to: 0,
            config: { mass: 0.5, damping: 10 },
          });

          const y = spring({
            frame: frame - delay,
            fps,
            from: fromY,
            to: 0,
            config: { mass: 0.5, damping: 10 },
          });

          return (
            <span
              key={wIdx}
              style={{
                display: "inline-block",
                opacity,
                color,
                fontSize,
                fontWeight: "bold",
                transform: `translate(${x}px, ${y}px)`,
                textShadow: "0px 4px 10px rgba(0,0,0,0.5)"
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
    </div>
  );
}
