import React, { Component, ErrorInfo } from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

class ErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Gallery Component Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: "#ef4444", padding: 20, textAlign: "center", fontSize: 18, fontFamily: "monospace" }}>
          ⚠️ Error rendering preview<br/>
          <span style={{ fontSize: 14, color: "#fca5a5" }}>{this.state.error?.message}</span>
        </div>
      );
    }
    return this.props.children;
  }
}

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
                    <ErrorBoundary>
                      <Component surface={surface} content={content} />
                    </ErrorBoundary>
                 </Sequence>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
