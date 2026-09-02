import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  TOTAL_TEMPLATES_COUNT,
  SCENE_TEMPLATES,
  ELEMENT_TEMPLATES,
  EFFECT_TEMPLATES,
  ENGINE_TEMPLATES,
  TRANSITION_TEMPLATES,
} from "../registry";

export const IntroSection: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: { damping: 14 } });
  const countScale = interpolate(titleProgress, [0, 1], [0.8, 1]);
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#060813",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color: "#f8fafc",
        fontFamily: "'Inter', system-ui, sans-serif",
        opacity,
        padding: "40px",
        overflow: "hidden",
      }}
    >
      {/* Background Cyber Grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(to right, rgba(56, 189, 248, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(56, 189, 248, 0.05) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          pointerEvents: "none",
        }}
      />

      {/* Glowing Orb */}
      <div
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(56, 189, 248, 0.15) 0%, rgba(99, 102, 241, 0.08) 50%, transparent 70%)",
          filter: "blur(40px)",
          pointerEvents: "none",
        }}
      />

      {/* Main Title Badge */}
      <div
        style={{
          transform: `scale(${countScale})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          zIndex: 10,
        }}
      >
        <div
          style={{
            padding: "6px 18px",
            borderRadius: "999px",
            backgroundColor: "rgba(56, 189, 248, 0.12)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            color: "#38bdf8",
            fontSize: "14px",
            fontWeight: 700,
            letterSpacing: "2px",
            textTransform: "uppercase",
            marginBottom: "20px",
          }}
        >
          Clean Video Workspace • Studio Gallery
        </div>

        <h1
          style={{
            fontSize: "72px",
            fontWeight: 900,
            letterSpacing: "-2px",
            margin: "0 0 12px 0",
            background: "linear-gradient(135deg, #ffffff 0%, #38bdf8 50%, #818cf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            textAlign: "center",
          }}
        >
          FULL SYSTEM SHOWCASE
        </h1>

        <p
          style={{
            fontSize: "22px",
            color: "#94a3b8",
            margin: "0 0 40px 0",
            maxWidth: "700px",
            textAlign: "center",
            lineHeight: "1.5",
          }}
        >
          Comprehensive Live Preview of all {TOTAL_TEMPLATES_COUNT}+ Templates, Scenes, Elements,
          Effects, Engine Primitives & Transitions.
        </p>

        {/* Stats Row */}
        <div style={{ display: "flex", gap: "24px", marginTop: "10px" }}>
          {[
            { label: "Total Catalog", value: TOTAL_TEMPLATES_COUNT, color: "#38bdf8" },
            { label: "Scenes", value: SCENE_TEMPLATES.length, color: "#34d399" },
            { label: "Elements", value: ELEMENT_TEMPLATES.length, color: "#a78bfa" },
            { label: "Effects & Motion", value: EFFECT_TEMPLATES.length, color: "#f472b6" },
            { label: "Transitions", value: TRANSITION_TEMPLATES.length, color: "#fbbf24" },
            { label: "Cinematic Engine", value: ENGINE_TEMPLATES.length, color: "#60a5fa" },
          ].map((stat, i) => (
            <div
              key={i}
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.8)",
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "14px",
                padding: "16px 24px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                minWidth: "120px",
              }}
            >
              <span style={{ fontSize: "36px", fontWeight: 800, color: stat.color }}>
                {stat.value}
              </span>
              <span style={{ fontSize: "12px", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
