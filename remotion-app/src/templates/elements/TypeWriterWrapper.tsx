import React from "react";
import { TypeWriter } from "remotion-bits";

export const TypeWriterWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const text = content?.text || surface?.text || "Loading systems...";
  const animProps = surface?.animation || {};
  
  // TypeWriter might take 'text' directly or as children.
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <TypeWriter
 {...template_props}         text={text}
        {...animProps}
        style={{
          color: surface?.color || "#00ff00",
          fontSize: surface?.fontSize || 60,
          fontFamily: surface?.fontFamily || "monospace",
        }}
      />
    </div>
  </div>
  );
};
