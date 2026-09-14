import React from "react";
import { RoadmapLanes } from "../../remotion-app/src/remotion/scenes/roadmap-lanes";
import type { TemplateProps } from "../../../registry/types";

export const RoadmapLanesWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <RoadmapLanes title={content?.text || undefined} />
  );
};
