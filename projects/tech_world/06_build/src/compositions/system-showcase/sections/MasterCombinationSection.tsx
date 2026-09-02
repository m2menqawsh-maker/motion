import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile, interpolate } from "remotion";
import { ShowcaseCard } from "../ShowcaseCard";

export const MasterCombinationSection: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 150], [1, 1.15], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <ShowcaseCard
        meta={{
          id: "master/composite",
          name: "Master Showcase Composition",
          type: "scene",
          family: "core",
          quality: "A",
          status: "verified",
          rtl_ready: true,
          source: "pipeline-orchestrator",
          path: "remotion-app/src/compositions/system-showcase/MasterCombinationSection.tsx",
          use_cases: ["commercial", "product-reveal", "full-pipeline"],
          intents: ["full_combination"],
          moods: ["cinematic", "dynamic"],
          capabilities: ["camera-rig", "ken-burns", "arabic-captions", "audio-sync", "effects"],
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            position: "relative",
            overflow: "hidden",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Layer 1: Background Video with KenBurns Zoom */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              transform: `scale(${zoom})`,
              transition: "transform 0.1s ease-out",
            }}
          >
            <video
              src={staticFile("media/video/bg_code_final.mp4")}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              muted
              loop
              autoPlay
            />
          </div>

          {/* Layer 2: Cyber Overlay Gradient */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "linear-gradient(135deg, rgba(6, 8, 19, 0.85) 0%, rgba(15, 23, 42, 0.6) 100%)",
            }}
          />

          {/* Layer 3: Glassmorphism Master Card */}
          <div
            style={{
              zIndex: 20,
              padding: "48px",
              borderRadius: "24px",
              backgroundColor: "rgba(10, 14, 26, 0.75)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              boxShadow: "0 30px 60px rgba(0,0,0,0.8)",
              textAlign: "center",
              maxWidth: "720px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 16px",
                borderRadius: "999px",
                backgroundColor: "rgba(56, 189, 248, 0.15)",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                color: "#38bdf8",
                fontSize: "13px",
                fontWeight: 700,
                letterSpacing: "1px",
              }}
            >
              <span>⭐</span>
              <span>FULL COMPOSITION ASSEMBLED</span>
            </div>

            <h1
              style={{
                fontSize: "48px",
                fontWeight: 900,
                margin: 0,
                background: "linear-gradient(135deg, #ffffff 0%, #38bdf8 60%, #a855f7 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Clean Video Pipeline
            </h1>

            {/* Arabic Caption Pill */}
            <div
              style={{
                direction: "rtl",
                padding: "12px 28px",
                borderRadius: "12px",
                backgroundColor: "rgba(168, 85, 247, 0.12)",
                border: "1px solid rgba(168, 85, 247, 0.3)",
                color: "#f8fafc",
                fontSize: "20px",
                fontWeight: 700,
                fontFamily: "'Cairo', system-ui, sans-serif",
              }}
            >
              تكامل كامل للأصول والمحرك السينمائي والقوالب في مشهد موحد
            </div>

            {/* Stack Tags */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center" }}>
              {["Remotion 4", "React 19", "CameraRig", "KenBurns", "RTL Engine", "Local Assets", "Probe QC"].map(
                (tag, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: "12px",
                      color: "#94a3b8",
                      backgroundColor: "rgba(255, 255, 255, 0.05)",
                      padding: "4px 10px",
                      borderRadius: "6px",
                    }}
                  >
                    ✓ {tag}
                  </span>
                )
              )}
            </div>
          </div>
        </div>
      </ShowcaseCard>
    </AbsoluteFill>
  );
};
