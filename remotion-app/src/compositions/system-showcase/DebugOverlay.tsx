import React from "react";
import { TemplateMeta } from "./types";

interface DebugOverlayProps {
  meta?: TemplateMeta;
  visible?: boolean;
  sectionName?: string;
  currentIndex?: number;
  totalCount?: number;
}

export const SHOW_DEBUG = true;

export const DebugOverlay: React.FC<DebugOverlayProps> = ({
  meta,
  visible = SHOW_DEBUG,
  sectionName,
  currentIndex,
  totalCount,
}) => {
  if (!visible || !meta) return null;

  const qualityColor =
    meta.quality === "A" ? "#10b981" : meta.quality === "B" ? "#3b82f6" : "#f59e0b";

  return (
    <div
      style={{
        position: "absolute",
        top: "24px",
        right: "24px",
        backgroundColor: "rgba(10, 14, 26, 0.88)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.12)",
        borderRadius: "10px",
        padding: "12px 18px",
        color: "#f8fafc",
        fontFamily: "'JetBrains Mono', monospace, sans-serif",
        fontSize: "12px",
        zIndex: 1000,
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        minWidth: "260px",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          paddingBottom: "6px",
          marginBottom: "8px",
        }}
      >
        <span style={{ fontWeight: 700, color: "#38bdf8", fontSize: "13px" }}>
          {meta.name}
        </span>
        <span
          style={{
            backgroundColor: qualityColor,
            color: "#000",
            fontWeight: 800,
            padding: "1px 6px",
            borderRadius: "4px",
            fontSize: "10px",
          }}
        >
          Q: {meta.quality}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 8px", color: "#94a3b8" }}>
        <span>Type:</span>
        <span style={{ color: "#e2e8f0" }}>{meta.type}</span>

        <span>Category:</span>
        <span style={{ color: "#e2e8f0" }}>{meta.family}</span>

        <span>RTL:</span>
        <span style={{ color: meta.rtl_ready ? "#10b981" : "#64748b" }}>
          {meta.rtl_ready ? "true (RTL Ready)" : "false"}
        </span>

        <span>Source:</span>
        <span style={{ color: "#e2e8f0" }}>{meta.source}</span>

        {meta.use_cases && meta.use_cases.length > 0 && (
          <>
            <span>Use Cases:</span>
            <span style={{ color: "#cbd5e1" }}>{meta.use_cases.join(", ")}</span>
          </>
        )}

        {meta.intents && meta.intents.length > 0 && (
          <>
            <span>Intent:</span>
            <span style={{ color: "#cbd5e1" }}>{meta.intents.join(", ")}</span>
          </>
        )}

        {sectionName && (
          <>
            <span>Section:</span>
            <span style={{ color: "#f59e0b" }}>
              {sectionName} {currentIndex !== undefined ? `(${currentIndex + 1}/${totalCount})` : ""}
            </span>
          </>
        )}
      </div>
    </div>
  );
};
