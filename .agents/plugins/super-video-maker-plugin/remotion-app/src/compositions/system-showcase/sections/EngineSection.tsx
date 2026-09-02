import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { ENGINE_TEMPLATES } from "../registry";
import { ShowcaseCard } from "../ShowcaseCard";
import { DebugOverlay } from "../DebugOverlay";

export const EngineSection: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const framesPerItem = 60; // 2 seconds per item
  const activeIndex = Math.min(
    Math.floor(frame / framesPerItem),
    ENGINE_TEMPLATES.length - 1
  );
  const currentMeta = ENGINE_TEMPLATES[activeIndex] || ENGINE_TEMPLATES[0];

  const localFrame = frame % framesPerItem;

  // Render rich live motion graphics based on engine component family & name
  const renderEngineVisual = () => {
    const name = currentMeta.name.toLowerCase();

    // 1. Camera / AutoZoom
    if (name.includes("camera") || name.includes("zoom")) {
      const zoomVal = interpolate(localFrame, [0, 30, 60], [1, 1.35, 1.1]);
      const panX = interpolate(localFrame, [0, 30, 60], [0, -60, 30]);
      const panY = interpolate(localFrame, [0, 30, 60], [0, -30, 15]);

      return (
        <div style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div
            style={{
              width: "700px",
              height: "400px",
              backgroundColor: "rgba(15, 23, 42, 0.9)",
              borderRadius: "20px",
              border: "1px solid rgba(56, 189, 248, 0.4)",
              boxShadow: "0 25px 60px rgba(0,0,0,0.8)",
              transform: `scale(${zoomVal}) translate(${panX}px, ${panY}px)`,
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "#38bdf8", fontWeight: 700, fontSize: "16px" }}>🎥 CameraRig 3D Viewport</span>
              <span style={{ backgroundColor: "#38bdf820", color: "#38bdf8", padding: "4px 8px", borderRadius: "4px", fontSize: "12px" }}>
                Zoom: {zoomVal.toFixed(2)}x
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", flex: 1 }}>
              {[1, 2, 3].map((n) => (
                <div key={n} style={{ backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "10px", padding: "16px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ width: "24px", height: "24px", borderRadius: "6px", backgroundColor: "#6366f1", marginBottom: "8px" }} />
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#fff" }}>Target #{n}</div>
                  <div style={{ fontSize: "11px", color: "#94a3b8" }}>Deep Pan Focus</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    // 2. Cursor / CursorSprite
    if (name.includes("cursor")) {
      const curX = interpolate(localFrame, [0, 25, 45, 60], [100, 380, 520, 300]);
      const curY = interpolate(localFrame, [0, 25, 45, 60], [200, 180, 260, 220]);
      const isClicking = localFrame >= 24 && localFrame <= 30;

      return (
        <div style={{ width: "100%", height: "100%", position: "relative", padding: "40px", boxSizing: "border-box" }}>
          {/* Target UI Buttons */}
          <div style={{ display: "flex", gap: "20px", justifyContent: "center", marginTop: "120px" }}>
            <div style={{ padding: "14px 28px", borderRadius: "10px", backgroundColor: "#1e293b", color: "#fff", border: "1px solid rgba(255,255,255,0.1)" }}>
              Cancel
            </div>
            <div
              style={{
                padding: "14px 28px",
                borderRadius: "10px",
                backgroundColor: isClicking ? "#0284c7" : "#0284c7bb",
                color: "#fff",
                fontWeight: 700,
                transform: isClicking ? "scale(0.95)" : "scale(1)",
                boxShadow: isClicking ? "0 0 25px rgba(56, 189, 248, 0.8)" : "none",
                transition: "all 0.1s ease",
              }}
            >
              Deploy Pipeline 🚀
            </div>
          </div>

          {/* Animated Cursor */}
          <div
            style={{
              position: "absolute",
              left: `${curX}px`,
              top: `${curY}px`,
              pointerEvents: "none",
              zIndex: 100,
              filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.6))",
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M4 4L11 20L14 13L21 10L4 4Z" fill="#38bdf8" stroke="#ffffff" strokeWidth="2" strokeLinejoin="round" />
            </svg>
            {isClicking && (
              <div
                style={{
                  position: "absolute",
                  left: "-10px",
                  top: "-10px",
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  border: "2px solid #38bdf8",
                  animation: "ping 0.5s cubic-bezier(0, 0, 0.2, 1) infinite",
                }}
              />
            )}
          </div>
        </div>
      );
    }

    // 3. CountUp / Counter
    if (name.includes("count")) {
      const val = Math.round(interpolate(localFrame, [5, 50], [0, 245890], { extrapolateRight: "clamp" }));
      return (
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
          <div style={{ fontSize: "14px", color: "#34d399", fontWeight: 700, letterSpacing: "2px" }}>
            COUNTUP PRIMITIVE
          </div>
          <div style={{ fontSize: "72px", fontWeight: 900, color: "#ffffff", fontFamily: "'JetBrains Mono', monospace" }}>
            ${val.toLocaleString()}
          </div>
          <div style={{ fontSize: "16px", color: "#94a3b8" }}>Real-time Keyframe Numeric Interpolation</div>
        </div>
      );
    }

    // 4. TrafficLights / Window
    if (name.includes("traffic") || name.includes("window")) {
      return (
        <div
          style={{
            width: "580px",
            borderRadius: "16px",
            backgroundColor: "#0d1117",
            border: "1px solid rgba(255,255,255,0.12)",
            boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
            overflow: "hidden",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)", gap: "8px" }}>
            <div style={{ width: "14px", height: "14px", borderRadius: "50%", backgroundColor: "#ef4444" }} />
            <div style={{ width: "14px", height: "14px", borderRadius: "50%", backgroundColor: "#f59e0b" }} />
            <div style={{ width: "14px", height: "14px", borderRadius: "50%", backgroundColor: "#10b981" }} />
            <span style={{ marginLeft: "12px", color: "#94a3b8", fontSize: "13px", fontFamily: "monospace" }}>
              AppWindow.tsx — Clean Workspace
            </span>
          </div>
          <div style={{ padding: "32px", color: "#f8fafc", fontSize: "18px", lineHeight: "1.6" }}>
            <div style={{ color: "#38bdf8", fontWeight: 700, marginBottom: "8px" }}>Desktop Frame Active</div>
            <div style={{ color: "#cbd5e1" }}>Structured layout window with draggable zones and responsive docking.</div>
          </div>
        </div>
      );
    }

    // 5. Default App UI / Primitive Simulation
    return (
      <div
        style={{
          width: "560px",
          padding: "32px",
          backgroundColor: "rgba(15, 23, 42, 0.85)",
          backdropFilter: "blur(20px)",
          borderRadius: "20px",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "14px",
        }}
      >
        <div style={{ fontSize: "13px", color: "#818cf8", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase" }}>
          Cinematic Engine • {currentMeta.family.toUpperCase()}
        </div>
        <h2 style={{ fontSize: "38px", fontWeight: 900, margin: 0, color: "#ffffff" }}>
          {currentMeta.name}
        </h2>
        <p style={{ fontSize: "16px", color: "#cbd5e1", margin: 0 }}>
          High-performance motion primitive with frame-accurate timing.
        </p>
        <div
          style={{
            marginTop: "8px",
            padding: "8px 20px",
            borderRadius: "8px",
            backgroundColor: "rgba(99, 102, 241, 0.15)",
            color: "#a5b4fc",
            fontSize: "13px",
            fontWeight: 700,
            border: "1px solid rgba(99, 102, 241, 0.4)",
          }}
        >
          Interactive Engine Rig Active
        </div>
      </div>
    );
  };

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
            padding: "40px",
            background: "radial-gradient(circle at center, #1e1b4b 0%, #030712 100%)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {renderEngineVisual()}
        </div>
      </ShowcaseCard>

      <DebugOverlay
        meta={currentMeta}
        sectionName="Cinematic Engine"
        currentIndex={activeIndex}
        totalCount={ENGINE_TEMPLATES.length}
      />
    </AbsoluteFill>
  );
};
