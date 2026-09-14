import React from "react";
import { AnimatedBarChart } from "../../remotion-app/src/remotion/scenes/animated-bar-chart";
import type { TemplateProps } from "../../../registry/types";

export const AnimatedBarChartWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <AnimatedBarChart title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
