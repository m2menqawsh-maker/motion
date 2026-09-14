import React from "react";
import { DragDropFlow } from "../../remotion-app/src/remotion/scenes/drag-drop-flow";
import type { TemplateProps } from "../../../registry/types";

export const DragDropFlowWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DragDropFlow label={content?.text || undefined} />
  );
};
