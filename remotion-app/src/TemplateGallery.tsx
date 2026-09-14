import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

export const TemplateGallery: React.FC = () => {
  // Get all registered templates
  const templates = Object.values(TEMPLATE_REGISTRY);

  // CSS Grid for a 5-column layout
  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a", padding: 40, fontFamily: "sans-serif" }}>
      <div style={{ textAlign: "center", color: "#38bdf8", fontSize: 60, fontWeight: "bold", marginBottom: 40 }}>
        ✨ معرض القوالب والانتقالات ({templates.length} قوالب) ✨
      </div>
      
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "20px",
          width: "100%",
          height: "100%",
        }}
      >
        {templates.map((template, index) => {
          const Component = template.component;
          // Some generic props to make elements visible
          const surface = {
            text: "TEXT",
            color: "#fff",
            background: "#1e293b",
            animation: { type: "linear" }
          };
          const content = {
            text: "LIVE PREVIEW",
            images: ["https://picsum.photos/300/300?1", "https://picsum.photos/300/300?2"],
            lines: ["const a = 1;", "console.log(a);"]
          };

          return (
            <div
              key={template.id}
              style={{
                backgroundColor: "#1e293b",
                borderRadius: 20,
                border: "2px solid #334155",
                overflow: "hidden",
                display: "flex",
                flexDirection: "column",
                position: "relative"
              }}
            >
              {/* Header */}
              <div style={{ backgroundColor: "#334155", padding: "10px", color: "#cbd5e1", fontSize: 24, fontWeight: "bold", textAlign: "center" }}>
                {template.label.en}
              </div>
              
              {/* Component Preview Container */}
              <div style={{ flex: 1, position: "relative", minHeight: 250, display: "flex", alignItems: "center", justifyContent: "center" }}>
                 <Sequence durationInFrames={300}>
                    <Component surface={surface} content={content} />
                 </Sequence>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
