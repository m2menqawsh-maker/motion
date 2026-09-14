import React from "react";
import { TimelineSteps } from "../../remotion-app/src/remotion/scenes/timeline-steps";
import type { TemplateProps } from "../../../registry/types";

export const TimelineStepsWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TimelineSteps title={content?.text || undefined} />
  );
};
