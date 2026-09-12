import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile } from "remotion";
import { SCENE_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";
import { renderLiveComponent } from "../componentRegistry";

export const ScenesSection: React.FC = () => {
  const frame = useCurrentFrame();
  const framesPerItem = 60; // 2 seconds per scene card
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    SCENE_TEMPLATES.length - 1
  );
  const currentMeta = SCENE_TEMPLATES[activeIndex] || SCENE_TEMPLATES[0];
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
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#0d1117",
            overflow: "hidden",
          }}
        >
          {liveComponent ? (
            <div style={{ width: "100%", height: "100%", position: "relative" }}>
              {liveComponent}
            </div>
          ) : (
            <>
              {/* Background live video */}
              <video
                src={staticFile("media/video/coding_keyboard.mp4")}
                style={{
                  position: "absolute",
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  opacity: 0.35,
                }}
                muted
                loop
                autoPlay
              />

              {/* Scene Graphic Simulation */}
              <div
                style={{
                  zIndex: 10,
                  padding: "40px",
                  borderRadius: "20px",
                  backgroundColor: "rgba(10, 14, 26, 0.75)",
                  backdropFilter: "blur(16px)",
                  border: "1px solid rgba(56, 189, 248, 0.3)",
                  boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
                  textAlign: "center",
                  maxWidth: "600px",
                }}
              >
                <div
                  style={{
                    fontSize: "14px",
                    color: "#38bdf8",
                    fontWeight: 700,
                    letterSpacing: "2px",
                    textTransform: "uppercase",
                    marginBottom: "8px",
                  }}
                >
                  Scene Component • {currentMeta.family.toUpperCase()}
                </div>
                <h2 style={{ fontSize: "36px", fontWeight: 800, margin: "0 0 12px 0", color: "#ffffff" }}>
                  {currentMeta.name}
                </h2>
                <p style={{ fontSize: "16px", color: "#94a3b8", margin: "0 0 20px 0" }}>
                  Commercial Motion Template with dynamic layer composition and camera pacing.
                </p>
                <div
                  style={{
                    display: "inline-block",
                    padding: "8px 20px",
                    borderRadius: "8px",
                    backgroundColor: "rgba(56, 189, 248, 0.15)",
                    color: "#38bdf8",
                    fontSize: "14px",
                    fontWeight: 600,
                    border: "1px solid rgba(56, 189, 248, 0.4)",
                  }}
                >
                  Live Scene Active
                </div>
              </div>
            </>
          )}
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Scenes"
        currentIndex={activeIndex}
        totalCount={SCENE_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
