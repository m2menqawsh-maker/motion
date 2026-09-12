import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile } from "remotion";
import { ELEMENT_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";
import { renderLiveComponent } from "../componentRegistry";

export const ElementsSection: React.FC = () => {
  const frame = useCurrentFrame();
  const framesPerItem = 45; // 1.5s per item
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    ELEMENT_TEMPLATES.length - 1
  );
  const currentMeta = ELEMENT_TEMPLATES[activeIndex] || ELEMENT_TEMPLATES[0];
  const liveComponent = renderLiveComponent(currentMeta);

  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <ShowcaseCard meta={currentMeta}>
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
            background: "radial-gradient(circle at center, #111827 0%, #030712 100%)",
          }}
        >
          {liveComponent ? (
            <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {liveComponent}
            </div>
          ) : (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "42px", fontWeight: 800, color: "#ffffff", marginBottom: "12px" }}>
                {currentMeta.name}
              </div>
              <div style={{ fontSize: "20px", color: "#a855f7", fontWeight: 600 }}>
                {currentMeta.family.toUpperCase()} Element Primitive
              </div>
            </div>
          )}
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Elements"
        currentIndex={activeIndex}
        totalCount={ELEMENT_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
