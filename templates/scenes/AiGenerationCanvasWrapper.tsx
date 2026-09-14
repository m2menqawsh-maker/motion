import React from "react";
import { AiGenerationCanvas } from "../../remotion-app/src/compositions/ai-generation-canvas";
import type { TemplateProps } from "../../../registry/types";

export const AiGenerationCanvasWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <AiGenerationCanvas  />
  );
};
