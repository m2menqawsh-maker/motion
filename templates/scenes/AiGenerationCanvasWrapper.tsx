import React from "react";
import { AiGenerationCanvas } from "../../remotion-app/src/compositions/ai-generation-canvas";
import type { TemplateProps } from "../../../registry/types";

export const AiGenerationCanvasWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <AiGenerationCanvas  {...template_props}  />
  </div>
  );
};
