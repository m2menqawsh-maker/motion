import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile } from "remotion";
import { EFFECT_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";
import { renderLiveComponent } from "../componentRegistry";

export const EffectsSection: React.FC = () => {
  const frame = useCurrentFrame();
  const framesPerItem = 45;
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    EFFECT_TEMPLATES.length - 1
  );
  const currentMeta = EFFECT_TEMPLATES[activeIndex] || EFFECT_TEMPLATES[0];
  const liveComponent = renderLiveComponent(currentMeta);

  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <ShowcaseCard meta={currentMeta}>
        <div
          style={{
            width: "100%",
            height: "100%",
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          {/* Base Background Video */}
          <video
            src={staticFile("media/video/bg_ai_final.mp4")}
            style={{
              position: "absolute",
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
            muted
            loop
            autoPlay
          />

          {/* Live Effect Component Rendered On Top */}
          {liveComponent ? (
            <div style={{ position: "absolute", inset: 0, zIndex: 15 }}>
              {liveComponent}
            </div>
          ) : (
            <div
              style={{
                position: "absolute",
                inset: 0,
                backgroundColor: "rgba(56, 189, 248, 0.15)",
                backdropFilter: "blur(6px)",
              }}
            />
          )}

          <div
            style={{
              zIndex: 20,
              padding: "24px 36px",
              borderRadius: "16px",
              backgroundColor: "rgba(6, 8, 19, 0.85)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              textAlign: "center",
              boxShadow: "0 25px 50px rgba(0,0,0,0.7)",
              pointerEvents: "none",
            }}
          >
            <div
              style={{
                fontSize: "12px",
                color: "#f472b6",
                fontWeight: 700,
                letterSpacing: "2px",
                textTransform: "uppercase",
                marginBottom: "6px",
              }}
            >
              Visual Effect Active
            </div>
            <h2 style={{ fontSize: "32px", fontWeight: 900, margin: "0 0 8px 0", color: "#ffffff" }}>
              {currentMeta.name}
            </h2>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: 0 }}>
              Family: <strong>{currentMeta.family}</strong> • Source: {currentMeta.source}
            </p>
          </div>
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Effects"
        currentIndex={activeIndex}
        totalCount={EFFECT_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
