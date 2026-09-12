import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { TYPOGRAPHY_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";
import { renderLiveComponent } from "../componentRegistry";

export const TypographySection: React.FC = () => {
  const frame = useCurrentFrame();
  const framesPerItem = 45;
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    TYPOGRAPHY_TEMPLATES.length - 1
  );
  const currentMeta = TYPOGRAPHY_TEMPLATES[activeIndex] || TYPOGRAPHY_TEMPLATES[0];
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
            padding: "48px",
            background: "radial-gradient(circle at center, #18181b 0%, #09090b 100%)",
            gap: "24px",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Live Component Animation */}
          {liveComponent ? (
            <div style={{ width: "100%", height: "240px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {liveComponent}
            </div>
          ) : (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "44px", fontWeight: 900, color: "#ffffff" }}>
                BUILD SOMETHING GREAT
              </div>
            </div>
          )}

          {/* Arabic RTL Typography Sample */}
          <div
            style={{
              textAlign: "center",
              direction: "rtl",
              padding: "16px 36px",
              borderRadius: "14px",
              backgroundColor: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(168, 85, 247, 0.2)",
              width: "80%",
              maxWidth: "640px",
              zIndex: 10,
            }}
          >
            <div style={{ fontSize: "12px", color: "#c084fc", fontWeight: 700, letterSpacing: "1px", marginBottom: "6px" }}>
              اختبار النصوص العربية والـ RTL
            </div>
            <div
              style={{
                fontSize: "28px",
                fontWeight: 800,
                color: "#f8fafc",
                lineHeight: 1.4,
                fontFamily: "'Cairo', 'Alexandria', system-ui, sans-serif",
              }}
            >
              هذا نص عربي تجريبي داخل المحرك
            </div>
          </div>
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Typography & RTL"
        currentIndex={activeIndex}
        totalCount={TYPOGRAPHY_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
