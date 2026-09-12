import React from "react";
import { AbsoluteFill, staticFile } from "remotion";
import { ShowcaseCard } from "../ShowcaseCard";

export const AssetsSection: React.FC = () => {
  const readyIcons = [
    "bookmark.svg", "bot.svg", "brain.svg", "calculator.svg",
    "code.svg", "database.svg", "laptop.svg", "moon.svg",
    "python.svg", "repeat.svg", "success.svg", "telegram.svg"
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "#060813" }}>
      <ShowcaseCard
        meta={{
          id: "assets/ready",
          name: "Ready Local Assets Gallery",
          type: "element",
          family: "assets",
          quality: "A",
          status: "verified",
          rtl_ready: true,
          source: "local-first",
          path: "assets/ready/",
          use_cases: ["b-roll", "sfx", "music", "icons"],
          intents: ["asset_management"],
          moods: ["premium"],
          capabilities: ["zero-download", "cached-locally"],
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "24px",
            padding: "32px",
            boxSizing: "border-box",
            backgroundColor: "#070b14",
          }}
        >
          {/* Video Assets Box */}
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.6)",
              borderRadius: "16px",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h3 style={{ margin: "0 0 12px 0", fontSize: "18px", color: "#38bdf8" }}>
              🎬 Local Video Assets (assets/ready/video/)
            </h3>
            <div style={{ flex: 1, position: "relative", borderRadius: "10px", overflow: "hidden" }}>
              <video
                src={staticFile("media/video/coding_keyboard.mp4")}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                muted
                loop
                autoPlay
              />
              <div
                style={{
                  position: "absolute",
                  bottom: "10px",
                  left: "10px",
                  backgroundColor: "rgba(0,0,0,0.7)",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  color: "#e2e8f0",
                }}
              >
                coding_keyboard.mp4 (All-Intra)
              </div>
            </div>
          </div>

          {/* SVG Icons Box */}
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.6)",
              borderRadius: "16px",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h3 style={{ margin: "0 0 12px 0", fontSize: "18px", color: "#a78bfa" }}>
              🎨 Rich SVG Badges (assets/ready/icons/)
            </h3>
            <div
              style={{
                flex: 1,
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "12px",
                alignContent: "center",
              }}
            >
              {readyIcons.map((icon, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    padding: "10px",
                    backgroundColor: "rgba(255, 255, 255, 0.04)",
                    borderRadius: "8px",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                  }}
                >
                  <img
                    src={staticFile(`media/icons/${icon}`)}
                    style={{ width: "32px", height: "32px" }}
                    alt={icon}
                  />
                  <span style={{ fontSize: "10px", color: "#94a3b8", marginTop: "4px" }}>
                    {icon.replace(".svg", "")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ShowcaseCard>
    </AbsoluteFill>
  );
};
