import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TRANSITION_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";

export const TransitionsSection: React.FC = () => {
  const frame = useCurrentFrame();
  const framesPerItem = 60; // 2 seconds per transition
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    TRANSITION_TEMPLATES.length - 1
  );
  const currentMeta = TRANSITION_TEMPLATES[activeIndex] || TRANSITION_TEMPLATES[0];

  const localFrame = frame % framesPerItem;
  const progress = interpolate(localFrame, [10, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <ShowcaseCard meta={currentMeta}>
        <div
          style={{
            width: "100%",
            height: "100%",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Scene A (Outgoing) */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "#1e1b4b",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              opacity: 1 - progress,
              transform: `scale(${1 - progress * 0.1})`,
            }}
          >
            <span style={{ fontSize: "16px", color: "#a5b4fc", fontWeight: 700, letterSpacing: "2px" }}>
              OUTGOING
            </span>
            <h1 style={{ fontSize: "56px", fontWeight: 900, color: "#ffffff", margin: "10px 0" }}>
              SCENE A
            </h1>
            <p style={{ color: "#c7d2fe", fontSize: "18px" }}>Primary Hook Sequence</p>
          </div>

          {/* Scene B (Incoming) */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "#064e3b",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              opacity: progress,
              transform: `scale(${0.9 + progress * 0.1})`,
            }}
          >
            <span style={{ fontSize: "16px", color: "#6ee7b7", fontWeight: 700, letterSpacing: "2px" }}>
              INCOMING
            </span>
            <h1 style={{ fontSize: "56px", fontWeight: 900, color: "#ffffff", margin: "10px 0" }}>
              SCENE B
            </h1>
            <p style={{ color: "#a7f3d0", fontSize: "18px" }}>Feature Reveal Sequence</p>
          </div>

          {/* Transition Visual Indicator */}
          <div
            style={{
              position: "absolute",
              bottom: "32px",
              left: "50%",
              transform: "translateX(-50%)",
              backgroundColor: "rgba(0,0,0,0.8)",
              backdropFilter: "blur(12px)",
              padding: "10px 24px",
              borderRadius: "999px",
              border: "1px solid rgba(255,255,255,0.2)",
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <span style={{ color: "#fbbf24", fontWeight: 700, fontSize: "14px" }}>
              Transition: {currentMeta.name}
            </span>
            <div
              style={{
                width: "120px",
                height: "6px",
                backgroundColor: "rgba(255,255,255,0.2)",
                borderRadius: "3px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${progress * 100}%`,
                  height: "100%",
                  backgroundColor: "#fbbf24",
                }}
              />
            </div>
            <span style={{ color: "#94a3b8", fontSize: "12px", fontFamily: "monospace" }}>
              {Math.round(progress * 100)}%
            </span>
          </div>
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Transitions"
        currentIndex={activeIndex}
        totalCount={TRANSITION_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
