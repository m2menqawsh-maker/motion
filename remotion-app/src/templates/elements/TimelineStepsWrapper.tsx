import React from "react";
import { TimelineSteps } from "@/remotion/scenes/timeline-steps";
import type { TemplateProps } from "@registry/types";

export const TimelineStepsWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <TimelineSteps  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
