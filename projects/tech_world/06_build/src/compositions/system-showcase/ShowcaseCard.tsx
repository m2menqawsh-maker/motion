import React from "react";
import { TemplateMeta } from "./types";
import { ShowcaseErrorBoundary } from "./ShowcaseErrorBoundary";

interface ShowcaseCardProps {
  meta: TemplateMeta;
  children: React.ReactNode;
  isUtility?: boolean;
  failureReason?: string;
}

export const ShowcaseCard: React.FC<ShowcaseCardProps> = ({
  meta,
  children,
  isUtility,
  failureReason,
}) => {
  const qualityBg =
    meta.quality === "A"
      ? "rgba(16, 185, 129, 0.15)"
      : meta.quality === "B"
      ? "rgba(59, 130, 246, 0.15)"
      : "rgba(245, 158, 11, 0.15)";
  const qualityColor =
    meta.quality === "A" ? "#34d399" : meta.quality === "B" ? "#60a5fa" : "#fbbf24";

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#070913",
        color: "#f8fafc",
        fontFamily: "'Inter', system-ui, sans-serif",
        position: "relative",
        overflow: "hidden",
        boxSizing: "border-box",
        padding: "32px",
      }}
    >
      {/* Header Info Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
          paddingBottom: "16px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
          <h2
            style={{
              margin: 0,
              fontSize: "32px",
              fontWeight: 800,
              letterSpacing: "-0.5px",
              background: "linear-gradient(135deg, #ffffff 0%, #94a3b8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {meta.name}
          </h2>
          <span
            style={{
              fontSize: "14px",
              color: "#64748b",
              textTransform: "uppercase",
              letterSpacing: "1px",
              fontWeight: 600,
            }}
          >
            {meta.type} • {meta.family}
          </span>
        </div>

        {/* Badges */}
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {meta.rtl_ready && (
            <span
              style={{
                backgroundColor: "rgba(168, 85, 247, 0.15)",
                color: "#c084fc",
                border: "1px solid rgba(168, 85, 247, 0.3)",
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 700,
              }}
            >
              RTL Ready
            </span>
          )}

          <span
            style={{
              backgroundColor: qualityBg,
              color: qualityColor,
              border: `1px solid ${qualityColor}40`,
              padding: "4px 10px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 700,
            }}
          >
            Quality {meta.quality}
          </span>

          <span
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.06)",
              color: "#94a3b8",
              padding: "4px 10px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
            }}
          >
            {meta.source}
          </span>
        </div>
      </div>

      {/* Main Preview Container */}
      <div
        key={meta.id}
        style={{
          flex: 1,
          width: "100%",
          position: "relative",
          borderRadius: "16px",
          overflow: "hidden",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          backgroundColor: "#0b0f19",
          boxShadow: "0 20px 50px rgba(0,0,0,0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {isUtility ? (
          <div
            style={{
              padding: "32px",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "16px",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                border: "1px solid rgba(56, 189, 248, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "28px",
              }}
            >
              ⚙️
            </div>
            <div>
              <h3 style={{ margin: "0 0 8px 0", fontSize: "22px", color: "#38bdf8" }}>
                Engine Utility Module
              </h3>
              <p style={{ margin: 0, color: "#94a3b8", fontSize: "14px", maxWidth: "500px" }}>
                This is a core TypeScript utility/schema module used programmatically by the engine and cinematic timeline.
              </p>
            </div>
            <div
              style={{
                backgroundColor: "rgba(0,0,0,0.4)",
                padding: "8px 16px",
                borderRadius: "8px",
                fontFamily: "monospace",
                fontSize: "12px",
                color: "#64748b",
              }}
            >
              {meta.path}
            </div>
          </div>
        ) : failureReason ? (
          <div
            style={{
              padding: "32px",
              textAlign: "center",
              color: "#f87171",
            }}
          >
            <h3 style={{ margin: "0 0 8px 0", fontSize: "22px", color: "#ef4444" }}>
              UNAVAILABLE
            </h3>
            <p style={{ margin: "0 0 12px 0", color: "#94a3b8", fontSize: "14px" }}>
              {failureReason}
            </p>
            <code style={{ fontSize: "12px", color: "#fca5a5" }}>{meta.path}</code>
          </div>
        ) : (
          <ShowcaseErrorBoundary meta={meta}>{children}</ShowcaseErrorBoundary>
        )}
      </div>

      {/* Footer Meta & Use cases */}
      <div
        style={{
          marginTop: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "13px",
          color: "#64748b",
        }}
      >
        <div style={{ display: "flex", gap: "16px" }}>
          <span>
            Use Case: <strong style={{ color: "#cbd5e1" }}>{meta.use_cases.join(", ") || "General"}</strong>
          </span>
          <span>
            Intent: <strong style={{ color: "#cbd5e1" }}>{meta.intents.join(", ") || "Visual"}</strong>
          </span>
        </div>
        <div style={{ fontFamily: "monospace", fontSize: "12px", color: "#475569" }}>
          {meta.path}
        </div>
      </div>
    </div>
  );
};
