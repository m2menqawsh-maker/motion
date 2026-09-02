import React, { Component, ErrorInfo, ReactNode } from "react";
import { TemplateMeta } from "./types";

interface Props {
  meta: TemplateMeta;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ShowcaseErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.warn(`[ShowcaseErrorBoundary] Error in ${this.props.meta.name}:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            width: "100%",
            height: "100%",
            backgroundColor: "#160b0b",
            border: "2px dashed #ef4444",
            borderRadius: "12px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            color: "#fca5a5",
            fontFamily: "system-ui, sans-serif",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: "28px", fontWeight: "bold", color: "#ef4444", marginBottom: "8px" }}>
            UNAVAILABLE
          </div>
          <div style={{ fontSize: "18px", color: "#f87171", marginBottom: "4px" }}>
            Template: <strong>{this.props.meta.name}</strong> ({this.props.meta.type})
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginBottom: "8px", maxWidth: "80%" }}>
            File: {this.props.meta.path}
          </div>
          <div
            style={{
              fontSize: "12px",
              backgroundColor: "rgba(0,0,0,0.5)",
              padding: "8px 12px",
              borderRadius: "6px",
              color: "#f87171",
              maxWidth: "90%",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            Reason: {this.state.error?.message || "Runtime execution error"}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
